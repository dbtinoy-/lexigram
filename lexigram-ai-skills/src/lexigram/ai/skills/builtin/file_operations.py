"""FileOperationsSkill — sandboxed file read and write skills."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.ai.skills.base import BaseSkill
from lexigram.ai.skills.exceptions import SkillExecutionError
from lexigram.contracts.ai.skills import SkillDefinition, SkillError, SkillResult
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


def _resolve_safe(base: Path, rel_path: str) -> Path | None:
    """Resolve *rel_path* relative to *base*, refusing directory traversal.

    Args:
        base: Allowed root directory.
        rel_path: Relative path provided by the caller.

    Returns:
        Resolved absolute :class:`Path`, or ``None`` when path escapes *base*.
    """
    try:
        resolved = (base / rel_path).resolve()
        resolved.relative_to(base.resolve())  # raises if outside base
        return resolved
    except ValueError:
        return None


class FileReadSkill(BaseSkill):
    """Read a file and return its content as a string.

    Files are only accessible within *base_dir* (defaults to the current
    working directory).  Directory traversal attempts return an error.

    Required permission: ``files.read``.
    """

    def __init__(self, base_dir: str | None = None) -> None:
        """Initialise with an optional sandbox directory.

        Args:
            base_dir: Base directory constraint.  Defaults to ``os.getcwd()``.
        """
        self._base = Path(base_dir) if base_dir else Path.cwd()

    @property
    def definition(self) -> SkillDefinition:  # type: ignore[override]
        """Return the skill definition.

        Returns:
            SkillDefinition for the file_read skill.
        """
        return SkillDefinition(
            name="file_read",
            description="Read the contents of a local file.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file to read.",
                    },
                    "encoding": {
                        "type": "string",
                        "description": "Text encoding. Defaults to 'utf-8'.",
                        "default": "utf-8",
                    },
                },
                "required": ["path"],
            },
            category="filesystem",
            permissions=["files.read"],
        )

    async def execute(self, **kwargs: Any) -> Result[SkillResult, SkillError]:
        """Read and return file content.

        Args:
            **kwargs: Requires ``path``; accepts ``encoding``.

        Returns:
            Ok result with ``content``, ``path``, and ``size_bytes``, or Err.
        """
        import asyncio

        rel_path: str = kwargs.get("path", "")
        encoding: str = kwargs.get("encoding", "utf-8")

        safe = _resolve_safe(self._base, rel_path)
        if safe is None:
            return Err(
                SkillExecutionError(
                    f"Path '{rel_path}' is outside the allowed directory."
                )
            )

        def _read() -> str:
            with safe.open(encoding=encoding) as fh:
                return fh.read()

        try:
            content = await asyncio.get_event_loop().run_in_executor(None, _read)
        except OSError as exc:
            return Err(SkillExecutionError(f"Cannot read '{rel_path}': {exc}"))

        return Ok(
            SkillResult(
                skill_name="file_read",
                success=True,
                output={
                    "content": content,
                    "path": rel_path,
                    "size_bytes": len(content.encode(encoding)),
                },
            )
        )


class FileWriteSkill(BaseSkill):
    """Write text content to a local file.

    Files are only writable within *base_dir*.  The parent directory must
    exist; write will not create intermediate directories.

    Required permission: ``files.write``.
    """

    def __init__(self, base_dir: str | None = None) -> None:
        """Initialise with an optional sandbox directory.

        Args:
            base_dir: Base directory constraint.  Defaults to ``os.getcwd()``.
        """
        self._base = Path(base_dir) if base_dir else Path.cwd()

    @property
    def definition(self) -> SkillDefinition:  # type: ignore[override]
        """Return the skill definition.

        Returns:
            SkillDefinition for the file_write skill.
        """
        return SkillDefinition(
            name="file_write",
            description="Write text content to a local file.",
            parameters_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path of the file to write.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Text content to write.",
                    },
                    "encoding": {
                        "type": "string",
                        "description": "Text encoding. Defaults to 'utf-8'.",
                        "default": "utf-8",
                    },
                },
                "required": ["path", "content"],
            },
            category="filesystem",
            permissions=["files.write"],
        )

    async def execute(self, **kwargs: Any) -> Result[SkillResult, SkillError]:
        """Write content to the specified path.

        Args:
            **kwargs: Requires ``path`` and ``content``; accepts ``encoding``.

        Returns:
            Ok result with ``path`` and ``bytes_written``, or Err.
        """
        import asyncio

        rel_path: str = kwargs.get("path", "")
        content: str = kwargs.get("content", "")
        encoding: str = kwargs.get("encoding", "utf-8")

        safe = _resolve_safe(self._base, rel_path)
        if safe is None:
            return Err(
                SkillExecutionError(
                    f"Path '{rel_path}' is outside the allowed directory."
                )
            )

        encoded = content.encode(encoding)

        def _write() -> None:
            with safe.open("wb") as fh:
                fh.write(encoded)

        try:
            await asyncio.get_event_loop().run_in_executor(None, _write)
        except OSError as exc:
            return Err(SkillExecutionError(f"Cannot write '{rel_path}': {exc}"))

        return Ok(
            SkillResult(
                skill_name="file_write",
                success=True,
                output={"path": rel_path, "bytes_written": len(encoded)},
            )
        )
