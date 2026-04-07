"""MediaLibrary — metadata management for the admin media library."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
import uuid

from lexigram.admin.media.models import MediaItem, MediaPage


class MediaLibrary:
    """Manages the metadata layer for the admin media library.

    Args:
        storage: Optional storage service instance (used for
            :meth:`delete_storage`).
        default_folder: Default folder prefix for new uploads.
    """

    def __init__(
        self,
        storage: Any = None,
        default_folder: str = "uploads",
    ) -> None:
        self._storage = storage
        self._default_folder = default_folder
        self._items: dict[str, MediaItem] = {}

    # ------------------------------------------------------------------
    # Register / update
    # ------------------------------------------------------------------

    async def register(
        self,
        path: str,
        *,
        filename: str = "",
        mime_type: str = "",
        size_bytes: int = 0,
        uploaded_by: str = "system",
        alt_text: str = "",
        caption: str = "",
        tags: list[str] | None = None,
        width: int = 0,
        height: int = 0,
        item_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MediaItem:
        """Register a newly uploaded file in the library.

        Args:
            path: Storage path.
            filename: Human-readable filename.
            mime_type: MIME type.
            size_bytes: File size in bytes.
            uploaded_by: Uploader user ID.
            alt_text: Accessible alt text.
            caption: Optional caption.
            tags: Categorisation tags.
            width: Image width (pixels).
            height: Image height (pixels).
            item_id: Explicit ID (auto-generated if omitted).
            metadata: Extra metadata.

        Returns:
            The registered :class:`MediaItem`.
        """
        folder = "/".join(path.split("/")[:-1]) if "/" in path else self._default_folder
        if not filename:
            filename = path.rsplit("/", maxsplit=1)[-1]

        item = MediaItem(
            item_id=item_id or str(uuid.uuid4())[:12],
            path=path,
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            folder=folder,
            uploaded_by=uploaded_by,
            alt_text=alt_text,
            caption=caption,
            tags=tags or [],
            width=width,
            height=height,
            metadata=metadata or {},
        )
        self._items[item.item_id] = item
        return item

    def update(
        self,
        item_id: str,
        *,
        alt_text: str | None = None,
        caption: str | None = None,
        tags: list[str] | None = None,
    ) -> MediaItem | None:
        """Update the metadata of a registered item.

        Args:
            item_id: Library item ID.
            alt_text: New alt text (``None`` = no change).
            caption: New caption.
            tags: New tags list.

        Returns:
            Updated :class:`MediaItem` or ``None`` if not found.
        """
        item = self._items.get(item_id)
        if item is None:
            return None
        if alt_text is not None:
            item.alt_text = alt_text
        if caption is not None:
            item.caption = caption
        if tags is not None:
            item.tags = list(tags)
        return item

    # ------------------------------------------------------------------
    # Browse
    # ------------------------------------------------------------------

    def get(self, item_id: str) -> MediaItem | None:
        """Return a single item by ID.

        Args:
            item_id: Library item ID.
        """
        return self._items.get(item_id)

    def list_folder(
        self,
        folder: str = "",
        *,
        page: int = 1,
        page_size: int = 24,
        include_deleted: bool = False,
    ) -> MediaPage:
        """Return a paginated list of items in *folder*.

        Args:
            folder: Folder path prefix (empty = all items).
            page: 1-based page number.
            page_size: Items per page.
            include_deleted: When ``True``, soft-deleted items are included.

        Returns:
            :class:`MediaPage` with items for the requested page.
        """
        all_items = [
            item
            for item in self._items.values()
            if (not folder or item.folder.startswith(folder))
            and (include_deleted or not item.is_deleted)
        ]
        all_items.sort(key=lambda i: i.uploaded_at, reverse=True)
        total = len(all_items)
        start = (page - 1) * page_size
        end = start + page_size
        return MediaPage(
            items=all_items[start:end],
            page=page,
            page_size=page_size,
            total=total,
        )

    def search(
        self,
        query: str,
        *,
        mime_prefix: str = "",
        tags: list[str] | None = None,
        include_deleted: bool = False,
    ) -> list[MediaItem]:
        """Search for items by filename, alt text, caption, or tags.

        Args:
            query: Search string (case-insensitive).
            mime_prefix: Filter by MIME type prefix (e.g. ``"image/"``).
            tags: Filter by tags (item must have all listed tags).
            include_deleted: Include soft-deleted items.

        Returns:
            Matching items sorted by relevance (exact filename match first).
        """
        q = query.lower()
        results = []
        for item in self._items.values():
            if not include_deleted and item.is_deleted:
                continue
            if mime_prefix and not item.mime_type.startswith(mime_prefix):
                continue
            if tags:
                if not all(t in item.tags for t in tags):
                    continue
            if (
                q in item.filename.lower()
                or q in item.alt_text.lower()
                or q in item.caption.lower()
                or any(q in tag.lower() for tag in item.tags)
            ):
                results.append(item)

        results.sort(
            key=lambda i: (
                0 if i.filename.lower() == q else 1,
                -i.uploaded_at.timestamp(),
            )
        )
        return results

    def list_folders(self) -> list[str]:
        """Return all unique folder paths (sorted, excluding deleted items)."""
        return sorted(
            {item.folder for item in self._items.values() if not item.is_deleted}
        )

    # ------------------------------------------------------------------
    # Soft delete / restore
    # ------------------------------------------------------------------

    def soft_delete(self, item_id: str) -> MediaItem | None:
        """Soft-delete an item (moves to trash without destroying storage).

        Args:
            item_id: Library item ID.

        Returns:
            Updated :class:`MediaItem` or ``None`` if not found.
        """
        item = self._items.get(item_id)
        if item is None:
            return None
        item.is_deleted = True
        item.deleted_at = datetime.now(UTC)
        return item

    def restore(self, item_id: str) -> MediaItem | None:
        """Restore a soft-deleted item.

        Args:
            item_id: Library item ID.

        Returns:
            Updated :class:`MediaItem` or ``None`` if not found.
        """
        item = self._items.get(item_id)
        if item is None:
            return None
        item.is_deleted = False
        item.deleted_at = None
        return item

    async def purge(self, item_id: str) -> bool:
        """Permanently remove an item from the library (and optionally storage).

        Args:
            item_id: Library item ID.

        Returns:
            ``True`` if removed, ``False`` if not found.
        """
        item = self._items.pop(item_id, None)
        if item is None:
            return False
        if self._storage:
            try:
                await self._storage.delete(item.path)
            except Exception:  # noqa: BLE001
                pass
        return True

    def trash(self) -> list[MediaItem]:
        """Return all soft-deleted items."""
        return [i for i in self._items.values() if i.is_deleted]


__all__ = [
    "MediaLibrary",
]
