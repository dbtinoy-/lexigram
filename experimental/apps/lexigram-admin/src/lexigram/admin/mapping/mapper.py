"""AdminObjectMapper — registry-based object-to-object mapper for lexigram-admin.

Implements :class:`lexigram.contracts.mapping.ObjectMapperProtocol` so the mapper
can be resolved by any consumer that depends on the contract.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.mapping import ObjectMapperProtocol

logger = get_logger(__name__)


class AdminObjectMapper:
    """Registry-based mapper for admin domain objects.

    Satisfies :class:`~lexigram.contracts.mapping.ObjectMapperProtocol`.

    Example::

        mapper = AdminObjectMapper()
        mapper.register(AdminUserEntity, AdminUserRecord, lambda e: e.to_user())
        record = mapper.map(entity, AdminUserRecord)
    """

    def __init__(self) -> None:
        self._registry: dict[tuple[type, type], Any] = {}

    def register(
        self,
        source_type: type[Any],
        dest_type: type[Any],
        mapper_func: Any,
    ) -> None:
        """Register a mapping function from *source_type* to *dest_type*.

        Args:
            source_type: The type to map from.
            dest_type: The target type to produce.
            mapper_func: Callable that accepts a source instance and returns a dest
                instance.
        """
        self._registry[(source_type, dest_type)] = mapper_func
        logger.debug(
            "admin_mapper_registered",
            source=source_type.__name__,
            dest=dest_type.__name__,
        )

    def map(
        self,
        source: Any,
        dest_type: type[Any],
        *,
        validate: bool = False,
        validator: Any | None = None,
    ) -> Any:
        """Map *source* to an instance of *dest_type*.

        Args:
            source: The source object to transform.
            dest_type: The target type to produce.
            validate: Whether to validate the result after mapping (unused by
                default; pass a *validator* to enable).
            validator: Optional callable ``validator(result) -> None`` that raises
                on invalid data.

        Returns:
            A new instance of *dest_type*.

        Raises:
            KeyError: If no mapping is registered for this type pair.
        """
        key = (type(source), dest_type)
        mapper_func = self._registry.get(key)
        if mapper_func is None:
            raise KeyError(
                f"No mapping registered from {type(source).__name__!r} "
                f"to {dest_type.__name__!r}"
            )
        result = mapper_func(source)
        if validate and validator is not None:
            validator(result)
        return result


# Ensure the class satisfies the protocol at import time (structural check).
_: ObjectMapperProtocol = AdminObjectMapper()

__all__ = ["AdminObjectMapper"]
