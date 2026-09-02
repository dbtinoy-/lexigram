"""Run ruff over generated code, in-memory or on disk.

Generation never depends on the linter being installed: every entry point
here degrades to a no-op when ruff is missing or fails, because a formatter
that can fail the build turns a cosmetic dependency into a hard one.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

__all__ = ["autofix_text", "format_project"]


def autofix_text(text: str, filename: str) -> str:
    """Run ``ruff check --fix`` on *text* in-memory, returning fixed source.

    Used for generators whose templates emit auto-fixable lint noise (unused
    imports, modern-type style). Falls back to the original text if ruff is
    unavailable or fails, so generation never depends on the linter being
    installed.
    """
    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "--fix",
                "-",
                "--stdin-filename",
                filename,
            ],
            input=text,
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return text
    # ruff writes the fixed source to stdout even when it reports fixes made.
    return proc.stdout if proc.stdout else text


def format_project(project_dir: Path) -> None:
    """Lint-fix and format the generated project in place.

    Framework templates (notably ``lexigram-tasks``' task template, see
    TASK-3 in docs/LEXIGRAM_FRAMEWORK_BUGS.md) emit code with auto-fixable
    lint issues: trailing whitespace in Jinja blanks (W293), unsorted
    imports (I001), ``dict.get(k, None)`` (SIM910), and dead parameter
    locals (F841). ``ruff format`` only handles whitespace, so run
    ``ruff check --fix`` first. ``--unsafe-fixes`` is intentional: the
    code is freshly generated (no hand edits to protect) and the only
    unsafe fix that fires is removing a provably-unused local.
    """
    ruff = shutil.which("ruff")
    if ruff is None:
        return
    for argv in (
        [ruff, "check", "--fix", "--unsafe-fixes", "."],
        [ruff, "format", "."],
    ):
        subprocess.run(  # noqa: S603 - fixed argv, no shell
            argv,
            cwd=project_dir,
            check=False,
            capture_output=True,
            timeout=60,
        )
