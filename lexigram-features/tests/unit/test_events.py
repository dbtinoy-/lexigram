"""Tests for feature flags events."""

from __future__ import annotations

import pytest

from lexigram.contracts.domain.events import DomainEvent
from lexigram.features.events import FlagChangeEvent


class TestFlagChangeEvent:
    """Tests for FlagChangeEvent."""

    def test_creates_with_all_args(self) -> None:
        """Should create event with all fields."""
        event = FlagChangeEvent(
            flag_name="beta_feature",
            old_enabled=False,
            new_enabled=True,
            actor="admin",
        )
        assert event.flag_name == "beta_feature"
        assert event.old_enabled is False
        assert event.new_enabled is True
        assert event.actor == "admin"

    def test_creates_without_actor(self) -> None:
        """Should create event without actor (defaults to None)."""
        event = FlagChangeEvent(
            flag_name="dark_mode",
            old_enabled=None,
            new_enabled=True,
        )
        assert event.flag_name == "dark_mode"
        assert event.old_enabled is None
        assert event.new_enabled is True
        assert event.actor is None

    def test_creates_with_old_enabled_none(self) -> None:
        """Should create event with old_enabled=None (no prior override)."""
        event = FlagChangeEvent(
            flag_name="new_flag",
            old_enabled=None,
            new_enabled=False,
        )
        assert event.old_enabled is None

    def test_is_domain_event(self) -> None:
        """Should inherit from DomainEvent."""
        event = FlagChangeEvent(
            flag_name="test",
            old_enabled=False,
            new_enabled=True,
        )
        assert isinstance(event, DomainEvent)

    def test_is_frozen(self) -> None:
        """Should be immutable (frozen dataclass)."""
        event = FlagChangeEvent(
            flag_name="test",
            old_enabled=False,
            new_enabled=True,
        )
        with pytest.raises(AttributeError):
            event.flag_name = "changed"

    def test_repr_contains_fields(self) -> None:
        """repr should include all fields."""
        event = FlagChangeEvent(
            flag_name="my_flag",
            old_enabled=False,
            new_enabled=True,
            actor="bot",
        )
        r = repr(event)
        assert "my_flag" in r
        assert "True" in r
