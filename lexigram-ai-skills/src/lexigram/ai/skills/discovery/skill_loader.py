"""SkillLoader — loads bundled files and executes skill scripts."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

from lexigram.logging import (
    get_logger,
)
from lexigram.serialization import JSONDecodeError, dumps_str, loads

logger = get_logger(__name__)


class SkillLoader:
    """Handles loading bundled files and executing skill scripts.

    Features:
    - Reading reference.md, forms.md, and other bundled context files
    - Executing scripts (Python, Shell, JavaScript) with parameters
    - Sandboxed execution with path validation
    - Timeout enforcement
    - Environment variable injection
    """

    def __init__(
        self,
        sandbox: bool = True,
        timeout_seconds: int = 30,
        max_file_size: int = 1024 * 1024,
    ) -> None:
        """Initialize the loader.

        Args:
            sandbox: Whether to enable sandboxing (default: True).
            timeout_seconds: Script execution timeout (default: 30s).
            max_file_size: Maximum file size for context loading (default: 1MB).
        """
        self._sandbox = sandbox
        self._timeout = timeout_seconds
        self._max_file_size = max_file_size

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
        """Execute a skill script with parameters."""
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
        """Path safety check for sandboxing."""
        try:
            path.resolve()
            return ".." not in str(path)
        except Exception:  # noqa: BLE001  # path.resolve() can raise OSError or ValueError; any failure means unsafe
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
        """Execute a Python script."""

        try:
            code = script_path.read_text(encoding="utf-8")

            local_ns: dict[str, Any] = {
                "params": params,
                "os": os,
                "json": __import__("json"),
            }

            try:
                compiled = compile(code, str(script_path), "exec")
                exec(compiled, local_ns)  # noqa: S102
            except Exception as e:  # noqa: BLE001  # exec() on user scripts can raise any exception
                return {
                    "status": "error",
                    "error": str(e),
                    "script": str(script_path),
                }

            main_fn = local_ns.get("main")
            if callable(main_fn):
                if asyncio.iscoroutinefunction(main_fn):
                    result = await asyncio.wait_for(
                        main_fn(params),
                        timeout=self._timeout,
                    )
                else:
                    result = main_fn(params)

                if isinstance(result, dict):
                    result["status"] = "success"
                    result["script"] = str(script_path)
                    return result
                return {
                    "status": "success",
                    "output": str(result),
                    "script": str(script_path),
                }

            return {
                "status": "success",
                "message": "Script executed (no main() function)",
                "script": str(script_path),
            }

        except TimeoutError:
            return {
                "status": "error",
                "error": f"Script execution timed out after {self._timeout}s",
                "script": str(script_path),
            }
        except Exception as exc:  # noqa: BLE001  # user script execution can raise any exception type
            logger.warning("skill_loader_python_error", error=str(exc))
            return {
                "status": "error",
                "error": str(exc),
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
