"""Relation manager domain errors."""

from __future__ import annotations

from lexigram.contracts.exceptions import DomainError

__all__ = ["RelationPersistenceError"]


class RelationPersistenceError(DomainError):
    """Raised when a relation operation needs persistence it does not have.

    Relation managers that perform attach/detach/sync against a pivot
    table require both a configured ``pivot_table`` and an attached
    data source (``data_source`` or :meth:`set_data_source`).
    """
