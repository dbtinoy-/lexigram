"""Tests that ``LexigramConfig()`` with no YAML file produces working defaults.

Verifies that the zero-argument constructor of
:class:`~lexigram.config.main.LexigramConfig` returns a fully-operational
configuration object whose ``get_section`` helpers yield valid typed defaults
for the core ``web`` and ``db`` sections.
"""

from __future__ import annotations

from lexigram.config.main import LexigramConfig


class TestZeroConfigWebDefaults:
    """``LexigramConfig()`` → ``get_section("web", WebConfig)`` sensible defaults."""

    def test_bare_config_has_web_defaults(self) -> None:
        """get_section returns a WebConfig with default host and port even without YAML.

        The :class:`~lexigram.web.config.WebConfig` default server host is
        ``"0.0.0.0"`` and port is ``8000`` (defined in ``lexigram.web.constants``).
        """
        from lexigram.web.config import WebConfig

        cfg = LexigramConfig()
        web = cfg.get_section("web", WebConfig)

        assert isinstance(web, WebConfig)
        # server.host and server.port come from WebConfig → ServerConfig defaults
        assert web.server.host == "0.0.0.0"
        assert web.server.port == 8000

    def test_bare_config_web_section_is_enabled_by_default(self) -> None:
        """The default WebConfig has ``enabled=True``."""
        from lexigram.web.config import WebConfig

        cfg = LexigramConfig()
        web = cfg.get_section("web", WebConfig)

        assert web.enabled is True


class TestZeroConfigDbDefaults:
    """``LexigramConfig()`` → ``get_section("db", DatabaseConfig)`` defaults."""

    def test_bare_config_has_db_defaults(self) -> None:
        """get_section returns a DatabaseConfig with a default SQLite URL without YAML.

        The :class:`~lexigram.sql.config.DatabaseConfig` default backend
        URL is ``sqlite:///piccolina.db``, satisfying the "returns something with url"
        requirement stated in the zero-config DX spec.
        """
        from lexigram.sql.config import DatabaseConfig

        cfg = LexigramConfig()
        db = cfg.get_section("db", DatabaseConfig)

        assert isinstance(db, DatabaseConfig)
        url = db.backend.url.get_secret_value()
        assert url  # non-empty
        assert "sqlite" in url.lower()

    def test_bare_config_db_backend_url_is_valid_string(self) -> None:
        """The default database URL is a non-empty string with a recognised scheme."""
        from lexigram.sql.config import DatabaseConfig

        cfg = LexigramConfig()
        db = cfg.get_section("db", DatabaseConfig)

        url = db.backend.url.get_secret_value()
        valid_prefixes = ("sqlite", "postgresql", "postgres", "mysql")
        assert any(url.startswith(p) for p in valid_prefixes), (
            f"Expected a recognised DB URL scheme, got: {url!r}"
        )
