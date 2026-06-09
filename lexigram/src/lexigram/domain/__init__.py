"""Lexigram Domain — DDD domain primitives for the Lexigram Framework.

Groups the core DDD primitives — entities, value objects, and aggregate
roots — under a single cohesive package.  All types are sourced from the
``models`` subpackage and re-exported here for convenient access.

Domain primitives are pure Python with no infrastructure dependencies.
They integrate with the IoC container via :class:`DomainModule` for
graph completeness but require no provider registration.

Basic Usage::

    from lexigram.domain import Entity, ValueObject, AggregateRoot, DomainModel

    class UserId(ValueObject):
        value: str

    class User(Entity):
        name: str
        email: str

Module Structure:
    - config: Domain configuration (``DomainConfig``)
    - exceptions: Domain exception hierarchy (``DomainError``, ``DomainPolicyViolationError``)
    - models: Entity, ValueObject, AggregateRoot, DomainModel primitives
    - module: ``DomainModule`` IoC registration
    - types: Domain type aliases
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.domain.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.contracts.data.exceptions import UnitOfWorkError
    from lexigram.contracts.exceptions.domain import (
        DomainError,
        FieldError,
        ValidationError,
    )
    from lexigram.domain.config import DomainConfig
    from lexigram.domain.exceptions import DomainPolicyViolationError
    from lexigram.domain.models.aggregate import AggregateRoot
    from lexigram.domain.models.base import DomainModel
    from lexigram.domain.models.entity import ID, Entity
    from lexigram.domain.models.factory import create_model
    from lexigram.domain.models.value_object import ValueObject
    from lexigram.domain.module import DomainModule

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # --- Module ---
    "DomainModule": ("lexigram.domain.module", "DomainModule"),
    # --- Config ---
    "DomainConfig": ("lexigram.domain.config", "DomainConfig"),
    # --- Models ---
    "DomainModel": ("lexigram.domain.models.base", "DomainModel"),
    "Entity": ("lexigram.domain.models.entity", "Entity"),
    "ID": ("lexigram.domain.models.entity", "ID"),
    "ValueObject": ("lexigram.domain.models.value_object", "ValueObject"),
    "AggregateRoot": ("lexigram.domain.models.aggregate", "AggregateRoot"),
    "create_model": ("lexigram.domain.models.factory", "create_model"),
    # --- Exceptions (sourced from contracts) ---
    "DomainError": ("lexigram.contracts.exceptions.domain", "DomainError"),
    "DomainPolicyViolationError": (
        "lexigram.domain.exceptions",
        "DomainPolicyViolationError",
    ),
    "FieldError": ("lexigram.contracts.exceptions.domain", "FieldError"),
    "ValidationError": ("lexigram.contracts.exceptions.domain", "ValidationError"),
    "UnitOfWorkError": ("lexigram.contracts.data.exceptions", "UnitOfWorkError"),
    # --- Protocols (sourced from contracts) ---
    "DomainEvent": ("lexigram.contracts.domain", "DomainEvent"),
    "EventBusProtocol": ("lexigram.contracts.events.protocols", "EventBusProtocol"),
    "RepositoryProtocol": ("lexigram.contracts.data.repository", "RepositoryProtocol"),
    "SpecificationProtocol": ("lexigram.contracts.domain", "SpecificationProtocol"),
    "UnitOfWorkProtocol": (
        "lexigram.contracts.data.sql.unit_of_work",
        "UnitOfWorkProtocol",
    ),
}


def __getattr__(name: str) -> Any:
    """Lazy-load symbols on first access."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__: list[str] = [
    "ID",
    "AggregateRoot",
    "DomainConfig",
    "DomainError",
    "DomainEvent",
    "DomainModel",
    "DomainModule",
    "DomainPolicyViolationError",
    "Entity",
    "EventBusProtocol",
    "FieldError",
    "RepositoryProtocol",
    "SpecificationProtocol",
    "UnitOfWorkError",
    "UnitOfWorkProtocol",
    "ValidationError",
    "ValueObject",
    "create_model",
]
