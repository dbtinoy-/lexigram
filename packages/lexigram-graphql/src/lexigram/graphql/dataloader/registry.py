"""DataLoaderProtocol Registry for per-request scoping.

This module provides a registry for DataLoaderProtocol factories that creates
fresh loaders per request to prevent cache leakage.
"""

from __future__ import annotations

from collections.abc import Callable

from lexigram.graphql.dataloader.loader import DataLoaderProtocol
from lexigram.primitives.registry import Registry


class DataLoaderRegistry(Registry[str, Callable[[], DataLoaderProtocol]]):
    """Registry for DataLoaderProtocol factories.

    Creates fresh DataLoaders per request to prevent cache leakage
    between concurrent requests.  Extends :class:`Registry` for
    unified introspection and lifecycle hooks.

    Example:
        registry = DataLoaderRegistry()

        def create_user_loader(context):
            return DataLoaderProtocol(
                name="users",
                batch_load_fn=lambda keys: fetch_users(keys),
            )

        registry.register("users", create_user_loader)

        # In request context:
        loaders = registry.create_loaders(context)
        user_loader = loaders["users"]
    """

    def __init__(self) -> None:
        """Initialize the registry."""
        super().__init__(name="graphql.dataloaders", allow_overwrite=True)

    def create_loaders(self) -> dict[str, DataLoaderProtocol]:
        """Create all registered DataLoaders for a new request.

        Returns:
            Dictionary mapping loader names to DataLoaderProtocol instances.
        """
        return {name: factory() for name, factory in self.items()}

    def get_names(self) -> list[str]:
        """Get all registered DataLoaderProtocol names.

        Returns:
            List of DataLoaderProtocol names.
        """
        return list(self.keys())


# Decorator for easy registration
def dataloader(
    name: str,
) -> Callable[[Callable[[], DataLoaderProtocol]], Callable[[], DataLoaderProtocol]]:
    """Decorator to register a DataLoaderProtocol factory.

    Args:
        name: Unique name for the DataLoaderProtocol.

    Returns:
        Decorator function.

    Example:
        @dataloader("users")
        def create_user_loader():
            return DataLoaderProtocol(
                name="users",
                batch_load_fn=lambda keys: fetch_users(keys),
            )
    """

    def decorator(
        factory: Callable[[], DataLoaderProtocol],
    ) -> Callable[[], DataLoaderProtocol]:
        # This will be registered via DataLoaderRegistry
        factory._dataloader_name = name  # type: ignore[attr-defined]
        return factory

    return decorator


__all__ = [
    "DataLoaderRegistry",
    "dataloader",
]
