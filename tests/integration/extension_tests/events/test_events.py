"""Core tests: validate Event base behavior without user-specific domain types."""

from datetime import datetime
from uuid import UUID, uuid4

from lexigram.events.messages.event import Event


class MinimalEvent(Event):
    pass


def test_event_defaults():
    eid = uuid4()
    e = MinimalEvent(aggregate_id=eid)
    assert e.aggregate_id == eid
    assert e.event_type == "MinimalEvent"
    assert isinstance(e.occurred_at, datetime)
    assert isinstance(e.event_id, UUID)
