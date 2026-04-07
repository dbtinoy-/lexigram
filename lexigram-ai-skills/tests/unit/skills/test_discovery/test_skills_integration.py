"""Integration test for skill sources discovery flow."""

from __future__ import annotations

import pytest
from pathlib import Path

from lexigram.ai.skills.discovery.skill_source_scanner import SkillSourceScanner
from lexigram.ai.skills.discovery.skill_loader import SkillLoader
from lexigram.ai.skills.registry import SkillRegistry


class TestSkillsIntegration:
    """Full integration test for skill sources discovery."""

    @pytest.mark.asyncio
    async def test_full_discovery_flow(self, tmp_path: Path) -> None:
        """Test discovering skills from configured paths."""
        skill1 = tmp_path / "skill-one"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("""---
name: skill-one
description: First skill
---

First skill instructions.
""")
        
        skill2 = tmp_path / "skill-two"
        skill2.mkdir()
        (skill2 / "SKILL.md").write_text("""---
name: skill-two  
description: Second skill
version: 2.0.0
---

Second skill instructions.
""")
        
        registry = SkillRegistry()
        scanner = SkillSourceScanner()
        
        count = await scanner.scan(registry, tmp_path)
        
        assert count == 2

    @pytest.mark.asyncio
    async def test_script_execution_integration(self, tmp_path: Path) -> None:
        """Test full flow: discover skill with script and execute it."""
        skill_dir = tmp_path / "exec-skill"
        skill_dir.mkdir()
        scripts = skill_dir / "scripts"
        scripts.mkdir()
        
        (scripts / "main.py").write_text("""
def main(params):
    return {"status": "success", "echo": params.get("message")}
""")
        
        (skill_dir / "SKILL.md").write_text("""---
name: exec-skill
description: Executable skill
---

Execute the script.
""")
        
        registry = SkillRegistry()
        scanner = SkillSourceScanner()
        
        count = await scanner.scan(registry, tmp_path)
        assert count == 1
        
        skill = registry.get("exec-skill")
        assert skill is not None
        
        result = await skill.execute(message="hello")
        assert result.is_ok()
        assert result.unwrap().output["status"] == "success"

    @pytest.mark.asyncio
    async def test_argument_substitution_integration(self, tmp_path: Path) -> None:
        """Test $ARGUMENTS substitution in skill body."""
        skill_dir = tmp_path / "arg-skill"
        skill_dir.mkdir()
        
        (skill_dir / "SKILL.md").write_text("""---
name: arg-skill
description: Argument skill
---

Process these: $ARGUMENTS
""")
        
        registry = SkillRegistry()
        scanner = SkillSourceScanner()
        
        await scanner.scan(registry, tmp_path)
        
        skill = registry.get("arg-skill")
        result = await skill.execute(foo="bar", baz=123)
        
        assert result.is_ok()
        output = result.unwrap().output
        assert "foo=" in output["instructions"]
        assert "baz=" in output["instructions"]

    @pytest.mark.asyncio
    async def test_context_files_lazy_load(self, tmp_path: Path) -> None:
        """Test context files are discovered but not loaded until needed."""
        skill_dir = tmp_path / "context-skill"
        skill_dir.mkdir()
        
        (skill_dir / "reference.md").write_text("# Reference\n\nImportant info.")
        (skill_dir / "SKILL.md").write_text("""---
name: context-skill
description: Context skill
context:
  - reference.md
---

Main instructions.
""")
        
        registry = SkillRegistry()
        scanner = SkillSourceScanner()
        
        await scanner.scan(registry, tmp_path)
        
        skill = registry.get("context-skill")
        result = await skill.execute()
        
        assert result.is_ok()
        output = result.unwrap().output
        assert "reference.md" in output.get("context_files", [])

    @pytest.mark.asyncio
    async def test_nested_discovery(self, tmp_path: Path) -> None:
        """Test discovering skills in nested directories."""
        nested = tmp_path / "subdir" / "nested-skill"
        nested.mkdir(parents=True)
        (nested / "SKILL.md").write_text("""---
name: nested-skill
description: Nested skill
---

Nested skill instructions.
""")
        
        registry = SkillRegistry()
        scanner = SkillSourceScanner()
        
        count = await scanner.scan(registry, tmp_path)
        
        assert count == 1
