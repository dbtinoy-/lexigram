"""Tests for lexigram/types.py — type aliases and generics."""

from __future__ import annotations


class TestTypeAliases:
    """Tests for type aliases in lexigram/types.py."""

    def test_service_factory_importable(self) -> None:
        """ServiceFactory is importable."""
        from lexigram.types import ServiceFactory

        assert callable(ServiceFactory)

    def test_async_service_factory_importable(self) -> None:
        """AsyncServiceFactory is importable."""
        from lexigram.types import AsyncServiceFactory

        assert callable(AsyncServiceFactory)

    def test_middleware_factory_importable(self) -> None:
        """MiddlewareFactory is importable."""
        from lexigram.types import MiddlewareFactory

        assert callable(MiddlewareFactory)

    def test_guard_function_importable(self) -> None:
        """GuardFunction is importable."""
        from lexigram.types import GuardFunction

        assert callable(GuardFunction)

    def test_filter_handler_importable(self) -> None:
        """FilterHandler is importable."""
        from lexigram.types import FilterHandler

        assert callable(FilterHandler)

    def test_action_handler_importable(self) -> None:
        """ActionHandler is importable."""
        from lexigram.types import ActionHandler

        assert callable(ActionHandler)

    def test_error_handler_importable(self) -> None:
        """ErrorHandler is importable."""
        from lexigram.types import ErrorHandler

        assert callable(ErrorHandler)


class TestTypeVariables:
    """Tests for type variables exported from lexigram/types.py."""

    def test_type_var_t_importable(self) -> None:
        """TypeVar T is importable."""
        from lexigram.types import T

        assert T.__name__ == "T"

    def test_type_var_e_importable(self) -> None:
        """TypeVar E is importable."""
        from lexigram.types import E

        assert E.__name__ == "E"

    def test_type_var_k_importable(self) -> None:
        """TypeVar K is importable."""
        from lexigram.types import K

        assert K.__name__ == "K"

    def test_type_var_v_importable(self) -> None:
        """TypeVar V is importable."""
        from lexigram.types import V

        assert V.__name__ == "V"
