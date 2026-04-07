"""
Utility functions for admin storage service.

Provides path generation, content type detection, and other helper functions.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Any
from uuid import uuid4


def generate_upload_path(
    filename: str,
    resource_type: str | None = None,
    resource_id: Any = None,
    base_path: str = "uploads",
) -> str:
    """Generate unique upload path.

    Args:
        filename: Original filename
        resource_type: Optional resource type for organization
        resource_id: Optional resource ID
        base_path: Base path prefix

    Returns:
        Unique storage path

    Example:
        >>> generate_upload_path("avatar.jpg", "users", 123)
        "uploads/users/123/abc123_avatar.jpg"
    """
    # Generate unique prefix
    unique_id = uuid4().hex[:8]

    # Sanitize filename
    safe_filename = Path(filename).name
    safe_filename = "".join(c for c in safe_filename if c.isalnum() or c in ".-_")

    # Build path
    parts = [base_path]
    if resource_type:
        parts.append(resource_type)
    if resource_id:
        parts.append(str(resource_id))
    parts.append(f"{unique_id}_{safe_filename}")

    return "/".join(parts)


def get_content_type(filename: str) -> str:
    """Get content type from filename."""
    content_type, _ = mimetypes.guess_type(filename)
    return content_type or "application/octet-stream"
