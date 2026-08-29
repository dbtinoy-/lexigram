"""Task generator rendering tests."""

from __future__ import annotations

import ast
from pathlib import Path

from lexigram.tasks.cli.generators.task import TaskGenerator

PYPROJECT = '[project]\nname = "demo"\nversion = "0.1.0"\n'


def _render(tmp_path: Path, name: str, **kwargs: object) -> str:
    """Generate a task module inside an anchored src-layout project."""
    (tmp_path / "pyproject.toml").write_text(PYPROJECT)
    out = tmp_path / "src" / "tasks"
    out.mkdir(parents=True, exist_ok=True)
    result = TaskGenerator(output_dir=out).generate(name, **kwargs)
    return Path(result.files_created[0]).read_text()


def test_task_generator_uses_snake_case_function_name(tmp_path: Path) -> None:
    """Generated task entrypoints should be valid snake_case identifiers."""
    content = _render(tmp_path, "SendWeeklyDigest", schedule="0 9 * * 1")

    assert 'async def send_weekly_digest(' in content
    assert 'async def SendWeeklyDigest(' not in content
    assert 'name="send_weekly_digest"' in content


def test_task_generator_omits_dead_param_extraction(tmp_path: Path) -> None:
    """Generated task modules should not emit unused kwargs assignments."""
    content = _render(tmp_path, "cleanup", params_str="id=None,email=None")

    assert 'kwargs.get("id", None)' not in content
    assert 'kwargs.get("email", None)' not in content
    assert "result_data = await _process_cleanup(*args, **kwargs)" in content


def test_task_generator_output_is_syntactically_clean(tmp_path: Path) -> None:
    """Generated task modules should stay parseable and neatly framed."""
    content = _render(tmp_path, "cleanup", schedule="*/15 * * * *")

    ast.parse(content)
    assert content.endswith("\n")
    assert "@scheduled(\n" in content
    assert "\n\nasync def _process_cleanup(" in content
