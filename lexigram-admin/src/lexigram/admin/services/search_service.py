"""Global search service for cross-resource search."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchResult:
    """A single search result from any resource."""

    resource_name: str
    resource_label: str
    id: Any
    title: str
    subtitle: str = ""
    url: str = ""


@dataclass
class SearchResults:
    """Aggregated search results grouped by resource."""

    query: str
    total_count: int = 0
    results: list[SearchResult] = field(default_factory=list)
    resource_counts: dict[str, int] = field(default_factory=dict)

    @property
    def has_results(self) -> bool:
        return self.total_count > 0

    @property
    def group_count(self) -> int:
        return len(self.resource_counts)


class SearchService:
    """Searches across all registered admin resources.

    Discovers resources, runs Resource.search() on each, aggregates
    and returns combined results.
    """

    def __init__(self, resource_manager: Any) -> None:
        self._resource_manager = resource_manager

    async def search(
        self,
        query: str,
        *,
        limit: int = 5,
        per_resource: int = 5,
    ) -> SearchResults:
        """Search across all resources.

        Args:
            query: The search query string.
            limit: Maximum total results.
            per_resource: Maximum results per resource.

        Returns:
            Aggregated SearchResults.
        """
        if not query or not query.strip():
            return SearchResults(query=query)

        query = query.strip()
        results = SearchResults(query=query)
        resources = self.get_searchable_resources()

        for resource_cls in resources:
            try:
                items = await resource_cls.search(query, limit=per_resource)
            except Exception:  # noqa: S112
                continue

            if not items:
                continue

            resource_name = getattr(resource_cls, "name", "")
            resource_label = getattr(resource_cls, "label", resource_name)
            resource_count = 0

            for item in items:
                title = item.get("title", str(item.get("id", "")))
                subtitle = item.get("subtitle", "")
                item_id = item.get("id", "")
                url = f"/admin/{resource_name}/{item_id}"

                results.results.append(
                    SearchResult(
                        resource_name=resource_name,
                        resource_label=resource_label,
                        id=item_id,
                        title=title,
                        subtitle=subtitle,
                        url=url,
                    )
                )
                resource_count += 1

            results.resource_counts[resource_name] = resource_count

        results.total_count = len(results.results)
        if limit > 0 and results.total_count > limit:
            results.results = results.results[:limit]
            results.total_count = limit

        return results

    def get_searchable_resources(self) -> list[Any]:
        """Get list of resources with search_fields configured."""
        resources: list[Any] = []
        try:
            registered = self._resource_manager.get_all_resources()
            for r in registered:
                search_fields = getattr(r, "search_fields", None) or []
                if search_fields:
                    resources.append(r)
        except Exception:  # noqa: S112
            pass
        return resources
