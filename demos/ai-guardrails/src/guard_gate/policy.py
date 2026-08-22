"""Container-managed protection knob (resilient-rates FaultController idiom)."""

from __future__ import annotations


class PolicyToggle:
    """Flips guard + governance protection on/off live."""

    def __init__(self) -> None:
        self._enabled = True

    @property
    def enabled(self) -> bool:
        """Whether protection currently applies."""
        return self._enabled

    def set(self, enabled: bool) -> None:
        """Flip protection."""
        self._enabled = enabled
