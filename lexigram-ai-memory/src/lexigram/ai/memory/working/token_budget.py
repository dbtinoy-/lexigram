"""Token budget allocation for working memory assembly."""

from __future__ import annotations

from lexigram.ai.memory.config import WorkingMemoryConfig


class TokenBudgetAllocator:
    """Distributes a total token budget across working memory sections.

    The budget is split in this order:
    1. System prompt receives a fixed allocation.
    2. The remaining budget is divided among recent turns, episodic recall,
       semantic facts, and tool descriptions using the configured fractions.
    """

    def __init__(self, config: WorkingMemoryConfig | None = None) -> None:
        """Initialise with optional config.

        Args:
            config: Working memory configuration; uses defaults if None.
        """
        self._config = config or WorkingMemoryConfig()

    def allocate(self, total_tokens: int) -> dict[str, int]:
        """Compute token allocations for each memory section.

        Args:
            total_tokens: Total token budget available.

        Returns:
            Mapping of section name to token allocation.
        """
        system = min(self._config.system_prompt_tokens, total_tokens)
        remaining = max(0, total_tokens - system)

        sections = {
            "recent_turns": int(remaining * self._config.recent_turns_fraction),
            "episodic": int(remaining * self._config.episodic_fraction),
            "semantic": int(remaining * self._config.semantic_fraction),
            "tool_descriptions": int(
                remaining * self._config.tool_descriptions_fraction
            ),
        }
        # Distribute any rounding remainder to the largest bucket
        allocated = sum(sections.values())
        remainder = remaining - allocated
        if remainder > 0 and sections:
            largest = max(sections, key=sections.__getitem__)
            sections[largest] += remainder

        return {"system_prompt": system, **sections}

    def budget_for(self, section: str, total_tokens: int) -> int:
        """Return the token budget for a single named section.

        Args:
            section: Section name (e.g. 'episodic', 'semantic').
            total_tokens: Total token budget.

        Returns:
            Token count allocated to the requested section.
        """
        return self.allocate(total_tokens).get(section, 0)


__all__ = ["TokenBudgetAllocator"]
