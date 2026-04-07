"""Tests for GraphQL scalars."""

from datetime import date, datetime, time
import pytest

from lexigram.graphql.scalars.date import Date
from lexigram.graphql.scalars.time import Time
from lexigram.graphql.scalars.datetime import DateTime
from lexigram.graphql.scalars.timestamp import Timestamp


class TestDateScalar:
    """Tests for Date scalar."""

    def test_serialize_date(self) -> None:
        """Should serialize date to ISO format."""
        d = date(2024, 1, 15)
        result = Date.serialize(d)
        assert result == "2024-01-15"

    def test_serialize_none(self) -> None:
        """Should serialize None."""
        assert Date.serialize(None) is None

    def test_serialize_invalid(self) -> None:
        """Should raise on invalid type."""
        with pytest.raises(ValueError):
            Date.serialize("invalid")

    def test_parse_value(self) -> None:
        """Should parse ISO string to date."""
        result = Date.parse_value("2024-01-15")
        assert result == date(2024, 1, 15)

    def test_parse_value_none(self) -> None:
        """Should parse None."""
        assert Date.parse_value(None) is None


class TestTimeScalar:
    """Tests for Time scalar."""

    def test_serialize_time(self) -> None:
        """Should serialize time to ISO format."""
        t = time(14, 30, 45)
        result = Time.serialize(t)
        assert result == "14:30:45"

    def test_serialize_none(self) -> None:
        """Should serialize None."""
        assert Time.serialize(None) is None


class TestDateTimeScalar:
    """Tests for DateTime scalar."""

    def test_serialize_datetime(self) -> None:
        """Should serialize datetime to ISO format."""
        dt = datetime(2024, 1, 15, 14, 30, 45)
        result = DateTime.serialize(dt)
        assert result == "2024-01-15T14:30:45"

    def test_serialize_none(self) -> None:
        """Should serialize None."""
        assert DateTime.serialize(None) is None


class TestTimestampScalar:
    """Tests for Timestamp scalar."""

    def test_serialize_datetime(self) -> None:
        """Should serialize datetime to timestamp."""
        dt = datetime(2024, 1, 15, 0, 0, 0)
        result = Timestamp.serialize(dt)
        assert isinstance(result, int)

    def test_serialize_none(self) -> None:
        """Should serialize None."""
        assert Timestamp.serialize(None) is None
