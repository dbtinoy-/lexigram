"""Finite state machine implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.logging import get_logger
from lexigram.workflow.state.exceptions import StateConcurrencyError, StateError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from lexigram.contracts.workflow.protocols import (
        StateMachineProtocol,
        StatePersistenceProtocol,
        StateTransitionRecord,
    )
    from lexigram.workflow.state.models import State, Transition

logger = get_logger(__name__)

__all__ = ["StateMachine"]


class StateMachine:
    """General-purpose async finite state machine.

    Callers define the set of allowed states and their permitted transitions
    upfront, then drive the machine with :meth:`transition`.  Entry/exit hooks
    and per-transition guards let consumers add side-effects and conditional
    logic without subclassing.

    Example::

        from lexigram.workflow.state import StateMachine, State, Transition

        sm = StateMachine(
            states=[
                State("idle", transitions={"start": Transition("start", "running")}),
                State("running", transitions={"stop": Transition("stop", "idle"),
                                              "fail": Transition("fail", "error")}),
                State("error"),
            ],
            initial_state="idle",
        )

        current = await sm.transition("start")
        assert current == "running"

    Args:
        states: All states recognised by this machine.
        initial_state: Name of the state the machine starts in.

    Raises:
        ValueError: When *initial_state* is not in *states*.
    """

    def __init__(
        self,
        states: list[State],
        initial_state: str,
        persistence: StatePersistenceProtocol | None = None,
        machine_id: str | None = None,
    ) -> None:
        self._states: dict[str, State] = {s.name: s for s in states}
        if initial_state not in self._states:
            raise ValueError(
                f"Initial state {initial_state!r} is not in the states list."
            )
        if persistence is not None and not machine_id:
            raise ValueError("machine_id is required when persistence is enabled")
        self._initial_state = initial_state
        self._current = initial_state
        self._version = 0
        self._persistence = persistence
        self._machine_id = machine_id
        logger.debug(
            "state_machine.created",
            initial_state=initial_state,
            states=list(self._states),
            machine_id=machine_id,
            persistence=type(persistence).__name__ if persistence is not None else None,
        )

    # ------------------------------------------------------------------
    # StateMachineProtocol
    # ------------------------------------------------------------------

    @property
    def current_state(self) -> str:
        """The name of the active state.

        Returns:
            String name of the current state.
        """
        return self._current

    @property
    def version(self) -> int:
        """Current monotonic transition version."""
        return self._version

    def can_transition(self, event: str) -> bool:
        """Return whether *event* is permitted from the current state.

        Args:
            event: The event name to test.

        Returns:
            ``True`` when the transition exists; ``False`` otherwise.
        """
        return event in self._states[self._current].transitions

    async def transition(self, event: str) -> str:
        """Trigger *event*, advancing to the configured target state.

        Invokes ``on_exit`` of the source state, evaluates any guard on the
        transition (skipping the transition and raising :exc:`StateError` if
        the guard returns ``False``), changes state, then invokes
        ``on_enter`` of the destination state and the transition's own
        ``on_transition`` callback.

        Args:
            event: The event name that triggers the transition.

        Returns:
            Name of the new current state.

        Raises:
            StateError: When *event* is not permitted from the current state,
                or when a guard returns ``False``.
        """
        source_state = self._states[self._current]
        if event not in source_state.transitions:
            raise StateError(event, self._current)

        tr: Transition = source_state.transitions[event]

        if tr.guard is not None:
            allowed = await tr.guard()
            if not allowed:
                raise StateError(event, self._current)

        if source_state.on_exit is not None:
            await source_state.on_exit()

        previous = self._current
        self._current = tr.target
        self._version += 1

        if self._persistence is not None:
            assert self._machine_id is not None
            expected_version = self._version - 1
            try:
                self._version = await self._persistence.append_transition(
                    machine_id=self._machine_id,
                    from_state=previous,
                    event=event,
                    to_state=self._current,
                    expected_version=expected_version,
                )
            except RuntimeError as exc:
                actual_version = await self._persistence.get_current_version(
                    self._machine_id
                )
                self._current = previous
                self._version = actual_version
                raise StateConcurrencyError(
                    event=event,
                    current_state=previous,
                    expected_version=expected_version,
                    actual_version=actual_version,
                ) from exc

        target_state = self._states[self._current]

        logger.debug(
            "state_machine.transitioned",
            transition_event=event,
            from_state=previous,
            to_state=self._current,
        )

        if target_state.on_enter is not None:
            await target_state.on_enter()

        if tr.on_transition is not None:
            await tr.on_transition(event, self._current)

        return self._current

    async def recover(self, machine_id: str | None = None) -> str:
        """Rebuild current state from persisted transition history.

        Args:
            machine_id: Optional machine identifier override.

        Returns:
            Recovered current state name.
        """
        if self._persistence is None:
            return self._current

        resolved_machine_id = machine_id or self._machine_id
        if not resolved_machine_id:
            raise ValueError("machine_id is required to recover persisted state")

        transitions = await self._persistence.load_transitions(resolved_machine_id)
        self._rebuild_from_transitions(transitions)
        self._machine_id = resolved_machine_id

        logger.debug(
            "state_machine.recovered",
            machine_id=resolved_machine_id,
            current_state=self._current,
            version=self._version,
            transition_count=len(transitions),
        )
        return self._current

    def _rebuild_from_transitions(
        self,
        transitions: Sequence[StateTransitionRecord],
    ) -> None:
        """Apply persisted transitions to rebuild in-memory state."""
        current = self._initial_state
        version = 0
        for record in transitions:
            if record.from_state != current:
                logger.warning(
                    "state_machine.recovery_inconsistent_from_state",
                    expected=current,
                    actual=record.from_state,
                    machine_id=record.machine_id,
                    version=record.version,
                )
            current = record.to_state
            version = record.version

        self._current = current
        self._version = version


# Verify structural subtyping at import time (mypy also checks this).
_: StateMachineProtocol = StateMachine.__new__(StateMachine)
