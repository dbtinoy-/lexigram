"""ResourceManagerFactory: factory for creating ResourceManager instances."""

from __future__ import annotations

from typing import Any, TypeVar

from lexigram.admin.services.resource_manager import (
    DefaultAuthorizer,
    DefaultValidator,
    ResourceDataSourceProtocol,
    ResourceManager,
    Validator,
)
from lexigram.contracts.admin.authorizer import AdminAuthorizerProtocol
from lexigram.di.decorators import inject

T = TypeVar("T")


@inject
class ResourceManagerFactory:
    """Factory for creating ResourceManager instances.

    Useful for dependency injection and consistent configuration.

    Example:
        >>> factory = ResourceManagerFactory(
        ...     default_authorizer=role_authorizer,
        ... )
        >>> user_manager = factory.create(
        ...     "users",
        ...     user_data_source,
        ...     validator=user_validator,
        ... )
    """

    def __init__(
        self,
        default_authorizer: AdminAuthorizerProtocol | None = None,
        default_validator: Validator | None = None,
    ):
        """Initialize the factory.

        Args:
            default_authorizer: Default authorizer for all managers
            default_validator: Default validator for all managers
        """
        self.default_authorizer = default_authorizer
        self.default_validator = default_validator
        self._managers: dict[str, ResourceManager[Any]] = {}

    def create(
        self,
        resource_name: str,
        data_source: ResourceDataSourceProtocol[T],
        *,
        validator: Validator | None = None,
        authorizer: AdminAuthorizerProtocol | None = None,
    ) -> ResourceManager[T]:
        """Create a ResourceManager instance.

        Args:
            resource_name: Name of the resource
            data_source: Data source for the resource
            validator: Optional validator (uses default if not provided)
            authorizer: Optional authorizer (uses default if not provided)

        Returns:
            Configured ResourceManager instance
        """
        manager: ResourceManager[T] = ResourceManager(
            resource_name=resource_name,
            data_source=data_source,
            validator=validator or self.default_validator,
            authorizer=authorizer or self.default_authorizer,
        )
        self._managers[resource_name] = manager
        return manager

    def get(self, resource_name: str) -> ResourceManager[Any] | None:
        """Get a previously created manager by name.

        Args:
            resource_name: Name of the resource

        Returns:
            ResourceManager if exists, None otherwise
        """
        return self._managers.get(resource_name)


__all__ = [
    "AdminAuthorizerProtocol",
    "DefaultAuthorizer",
    "DefaultValidator",
    "ResourceDataSourceProtocol",
    "ResourceManager",
    "ResourceManagerFactory",
    "Validator",
]
