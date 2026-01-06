"""Tests for ModuleScanner discovery."""

from __future__ import annotations

import types
from unittest.mock import MagicMock

import pytest

from lexigram.contracts.ai.skills import SkillDefinition, SkillResult
from lexigram.result import Ok

from lexigram.ai.skills.base import AbstractSkill
from lexigram.ai.skills.discovery.module_scanner import ModuleScanner
from lexigram.ai.skills.registry import SkillRegistry


class _DiscoveredSkill(AbstractSkill):
    """Skill placed at module level for discovery testing."""

    @property
    def definition(self) -> SkillDefinition:
        return SkillDefinition(
            name="discovered",
            description="Discovered by scanner.",
            parameters_schema={"type": "object", "properties": {}, "required": []},
            category="test",
        )

    async def execute(self, **kwargs):
        return Ok(SkillResult(skill_name="discovered", success=True, output={}))


class TestModuleScanner:
    """Tests for ModuleScanner."""

    @pytest.mark.asyncio
    async def test_scan_discovers_skill_instances(
        self, monkeypatch, registry: SkillRegistry
    ) -> None:
        """Scanner should find BaseSkill instances at module top-level."""
        import importlib

        fake_module = types.ModuleType("fake_skills_module")
        fake_module.my_skill = _DiscoveredSkill()
        fake_module.NOT_A_SKILL = "just a string"

        monkeypatch.setattr(importlib, "import_module", lambda path: fake_module)

        scanner = ModuleScanner()
        count = await scanner.scan(registry, "fake_skills_module")
        assert count == 1
        assert registry.get("discovered") is not None

    @pytest.mark.asyncio
    async def test_scan_raises_on_import_error(
        self, monkeypatch, registry: SkillRegistry
    ) -> None:
        import importlib

        def _raise(path):
            raise ImportError("not found")

        monkeypatch.setattr(importlib, "import_module", _raise)

        scanner = ModuleScanner()
        with pytest.raises(ImportError):
            await scanner.scan(registry, "nonexistent.module")

    @pytest.mark.asyncio
    async def test_duplicate_registration_is_skipped(
        self, monkeypatch, registry: SkillRegistry
    ) -> None:
        import importlib

        skill = _DiscoveredSkill()
        registry.register(skill)  # pre-register to force duplicate

        fake_module = types.ModuleType("dup_module")
        fake_module.my_skill = skill
        monkeypatch.setattr(importlib, "import_module", lambda _: fake_module)

        scanner = ModuleScanner()
        count = await scanner.scan(registry, "dup_module")
        # duplicate skipped gracefully
        assert count == 0

    @pytest.mark.asyncio
    async def test_scan_discovers_and_instantiates_classes_via_di(
        self, monkeypatch, registry: SkillRegistry
    ) -> None:
        """Scanner should resolve BaseSkill subclasses via the DI container."""
        from unittest.mock import AsyncMock
        import importlib
        
        class _DIInjectedTestSkill(_DiscoveredSkill):
            pass

        fake_module = types.ModuleType("di_module")
        fake_module.MyDISkill = _DIInjectedTestSkill
        monkeypatch.setattr(importlib, "import_module", lambda _: fake_module)

        mock_container = AsyncMock()
        mock_container.resolve.return_value = _DIInjectedTestSkill()

        scanner = ModuleScanner(container=mock_container)
        count = await scanner.scan(registry, "di_module")
        
        assert count == 1
        assert registry.get("discovered") is not None
        mock_container.resolve.assert_awaited_once_with(_DIInjectedTestSkill)
