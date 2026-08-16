"""State machine exceptions."""

from __future__ import annotations

from lexigram.contracts.exceptions import LexigramError

__all__ = ["StateConcurrencyError", "StateError"]


class StateError(LexigramError):
    """Raised when an invalid state transition is attempted.

    Attributes:
        event: The event that was not permitted.
        current_state: The state the machine was in when the error occurred.
    """

    _code: str = "LEX_ERR_WF_017"

    def __init__(self, event: str, current_state: str) -> None:
        super().__init__(
            f"Event {event!r} is not permitted from state {current_state!r}"
        )
        self.event = event
        self.current_state = current_state


class StateConcurrencyError(StateError):
    """Raised when optimistic version checks fail during a transition."""

    _code: str = "LEX_ERR_WF_018"

    def __init__(
        self,
        event: str,
        current_state: str,
        expected_version: int,
        actual_version: int,
    ) -> None:
        super().__init__(event=event, current_state=current_state)
        self.expected_version = expected_version
        self.actual_version = actual_version
        self.message = (
            f"Optimistic lock failed for event {event!r} from {current_state!r}: "
            f"expected version {expected_version}, got {actual_version}"
        )
