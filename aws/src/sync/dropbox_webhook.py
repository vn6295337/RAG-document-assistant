# src/sync/dropbox_webhook.py
"""Dropbox webhook handler for automatic change detection."""

import logging
import hmac
import hashlib
import os
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WebhookVerification:
    """Result of webhook verification challenge."""
    is_valid: bool
    challenge: str
    error: Optional[str] = None


@dataclass
class ChangeNotification:
    """Parsed webhook notification."""
    accounts: List[str]  # Dropbox account IDs with changes
    is_valid: bool
    error: Optional[str] = None


class DropboxWebhookHandler:
    """
    Handles Dropbox webhook verification and notifications.

    Dropbox Webhook Flow:
    1. Register webhook URL in Dropbox App Console
    2. Dropbox sends GET with ?challenge=xxx for verification
    3. Return the challenge string to verify
    4. Dropbox sends POST when files change (contains account IDs)
    5. Fetch actual changes using list_folder/continue with cursor
    """

    def __init__(self, app_secret: str = None):
        """
        Initialize webhook handler.

        Args:
            app_secret: Dropbox app secret for signature verification
        """
        self.app_secret = app_secret or os.getenv("DROPBOX_APP_SECRET", "")

    def verify_challenge(self, challenge: str) -> WebhookVerification:
        """
        Handle Dropbox webhook verification (GET request).

        Dropbox sends: GET /webhook?challenge=random_string
        We must respond with the challenge string.

        Args:
            challenge: The challenge string from Dropbox

        Returns:
            WebhookVerification with challenge to echo back
        """
        if not challenge:
            return WebhookVerification(
                is_valid=False,
                challenge="",
                error="No challenge parameter provided"
            )

        logger.info(f"Webhook verification challenge received")
        return WebhookVerification(
            is_valid=True,
            challenge=challenge
        )

    def verify_signature(self, body: bytes, signature: str) -> bool:
        """
        Verify webhook signature using HMAC-SHA256.

        Args:
            body: Raw request body bytes
            signature: X-Dropbox-Signature header value

        Returns:
            True if signature is valid
        """
        if not self.app_secret:
            if os.getenv("ENV", "development") == "production":
                logger.error("DROPBOX_APP_SECRET missing in production")
                return False
            logger.warning("No app secret configured, skipping signature verification")
            return True  # Allow in non-production only

        if not signature:
            logger.warning("No signature header in webhook request")
            return False

        expected = hmac.new(
            self.app_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    def parse_notification(
        self,
        body: bytes,
        signature: str = None
    ) -> ChangeNotification:
        """
        Parse webhook notification (POST request).

        Dropbox sends JSON with account IDs that have changes:
        {
            "list_folder": {
                "accounts": ["dbid:AAH4f99T0taONIb-OurWxbNQ6ywGRopQngc"]
            },
            "delta": {
                "users": [12345678]
            }
        }

        Args:
            body: Raw request body
            signature: X-Dropbox-Signature header

        Returns:
            ChangeNotification with account IDs
        """
        import json

        # Verify signature if app secret is configured
        if not self.verify_signature(body, signature):
            return ChangeNotification(
                accounts=[],
                is_valid=False,
                error="Invalid or missing webhook signature"
            )

        try:
            data = json.loads(body.decode('utf-8'))

            accounts = []

            # Extract accounts from list_folder notification
            if "list_folder" in data:
                accounts.extend(data["list_folder"].get("accounts", []))

            # Extract user IDs from delta notification (legacy)
            if "delta" in data:
                users = data["delta"].get("users", [])
                accounts.extend([str(u) for u in users])

            logger.info(f"Webhook notification: {len(accounts)} account(s) with changes")

            return ChangeNotification(
                accounts=accounts,
                is_valid=True
            )

        except json.JSONDecodeError as e:
            return ChangeNotification(
                accounts=[],
                is_valid=False,
                error=f"Invalid JSON: {str(e)}"
            )
        except Exception as e:
            return ChangeNotification(
                accounts=[],
                is_valid=False,
                error=str(e)
            )


# Module-level singleton
_handler = None


def get_webhook_handler() -> DropboxWebhookHandler:
    """Get singleton webhook handler instance."""
    global _handler
    if _handler is None:
        _handler = DropboxWebhookHandler()
    return _handler


def verify_webhook(challenge: str) -> WebhookVerification:
    """Verify webhook challenge (convenience function)."""
    return get_webhook_handler().verify_challenge(challenge)


def handle_webhook_notification(
    body: bytes,
    signature: str = None
) -> ChangeNotification:
    """Handle webhook notification (convenience function)."""
    return get_webhook_handler().parse_notification(body, signature)
