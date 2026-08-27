"""Container-managed protection knob (resilient-rates FaultController idiom).

This toggle is registered as a singleton in the DI container.
Both the API controller and the assistant service share the same
instance — flip it in the UI and every subsequent request sees the
change immediately.  This is the Lexigram pattern for live config
that doesn't require a restart.
"""

from __future__ import annotations


class PolicyToggle:
    """Flips guard + governance protection on/off live.

    In a real app, this could wrap a feature flag service
    or a database-backed config.  The pattern stays the same: a
    shared mutable object registered as singleton, with a simple
    getter/setter interface.  Tests flip it directly via toggle.set().
    """

    def __init__(self) -> None:
        self._enabled = True

    @property
    def enabled(self) -> bool:
        """Whether protection currently applies."""
        return self._enabled

    def set(self, enabled: bool) -> None:
        """Flip protection."""
        self._enabled = enabled
