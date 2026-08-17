"""REST API data source adapter for Lexigram Admin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

try:
    import httpx

    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

from lexigram.admin.data.data_source import IDataSource, QueryResult
from lexigram.di.decorators import inject

if TYPE_CHECKING:
    from lexigram.admin.data.query import QuerySpec

T = TypeVar("T")


@inject
class APIDataSource(IDataSource[T], Generic[T]):
    """Data source adapter for REST API endpoints.

    This adapter communicates with a backend API using HTTP requests,
    translating the Query object into URL parameters.
    """

    def __init__(
        self,
        base_url: str,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize with API configuration.

        Args:
            base_url: The base URL of the API endpoint.
            client: Optional httpx.AsyncClient instance.
            timeout: Default timeout for requests in seconds.
            headers: Optional default headers for requests.

        Raises:
            ImportError: If 'httpx' is not installed.
        """
        if not HAS_HTTPX:
            raise ImportError(
                "httpx is required for APIDataSource. Install with: pip install httpx",
            )

        self.base_url = base_url.rstrip("/")
        self._client = client
        self.timeout = timeout
        self.headers = headers or {}

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create an async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout, headers=self.headers)
        return self._client

    async def find_one(self, item_id: Any) -> T | None:
        """Fetch a single entity by its resource ID."""
        client = await self._get_client()
        url = f"{self.base_url}/{item_id}"

        response = await client.get(url)
        if response.status_code == 404:
            return None

        response.raise_for_status()
        return response.json()

    async def find_many(self, query: QuerySpec) -> QueryResult[T]:
        """Fetch multiple entities using query parameters."""
        client = await self._get_client()
        params = self._transform_query(query)

        response = await client.get(self.base_url, params=params)
        response.raise_for_status()

        data = response.json()

        # We assume the API returns a standard structure or a list
        if isinstance(data, list):
            items = data
            return QueryResult(
                items=items,
                total=len(items),
                page=query.page,
                per_page=query.per_page,
            )

        # If it's an object, we try to extract common pagination fields
        items = data.get("items", [])
        total = data.get("total", len(items))

        return QueryResult(
            items=items,
            total=total,
            page=data.get("page", query.page),
            per_page=data.get("per_page", query.per_page),
            has_next=data.get("has_next", False),
            has_prev=data.get("has_prev", False),
            cursor=data.get("cursor"),
        )

    async def count(self, query: QuerySpec) -> int:
        """Count matching entities (often requires a separate endpoint or HEAD)."""
        client = await self._get_client()
        params = self._transform_query(query)
        params["count_only"] = "true"

        response = await client.get(f"{self.base_url}/count", params=params)
        if response.status_code == 404:
            # Fallback to find_many and extract total
            res = await self.find_many(query)
            return res.total

        response.raise_for_status()
        return response.json().get("count", 0)

    async def create(self, data: dict[str, Any]) -> T:
        """Create a new entity via POST."""
        client = await self._get_client()
        response = await client.post(self.base_url, json=data)
        response.raise_for_status()
        return response.json()

    async def update(self, item_id: Any, data: dict[str, Any]) -> T:
        """Update an entity via PATCH or PUT."""
        client = await self._get_client()
        url = f"{self.base_url}/{item_id}"
        response = await client.patch(url, json=data)
        response.raise_for_status()
        return response.json()

    async def delete(self, item_id: Any) -> bool:
        """Delete an entity via DELETE."""
        client = await self._get_client()
        url = f"{self.base_url}/{item_id}"
        response = await client.delete(url)
        return response.status_code in (200, 204)

    async def bulk_create(self, items: list[dict[str, Any]]) -> list[T]:
        """Bulk create via batch POST."""
        client = await self._get_client()
        url = f"{self.base_url}/bulk"
        response = await client.post(url, json={"items": items})
        response.raise_for_status()
        return response.json().get("items", [])

    async def bulk_update(self, ids: list[Any], data: dict[str, Any]) -> int:
        """Bulk update via batch PATCH."""
        client = await self._get_client()
        url = f"{self.base_url}/bulk"
        response = await client.patch(url, json={"ids": ids, "data": data})
        response.raise_for_status()
        return response.json().get("updated_count", 0)

    async def bulk_delete(self, ids: list[Any]) -> int:
        """Bulk delete via batch DELETE."""
        client = await self._get_client()
        url = f"{self.base_url}/bulk"
        response = await client.request("DELETE", url, json={"ids": ids})
        response.raise_for_status()
        return response.json().get("deleted_count", 0)

    def _transform_query(self, query: QuerySpec) -> dict[str, Any]:
        """Translate Query object to URL parameters."""
        params: dict[str, Any] = {
            "page": query.page,
            "per_page": query.per_page,
        }

        if query.sort_by:
            params["sort_by"] = query.sort_by
            params["sort_order"] = query.sort_order

        if query.search:
            params["search"] = query.search
            if query.search_fields:
                params["search_fields"] = ",".join(query.search_fields)

        if query.select_fields:
            params["select"] = ",".join(query.select_fields)

        if query.include:
            params["include"] = ",".join(query.include)

        if query.cursor:
            params["cursor"] = query.cursor

        # Transform filters
        for condition in query.filter_conditions:
            key = f"filter[{condition.field}][{condition.operator.value}]"
            params[key] = condition.value

        return params
