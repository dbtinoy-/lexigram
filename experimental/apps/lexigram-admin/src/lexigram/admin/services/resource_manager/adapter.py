"""Safe data-source adapters for the resource manager.

Bridges legacy ``ResourceDataSourceProtocol`` implementations (plain returns,
exception-based failures) and Result-based ``ResultDataSource`` adapters so
the manager always works with ``Result`` values.
"""

from __future__ import annotations

from typing import Any, TypeVar

from lexigram.admin.data.paged_result import PagedResult
from lexigram.admin.data.query import QuerySpec
from lexigram.admin.exceptions import AdminDataError
from lexigram.admin.services.resource_manager.protocols import (
    ResourceDataSourceProtocol,
)
from lexigram.result import Err, Ok, Result

T = TypeVar("T")


def is_result_data_source(data_source: ResourceDataSourceProtocol[T]) -> bool:
    """Check if a data source implements the ResultDataSource protocol.

    Uses a marker attribute for reliable detection rather than isinstance,
    which doesn't check return types for @runtime_checkable protocols.
    Only returns True if explicitly marked as result-based.

    Args:
        data_source: Data source to inspect.

    Returns:
        True only when the adapter is explicitly marked as result-based.
    """
    return getattr(data_source, "returns_result", False) is True


async def find_many_safe(
    data_source: ResourceDataSourceProtocol[T],
    resource_name: str,
    query: QuerySpec,
) -> Result[PagedResult[T], AdminDataError]:
    """Safely call find_many on either data-source flavor.

    If the data source implements ResultDataSource, use it directly.
    Otherwise, wrap the traditional ResourceDataSourceProtocol method with
    error handling.

    Args:
        data_source: Data source performing the lookup.
        resource_name: Resource name used in error messages.
        query: Query specification for filtering/pagination.

    Returns:
        Ok(PagedResult) on success, Err(AdminDataError) on failure.
    """
    if is_result_data_source(data_source):
        return await data_source.find_many(query)  # type: ignore[return-value]

    try:
        result = await data_source.find_many(query)
        return Ok(result)
    except (ConnectionError, RuntimeError, ValueError, OSError) as e:
        return Err(AdminDataError(f"Failed to list {resource_name}: {e}"))


async def find_one_safe(
    data_source: ResourceDataSourceProtocol[T],
    resource_name: str,
    item_id: Any,
) -> Result[T | None, AdminDataError]:
    """Safely call find_one on either data-source flavor.

    Args:
        data_source: Data source performing the lookup.
        resource_name: Resource name used in error messages.
        item_id: Resource identifier.

    Returns:
        Ok(record or None) on success, Err(AdminDataError) on failure.
    """
    if is_result_data_source(data_source):
        return await data_source.find_one(item_id)  # type: ignore[return-value]

    try:
        result = await data_source.find_one(item_id)
        return Ok(result)
    except (ConnectionError, RuntimeError, ValueError, OSError) as e:
        return Err(AdminDataError(f"Failed to find {resource_name} {item_id}: {e}"))


__all__ = ["find_many_safe", "find_one_safe", "is_result_data_source"]
