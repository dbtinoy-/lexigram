"""Tests for idempotency types."""


from lexigram.contracts.domain.idempotency import IdempotencyStatus


class TestIdempotencyStatus:
    """Tests for IdempotencyStatus enum."""

    def test_has_pending_status(self) -> None:
        """Should have PENDING status."""
        assert IdempotencyStatus.PENDING is not None
