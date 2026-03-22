# src/api/webhook_routes.py
"""Webhook routes for Dropbox change detection."""

import logging
from fastapi import APIRouter, Request, Response, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


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

    # Auto-fetch changes using stored token
    from src.sync.change_tracker import auto_fetch_changes
    import asyncio
    try:
        changes = await auto_fetch_changes()
        logger.info(f"Auto-fetched {len(changes)} changes from webhook")
    except Exception as e:
        logger.error(f"Auto-fetch in webhook failed: {e}")
        changes = []

    # Always return 200 OK to acknowledge receipt
    return {"status": "ok", "accounts_notified": len(result.accounts), "changes_fetched": len(changes)}


@router.get("/sync/status")
async def sync_status():
    """
    Get current sync status.

    Returns:
    - has_cursor: Whether we have a sync cursor
    - last_sync: Timestamp of last sync
    - pending_count: Number of pending changes
    """
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
async def sync_pending():
    """
    Get pending changes that haven't been processed yet.
    """
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
    from src.sync.change_tracker import mark_changes_processed

    body = await request.json()
    paths = body.get("paths")

    mark_changes_processed(paths)

    return {"status": "ok", "message": "Changes marked as processed"}
