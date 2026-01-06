"""lexigram-example-ai — AI pipeline reference application.

Demonstrates:
- Multi-turn chat with token-aware history management (lexigram-ai-llm)
- Retrieval-Augmented Generation: embed → retrieve → generate (lexigram-ai-rag)
- Agent tool implementing ToolProtocol (lexigram-ai-agents)
- Conversation domain model with domain events (lexigram-contracts)

See README.md for the full architecture walkthrough.
"""

from __future__ import annotations

from lexigram_example_ai.config import AIConfig
from lexigram_example_ai.module import AIModule

__all__ = [
    "AIConfig",
    "AIModule",
]
