"""Base resource class for Admin Resources.

.. stability:: stable

Resources define the configuration for admin UI views including
columns, actions, filters, and permissions.

Cohesive concerns are composed via sibling mixins:

- :class:`~lexigram.admin.resources.specs.IntegrationSpecsMixin` —
  ``cache_spec`` / ``search_spec`` / ``resilient_spec`` builders
- :class:`~lexigram.admin.resources.hooks.ResourceHooksMixin` — record
  lifecycle hooks and action-hook attachment
- :class:`~lexigram.admin.resources.table_config.TableConfigMixin` —
  table/form-display/layout configuration resolvers
- :class:`~lexigram.admin.resources.archive_ops.ArchiveOperationsMixin` —
  clone/restore/purge flows
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, ClassVar
import warnings

from lexigram.admin.data.data_source import IDataSource
from lexigram.admin.resources.archive_ops import ArchiveOperationsMixin
from lexigram.admin.resources.form_guard import PROTECTED_FORM_FIELDS
from lexigram.admin.resources.hooks import ResourceHooksMixin
from lexigram.admin.resources.specs import IntegrationSpecsMixin
from lexigram.admin.resources.table_config import TableConfigMixin

if TYPE_CHECKING:
    from lexigram.admin.actions.base import HeaderAction
    from lexigram.admin.forms.components import FormBase
    from lexigram.admin.rbac.schema import ResourcePermissions
    from lexigram.admin.relations.manager_ext import RelationManager
    from lexigram.admin.ui.filters.base import Filter
    from lexigram.domain import DomainModel
    from lexigram.ui.actions import Action, BulkAction
    from lexigram.ui.columns import Column

_VALID_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)?$")


def _validate_resource_name(name: str) -> None:
    """Validate a Resource name is a dotted slug.

    Raises ``ValueError`` if the name doesn't match
    the slug pattern (lowercase alphanumeric with underscores,
    optionally dotted for namespaced resources).
    """
    if not _VALID_NAME_RE.match(name):
        raise ValueError(
            f"Resource name {name!r} is not a valid slug. "
            f"Allowed: lowercase alphanumeric + underscores, "
            f"optionally dotted for namespaced resources. "
            f"Pattern: {_VALID_NAME_RE.pattern!r}"
        )


class Resource(
    ResourceHooksMixin,
    IntegrationSpecsMixin,
    TableConfigMixin,
    ArchiveOperationsMixin,
):
    """Base class for Admin Resources.

    Resources define the configuration for list views (tables) and form views
    in the admin interface. Subclass this to create custom resources.

    Example:
        >>> class UserResource(Resource):
        ...     model = UserModel
        ...     icon = "users"
        ...     columns = [
        ...         TextColumn("name").sortable(),
        ...         TextColumn("email").sortable(),
        ...     ]
        ...     actions = [EditAction(), DeleteAction()]
    """

    # Data Model
    model: type[DomainModel] | None = None

    # Registration metadata
    name: str | None = None
    cluster: str | None = None
    """Cluster name for navigation grouping."""

    # Permissions
    permissions: ResourcePermissions | None = None

    # UI Configuration
    icon: str = "box"
    label: str | None = None
    visible_in_sidebar: bool = True

    # Table Configuration
    columns: list[Column] = []
    actions: list[Action] = []
    action_layout: str = "horizontal"
    header_actions: list[HeaderAction] = []
    bulk_actions: list[BulkAction] = []
    filters: list[Filter] = []

    # New declarative field system — SchemaField instances
    # When set, columns and filters are derived automatically.
    fields: list[Any] = []

    page_size: int = 20
    default_sort: str | None = None

    # Optional default grouping column (users can override via the toolbar)
    group_by: str | None = None

    # Table empty-state copy overrides (None = framework defaults)
    empty_state_title: str | None = None
    empty_state_message: str | None = None
    empty_state_icon: str | None = None

    # Form Configuration
    form_class: type[FormBase] | None = None
    # Form display mode: "page" (full page), "modal" (centered modal), "slider" (side panel)
    form_display_mode: str = "modal"  # Options: "page", "modal", "slider"
    # Model fields excluded from generated forms (e.g. secrets, framework-managed
    # columns).  Resources may extend the default to exclude their own fields.
    form_exclude_fields: tuple[str, ...] = ("id", "created_at", "updated_at")

    # Resource Config (Optional fluent config)
    config: Any = None

    # Form security — see lexigram.admin.resources.form_guard
    protected_form_fields: ClassVar[frozenset[str]] = PROTECTED_FORM_FIELDS
    """Framework-managed columns never settable from form data."""
    form_allow_extra_fields: bool = False
    """When True, form keys outside the model are kept (protected fields still stripped)."""

    # Class attributes holding mutable collections. Each subclass gets its
    # own copy so appending at class level never leaks into sibling
    # resources that did not override the attribute.
    _COLLECTION_ATTRS: ClassVar[tuple[str, ...]] = (
        "columns",
        "actions",
        "header_actions",
        "bulk_actions",
        "filters",
        "fields",
        "relations",
        "search_fields",
        "form_exclude_fields",
    )

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Validate and auto-derive backward-compat attributes when using ``fields``."""
        super().__init_subclass__(**kwargs)

        own = cls.__dict__
        declared = set(own)

        # Copy inherited mutable collection defaults per subclass so class-level
        # appends are isolated (no shared mutable class state). Subclasses that
        # define their own list keep its identity.
        for attr in cls._COLLECTION_ATTRS:
            if attr in declared:
                continue
            value = getattr(cls, attr, None)
            if isinstance(value, list):
                setattr(cls, attr, list(value))

        # Validate name if explicitly set — must be a dotted slug
        if "name" in own and own["name"] is not None:
            _validate_resource_name(own["name"])

        has_fields = "fields" in declared
        has_columns = "columns" in declared
        has_filters = "filters" in declared
        has_form_class = "form_class" in declared

        if has_fields:
            if has_columns or has_filters or has_form_class:
                warnings.warn(
                    "Resource.fields is the new declarative path for schema "
                    "configuration. When fields is set, columns, filters, and "
                    "form_class should not be set — they will be derived from "
                    "fields automatically.",
                    DeprecationWarning,
                    stacklevel=2,
                )

            # Derive columns from fields for backward compatibility
            if not has_columns:
                cls.columns = list(cls.fields)

            # Derive filters from fields for backward compatibility
            if not has_filters:
                cls.filters = [f for f in cls.fields if getattr(f, "filterable", False)]

    # Relation managers for inline related-record editing on the ViewPage
    relations: list[type[RelationManager]] = []

    # Search Configuration
    # Fields to include in global search queries. Empty list disables search for this resource.
    search_fields: list[str] = []
    # Field used as the display title in search results (falls back to "id")
    search_title_field: str = "name"

    # Optional integration knobs
    cacheable: bool | Any = False  # True or CacheableSpec enables list caching
    searchable: bool | Any = False  # True or SearchableSpec enables search index
    resilient: bool | Any = False  # True or ResilientSpec enables retry/circuit

    # Data source instance for search (set at runtime via set_data_source)
    _data_source: IDataSource | None = None

    def set_data_source(self, data_source: IDataSource) -> None:
        """Attach a data source to this resource for search and list support.

        Args:
            data_source: An IDataSource-compatible instance.

        Raises:
            TypeError: If data_source does not satisfy IDataSource protocol.
        """
        if not isinstance(data_source, IDataSource):
            raise TypeError(
                f"data_source must implement IDataSource, got {type(data_source).__name__}"
            )
        self._data_source = data_source

    async def search(self, query: str, *, limit: int = 5) -> list[dict[str, Any]]:
        """Search this resource for items matching *query*.

        Override in subclasses for custom search logic.  The default
        implementation queries the attached data source using
        :attr:`search_fields`.

        Args:
            query: Search term entered by the user.
            limit: Maximum number of results to return.

        Returns:
            List of dicts with ``id``, ``title``, and ``subtitle`` keys.
        """
        if not self.search_fields or self._data_source is None:
            return []

        from lexigram.admin.data.query import QuerySpec

        qs = (
            QuerySpec()
            .with_search(query, self.search_fields)
            .with_page(1)
            .with_per_page(limit)
        )
        try:
            result = await self._data_source.find_many(qs)
        except (AttributeError, TypeError, ValueError, KeyError, RuntimeError):
            return []

        hits: list[dict[str, Any]] = []
        for item in result.items:
            if isinstance(item, dict):
                item_id = item.get("id", "")
                title = (
                    item.get(self.search_title_field)
                    or item.get("name")
                    or item.get("title")
                    or str(item_id)
                )
                subtitle = item.get("email") or item.get("description") or ""
            else:
                item_id = getattr(item, "id", "")
                title = (
                    getattr(item, self.search_title_field, None)
                    or getattr(item, "name", None)
                    or str(item_id)
                )
                subtitle = (
                    getattr(item, "email", "") or getattr(item, "description", "") or ""
                )
            hits.append(
                {"id": str(item_id), "title": str(title), "subtitle": str(subtitle)}
            )
        return hits

    async def fetch_list(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        filters: dict[str, Any] | None = None,
        search: str | None = None,
        search_fields: list[str] | None = None,
        sort_by: str | None = None,
        sort_order: str = "asc",
        include_deleted: bool = False,
    ) -> tuple[list[Any], int]:
        """Fetch a paginated list of items via the attached IDataSource.

        Builds a Query object from the pagination/search/filter/sort parameters
        and delegates to ``self._data_source.find_many(query)``.

        Override this in resource subclasses for custom data access logic.

        Returns:
            Tuple of (items, total_count).
        """
        if self._data_source is None:
            return [], 0

        from lexigram.admin.data.query import QuerySpec

        page = (offset // limit) + 1 if limit else 1
        qs = QuerySpec().with_page(page).with_per_page(limit)

        if search and search_fields:
            qs = qs.with_search(search, search_fields)

        if sort_by:
            qs = qs.with_order_by(sort_by, sort_order)

        if include_deleted:
            qs = qs.with_deleted(True)

        for field, value in (filters or {}).items():
            if isinstance(value, list):
                qs = qs.with_where_in(field, value)
            else:
                qs = qs.with_where_eq(field, value)

        result = await self._data_source.find_many(qs)
        items = list(result.items)
        total = result.total
        return items, total

    @classmethod
    def get_form_class(cls) -> type[FormBase] | None:
        """Return the Form class to use for create/edit views.

        Returns:
            Form class or None
        """
        return cls.form_class


__all__ = ["Resource"]
