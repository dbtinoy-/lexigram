"""Shared mocks for the multi-hop reasoning test modules."""

from __future__ import annotations


class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_count = 0

    async def complete(self, messages, temperature=0.7, max_tokens=None):
        """Return mock response."""
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
            self.call_count += 1
            return MockResponse(response)
        return MockResponse("Default response")


class MockResponse:
    """Mock response object."""

    def __init__(self, content):
        self.content = content

    def is_err(self):
        return False

    def unwrap(self):
        return self

    def unwrap_err(self):
        raise AssertionError("MockResponse has no error")


# Mock Vector Store
class MockVectorStore:
    """Mock vector store for testing."""

    def __init__(self, documents=None):
        self.documents = documents or []

    async def search(self, query, limit=5, filters=None):
        """Return mock search results."""
        # Return different docs based on query
        if "founder" in query.lower() or "tesla" in query.lower():
            return [
                MockDocument("Elon Musk is the founder of Tesla, Inc."),
                MockDocument("Tesla was founded in 2003."),
            ]
        if "elon" in query.lower() or "born" in query.lower():
            return [
                MockDocument("Elon Musk was born on June 28, 1971."),
                MockDocument("Elon Musk is a South African entrepreneur."),
            ]
        if "capital" in query.lower() and "france" in query.lower():
            return [MockDocument("Paris is the capital of France.")]
        if "capital" in query.lower() and "germany" in query.lower():
            return [MockDocument("Berlin is the capital of Germany.")]
        if "population" in query.lower() and "paris" in query.lower():
            return [
                MockDocument("Paris has a population of approximately 2.1 million."),
            ]
        if "population" in query.lower() and "berlin" in query.lower():
            return [
                MockDocument("Berlin has a population of approximately 3.6 million."),
            ]
        if "quantum" in query.lower():
            return [
                MockDocument("Quantum computing uses quantum mechanics principles."),
                MockDocument("Quantum computers use qubits instead of bits."),
                MockDocument(
                    "Quantum computing can solve certain problems exponentially faster.",
                ),
            ]
        return self.documents[:limit]


class MockDocument:
    """Mock document object."""

    def __init__(self, content):
        self.content = content


