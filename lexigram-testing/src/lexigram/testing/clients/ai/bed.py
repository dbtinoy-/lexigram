from __future__ import annotations

from lexigram.testing.clients.ai.data import AITestData
from lexigram.testing.fixtures.bed import TestEnvironment


class AITestBed(TestEnvironment):
    def __init__(self, name: str = "ai-test", **kwargs) -> None:
        super().__init__(name, **kwargs)
        self.test_data = AITestData()
