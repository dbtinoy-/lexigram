class TestDecoratorsModule:
    """Tests for ui decorators module."""

    def test_component_decorator_exported(self) -> None:
        """Test component decorator is exported."""
        from lexigram.ui import decorators

        assert hasattr(decorators, "component")

    def test_component_decorator_returns_callable(self) -> None:
        """Test component decorator returns callable."""
        from lexigram.ui.decorators import component

        @component("test")
        def test_func() -> str:
            return "test"

        assert callable(test_func)

    def test_component_decorator_adds_name(self) -> None:
        """Test decorator adds component name."""
        from lexigram.ui.decorators import component

        @component("my_component")
        def my_func() -> str:
            return "test"

        assert hasattr(my_func, "__component_name__")
        assert my_func.__component_name__ == "my_component"

    def test_component_decorator_default_name(self) -> None:
        """Test decorator uses function name by default."""
        from lexigram.ui.decorators import component

        @component()
        def my_default_func() -> str:
            return "test"

        assert my_default_func.__component_name__ == "my_default_func"

    def test_component_decorator_cacheable(self) -> None:
        """Test decorator sets cacheable."""
        from lexigram.ui.decorators import component

        @component("cached", cacheable=True)
        def cached_func() -> str:
            return "test"

        assert cached_func.__component_cacheable__ is True

    def test_component_decorator_not_cacheable_by_default(self) -> None:
        """Test cacheable defaults to False."""
        from lexigram.ui.decorators import component

        @component("test")
        def test_func() -> str:
            return "test"

        assert test_func.__component_cacheable__ is False


class TestConfigModule:
    """Tests for config module."""

    def test_config_exported(self) -> None:
        """Test config module is accessible."""
        from lexigram.ui import config

        assert config is not None


class TestConstantsModule:
    """Tests for constants module."""

    def test_constants_exported(self) -> None:
        """Test constants module is accessible."""
        from lexigram.ui import constants

        assert constants is not None


class TestProtocolsModule:
    """Tests for protocols module."""

    def test_protocols_exported(self) -> None:
        """Test protocols module is accessible."""
        from lexigram.ui import protocols

        assert protocols is not None