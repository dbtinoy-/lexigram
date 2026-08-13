"""Test bed for lexigram-events testing."""

from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from lexigram.testing.clients.events.components.test_data import EventTestData

from lexigram.events import CommandBusProtocol, EventBusProtocol, QueryBusProtocol
from lexigram.testing import TestEnvironment


class EventTestBed(TestEnvironment):
    """Test bed for lexigram-events testing.

    Provides a complete testing environment with event buses, command buses,
    query buses, and mock handlers.

    Example:
        >>> async with EventTestBed() as bed:
        ...     event_client = EventTestClient(bed)
        ...     command_client = CommandTestClient(bed)
        ...     # Use clients for testing
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the event test bed."""
        super().__init__(**kwargs)
        self._event_bus: EventBusProtocol | None = None
        self._command_bus: CommandBusProtocol | None = None
        self._query_bus: QueryBusProtocol | None = None

    async def setup(self) -> Any:
        """Setup the test environment with event buses."""
        # First call parent setup
        app = await super().setup()

        # Then setup event-specific providers
        await self.setup_event_providers()

        return app

    async def setup_event_providers(self) -> None:
        """Set up event-related providers."""
        # Create event bus
        self._event_bus = EventBusProtocol()  # type: ignore[misc]
        assert self.container is not None
        self.container.singleton(EventBusProtocol, lambda: self._event_bus)

        # Create command bus
        self._command_bus = CommandBusProtocol()  # type: ignore[misc]
        self.container.singleton(CommandBusProtocol, lambda: self._command_bus)

        # Create query bus
        self._query_bus = QueryBusProtocol()  # type: ignore[misc]
        self.container.singleton(QueryBusProtocol, lambda: self._query_bus)

    async def teardown_event_providers(self) -> None:
        """Clean up event-related providers."""
        # Clear all subscriptions and registrations
        if self._event_bus:
            self._event_bus._subscribers.clear()  # type: ignore[attr-defined]
            self._event_bus._global_handlers.clear()  # type: ignore[attr-defined]

        if self._command_bus:
            self._command_bus._handlers.clear()  # type: ignore[attr-defined]

        if self._query_bus:
            self._query_bus._handlers.clear()  # type: ignore[attr-defined]

        await super().teardown_providers()  # type: ignore[misc]

    @property
    def event_bus(self) -> EventBusProtocol:  # type: ignore[override]
        """Get the event bus."""
        return cast("EventBusProtocol", self._event_bus)

    @property
    def command_bus(self) -> CommandBusProtocol:  # type: ignore[override]
        """Get the command bus."""
        return cast("CommandBusProtocol", self._command_bus)

    @property
    def query_bus(self) -> QueryBusProtocol:  # type: ignore[override]
        """Get the query bus."""
        return cast("QueryBusProtocol", self._query_bus)

    def create_test_data(self, prefix: str = "test") -> EventTestData:
        """Create test data (synchronous helper)."""
        from lexigram.testing.clients.events.components.test_data import EventTestData

        return EventTestData(prefix)

    async def __aenter__(self) -> Any:
        """Async context manager entry."""
        await self.setup()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> Any:
        """Async context manager exit."""
        await self.teardown()  # type: ignore[misc,func-returns-value]
