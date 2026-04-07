"""Domain events for lexigram-ai-platform prompt submodule.

Emitted when prompt lifecycle operations complete. Consumed by analytics,
audit, and prompt optimization systems.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from lexigram.contracts.domain.events import DomainEvent

__all__ = [
    "PromptRenderedEvent",
]


@dataclass(frozen=True, init=False)
class PromptRenderedEvent(DomainEvent):
    """Emitted when a prompt template is rendered with variables.

    Consumed by: analytics, prompt optimization, audit.
    """

    template_name: str = field(kw_only=True)
    variable_count: int = field(kw_only=True)
