"""Deterministic scenario scripts driving the scripted LLM.

Each entry is one full completion. ReAct parses THOUGHT/ACTION/
ACTION_INPUT markers and terminates on FINAL_ANSWER (react.py:53-81).
"""

from __future__ import annotations

from dataclasses import dataclass, field

HAPPY_SCRIPT: list[str] = [
    (
        "THOUGHT: I need the order details first.\n"
        "ACTION: lookup_order\n"
        'ACTION_INPUT: {"order_id": "A-100"}'
    ),
    (
        "THOUGHT: The order shipped via FastShip.\n"
        "FINAL_ANSWER: Order A-100 shipped via FastShip, tracking FS123456789."
    ),
]

MULTI_TOOL_SCRIPT: list[str] = [
    (
        "THOUGHT: Look up the order.\n"
        "ACTION: lookup_order\n"
        'ACTION_INPUT: {"order_id": "A-102"}'
    ),
    (
        "THOUGHT: Delivered recently; compute the refund.\n"
        "ACTION: calculate_refund\n"
        'ACTION_INPUT: {"order_total": 74.5, "days_since_delivery": 10}'
    ),
    (
        "THOUGHT: Half refund applies.\n"
        "FINAL_ANSWER: You are eligible for a $37.25 half refund."
    ),
]

FAILURE_SCRIPT: list[str] = [
    "THOUGHT: Try the wrong tool.\nACTION: teleport_order\nACTION_INPUT: {}",
    (
        "THOUGHT: That tool does not exist; answer directly.\n"
        "FINAL_ANSWER: I could not complete that request."
    ),
]


@dataclass(frozen=True)
class Scenario:
    """One deterministic demo act: key, display label, scripted turns."""

    key: str
    label: str
    script: list[str] = field(default_factory=list)


SCENARIOS: dict[str, Scenario] = {
    "happy": Scenario("happy", "Happy path", HAPPY_SCRIPT),
    "multi_tool": Scenario("multi_tool", "Multi-tool", MULTI_TOOL_SCRIPT),
    "failure": Scenario("failure", "Failure", FAILURE_SCRIPT),
}
