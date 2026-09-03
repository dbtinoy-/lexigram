"""Local fallback implementations for the export job stack.

The admin bundle's :class:`ExportService` depends on two framework
protocols — ``BlobStoreProtocol`` and ``TaskManagerProtocol`` — that a host
application *may* provide via the DI container, but frequently will not
(the ``storage`` pyproject extra ships empty). These fallbacks make the
job-based export lifecycle work out of the box with zero configuration:

* :class:`LocalExportBlobStore` — a filesystem blob store rooted at a
  dedicated export directory, with a path-traversal guard so no key can
  escape the root.
* :class:`InlineTaskRunner` — a minimal task manager wrapping
  ``asyncio.create_task`` with tracking and graceful shutdown.

Both are drop-in compatible with the protocol surfaces the export stack
uses; when a host registers real implementations, the DI sub-provider
prefers those instead (see ``di/sub_providers/export.py``).
"""

from __future__ import annotations

import asyncio
import contextlib
from datetime import UTC, datetime
import mimetypes
from pathlib import Path
import tempfile
from typing import TYPE_CHECKING, Any

from lexigram.contracts.infra.storage.models import FileInfo, UploadOptions

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable

_DEFAULT_SUBDIR = "lexigram-admin-exports"


class LocalExportBlobStore:
    """Filesystem ``BlobStoreProtocol`` implementation for export artifacts.

    Keys are treated as relative paths under a fixed root directory; any key
    that resolves outside the root (``..`` segments, absolute paths,
    symlink escapes) is rejected with ``ValueError``.
    """

    def __init__(self, root: str | Path | None = None) -> None:
        base = Path(root) if root else Path(tempfile.gettempdir()) / _DEFAULT_SUBDIR
        base.mkdir(parents=True, exist_ok=True)
        self._root = base.resolve()

    @property
    def root(self) -> Path:
        """Return the resolved root directory."""
        return self._root

    def _resolve(self, path: str) -> Path:
        """Resolve ``path`` strictly under the root or raise ``ValueError``."""
        candidate = (self._root / str(path).lstrip("/\\")).resolve()
        if candidate != self._root and self._root not in candidate.parents:
            msg = f"Storage path escapes export root: {path!r}"
            raise ValueError(msg)
        return candidate

    @staticmethod
    def _to_bytes(data: Any) -> bytes:
        if isinstance(data, bytes):
            return data
        if isinstance(data, str):
            return data.encode("utf-8")
        if hasattr(data, "read"):
            content = data.read()
            return content.encode("utf-8") if isinstance(content, str) else content
        msg = f"Unsupported upload payload type: {type(data)!r}"
        raise TypeError(msg)

    def _file_info(self, path: str, target: Path) -> FileInfo:
        stat = target.stat()
        content_type = mimetypes.guess_type(target.name)[0] or (
            "application/octet-stream"
        )
        return FileInfo(
            path=str(path),
            size=stat.st_size,
            content_type=content_type,
            last_modified=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
        )

    async def upload(
        self,
        path: str,
        data: Any,
        content_type: UploadOptions | str | None = None,
        **options: Any,
    ) -> FileInfo:
        """Write ``data`` under the root and return its :class:`FileInfo`."""
        target = self._resolve(path)
        payload: bytes
        if hasattr(data, "__aiter__"):  # async iterator payloads
            chunks = [self._to_bytes(chunk) async for chunk in data]
            payload = b"".join(chunks)
        else:
            payload = self._to_bytes(data)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        info = self._file_info(path, target)
        if isinstance(content_type, str) and content_type:
            info = FileInfo(
                path=info.path,
                size=info.size,
                content_type=content_type,
                last_modified=info.last_modified,
            )
        return info

    async def download(self, path: str) -> bytes:
        """Read a stored file fully into memory."""
        target = self._resolve(path)
        return target.read_bytes()

    async def stream(self, path: str, chunk_size: int = 8192) -> AsyncIterator[bytes]:
        """Yield a stored file in ``chunk_size`` byte chunks."""
        target = self._resolve(path)
        with target.open("rb") as handle:
            while chunk := handle.read(chunk_size):
                yield chunk

    async def exists(self, path: str) -> bool:
        """Return True when the key exists under the root."""
        try:
            return self._resolve(path).is_file()
        except ValueError:
            return False

    async def delete(self, path: str) -> None:
        """Delete a stored file (missing files are a no-op)."""
        target = self._resolve(path)
        with contextlib.suppress(FileNotFoundError):
            target.unlink()

    async def info(self, path: str) -> FileInfo:
        """Return metadata for a stored file."""
        target = self._resolve(path)
        if not target.is_file():
            raise FileNotFoundError(path)
        return self._file_info(path, target)

    async def list(self, prefix: str = "") -> AsyncIterator[FileInfo]:
        """Yield :class:`FileInfo` for every stored file matching ``prefix``."""
        base = self._resolve(prefix) if prefix else self._root
        if base.is_file():
            yield self._file_info(prefix, base)
            return
        if not base.is_dir():
            return
        for item in sorted(base.rglob("*")):
            if item.is_file():
                yield self._file_info(str(item.relative_to(self._root)), item)


class InlineTaskRunner:
    """Minimal ``TaskManagerProtocol`` backed by ``asyncio.create_task``."""

    def __init__(self) -> None:
        self._background: set[asyncio.Task[Any]] = set()
        self._critical: set[asyncio.Task[Any]] = set()

    def _track(
        self,
        bucket: set[asyncio.Task[Any]],
        coro: Awaitable[Any],
        name: str | None,
    ) -> asyncio.Task[Any]:
        task = asyncio.ensure_future(coro)
        if name and hasattr(task, "set_name"):
            task.set_name(name)
        bucket.add(task)
        task.add_done_callback(bucket.discard)
        return task

    def create_background_task(
        self,
        coro: Awaitable[Any],
        *,
        name: str | None = None,
    ) -> asyncio.Task[Any]:
        """Create a cancellable background task."""
        return self._track(self._background, coro, name)

    def create_critical_task(
        self,
        coro: Awaitable[Any],
        *,
        name: str | None = None,
    ) -> asyncio.Task[Any]:
        """Create a task that should complete before shutdown."""
        return self._track(self._critical, coro, name)

    def get_task_counts(self) -> dict[str, int]:
        """Return live task counts by category."""
        return {
            "background": len(self._background),
            "critical": len(self._critical),
        }

    async def shutdown_gracefully(
        self,
        critical_timeout: float = 10.0,
        background_timeout: float = 2.0,
    ) -> None:
        """Await critical tasks, then cancel remaining background tasks."""
        if self._critical:
            _done, pending = await asyncio.wait(
                self._critical, timeout=critical_timeout
            )
            for task in pending:
                task.cancel()
        for task in list(self._background):
            if not task.done():
                task.cancel()
        if self._background:
            await asyncio.wait(self._background, timeout=background_timeout)


__all__ = ["InlineTaskRunner", "LocalExportBlobStore"]
