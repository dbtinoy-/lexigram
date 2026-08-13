from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from lexigram.ai.governance.audit.models import AuditQuery, AuditSummary
    from lexigram.contracts.ai.governance import AIAuditEvent


@runtime_checkable
class AIAuditStore(Protocol):
    """Protocol for audit event persistence backends.

    Implementations must be async and should treat ``record()`` as
    fire-and-forget safe — governance/LLM hot-paths must never block
    on audit persistence.
    """

    async def record(self, event: AIAuditEvent) -> None:
        """Persist a single audit event.

        Args:
            event: The audit event to store.
        """
        ...

    async def query(self, query: AuditQuery) -> list[AIAuditEvent]:
        """Retrieve audit events matching the given filter.

        Args:
            query: Filter criteria.

        Returns:
            List of matching events ordered by timestamp descending.
        """
        ...

    async def aggregate(self, query: AuditQuery) -> AuditSummary:
        """Compute aggregated statistics for matching events.

        Args:
            query: Filter criteria that scope the aggregation.

        Returns:
            Summary statistics for the matching events.
        """
        ...


# ---------------------------------------------------------------------------
# In-memory implementation (testing / development)
# ---------------------------------------------------------------------------
