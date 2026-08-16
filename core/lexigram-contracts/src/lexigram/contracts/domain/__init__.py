"""Domain-driven design primitives package.

Organized into focused submodules:

* ``base`` – DomainModelProtocol and ID type variable
* ``events`` – DomainEvent and related helpers
* ``aggregates`` – AggregateRootProtocol (protocol only; implementation in ``lexigram.domain``)
* ``specification`` – SpecificationProtocol protocol

Note: DomainModel, Entity, and ValueObject implementations have moved to
``lexigram.domain.base``. Import from there instead.
Note: The concrete ``AggregateRoot`` base class lives in ``lexigram.domain.models.aggregate``.
"""

from __future__ import annotations

# re-export core domain primitives for convenience
from lexigram.contracts.domain.aggregates import AggregateRootProtocol
from lexigram.contracts.domain.base import (
    ID,
    DomainModelProtocol,
)
from lexigram.contracts.domain.events import DomainEvent
from lexigram.contracts.domain.idempotency import (
    IdempotencyRecord,
    IdempotencyStatus,
)
from lexigram.contracts.domain.pagination import (
    CursorPage,
    CursorPageProtocol,
    OffsetPageProtocol,
)
from lexigram.contracts.domain.specification import SpecificationProtocol

__all__: list[str] = [
    "ID",
    "AggregateRootProtocol",
    "CursorPage",
    "CursorPageProtocol",
    "DomainEvent",
    "DomainModelProtocol",
    "IdempotencyRecord",
    "IdempotencyStatus",
    "OffsetPageProtocol",
    "SpecificationProtocol",
]
