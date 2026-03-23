# src/api/webhook_routes.py
"""Webhook routes for Dropbox change detection."""

import logging
import os
from fastapi import APIRouter, Request, Response, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


def _require_sync_admin(request: Request):
    """Protect operational sync endpoints with a shared admin token."""
    expected_token = os.getenv("SYNC_ADMIN_TOKEN")
    if not expected_token:
        raise HTTPException(status_code=503, detail="SYNC_ADMIN_TOKEN not configured")

    provided_token = request.headers.get("X-Admin-Token", "")
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        provided_token = auth_header.split(" ", 1)[1].strip()

    if provided_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.get("/dropbox")
async def dropbox_webhook_verify(request: Request):
    """
    Dropbox webhook verification endpoint.

    Dropbox sends: GET /webhook/dropbox?challenge=random_string
    We must return the challenge string in plain text.
    """
    from src.sync.dropbox_webhook import verify_webhook

    challenge = request.query_params.get("challenge", "")

    if not challenge:
        raise HTTPException(status_code=400, detail="Missing challenge parameter")

    result = verify_webhook(challenge)

    if not result.is_valid:
        raise HTTPException(status_code=400, detail=result.error)

    # Return challenge as plain text (required by Dropbox)
    return Response(
        content=result.challenge,
        media_type="text/plain"
    )


@router.post("/dropbox")
async def dropbox_webhook_notification(request: Request):
    """
    Dropbox webhook notification endpoint.

    When files change, Dropbox sends a POST with account IDs.
    We record the notification and respond with 200 OK.

    Note: We must respond within 10 seconds, so actual sync
    happens asynchronously via get_changes().
    """
    from src.sync.dropbox_webhook import handle_webhook_notification

    # Get raw body and signature
    body = await request.body()
    signature = request.headers.get("X-Dropbox-Signature", "")

    result = handle_webhook_notification(body, signature)

    if not result.is_valid:
        logger.error(f"Invalid webhook notification: {result.error}")
        raise HTTPException(status_code=400, detail=result.error)

    # Log the accounts with changes
    if result.accounts:
        logger.info(f"Dropbox change notification for accounts: {result.accounts}")

    # Acknowledge immediately. Dropbox webhooks do not include an OAuth token,
    # so actual delta fetching must happen through an authenticated sync call.
    return {
        "status": "ok",
        "accounts_notified": len(result.accounts),
        "message": "Notification accepted. Fetch changes via authenticated sync endpoints."
    }


async def _send_change_notification(changes):
    """Send SNS email notification for file changes."""
    import boto3
    import os

    sns_topic = os.getenv("SNS_TOPIC_ARN", "arn:aws:sns:us-east-1:691210491730:rag-dropbox-changes")

    try:
        sns = boto3.client('sns', region_name=os.getenv('AWS_REGION', 'us-east-1'))

        # Build message
        change_list = "\n".join([
            f"  - [{c.change_type.value.upper()}] {c.path}"
            for c in changes[:10]  # Limit to 10 in email
        ])

        if len(changes) > 10:
            change_list += f"\n  ... and {len(changes) - 10} more"

        message = f"""Dropbox File Changes Detected

{len(changes)} file(s) changed:
{change_list}

These files may need re-indexing for your RAG system.

--
RAG Document Assistant
"""

        sns.publish(
            TopicArn=sns_topic,
            Subject=f"Dropbox: {len(changes)} file(s) changed",
            Message=message
        )
        logger.info(f"Sent SNS notification for {len(changes)} changes")
    except Exception as e:
        logger.error(f"Failed to send SNS notification: {e}")


@router.get("/sync/status")
async def sync_status(request: Request):
    """
    Get current sync status.

    Returns:
    - has_cursor: Whether we have a sync cursor
    - last_sync: Timestamp of last sync
    - pending_count: Number of pending changes
    """
    _require_sync_admin(request)
    from src.sync.change_tracker import get_change_tracker

    tracker = get_change_tracker()
    return tracker.get_sync_status()


@router.post("/sync/init")
async def sync_init(request: Request):
    """
    Initialize sync cursor for a Dropbox account.

    Must be called once before webhooks will detect changes.

    Request body:
    - access_token: Dropbox OAuth token
    - path: Folder path to sync (empty = root)
    """
    _require_sync_admin(request)
    from src.sync.change_tracker import get_change_tracker

    body = await request.json()
    access_token = body.get("access_token")
    path = body.get("path", "")

    if not access_token:
        raise HTTPException(status_code=400, detail="access_token required")

    tracker = get_change_tracker()

    try:
        cursor = await tracker.initialize_cursor(access_token, path)
        return {
            "status": "ok",
            "message": "Sync cursor initialized",
            "cursor_set": True
        }
    except Exception as e:
        logger.error(f"Failed to initialize sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync/check")
async def sync_check(request: Request):
    """
    Check for changes since last sync.

    Request body:
    - access_token: Dropbox OAuth token

    Returns list of file changes.
    """
    _require_sync_admin(request)
    from src.sync.change_tracker import get_change_tracker

    body = await request.json()
    access_token = body.get("access_token")

    if not access_token:
        raise HTTPException(status_code=400, detail="access_token required")

    tracker = get_change_tracker()

    try:
        changes = await tracker.get_changes(access_token)
        return {
            "status": "ok",
            "changes": [
                {
                    "path": c.path,
                    "type": c.change_type.value,
                    "file_id": c.file_id,
                    "content_hash": c.content_hash,
                    "modified_at": c.modified_at
                }
                for c in changes
            ],
            "total_changes": len(changes)
        }
    except Exception as e:
        logger.error(f"Failed to check changes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/pending")
async def sync_pending(request: Request):
    """
    Get pending changes that haven't been processed yet.
    """
    _require_sync_admin(request)
    from src.sync.change_tracker import get_pending_changes

    changes = get_pending_changes()
    return {
        "pending": [
            {
                "path": c.path,
                "type": c.change_type.value,
                "file_id": c.file_id
            }
            for c in changes
        ],
        "count": len(changes)
    }


@router.post("/sync/mark-processed")
async def sync_mark_processed(request: Request):
    """
    Mark changes as processed after re-indexing.

    Request body:
    - paths: List of file paths to mark as processed (optional, all if empty)
    """
    _require_sync_admin(request)
    from src.sync.change_tracker import mark_changes_processed

    body = await request.json()
    paths = body.get("paths")

    mark_changes_processed(paths)

    return {"status": "ok", "message": "Changes marked as processed"}
