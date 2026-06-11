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
    and returns combined results. Resources that opted into indexed
    search (via ``SearchableSpec``) are queried through the search
    integration instead when one is available.
    """

    def __init__(self, resource_manager: Any) -> None:
        self._resource_manager = resource_manager

    async def search(
        self,
        query: str,
        *,
        limit: int = 5,
        per_resource: int = 5,
        rule: str | None = None,
    ) -> SearchResults:
        """Search across all resources.

        Args:
            query: The search query string.
            limit: Maximum total results.
            per_resource: Maximum results per resource.
            rule: Query-builder block JSON string applied to indexed
                resources (ignored for LIKE-based resource search).

        Returns:
            Aggregated SearchResults.
        """
        if not query or not query.strip():
            return SearchResults(query=query)

        query = query.strip()
        results = SearchResults(query=query)
        resources = self.get_searchable_resources()
        integration = self._get_search_integration()

        for resource_cls in resources:
            try:
                spec = self._index_spec(resource_cls)
                if (
                    spec is not None
                    and integration is not None
                    and integration.is_available
                ):
                    items = await self._search_index(
                        integration,
                        resource_cls,
                        spec,
                        query,
                        per_resource,
                        rule,
                    )
                else:
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
        """Get list of resources with search_fields or an index spec."""
        resources: list[Any] = []
        try:
            registered = self._resource_manager.get_all_resources()
            for r in registered:
                search_fields = getattr(r, "search_fields", None) or []
                if search_fields:
                    resources.append(r)
                    continue
                spec = self._index_spec(r)
                if spec is not None and spec.index_name:
                    resources.append(r)
        except Exception:  # noqa: S112
            pass
        return resources

    def get_search_field_catalog(self) -> list[dict[str, Any]]:
        """Build a query-builder field catalog from searchable resources.

        Collects the searchable field names of every resource that is
        searchable (``search_fields`` and/or ``SearchableSpec.fields``),
        deduplicated, labeled for display.

        Returns:
            A list of ``{"name", "label"}`` catalog entries (possibly
            empty when no resource exposes searchable fields).
        """
        catalog: list[dict[str, Any]] = []
        try:
            for resource in self.get_searchable_resources():
                names: list[str] = list(
                    getattr(resource, "search_fields", None) or []
                )
                spec = self._index_spec(resource)
                if spec is not None:
                    names += list(getattr(spec, "fields", None) or [])
                for name in dict.fromkeys(names):
                    catalog.append(
                        {"name": name, "label": name.replace("_", " ").title()}
                    )
        except Exception:  # noqa: S112
            return []
        return catalog

    @staticmethod
    def _index_spec(resource: Any) -> Any | None:
        """Return the resource's SearchableSpec, or None when not opted in."""
        spec_fn = getattr(resource, "search_spec", None)
        if not spec_fn:
            return None
        try:
            return spec_fn()
        except Exception:  # noqa: S112
            return None

    @staticmethod
    def _get_search_integration() -> Any:
        """Return the registered SearchIntegration instance, or None."""
        from lexigram.admin.integrations import get as get_integration

        return get_integration("SearchIntegration")

    async def _search_index(
        self,
        integration: Any,
        resource: Any,
        spec: Any,
        query: str,
        limit: int,
        rule: str | None = None,
    ) -> list[dict[str, Any]]:
        """Query the search index for *resource* and shape docs into hits.

        Index results carry the original document in ``SearchResult.data``
        (the ``SearchableSpec.fields`` plus ``id``); ``search_title_field``/
        ``name``/``title`` resolve the display title, mirroring
        ``Resource.search()``'s hit shape. Backends that return plain dicts
        are handled as well.
        """
        result = await integration.query(
            spec.index_name, query, limit=limit, rule=rule
        )
        raw = result.get("results", []) if isinstance(result, dict) else []
        title_field = getattr(resource, "search_title_field", "name")
        hits: list[dict[str, Any]] = []
        for item in raw:
            doc: Any
            if isinstance(item, dict):
                item_id = item.get("id", "")
                doc = item
            else:
                item_id = getattr(item, "id", None)
                doc = getattr(item, "data", None)
            if not item_id or not isinstance(doc, dict):
                continue
            title = (
                doc.get(title_field)
                or doc.get("name")
                or doc.get("title")
                or str(item_id)
            )
            subtitle = doc.get("email") or doc.get("description") or ""
            hits.append({"id": str(item_id), "title": title, "subtitle": subtitle})
        return hits
