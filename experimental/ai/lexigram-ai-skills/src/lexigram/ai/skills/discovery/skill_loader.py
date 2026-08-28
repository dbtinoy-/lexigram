"""SkillLoader — loads bundled files and executes skill scripts."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys
from typing import Any

from lexigram.logging import (
    get_logger,
)
from lexigram.serialization import JSONDecodeError, dumps_str, loads

logger = get_logger(__name__)

# Bootstrap executed in a subprocess (``python -c``) for ``.py`` skills.
# It receives the script path as argv[1] and JSON params on stdin, runs the
# script with the same namespace contract as the historical in-process
# executor (``params``, ``os``, ``json``), then writes a single JSON result
# object to stdout.  Script stdout is diverted to stderr so prints cannot
# corrupt the result protocol.  ``BaseException`` is caught so that
# ``sys.exit`` and script crashes still produce a structured error result.
_PY_BOOTSTRAP = r"""
import asyncio
import json
import os
import sys

script = sys.argv[1]
params = json.loads(sys.stdin.buffer.read() or b"{}")
result = None
real_stdout = sys.stdout
try:
    sys.stdout = sys.stderr
    local_ns = {"params": params, "os": os, "json": json}
    with open(script, "r", encoding="utf-8") as fh:
        code = fh.read()
    compiled = compile(code, script, "exec")
    exec(compiled, local_ns)
    main_fn = local_ns.get("main")
    if callable(main_fn):
        out = main_fn(params)
        if asyncio.iscoroutine(out):
            out = asyncio.run(out)
        if isinstance(out, dict):
            out.setdefault("status", "success")
            out.setdefault("script", script)
            result = out
        else:
            result = {
                "status": "success",
                "output": str(out),
                "script": script,
            }
    else:
        result = {
            "status": "success",
            "message": "Script executed (no main() function)",
            "script": script,
        }
except BaseException as exc:  # noqa: BLE001 - subprocess boundary: report any failure
    result = {"status": "error", "error": str(exc), "script": script}
finally:
    sys.stdout = real_stdout
sys.stdout.write(json.dumps(result))
"""


class SkillLoader:
    """Handles loading bundled files and executing skill scripts.

    Features:
    - Reading reference.md, forms.md, and other bundled context files
    - Executing scripts (Python, Shell, JavaScript) with parameters
    - Subprocess execution with path validation (all script types)
    - Timeout enforcement (covers module-level code and sync main() too)

    Note:
        Skill directories are **executable content** — only populate them
        from trusted sources.  Script execution is gated by containment
        against the configured root and by ``allowed_script_types``; each
        script type runs in its own subprocess with a hard timeout, so a
        runaway or malicious script cannot wedge the host process.
    """

    def __init__(
        self,
        sandbox: bool = True,
        timeout_seconds: int = 30,
        max_file_size: int = 1024 * 1024,
        skill_root: Path | None = None,
        allowed_script_types: tuple[str, ...] | None = None,
    ) -> None:
        """Initialize the loader.

        Args:
            sandbox: Whether to enable sandboxing (default: True).
            timeout_seconds: Script execution timeout (default: 30s).
            max_file_size: Maximum file size for context loading (default: 1MB).
            skill_root: Root directory that skill scripts must resolve
                inside of.  ``None`` denies every path (fail-closed).
            allowed_script_types: Script suffixes permitted for execution
                (e.g. ``("py", "sh", "js")``, without leading dots).
                ``None`` denies every script type (fail-closed).
        """
        self._sandbox = sandbox
        self._timeout = timeout_seconds
        self._max_file_size = max_file_size
        self._skill_root = skill_root
        self._allowed_script_types = allowed_script_types
        if not sandbox:
            logger.warning(
                "skill_loader_sandbox_disabled",
                hint="skill directories are executable content; only populate from trusted sources",
            )

    async def load_bundled_file(self, path: Path) -> str | None:
        """Load a bundled context file with size limit."""
        if not path.exists():
            logger.warning("skill_loader_file_not_found", path=str(path))
            return None

        try:
            stat = path.stat()
            if stat.st_size > self._max_file_size:
                logger.warning(
                    "skill_loader_file_too_large",
                    path=str(path),
                    size=stat.st_size,
                )
                return None

            return path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("skill_loader_read_error", path=str(path), error=str(exc))
            return None

    async def load_bundled_context(
        self, skill_dir: Path, context_files: list[str]
    ) -> dict[str, str]:
        """Load multiple bundled context files."""
        result: dict[str, str] = {}
        for filename in context_files:
            path = skill_dir / filename
            content = await self.load_bundled_file(path)
            if content is not None:
                result[filename] = content
        return result

    async def execute_script(
        self, script_path: Path, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a skill script with parameters.

        Note:
            Skill directories are **executable content** — only populate
            them from trusted sources.  Script execution is gated by
            containment against the configured root and by
            ``allowed_script_types``.
        """
        if not script_path.exists():
            return {
                "status": "error",
                "error": f"Script not found: {script_path}",
            }

        if self._sandbox:
            if not self._is_safe_path(script_path):
                return {
                    "status": "error",
                    "error": "Script path not allowed (sandbox violation)",
                }

        script_type = script_path.suffix.lower()

        if (
            self._allowed_script_types is not None
            and script_type.lstrip(".") not in self._allowed_script_types
        ):
            return {
                "status": "error",
                "error": (
                    f"Script type not allowed: {script_type} "
                    f"(allowed: {', '.join(self._allowed_script_types)})"
                ),
            }

        executors = {
            ".py": self._execute_python,
            ".sh": self._execute_shell,
            ".js": self._execute_javascript,
        }

        executor = executors.get(script_type)
        if executor:
            return await executor(script_path, params)

        return {
            "status": "error",
            "error": f"Unsupported script type: {script_type}",
        }

    def _is_safe_path(self, path: Path) -> bool:
        """Return True only if the resolved path is a regular file inside the configured root.

        Note:
            Skill directories are executable content. This check is a fail-closed
            containment boundary: absolute paths outside the root, ``..`` escapes,
            and symlinks resolving outside the root are all denied. A ``None``
            root denies everything.
        """
        try:
            if self._skill_root is None:
                return False
            resolved = path.resolve()
            return resolved.is_file() and resolved.is_relative_to(self._skill_root)
        except (OSError, ValueError, RuntimeError):
            return False

    def _get_env(self, script_path: Path) -> dict[str, str]:
        """Get environment variables for script execution."""
        skill_dir = script_path.parent.parent
        return {
            **os.environ,
            "LEX_SKILL_NAME": skill_dir.name,
            "LEX_SKILL_DIR": str(skill_dir.resolve()),
            "LEX_SCRIPT_NAME": script_path.name,
        }

    async def _execute_python(
        self, script_path: Path, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a Python skill script in a subprocess.

        The script runs via ``sys.executable -c <bootstrap>`` with JSON
        params on stdin and a JSON result on stdout, mirroring the
        ``.sh``/``.js`` executors: process isolation, event-loop safety,
        and a hard ``timeout_seconds`` that covers module-level code and
        synchronous ``main()`` alike.  The namespace contract is preserved
        (``params``, ``os``, ``json`` globals; ``main(params)`` may be sync
        or async and return a dict or a scalar).
        """

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-c",
                _PY_BOOTSTRAP,
                str(script_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._get_env(script_path),
            )
            input_json = dumps_str(params).encode()
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=input_json),
                timeout=self._timeout,
            )
        except TimeoutError:
            process.kill()
            return {
                "status": "error",
                "error": f"Script execution timed out after {self._timeout}s",
                "script": str(script_path),
            }
        except Exception as exc:  # noqa: BLE001  # subprocess spawn can raise any exception type
            return {
                "status": "error",
                "error": str(exc),
                "script": str(script_path),
            }

        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")
        try:
            output = loads(stdout_text)
        except JSONDecodeError:
            output = stdout_text

        if isinstance(output, dict) and "status" in output:
            output.setdefault("script", str(script_path))
            return output
        if process.returncode != 0:
            return {
                "status": "error",
                "error": f"Script exited with code {process.returncode}",
                "stderr": stderr_text,
                "script": str(script_path),
            }
        return {
            "status": "success",
            "output": output,
            "stderr": stderr_text,
            "script": str(script_path),
        }

    async def _execute_shell(
        self, script_path: Path, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a shell script."""
        try:
            process = await asyncio.create_subprocess_exec(
                str(script_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._get_env(script_path),
            )

            input_json = dumps_str(params).encode()
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=input_json),
                timeout=self._timeout,
            )

            return {
                "status": "success" if process.returncode == 0 else "error",
                "stdout": stdout.decode("utf-8"),
                "stderr": stderr.decode("utf-8"),
                "returncode": process.returncode,
                "script": str(script_path),
            }
        except TimeoutError:
            process.kill()
            return {
                "status": "error",
                "error": f"Script execution timed out after {self._timeout}s",
                "script": str(script_path),
            }
        except Exception as exc:  # noqa: BLE001  # user script execution can raise any exception type
            return {
                "status": "error",
                "error": str(exc),
                "script": str(script_path),
            }

    async def _execute_javascript(
        self, script_path: Path, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a JavaScript script using Node.js."""
        try:
            try:
                await asyncio.create_subprocess_exec(
                    "node",
                    "--version",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
            except FileNotFoundError:
                return {
                    "status": "error",
                    "error": "Node.js not available",
                    "script": str(script_path),
                }

            process = await asyncio.create_subprocess_exec(
                "node",
                str(script_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._get_env(script_path),
            )

            input_json = dumps_str(params).encode()
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=input_json),
                timeout=self._timeout,
            )

            try:
                output = loads(stdout.decode("utf-8"))
            except JSONDecodeError:
                output = stdout.decode("utf-8")

            return {
                "status": "success" if process.returncode == 0 else "error",
                "output": output,
                "stderr": stderr.decode("utf-8"),
                "returncode": process.returncode,
                "script": str(script_path),
            }
        except TimeoutError:
            process.kill()
            return {
                "status": "error",
                "error": f"Script execution timed out after {self._timeout}s",
                "script": str(script_path),
            }
        except Exception as exc:  # noqa: BLE001  # user script execution can raise any exception type
            return {
                "status": "error",
                "error": str(exc),
                "script": str(script_path),
            }


__all__ = ["SkillLoader"]
