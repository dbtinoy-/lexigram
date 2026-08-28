"""Python skill execution tests: subprocess isolation + hard timeout.

Covers the round-4 finding: ``.py`` skills previously ran in-process via
``exec()`` with no timeout for synchronous ``main()`` or module-level
code (a ``while True`` wedged the host event loop).  They now run in a
``sys.executable`` subprocess with JSON params on stdin and a JSON result
on stdout, under the same ``timeout_seconds``/kill contract as ``.sh``
and ``.js``.
"""

from __future__ import annotations

from pathlib import Path
import time

import pytest

from lexigram.ai.skills.discovery.skill_loader import SkillLoader


@pytest.fixture
def skill_root(tmp_path: Path) -> Path:
    root = tmp_path / "skills"
    (root / "scripts").mkdir(parents=True)
    return root


def _write(root: Path, name: str, body: str) -> Path:
    path = root / "scripts" / name
    path.write_text(body, encoding="utf-8")
    return path


@pytest.mark.asyncio
async def test_python_sync_main_returns_dict(skill_root: Path) -> None:
    script = _write(
        skill_root,
        "main.py",
        "def main(params):\n    return {'answer': params['x'] * 2}\n",
    )
    loader = SkillLoader(skill_root=skill_root)
    result = await loader.execute_script(script, {"x": 21})
    assert result["status"] == "success"
    assert result["answer"] == 42


@pytest.mark.asyncio
async def test_python_async_main_works(skill_root: Path) -> None:
    script = _write(
        skill_root,
        "main.py",
        "async def main(params):\n    return {'echo': params['v']}\n",
    )
    loader = SkillLoader(skill_root=skill_root)
    result = await loader.execute_script(script, {"v": "hi"})
    assert result["status"] == "success"
    assert result["echo"] == "hi"


@pytest.mark.asyncio
async def test_python_scalar_return_becomes_output(skill_root: Path) -> None:
    script = _write(skill_root, "main.py", "def main(params):\n    return 7\n")
    loader = SkillLoader(skill_root=skill_root)
    result = await loader.execute_script(script, {})
    assert result["status"] == "success"
    assert result["output"] == "7"


@pytest.mark.asyncio
async def test_python_no_main_returns_success(skill_root: Path) -> None:
    script = _write(skill_root, "main.py", "x = 1\n")
    loader = SkillLoader(skill_root=skill_root)
    result = await loader.execute_script(script, {})
    assert result["status"] == "success"
    assert "no main()" in result["message"]


@pytest.mark.asyncio
async def test_python_module_level_infinite_loop_times_out(
    skill_root: Path,
) -> None:
    script = _write(skill_root, "main.py", "while True:\n    pass\n")
    loader = SkillLoader(skill_root=skill_root, timeout_seconds=1)
    start = time.monotonic()
    result = await loader.execute_script(script, {})
    elapsed = time.monotonic() - start
    assert result["status"] == "error"
    assert "timed out" in result["error"]
    assert elapsed < 10


@pytest.mark.asyncio
async def test_python_sync_main_infinite_loop_times_out(skill_root: Path) -> None:
    """Regression test: sync main() previously wedged the event loop."""
    script = _write(
        skill_root,
        "main.py",
        "def main(params):\n    while True:\n        pass\n",
    )
    loader = SkillLoader(skill_root=skill_root, timeout_seconds=1)
    start = time.monotonic()
    result = await loader.execute_script(script, {})
    elapsed = time.monotonic() - start
    assert result["status"] == "error"
    assert "timed out" in result["error"]
    assert elapsed < 10


@pytest.mark.asyncio
async def test_python_sys_exit_returns_error(skill_root: Path) -> None:
    script = _write(skill_root, "main.py", "import sys\nsys.exit(3)\n")
    loader = SkillLoader(skill_root=skill_root)
    result = await loader.execute_script(script, {})
    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_python_exception_returns_error_dict(skill_root: Path) -> None:
    script = _write(
        skill_root,
        "main.py",
        "def main(params):\n    raise ValueError('boom')\n",
    )
    loader = SkillLoader(skill_root=skill_root)
    result = await loader.execute_script(script, {})
    assert result["status"] == "error"
    assert "boom" in result["error"]


@pytest.mark.asyncio
async def test_python_env_and_params_injected(skill_root: Path) -> None:
    script = _write(
        skill_root,
        "main.py",
        "import os\n"
        "def main(params):\n"
        "    return {'skill': os.environ['LEX_SKILL_NAME'], 'p': params['p']}\n",
    )
    loader = SkillLoader(skill_root=skill_root)
    result = await loader.execute_script(script, {"p": "v"})
    assert result["status"] == "success"
    assert result["skill"] == "skills"
    assert result["p"] == "v"


@pytest.mark.asyncio
async def test_python_prints_do_not_corrupt_result(skill_root: Path) -> None:
    script = _write(
        skill_root,
        "main.py",
        "def main(params):\n    print('noise on stdout')\n    return {'ok': True}\n",
    )
    loader = SkillLoader(skill_root=skill_root)
    result = await loader.execute_script(script, {})
    assert result["status"] == "success"
    assert result["ok"] is True
