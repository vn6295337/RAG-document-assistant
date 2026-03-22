# src/sync/change_tracker.py
"""Track file changes using Dropbox delta/cursor API."""

import logging
import os
import json
import httpx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Type of file change."""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"


@dataclass
class FileChange:
    """Represents a single file change."""
    path: str
    change_type: ChangeType
    file_id: Optional[str] = None
    content_hash: Optional[str] = None
    modified_at: Optional[str] = None
    size: Optional[int] = None


@dataclass
class SyncState:
    """Current sync state."""
    cursor: Optional[str] = None
    last_sync: Optional[str] = None
    pending_changes: List[FileChange] = field(default_factory=list)
    has_more: bool = False


class ChangeTracker:
    """
    Tracks file changes using Dropbox's delta sync API.

    Flow:
    1. Initial: Call list_folder to get first cursor
    2. On webhook: Call list_folder/continue with cursor
    3. Get changes since last cursor
    4. Update cursor for next sync

    Cursor storage:
    - SSM Parameter Store (production)
    - Local file (development)
    """

    def __init__(self, state_path: str = None):
        """
        Initialize change tracker.

        Args:
            state_path: Path to store sync state (None = SSM)
        """
        self.state_path = state_path or os.getenv(
            "SYNC_STATE_PATH",
            "/tmp/dropbox_sync_state.json"
        )
        self._state: Optional[SyncState] = None
        self._access_token: Optional[str] = None
        self._load_state()

    def _load_state(self):
        """Load sync state from storage."""
        try:
            if os.path.exists(self.state_path):
                with open(self.state_path, "r") as f:
                    data = json.load(f)
                    self._state = SyncState(
                        cursor=data.get("cursor"),
                        last_sync=data.get("last_sync"),
                        pending_changes=[
                            FileChange(
                                path=c["path"],
                                change_type=ChangeType(c["change_type"]),
                                file_id=c.get("file_id"),
                                content_hash=c.get("content_hash"),
                                modified_at=c.get("modified_at"),
                                size=c.get("size")
                            )
                            for c in data.get("pending_changes", [])
                        ],
                        has_more=data.get("has_more", False)
                    )
                    self._access_token = data.get("access_token")
            else:
                self._state = SyncState()
        except Exception as e:
            logger.warning(f"Failed to load sync state: {e}")
            self._state = SyncState()

    def _save_state(self):
        """Save sync state to storage."""
        try:
            data = {
                "cursor": self._state.cursor,
                "last_sync": self._state.last_sync,
                "access_token": self._access_token,
                "pending_changes": [
                    {
                        "path": c.path,
                        "change_type": c.change_type.value,
                        "file_id": c.file_id,
                        "content_hash": c.content_hash,
                        "modified_at": c.modified_at,
                        "size": c.size
                    }
                    for c in self._state.pending_changes
                ],
                "has_more": self._state.has_more
            }
            with open(self.state_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save sync state: {e}")

    async def initialize_cursor(
        self,
        access_token: str,
        path: str = ""
    ) -> str:
        """
        Get initial cursor for a folder.

        Args:
            access_token: Dropbox OAuth token
            path: Folder path (empty = root)

        Returns:
            Cursor string for future sync
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.dropboxapi.com/2/files/list_folder",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "path": path,
                    "recursive": True,
                    "include_deleted": True
                }
            )

            if response.status_code != 200:
                logger.error(f"Failed to initialize cursor: {response.text}")
                raise Exception(f"Dropbox API error: {response.status_code}")

            data = response.json()
            cursor = data.get("cursor")

            self._state.cursor = cursor
            self._state.last_sync = datetime.utcnow().isoformat()
            self._access_token = access_token  # Store for auto-sync
            self._save_state()

            logger.info(f"Initialized sync cursor")
            return cursor

    async def get_changes(
        self,
        access_token: str
    ) -> List[FileChange]:
        """
        Get changes since last sync using cursor.

        Args:
            access_token: Dropbox OAuth token

        Returns:
            List of FileChange objects
        """
        if not self._state.cursor:
            logger.warning("No cursor, need to initialize first")
            await self.initialize_cursor(access_token)
            return []  # First sync, no changes to report

        changes = []
        has_more = True

        async with httpx.AsyncClient() as client:
            while has_more:
                response = await client.post(
                    "https://api.dropboxapi.com/2/files/list_folder/continue",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json"
                    },
                    json={"cursor": self._state.cursor}
                )

                if response.status_code != 200:
                    logger.error(f"Failed to get changes: {response.text}")
                    raise Exception(f"Dropbox API error: {response.status_code}")

                data = response.json()

                # Parse entries
                for entry in data.get("entries", []):
                    tag = entry.get(".tag")
                    path = entry.get("path_display", entry.get("path_lower", ""))

                    if tag == "deleted":
                        changes.append(FileChange(
                            path=path,
                            change_type=ChangeType.DELETED
                        ))
                    elif tag == "file":
                        # Check if it's a supported document type
                        if self._is_supported_file(path):
                            # Determine if added or modified
                            # (would need to compare with index, simplified here)
                            changes.append(FileChange(
                                path=path,
                                change_type=ChangeType.MODIFIED,  # Conservative
                                file_id=entry.get("id"),
                                content_hash=entry.get("content_hash"),
                                modified_at=entry.get("server_modified"),
                                size=entry.get("size")
                            ))

                # Update cursor
                self._state.cursor = data.get("cursor")
                has_more = data.get("has_more", False)

        # Update state
        self._state.last_sync = datetime.utcnow().isoformat()
        self._state.pending_changes.extend(changes)
        self._state.has_more = False
        self._save_state()

        logger.info(f"Found {len(changes)} changes since last sync")
        return changes

    def _is_supported_file(self, path: str) -> bool:
        """Check if file type is supported for indexing."""
        supported_extensions = {
            '.pdf', '.docx', '.doc', '.pptx', '.ppt',
            '.txt', '.md', '.rtf', '.html', '.htm'
        }
        ext = os.path.splitext(path.lower())[1]
        return ext in supported_extensions

    def get_pending_changes(self) -> List[FileChange]:
        """Get list of pending changes not yet processed."""
        return self._state.pending_changes.copy()

    def mark_processed(self, paths: List[str] = None):
        """
        Mark changes as processed.

        Args:
            paths: Specific paths to mark, or None for all
        """
        if paths is None:
            self._state.pending_changes = []
        else:
            self._state.pending_changes = [
                c for c in self._state.pending_changes
                if c.path not in paths
            ]
        self._save_state()

    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status."""
        return {
            "has_cursor": self._state.cursor is not None,
            "last_sync": self._state.last_sync,
            "pending_count": len(self._state.pending_changes),
            "pending_by_type": {
                "added": sum(1 for c in self._state.pending_changes if c.change_type == ChangeType.ADDED),
                "modified": sum(1 for c in self._state.pending_changes if c.change_type == ChangeType.MODIFIED),
                "deleted": sum(1 for c in self._state.pending_changes if c.change_type == ChangeType.DELETED)
            }
        }


# Module-level singleton
_tracker = None


def get_change_tracker() -> ChangeTracker:
    """Get singleton change tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = ChangeTracker()
    return _tracker


def get_pending_changes() -> List[FileChange]:
    """Get pending changes (convenience function)."""
    return get_change_tracker().get_pending_changes()


def mark_changes_processed(paths: List[str] = None):
    """Mark changes as processed (convenience function)."""
    get_change_tracker().mark_processed(paths)


async def auto_fetch_changes() -> List[FileChange]:
    """
    Auto-fetch changes using stored access token.
    Called by webhook handler when notification received.
    """
    tracker = get_change_tracker()
    if not tracker._access_token:
        logger.warning("No stored access token, cannot auto-fetch changes")
        return []

    try:
        changes = await tracker.get_changes(tracker._access_token)
        logger.info(f"Auto-fetched {len(changes)} changes")
        return changes
    except Exception as e:
        logger.error(f"Auto-fetch failed: {e}")
        return []
