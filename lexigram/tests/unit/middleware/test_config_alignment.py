"""Tests verifying middleware config constants and model_config alignment."""

from __future__ import annotations


class TestMiddlewareConfigConstants:
    def test_env_prefix_double_underscore(self) -> None:
        from lexigram.middleware.constants import ENV_PREFIX

        assert ENV_PREFIX == "LEX_MIDDLEWARE__"

    def test_env_nested_delimiter_exists(self) -> None:
        from lexigram.middleware.constants import ENV_NESTED_DELIMITER

        assert ENV_NESTED_DELIMITER == "__"

    def test_env_prefix_in_all(self) -> None:
        import lexigram.middleware.constants as c

        assert "ENV_PREFIX" in c.__all__

    def test_env_nested_delimiter_in_all(self) -> None:
        import lexigram.middleware.constants as c

        assert "ENV_NESTED_DELIMITER" in c.__all__

    def test_config_has_no_local_env_prefix(self) -> None:
        """Verify config.py does not redefine ENV_PREFIX locally."""
        import inspect

        import lexigram.middleware.config as cfg_mod

        src = inspect.getsource(cfg_mod)
        assert 'ENV_PREFIX: str = "LEX_MIDDLEWARE__"' not in src
