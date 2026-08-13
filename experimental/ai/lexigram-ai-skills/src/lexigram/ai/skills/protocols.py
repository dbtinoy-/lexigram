"""Protocol re-exports for skills — convenience surface for consumers."""

from __future__ import annotations

from lexigram.contracts.ai.skills import SkillExecutorProtocol as SkillExecutorProtocol
from lexigram.contracts.ai.skills import SkillProtocol as SkillProtocol
from lexigram.contracts.ai.skills import SkillRegistryProtocol as SkillRegistryProtocol

__all__ = [
    "SkillExecutorProtocol",
    "SkillProtocol",
    "SkillRegistryProtocol",
]
