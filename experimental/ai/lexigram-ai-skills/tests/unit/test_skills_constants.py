"""Unit tests for skills constants."""

from __future__ import annotations

import pytest
from lexigram.ai.skills import constants as const


class TestVersion:
    """Tests for __version__."""

    def test_version_format(self) -> None:
        """Test version is a non-empty string."""
        assert isinstance(const.__version__, str)
        assert len(const.__version__) > 0


class TestEnvironmentPrefixes:
    """Tests for environment variable prefixes."""

    def test_env_prefix(self) -> None:
        """Test ENV_PREFIX value."""
        assert const.ENV_PREFIX == "LEX_AI_SKILLS__"

    def test_env_nested_delimiter(self) -> None:
        """Test ENV_NESTED_DELIMITER value."""
        assert const.ENV_NESTED_DELIMITER == "__"


class TestExecutionDefaults:
    """Tests for execution default constants."""

    def test_default_timeout(self) -> None:
        """Test DEFAULT_TIMEOUT_S is a valid timeout."""
        assert isinstance(const.DEFAULT_TIMEOUT_S, float)
        assert const.DEFAULT_TIMEOUT_S > 0

    def test_default_max_retries(self) -> None:
        """Test DEFAULT_MAX_RETRIES is non-negative."""
        assert isinstance(const.DEFAULT_MAX_RETRIES, int)
        assert const.DEFAULT_MAX_RETRIES >= 0

    def test_default_max_concurrent(self) -> None:
        """Test DEFAULT_MAX_CONCURRENT is positive."""
        assert isinstance(const.DEFAULT_MAX_CONCURRENT, int)
        assert const.DEFAULT_MAX_CONCURRENT > 0


class TestCacheDefaults:
    """Tests for cache default constants."""

    def test_default_cache_enabled(self) -> None:
        """Test DEFAULT_CACHE_ENABLED is a boolean."""
        assert isinstance(const.DEFAULT_CACHE_ENABLED, bool)

    def test_default_cache_ttl(self) -> None:
        """Test DEFAULT_CACHE_TTL_S is positive."""
        assert isinstance(const.DEFAULT_CACHE_TTL_S, int)
        assert const.DEFAULT_CACHE_TTL_S > 0

    def test_default_cache_backend(self) -> None:
        """Test DEFAULT_CACHE_BACKEND is a string."""
        assert isinstance(const.DEFAULT_CACHE_BACKEND, str)
        assert const.DEFAULT_CACHE_BACKEND == "in_memory"


class TestDiscoveryDefaults:
    """Tests for discovery default constants."""

    def test_default_enforce_permissions(self) -> None:
        """Test DEFAULT_ENFORCE_PERMISSIONS is a boolean."""
        assert isinstance(const.DEFAULT_ENFORCE_PERMISSIONS, bool)

    def test_default_auto_discover(self) -> None:
        """Test DEFAULT_AUTO_DISCOVER is a boolean."""
        assert isinstance(const.DEFAULT_AUTO_DISCOVER, bool)

    def test_default_enable_builtin(self) -> None:
        """Test DEFAULT_ENABLE_BUILTIN is a boolean."""
        assert isinstance(const.DEFAULT_ENABLE_BUILTIN, bool)

    def test_default_builtin_skills(self) -> None:
        """Test DEFAULT_BUILTIN_SKILLS is a non-empty tuple."""
        assert isinstance(const.DEFAULT_BUILTIN_SKILLS, tuple)
        assert len(const.DEFAULT_BUILTIN_SKILLS) > 0
        assert "current_datetime" in const.DEFAULT_BUILTIN_SKILLS
        assert "math_calculate" in const.DEFAULT_BUILTIN_SKILLS
        assert "text_summarize" in const.DEFAULT_BUILTIN_SKILLS


class TestSkillPathDefaults:
    """Tests for skill path default constants."""

    def test_default_skill_directories(self) -> None:
        """Test DEFAULT_SKILL_DIRECTORIES is a dict with expected keys."""
        assert isinstance(const.DEFAULT_SKILL_DIRECTORIES, dict)
        assert len(const.DEFAULT_SKILL_DIRECTORIES) > 0
        assert "claude_code" in const.DEFAULT_SKILL_DIRECTORIES
        assert "opencode" in const.DEFAULT_SKILL_DIRECTORIES
        assert "codex" in const.DEFAULT_SKILL_DIRECTORIES

    def test_default_skill_paths(self) -> None:
        """Test DEFAULT_SKILL_PATHS is a non-empty tuple."""
        assert isinstance(const.DEFAULT_SKILL_PATHS, tuple)
        assert len(const.DEFAULT_SKILL_PATHS) > 0


class TestScriptExecutionDefaults:
    """Tests for script execution default constants."""

    def test_default_script_timeout(self) -> None:
        """Test DEFAULT_SCRIPT_TIMEOUT_SECONDS is positive."""
        assert isinstance(const.DEFAULT_SCRIPT_TIMEOUT_SECONDS, int)
        assert const.DEFAULT_SCRIPT_TIMEOUT_SECONDS > 0

    def test_default_allowed_script_types(self) -> None:
        """Test DEFAULT_ALLOWED_SCRIPT_TYPES contains expected types."""
        assert isinstance(const.DEFAULT_ALLOWED_SCRIPT_TYPES, tuple)
        assert "py" in const.DEFAULT_ALLOWED_SCRIPT_TYPES
        assert "sh" in const.DEFAULT_ALLOWED_SCRIPT_TYPES

    def test_default_max_file_size(self) -> None:
        """Test DEFAULT_MAX_FILE_SIZE_BYTES is positive."""
        assert isinstance(const.DEFAULT_MAX_FILE_SIZE_BYTES, int)
        assert const.DEFAULT_MAX_FILE_SIZE_BYTES > 0
        assert const.DEFAULT_MAX_FILE_SIZE_BYTES == 1024 * 1024


class TestProgressiveDisclosure:
    """Tests for progressive disclosure constants."""

    def test_default_lazy_load_context(self) -> None:
        """Test DEFAULT_LAZY_LOAD_CONTEXT is a boolean."""
        assert isinstance(const.DEFAULT_LAZY_LOAD_CONTEXT, bool)
        assert const.DEFAULT_LAZY_LOAD_CONTEXT is True


class TestExports:
    """Tests for __all__ exports."""

    def test_all_contains_expected_names(self) -> None:
        """Test __all__ contains expected constant names."""
        expected = [
            "DEFAULT_ALLOWED_SCRIPT_TYPES",
            "DEFAULT_AUTO_DISCOVER",
            "DEFAULT_BUILTIN_SKILLS",
            "DEFAULT_CACHE_BACKEND",
            "DEFAULT_CACHE_ENABLED",
            "DEFAULT_CACHE_TTL_S",
            "DEFAULT_ENABLE_BUILTIN",
            "DEFAULT_ENFORCE_PERMISSIONS",
            "DEFAULT_LAZY_LOAD_CONTEXT",
            "DEFAULT_MAX_CONCURRENT",
            "DEFAULT_MAX_FILE_SIZE_BYTES",
            "DEFAULT_MAX_RETRIES",
            "DEFAULT_SCRIPT_TIMEOUT_SECONDS",
            "DEFAULT_SKILL_DIRECTORIES",
            "DEFAULT_SKILL_PATHS",
            "DEFAULT_TIMEOUT_S",
            "ENV_NESTED_DELIMITER",
            "ENV_PREFIX",
            "__version__",
        ]
        for name in expected:
            assert name in const.__all__, f"{name} not in __all__"