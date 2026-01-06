"""Shared async file I/O helpers for document loaders."""

from __future__ import annotations

import asyncio
from pathlib import Path

try:
    import aiofiles

    HAS_AIOFILES = True
except ImportError:
    HAS_AIOFILES = False


async def read_file_bytes(path: Path) -> bytes:
    """Read a file as bytes, using aiofiles when available."""
    if HAS_AIOFILES:
        async with aiofiles.open(path, "rb") as file_handle:
            return await file_handle.read()
    return await asyncio.to_thread(path.read_bytes)


async def read_file_text(path: Path, encoding: str = "utf-8") -> str:
    """Read a file as text, using aiofiles when available."""
    if HAS_AIOFILES:
        async with aiofiles.open(path, encoding=encoding) as file_handle:
            return await file_handle.read()
    return await asyncio.to_thread(path.read_text, encoding=encoding)
