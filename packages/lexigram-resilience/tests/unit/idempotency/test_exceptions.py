"""Tests for idempotency exceptions."""


from lexigram.contracts.exceptions.idempotency import IdempotencyError


class TestIdempotencyError:
    """Tests for IdempotencyError."""

    def test_can_instantiate(self) -> None:
        """Should be able to create an error."""
        error = IdempotencyError("test")
        assert "test" in str(error)
