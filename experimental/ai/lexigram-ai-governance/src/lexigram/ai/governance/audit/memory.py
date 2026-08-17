from __future__ import annotations

from lexigram.ai.governance.audit.models import AIAuditEvent, AuditQuery, AuditSummary


class InMemoryAuditStore:
    """In-memory audit store for testing and development.

    Not suitable for production — events are lost on process restart.
    The store is intentionally simple: append-only list with linear scan
    queries.  For production use, implement :class:`AIAuditStore` with a
    durable backend (e.g. via ``DatabaseProviderProtocol``).
    """

    def __init__(self) -> None:
        self._events: list[AIAuditEvent] = []

    async def record(self, event: AIAuditEvent) -> None:
        """Append event to the in-memory list."""
        self._events.append(event)

    async def query(self, query: AuditQuery) -> list[AIAuditEvent]:
        """Linear scan with filter, ordered by timestamp descending."""
        results = self._filter(query)
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[query.offset : query.offset + query.limit]

    async def aggregate(self, query: AuditQuery) -> AuditSummary:
        """Compute summary statistics over matching events."""
        events = self._filter(query)
        summary = AuditSummary(total_events=len(events))

        for event in events:
            if event.cost is not None:
                summary.total_spend += event.cost
            if event.tokens is not None:
                summary.total_tokens += event.tokens
            if event.status == "denied":
                summary.denied_count += 1

            model_key = event.model or "unknown"
            summary.by_model[model_key] = summary.by_model.get(model_key, 0) + 1

            user_key = event.user_id or "anonymous"
            summary.by_user[user_key] = summary.by_user.get(user_key, 0) + 1

            type_key = event.event_type.value
            summary.by_event_type[type_key] = summary.by_event_type.get(type_key, 0) + 1

        return summary

    def _filter(self, query: AuditQuery) -> list[AIAuditEvent]:
        """Apply filter criteria and return matching events."""
        results: list[AIAuditEvent] = []
        for event in self._events:
            if query.start and event.timestamp < query.start:
                continue
            if query.end and event.timestamp > query.end:
                continue
            if query.event_types and event.event_type not in query.event_types:
                continue
            if query.user_id and event.user_id != query.user_id:
                continue
            if query.model and event.model != query.model:
                continue
            if query.provider and event.provider != query.provider:
                continue
            if query.status and event.status != query.status:
                continue
            results.append(event)
        return results


# ---------------------------------------------------------------------------
# Database-backed implementation
# ---------------------------------------------------------------------------
