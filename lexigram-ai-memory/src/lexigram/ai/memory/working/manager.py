"""Working memory manager — assembles token-budgeted context windows."""

from __future__ import annotations

from lexigram.ai.memory.config import WorkingMemoryConfig
from lexigram.ai.memory.working.token_budget import TokenBudgetAllocator
from lexigram.contracts.ai.memory import (
    EpisodicMemoryProtocol,
    MemoryEntry,
    MemoryQuery,
    SemanticMemoryProtocol,
)
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)


class WorkingMemoryManager:
    """Assembles the optimal context window from all memory tiers.

    Pulls recent turns from episodic memory and relevant facts from
    semantic memory, fitting everything within a configurable token budget.
    """

    def __init__(
        self,
        episodic: EpisodicMemoryProtocol | None = None,
        semantic: SemanticMemoryProtocol | None = None,
        config: WorkingMemoryConfig | None = None,
    ) -> None:
        """Initialise the working memory manager.

        Args:
            episodic: Episodic memory source for past interactions.
            semantic: Semantic memory source for structured facts.
            config: Token budget configuration.
        """
        self._episodic = episodic
        self._semantic = semantic
        self._config = config or WorkingMemoryConfig()
        self._allocator = TokenBudgetAllocator(self._config)
        self._current_entries: list[MemoryEntry] = []

    async def assemble(
        self,
        query: str,
        token_budget: int,
        session_id: str | None = None,
    ) -> list[MemoryEntry]:
        """Assemble context window from all available memory tiers.

        Args:
            query: Current user query used to retrieve relevant memories.
            token_budget: Total token budget for the assembled context.
            session_id: Optional session scope for retrieval filtering.

        Returns:
            Ordered list of memory entries ready for LLM context injection.
        """
        budget = self._allocator.allocate(token_budget)
        entries: list[MemoryEntry] = []

        if self._episodic:
            filters: dict = {}
            if session_id:
                filters["session_id"] = session_id

            # Recent conversation turns
            recent = await self._episodic.recall(
                MemoryQuery(
                    query=query,
                    top_k=self._config.max_recent_turns,
                    recency_weight=0.8,
                    importance_weight=0.1,
                    relevance_weight=0.1,
                    filters={**filters, "type": "turn"}
                    if filters
                    else {"type": "turn"},
                )
            )
            # Episodic semantic recall
            episodic_results = await self._episodic.recall(
                MemoryQuery(
                    query=query,
                    top_k=10,
                    recency_weight=0.2,
                    importance_weight=0.3,
                    relevance_weight=0.5,
                    filters=filters,
                )
            )

            # Merge: recent turns first, then semantic episodic hits
            seen_ids: set[str] = set()
            for result in recent:
                if result.entry.id not in seen_ids:
                    entries.append(result.entry)
                    seen_ids.add(result.entry.id)
            for result in episodic_results:
                if result.entry.id not in seen_ids:
                    entries.append(result.entry)
                    seen_ids.add(result.entry.id)

            logger.debug(
                "episodic_assembled",
                count=len(entries),
                budget=budget["episodic"] + budget["recent_turns"],
            )

        if self._semantic:
            # Inject top semantic facts as synthetic memory entries
            from datetime import UTC, datetime
            from uuid import uuid4

            facts = await self._semantic.query_facts(subject=query[:100])
            for fact in facts[: budget["semantic"] // 20]:  # rough token estimate
                fact_entry = MemoryEntry(
                    id=str(uuid4()),
                    content=f"{fact.get('subject')} {fact.get('predicate')} {fact.get('object_')}",
                    role="system",
                    timestamp=datetime.now(UTC),
                    importance=fact.get("confidence", 0.5),
                    metadata={"source": "semantic", **fact},
                )
                entries.append(fact_entry)

            logger.debug("semantic_injected", count=len(facts))

        self._current_entries = entries
        return entries

    async def add(self, entry: MemoryEntry) -> None:
        """Add an entry to the current working memory stream.

        Args:
            entry: Memory entry to add.
        """
        self._current_entries.append(entry)
        if self._episodic:
            await self._episodic.record(entry)

    async def get_context_entries(self) -> list[MemoryEntry]:
        """Return the entries currently assembled in working context.

        Returns:
            Current context entry list.
        """
        return list(self._current_entries)

    async def flush(self) -> None:
        """Clear the current context assembly."""
        self._current_entries.clear()

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check health of underlying memory tiers.

        Args:
            timeout: Maximum seconds for the health check.

        Returns:
            HealthCheckResult aggregating episodic and semantic tier health.
        """
        try:
            ep_healthy = True
            sem_healthy = True
            if self._episodic:
                ep_result = await self._episodic.health_check(timeout)
                ep_healthy = ep_result.status == HealthStatus.HEALTHY
            if self._semantic:
                sem_result = await self._semantic.health_check(timeout)
                sem_healthy = sem_result.status == HealthStatus.HEALTHY
            status = (
                HealthStatus.HEALTHY
                if ep_healthy and sem_healthy
                else HealthStatus.DEGRADED
            )
            return HealthCheckResult(component="working_memory", status=status)
        except Exception as exc:  # noqa: BLE001
            return HealthCheckResult(
                component="working_memory",
                status=HealthStatus.UNHEALTHY,
                message=str(exc),
            )


__all__ = ["WorkingMemoryManager"]
