"""Memory system service using Result pattern."""

from __future__ import annotations

from lexigram.contracts.ai.exceptions import AIMemoryError as MemoryServiceError
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)


class MemorySystemWithResultPattern:
    """Memory system using Result pattern."""

    async def store_fact(
        self,
        fact: str,
        category: str = "general",
    ) -> Result[str, MemoryServiceError]:
        """Store a fact in memory."""
        if not fact:
            return Err(MemoryServiceError("Fact cannot be empty"))

        fact_id = f"{category}:{len(fact)}"
        logger.info("fact_stored", category=category, fact_id=fact_id)
        return Ok(fact_id)

    async def retrieve_facts(
        self,
        category: str = "general",
    ) -> Result[list[str], MemoryServiceError]:
        """Retrieve facts from memory."""
        logger.info("facts_retrieved", category=category)
        return Ok([])


__all__ = ["MemorySystemWithResultPattern"]
