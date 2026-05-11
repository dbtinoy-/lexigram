"""Typed gateway configuration for the relay gateway.

Holds the static channel table plus model-suffix and provider-options
metadata. The suffix and option maps are consumed at conversion time by
the service layer; channel selection never reads them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from lexigram.contracts.ai.relay import JsonValue, RelayChannel

__all__ = ["RelayGatewayConfig"]


@dataclass(frozen=True, slots=True)
class RelayGatewayConfig:
    """Static configuration backing ``RelayChannelRegistry`` selection.

    Attributes:
        channels: Ordered channel configurations. Selection filters before
            sorting, so order is never observable in the result except as
            the stable ``name`` tiebreak. Duplicate names are rejected.
        model_suffix: Channel name to a suffix (e.g. ``":thinking"``)
            appended to the outbound model alias at the service layer.
            Selection does not use this field.
        provider_options: Channel name to provider-specific options merged
            into ``RelayConversionContext`` at conversion time. Selection
            does not use this field.
    """

    channels: tuple[RelayChannel, ...] = ()
    model_suffix: Mapping[str, str] = field(default_factory=dict)
    provider_options: Mapping[str, Mapping[str, JsonValue]] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        """Reject configurations with duplicate channel names."""
        names = [channel.name for channel in self.channels]
        if len(names) != len(set(names)):
            raise ValueError("duplicate channel names in RelayGatewayConfig")
