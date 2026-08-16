"""MongoDB session / transaction wrapper."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger
from lexigram.nosql.exceptions import TransactionError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = get_logger(__name__)


@asynccontextmanager
async def mongodb_session(client: Any) -> AsyncIterator[Any]:
    """Create a MongoDB client session with optional transaction support.

    Args:
        client: An ``AsyncIOMotorClient`` instance.

    Yields:
        A motor ``ClientSession``.

    Raises:
        TransactionError: If the session cannot be started.
    """
    try:
        async with await client.start_session() as session:
            yield session
    except Exception as exc:
        raise TransactionError(f"MongoDB session failed: {exc}") from exc


@asynccontextmanager
async def mongodb_transaction(client: Any) -> AsyncIterator[Any]:
    """Create a MongoDB session with an active transaction.

    Args:
        client: An ``AsyncIOMotorClient`` instance.

    Yields:
        A motor ``ClientSession`` with an active transaction.

    Raises:
        TransactionError: If the transaction fails.
    """
    try:
        async with await client.start_session() as session:
            async with session.start_transaction():
                yield session
    except Exception as exc:
        raise TransactionError(f"MongoDB transaction failed: {exc}") from exc


__all__ = ["mongodb_session", "mongodb_transaction"]
