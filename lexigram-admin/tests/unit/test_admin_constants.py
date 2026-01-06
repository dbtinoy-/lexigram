"""Unit tests for lexigram-admin constants."""

import pytest

from lexigram.admin.constants import (
    DEFAULT_ADMIN_PATH,
    DEFAULT_ITEMS_PER_PAGE,
    DEFAULT_MAX_ITEMS_PER_PAGE,
    DEFAULT_SEARCH_LIMIT,
    DEFAULT_SESSION_LIFETIME,
    ENV_NESTED_DELIMITER,
    ENV_PREFIX,
    LAYOUT_SIDEBAR,
    LAYOUT_TOP_NAV,
    PERMISSION_ADMIN,
    PERMISSION_CREATE,
    PERMISSION_DELETE,
    PERMISSION_EDIT,
    PERMISSION_VIEW,
    THEME_DARK,
    THEME_LIGHT,
    THEME_SYSTEM,
    __version__,
)


class TestAdminConstants:
    """Tests for admin constants."""

    def test_env_prefix(self) -> None:
        """Test environment variable prefix."""
        assert ENV_PREFIX == "LEX_ADMIN__"
        assert isinstance(ENV_PREFIX, str)

    def test_env_nested_delimiter(self) -> None:
        """Test environment nested delimiter."""
        assert ENV_NESTED_DELIMITER == "__"
        assert isinstance(ENV_NESTED_DELIMITER, str)

    def test_default_admin_path(self) -> None:
        """Test default admin path."""
        assert DEFAULT_ADMIN_PATH == "/admin"
        assert isinstance(DEFAULT_ADMIN_PATH, str)

    def test_default_items_per_page(self) -> None:
        """Test default items per page."""
        assert DEFAULT_ITEMS_PER_PAGE == 25
        assert isinstance(DEFAULT_ITEMS_PER_PAGE, int)
        assert DEFAULT_ITEMS_PER_PAGE > 0

    def test_default_max_items_per_page(self) -> None:
        """Test default max items per page."""
        assert DEFAULT_MAX_ITEMS_PER_PAGE == 200
        assert isinstance(DEFAULT_MAX_ITEMS_PER_PAGE, int)
        assert DEFAULT_MAX_ITEMS_PER_PAGE > 0

    def test_default_search_limit(self) -> None:
        """Test default search limit."""
        assert DEFAULT_SEARCH_LIMIT == 50
        assert isinstance(DEFAULT_SEARCH_LIMIT, int)
        assert DEFAULT_SEARCH_LIMIT > 0

    def test_default_session_lifetime(self) -> None:
        """Test default session lifetime."""
        assert DEFAULT_SESSION_LIFETIME == 86400
        assert isinstance(DEFAULT_SESSION_LIFETIME, int)
        assert DEFAULT_SESSION_LIFETIME > 0

    def test_permission_constants(self) -> None:
        """Test permission constants."""
        assert PERMISSION_VIEW == "view"
        assert PERMISSION_CREATE == "create"
        assert PERMISSION_EDIT == "edit"
        assert PERMISSION_DELETE == "delete"
        assert PERMISSION_ADMIN == "admin"

    def test_layout_constants(self) -> None:
        """Test layout constants."""
        assert LAYOUT_SIDEBAR == "sidebar"
        assert LAYOUT_TOP_NAV == "top_nav"

    def test_theme_constants(self) -> None:
        """Test theme constants."""
        assert THEME_LIGHT == "light"
        assert THEME_DARK == "dark"
        assert THEME_SYSTEM == "system"

    def test_version(self) -> None:
        """Test version constant."""
        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_all_exports(self) -> None:
        """Test that all constants are properly exported."""
        from lexigram.admin import constants

        expected = [
            "DEFAULT_ADMIN_PATH",
            "DEFAULT_ITEMS_PER_PAGE",
            "DEFAULT_MAX_ITEMS_PER_PAGE",
            "DEFAULT_SEARCH_LIMIT",
            "DEFAULT_SESSION_LIFETIME",
            "ENV_NESTED_DELIMITER",
            "ENV_PREFIX",
            "LAYOUT_SIDEBAR",
            "LAYOUT_TOP_NAV",
            "PERMISSION_ADMIN",
            "PERMISSION_CREATE",
            "PERMISSION_DELETE",
            "PERMISSION_EDIT",
            "PERMISSION_VIEW",
            "THEME_DARK",
            "THEME_LIGHT",
            "THEME_SYSTEM",
            "__version__",
        ]
        for name in expected:
            assert hasattr(constants, name)
