"""Shared fixtures/stubs for test_query_transformation tests."""

from __future__ import annotations


class _OkResult:
    """Minimal Result-like success wrapper for tests."""

    def __init__(self, value):
        self._value = value

    def is_err(self):
        return False

    def unwrap(self):
        return self._value

    def unwrap_err(self):
        raise AssertionError("_OkResult has no error")


class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self, responses=None):
        """Initialize with predefined responses."""
        self.responses = responses or []
        self.call_count = 0

    async def complete(self, messages, temperature=0.7, max_tokens=None):
        """Return predefined response."""
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return _OkResult(response)
        return _OkResult("default response")
