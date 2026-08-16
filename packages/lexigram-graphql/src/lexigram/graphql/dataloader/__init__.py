"""DataLoaderProtocol module.

This module provides DataLoaderProtocol implementation for efficient
batching and caching of data fetches in GraphQL resolvers.
"""

from __future__ import annotations

from lexigram.graphql.dataloader.batch import (
    BatchFunction,
    batch_load,
)
from lexigram.graphql.dataloader.cache import (
    InMemoryCache,
    LoaderCache,
)
from lexigram.graphql.dataloader.loader import (
    DataLoaderProtocol,
    create_loader,
)

__all__ = [
    # Batch
    "BatchFunction",
    # Loader
    "DataLoaderProtocol",
    "InMemoryCache",
    # Cache
    "LoaderCache",
    "batch_load",
    "create_loader",
]
