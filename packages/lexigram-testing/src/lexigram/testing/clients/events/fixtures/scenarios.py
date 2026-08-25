"""Scenario fixtures for events testing.

Provides complete end-to-end scenarios, such as an event-sourced bank
account exercise, for integration-style tests.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest


@pytest.fixture
def event_sourcing_scenario() -> Any:
    """Complete event sourcing scenario for testing."""
    from lexigram.events import (  # - local import for test fixtures
        AggregateRoot,
        Event,
    )

    class AccountAggregate(AggregateRoot):
        balance: float = 0.0

        def deposit(self, amount: float) -> Any:
            if amount <= 0:
                raise ValueError("Deposit amount must be positive")
            self.balance += amount

        def withdraw(self, amount: float) -> Any:
            if amount <= 0:
                raise ValueError("Withdrawal amount must be positive")
            if amount > self.balance:
                raise ValueError("Insufficient funds")
            self.balance -= amount

    class DepositedEvent(Event):
        amount: float

    class WithdrawnEvent(Event):
        amount: float

    return {
        "aggregate": AccountAggregate(),
        "events": [
            DepositedEvent(aggregate_id=uuid4(), amount=100.0),
            WithdrawnEvent(aggregate_id=uuid4(), amount=25.0),
            DepositedEvent(aggregate_id=uuid4(), amount=50.0),
        ],
        "expected_balance": 125.0,
    }
