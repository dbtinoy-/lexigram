"""Media library data models — MediaItem and MediaPage."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
import uuid


@dataclass
class MediaItem:
    """Metadata record for a single media file.

    Attributes:
        item_id: Unique library identifier.
        path: Storage path used to retrieve the file.
        filename: Original filename (human-friendly).
        mime_type: MIME type (e.g. ``"image/jpeg"``).
        size_bytes: File size in bytes.
        folder: Virtual folder (derived from *path* directory).
        uploaded_by: User identifier who uploaded the file.
        uploaded_at: UTC timestamp of upload.
        alt_text: Accessible alt text (for images).
        caption: Optional caption shown in UI.
        tags: Categorisation tags.
        width: Image width in pixels (``0`` if not an image).
        height: Image height in pixels (``0`` if not an image).
        is_deleted: Soft-delete flag.
        deleted_at: UTC timestamp of soft-delete.
        metadata: Arbitrary extra metadata.
    """

    item_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    path: str = ""
    filename: str = ""
    mime_type: str = ""
    size_bytes: int = 0
    folder: str = ""
    uploaded_by: str = ""
    uploaded_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    alt_text: str = ""
    caption: str = ""
    tags: list[str] = field(default_factory=list)
    width: int = 0
    height: int = 0
    is_deleted: bool = False
    deleted_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def extension(self) -> str:
        """File extension (lowercase, without dot)."""
        if "." in self.filename:
            return self.filename.rsplit(".", 1)[1].lower()
        return ""

    @property
    def is_image(self) -> bool:
        """Return ``True`` for image MIME types."""
        return self.mime_type.startswith("image/")

    @property
    def is_video(self) -> bool:
        """Return ``True`` for video MIME types."""
        return self.mime_type.startswith("video/")

    @property
    def is_document(self) -> bool:
        """Return ``True`` for document-like MIME types."""
        return self.mime_type in (
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "text/csv",
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-safe dict."""
        return {
            "item_id": self.item_id,
            "path": self.path,
            "filename": self.filename,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "folder": self.folder,
            "uploaded_by": self.uploaded_by,
            "uploaded_at": self.uploaded_at.isoformat(),
            "alt_text": self.alt_text,
            "caption": self.caption,
            "tags": list(self.tags),
            "width": self.width,
            "height": self.height,
            "is_deleted": self.is_deleted,
            "extension": self.extension,
            "is_image": self.is_image,
        }


@dataclass
class MediaPage:
    """Paginated result from :meth:`MediaLibrary.list_folder`.

    Attributes:
        items: Items on the current page.
        page: 1-based page number.
        page_size: Items per page requested.
        total: Total matching items (across all pages).
    """

    items: list[MediaItem]
    page: int
    page_size: int
    total: int

    @property
    def total_pages(self) -> int:
        """Total number of pages."""
        if self.page_size <= 0:
            return 1
        import math

        return math.ceil(self.total / self.page_size)

    @property
    def has_next(self) -> bool:
        """Return ``True`` if there are more pages after this one."""
        return self.page < self.total_pages

    @property
    def has_prev(self) -> bool:
        """Return ``True`` if this is not the first page."""
        return self.page > 1


__all__ = [
    "MediaItem",
    "MediaPage",
]
