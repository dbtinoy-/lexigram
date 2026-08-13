"""Testing client for lexigram-events command operations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from lexigram.events import Command, CommandBusProtocol, CommandHandlerProtocol
from lexigram.testing import TestEnvironment


class CommandTestClient:
    """Testing client for lexigram-events command operations.

    Provides high-level testing utilities for command sending and handler testing.

    Example:
        >>> async with EventTestBed() as bed:
        ...     client = CommandTestClient(bed)
        ...     result = await client.send_command(CreateUserCommand(name="John"))
        ...     assert result is not None
    """

    def __init__(self, test_bed: TestEnvironment):
        """Initialize the command test client.

        Args:
            test_bed: The test bed providing command infrastructure
        """
        self.test_bed = test_bed
        self._command_bus: CommandBusProtocol | None = None
        self._sent_commands: list[Command] = []
        self._command_results: dict[str, Any] = {}

    @property
    def command_bus(self) -> CommandBusProtocol:
        """Get the command bus from the test bed."""
        if self._command_bus is None:
            self._command_bus = getattr(self.test_bed, "_command_bus", None)
        return cast("CommandBusProtocol", self._command_bus)

    async def send_command(
        self,
        command: Command,
        expected_success: bool = True,
        expected_result: Any = None,
    ) -> Any:
        """Send a command and track it.

        Args:
            command: The command to send
            expected_success: Whether command should succeed
            expected_result: Expected command result

        Returns:
            Command execution result
        """
        # Track the command
        self._sent_commands.append(command)

        try:
            # Send through the bus
            result = await self.command_bus.send(command)  # type: ignore[attr-defined]
            self._command_results[str(id(command))] = result

            if expected_result is not None and result != expected_result:

                def _raise_expected_result_mismatch() -> None:
                    raise AssertionError(
                        f"Expected command result {expected_result}, got {result}",
                    )

                _raise_expected_result_mismatch()

            return result

        except Exception as e:
            self._command_results[str(id(command))] = e  # Store the exception as result
            if expected_success:
                raise AssertionError(
                    f"Expected command to succeed, but got error: {e}",
                ) from e
            # When expected_success=False, we don't raise - just track the failure
            return None

    async def register_handler(
        self,
        command_type: type[Command],
        handler: CommandHandlerProtocol | Callable,
    ) -> None:
        """Register a command handler.

        Args:
            command_type: The command type to handle
            handler: The handler function or class
        """
        self.command_bus.register(command_type, cast("Callable[..., Any]", handler))  # type: ignore[attr-defined]

    def get_sent_commands(
        self,
        command_type: type[Command] | None = None,
    ) -> list[Command]:
        """Get all sent commands, optionally filtered by type.

        Args:
            command_type: Filter by command type

        Returns:
            List of sent commands
        """
        if command_type:
            return [c for c in self._sent_commands if isinstance(c, command_type)]
        return self._sent_commands.copy()

    def assert_command_sent(
        self,
        command_type: type[Command],
        expected_count: int = 1,
        **filters: Any,
    ) -> list[Command]:
        """Assert that commands of a type were sent.

        Args:
            command_type: The command type to check
            expected_count: Expected number of commands
            **filters: Additional filters for command attributes

        Returns:
            List of matching commands
        """
        commands = self.get_sent_commands(command_type)

        # Apply filters
        if filters:
            commands = [
                command
                for command in commands
                if all(getattr(command, k, None) == v for k, v in filters.items())
            ]

        if len(commands) != expected_count:
            raise AssertionError(
                f"Expected {expected_count} {command_type.__name__} commands, "
                f"found {len(commands)}",
            )

        return commands

    def clear_sent_commands(self) -> None:
        """Clear the sent commands history."""
        self._sent_commands.clear()
        self._command_results.clear()
