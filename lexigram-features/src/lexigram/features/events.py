"""Feature-flag domain events.

Published to the :class:`~lexigram.contracts.events.protocols.EventBusProtocol`
whenever a runtime flag override is applied.  Consumers can subscribe to
:class:`FlagChangeEvent` to react to flag toggles without polling.

Example::

    from lexigram.features.events import FlagChangeEvent

    def on_flag_change(event: FlagChangeEvent) -> None:
        print(f"{event.flag_name} -> {event.new_enabled}")

    event_bus.subscribe(FlagChangeEvent, handler)
"""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.contracts.domain.events import DomainEvent


@dataclass(init=False, frozen=True)
class FlagChangeEvent(DomainEvent):
    """Published when a feature-flag runtime override is applied or cleared.

    Attributes:
        flag_name: Name of the feature flag that changed.
        old_enabled: State before the change (``None`` if no prior override).
        new_enabled: State after the change.
        actor: Optional identifier of the entity that triggered the change.
    """

    flag_name: str = ""
    old_enabled: bool | None = None
    new_enabled: bool = False
    actor: str | None = None

    def __init__(
        self,
        flag_name: str,
        old_enabled: bool | None,
        new_enabled: bool,
        actor: str | None = None,
    ) -> None:
        """Create a :class:`FlagChangeEvent`.

        Args:
            flag_name: Name of the feature flag that changed.
            old_enabled: Prior override state (``None`` if no override was set).
            new_enabled: New override state after the change.
            actor: Optional identifier of who triggered the change.
        """
        super().__init__()
        object.__setattr__(self, "flag_name", flag_name)
        object.__setattr__(self, "old_enabled", old_enabled)
        object.__setattr__(self, "new_enabled", new_enabled)
        object.__setattr__(self, "actor", actor)


__all__ = ["FlagChangeEvent"]
