"""Pure, offline tools the support agent calls during ReAct loops.

Bare async functions remain exported (direct invocation + tests);
``SUPPORT_TOOLS`` carries the ``FunctionTool`` wrappers the agent uses.
"""

from __future__ import annotations

from typing import Any

from lexigram.ai.agents import tool
from lexigram.primitives import Registry
from support_agent.repository.fixtures import KB, ORDERS

FULL_REFUND_DAYS = 7
HALF_REFUND_DAYS = 30


async def lookup_order(order_id: str) -> dict[str, Any]:
    """Return order details, or found=False when the id is unknown."""
    order = ORDERS.get(order_id)
    if order is None:
        return {"found": False, "order_id": order_id}
    return {"found": True, **order}


async def calculate_refund(
    order_total: float, days_since_delivery: int
) -> dict[str, Any]:
    """Apply the tiered policy: <=7d full, <=30d half, otherwise none."""
    if days_since_delivery <= FULL_REFUND_DAYS:
        tier, factor = "full", 1.0
    elif days_since_delivery <= HALF_REFUND_DAYS:
        tier, factor = "half", 0.5
    else:
        tier, factor = "none", 0.0
    return {"tier": tier, "amount": round(order_total * factor, 2)}


async def search_kb(query: str) -> list[dict[str, str]]:
    """Rank snippets by overlapping keyword count; top 2 returned."""
    terms = set(query.lower().split())
    scored: list[tuple[int, dict[str, str]]] = []
    for entry in KB:
        overlap = len(terms & set(entry["snippet"].lower().split()))
        if overlap:
            scored.append((overlap, entry))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [entry for _, entry in scored[:2]]


def _build_tools() -> Registry[str, Any]:
    """Framework Registry keyed by tool name."""
    registry: Registry[str, Any] = Registry()
    registry.register(
        "lookup_order",
        tool(description="Look up an order by ID and return status, items, and total.")(
            lookup_order,
        ),
    )
    registry.register(
        "calculate_refund",
        tool(description="Compute the refund amount for a delivered order.")(
            calculate_refund,
        ),
    )
    registry.register(
        "search_kb",
        tool(description="Search the FAQ knowledge base for relevant snippets.")(
            search_kb,
        ),
    )
    return registry


SUPPORT_TOOLS: Registry[str, Any] = _build_tools()
