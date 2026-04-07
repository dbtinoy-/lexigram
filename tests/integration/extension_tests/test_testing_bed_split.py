import pytest

from lexigram.testing import TestEnvironment
from lexigram.testing.fixtures.containers import apply_overrides
from lexigram.testing.mocks import MockProvider


class DummyContainer:
    """Test container that tracks registrations via public API."""

    def __init__(self):
        self._singletons = {}
        self._services = {}
        self._registered_singletons = []  # Track via public interface
        self._registered_services = []  # Track via public interface

    def singleton(self, interface, implementation):
        self._singletons[interface] = implementation
        self._registered_singletons.append(interface)

    def register(self, interface, factory):
        self._services[interface] = factory
        self._registered_services.append(interface)

    def is_singleton(self, interface) -> bool:
        """Check if interface was registered as singleton."""
        return interface in self._registered_singletons

    def has(self, interface) -> bool:
        """Check if interface is registered."""
        return (
            interface in self._registered_singletons
            or interface in self._registered_services
        )


def test_mockprovider_integration():
    class TestProvider(MockProvider):
        name = "mock-test"

    mp = TestProvider()
    assert mp.name == "mock-test"
    assert not mp.started


def test_apply_overrides_singleton():
    container = DummyContainer()
    apply_overrides(container, {str: "value"})
    # Use public API instead of internal _singletons
    assert container.has(str)
    assert container.is_singleton(str)


@pytest.mark.asyncio
async def test_testenvironment_create_mock():
    class TestProvider(MockProvider):
        name = "mock-created"

    bed = TestEnvironment()
    mock = bed.create_mock(TestProvider)
    assert mock.name == "mock-created"
