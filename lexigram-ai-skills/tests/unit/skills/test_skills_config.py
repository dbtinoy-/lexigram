"""Tests for SkillsConfig."""

from __future__ import annotations

import pytest

from lexigram.ai.skills.config import SkillsConfig


class TestSkillsConfigDefaults:
    """Test SkillsConfig default values."""

    def test_default_config_values(self) -> None:
        """Default config should have sensible defaults."""
        config = SkillsConfig()

        assert config.name == "ai-skills"
        assert config.default_timeout_seconds > 0
        assert config.max_retries >= 0
        assert config.max_concurrent_executions >= 1
        assert config.cache_enabled is True
        assert config.cache_ttl_seconds >= 1
        assert isinstance(config.cache_backend, str)

    def test_default_permissions_enforcement(self) -> None:
        """Default config should have permission enforcement setting."""
        config = SkillsConfig()

        assert isinstance(config.enforce_permissions, bool)

    def test_default_auto_discovery(self) -> None:
        """Default config should have auto-discovery setting."""
        config = SkillsConfig()

        assert isinstance(config.auto_discover, bool)
        assert isinstance(config.scan_packages, list)

    def test_default_builtin_skills(self) -> None:
        """Default config should have builtin skills setting."""
        config = SkillsConfig()

        assert config.enable_builtin is True
        assert isinstance(config.builtin_skills, list)


class TestSkillsConfigCustomization:
    """Test SkillsConfig customization."""

    def test_custom_timeout(self) -> None:
        """Config should allow custom timeout."""
        config = SkillsConfig(default_timeout_seconds=60.0)

        assert config.default_timeout_seconds == 60.0

    def test_custom_retries(self) -> None:
        """Config should allow custom retry count."""
        config = SkillsConfig(max_retries=5)

        assert config.max_retries == 5

    def test_custom_cache_settings(self) -> None:
        """Config should allow custom cache settings."""
        config = SkillsConfig(
            cache_enabled=False,
            cache_ttl_seconds=3600,
            cache_backend="redis",
        )

        assert config.cache_enabled is False
        assert config.cache_ttl_seconds == 3600
        assert config.cache_backend == "redis"

    def test_custom_permissions_enforcement(self) -> None:
        """Config should allow enabling/disabling permissions."""
        config = SkillsConfig(enforce_permissions=False)

        assert config.enforce_permissions is False

    def test_custom_discovery_settings(self) -> None:
        """Config should allow custom discovery settings."""
        packages = ["myapp.skills", "plugins.skills"]
        config = SkillsConfig(
            auto_discover=True,
            scan_packages=packages,
        )

        assert config.auto_discover is True
        assert config.scan_packages == packages

    def test_custom_builtin_skills(self) -> None:
        """Config should allow customizing builtin skills."""
        skills = ["math_skill", "string_skill"]
        config = SkillsConfig(
            enable_builtin=True,
            builtin_skills=skills,
        )

        assert config.enable_builtin is True
        assert config.builtin_skills == skills

    def test_disable_builtin_skills(self) -> None:
        """Config should allow disabling builtin skills."""
        config = SkillsConfig(enable_builtin=False)

        assert config.enable_builtin is False


class TestSkillsConfigValidation:
    """Test SkillsConfig validation."""

    def test_timeout_must_be_positive(self) -> None:
        """timeout_seconds must be > 0."""
        config = SkillsConfig(default_timeout_seconds=10.5)
        assert config.default_timeout_seconds == 10.5

    def test_max_retries_must_be_non_negative(self) -> None:
        """max_retries must be >= 0."""
        config = SkillsConfig(max_retries=0)
        assert config.max_retries == 0

        config = SkillsConfig(max_retries=5)
        assert config.max_retries == 5

    def test_max_concurrent_must_be_positive(self) -> None:
        """max_concurrent_executions must be >= 1."""
        config = SkillsConfig(max_concurrent_executions=10)
        assert config.max_concurrent_executions == 10

    def test_cache_ttl_must_be_positive(self) -> None:
        """cache_ttl_seconds must be >= 1."""
        config = SkillsConfig(cache_ttl_seconds=300)
        assert config.cache_ttl_seconds == 300


class TestSkillsConfigSkillSources:
    """Test SkillsConfig skill source settings."""

    def test_skill_source_settings(self) -> None:
        """Config should have skill source settings."""
        config = SkillsConfig()

        assert hasattr(config, "enable_skill_sources")
        assert isinstance(config.enable_skill_sources, bool)
        assert hasattr(config, "skill_paths")
        assert isinstance(config.skill_paths, list)
        assert hasattr(config, "enabled_directories")
        assert isinstance(config.enabled_directories, list)

    def test_custom_skill_paths(self) -> None:
        """Config should allow custom skill paths."""
        paths = ["/path/to/skills", "/another/path"]
        config = SkillsConfig(skill_paths=paths)

        assert config.skill_paths == paths

    def test_custom_enabled_directories(self) -> None:
        """Config should allow custom enabled directories."""
        dirs = ["claude_code", "opencode"]
        config = SkillsConfig(enabled_directories=dirs)

        assert config.enabled_directories == dirs


class TestSkillsConfigScriptExecution:
    """Test SkillsConfig script execution settings."""

    def test_script_settings(self) -> None:
        """Config should have script execution settings."""
        config = SkillsConfig()

        assert hasattr(config, "script_timeout_seconds")
        assert config.script_timeout_seconds > 0
        assert hasattr(config, "allowed_script_types")
        assert isinstance(config.allowed_script_types, list)

    def test_custom_script_timeout(self) -> None:
        """Config should allow custom script timeout."""
        config = SkillsConfig(script_timeout_seconds=120)

        assert config.script_timeout_seconds == 120

    def test_custom_allowed_script_types(self) -> None:
        """Config should allow custom allowed script types."""
        types = ["py", "js"]
        config = SkillsConfig(allowed_script_types=types)

        assert config.allowed_script_types == types
