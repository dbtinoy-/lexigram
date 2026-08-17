"""Sandbox containment tests for SkillLoader (security D1)."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def skill_root(tmp_path: Path) -> Path:
    root = tmp_path / "skills"
    (root / "scripts").mkdir(parents=True)
    (root / "scripts" / "main.py").write_text(
        "def main(params):\n    return {'status': 'ok'}\n"
    )
    return root


def _outside_script(tmp_path: Path) -> Path:
    target = tmp_path / "outside" / "evil_main.py"
    target.parent.mkdir(exist_ok=True)
    target.write_text("def main(params):\n    return {'status': 'ok'}\n")
    return target


@pytest.mark.asyncio
async def test_path_with_dotdot_escape_denied(skill_root: Path, tmp_path: Path) -> None:
    from lexigram.ai.skills.discovery.skill_loader import SkillLoader

    target = _outside_script(tmp_path)
    escape = skill_root / "scripts" / ".." / ".." / "outside" / "evil_main.py"
    assert escape.resolve() == target.resolve()  # ensures this exercises '..'
    loader = SkillLoader(skill_root=skill_root)
    result = await loader.execute_script(escape, {})
    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_absolute_path_outside_root_denied(skill_root: Path, tmp_path: Path) -> None:
    from lexigram.ai.skills.discovery.skill_loader import SkillLoader

    loader = SkillLoader(skill_root=skill_root)
    result = await loader.execute_script(_outside_script(tmp_path), {})
    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_symlink_escape_denied(skill_root: Path, tmp_path: Path) -> None:
    from lexigram.ai.skills.discovery.skill_loader import SkillLoader

    target = _outside_script(tmp_path)
    link = skill_root / "scripts" / "link.py"
    link.symlink_to(target)
    loader = SkillLoader(skill_root=skill_root)
    result = await loader.execute_script(link, {})
    assert result["status"] == "error"


@pytest.mark.asyncio
async def test_script_inside_root_executes(skill_root: Path) -> None:
    from lexigram.ai.skills.discovery.skill_loader import SkillLoader

    loader = SkillLoader(skill_root=skill_root)
    result = await loader.execute_script(skill_root / "scripts" / "main.py", {})
    assert result.get("status") != "error"


@pytest.mark.asyncio
async def test_allowed_script_types_gates_sh(skill_root: Path) -> None:
    from lexigram.ai.skills.discovery.skill_loader import SkillLoader

    sh = skill_root / "scripts" / "main.sh"
    sh.write_text("echo hi\n")
    loader = SkillLoader(skill_root=skill_root, allowed_script_types=("py",))
    result = await loader.execute_script(sh, {})
    assert result["status"] == "error"
