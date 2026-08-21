"""Base resource class for Admin Resources.

.. stability:: stable

Resources define the configuration for admin UI views including
columns, actions, filters, and permissions.
"""

from __future__ import annotations

import contextlib
import re
from typing import TYPE_CHECKING, Any
import warnings

from lexigram.admin.data.data_source import IDataSource
from lexigram.admin.resources.archive_ops import ArchiveOperationsMixin
from lexigram.admin.resources.layouts import apply_layout_config
from lexigram.admin.resources.config import TableConfiguration

if TYPE_CHECKING:
    from lexigram.admin.actions.base import HeaderAction
    from lexigram.admin.forms.components import FormBase
    from lexigram.admin.layout.layout_manager import LayoutManager
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


class Resource(ArchiveOperationsMixin):
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
    """Cluster name for navigation grouping. Replaces ``group``."""

    # Backward-compat alias for cluster
    group: str | None = None
    """Deprecated: use ``cluster`` instead. Kept in sync via __init_subclass__."""

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

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Validate and auto-derive backward-compat attributes when using ``fields``."""
        super().__init_subclass__(**kwargs)

        own = cls.__dict__

        # Sync group <-> cluster for backward compatibility
        if "group" in own and "cluster" not in own:
            cls.cluster = own["group"]
        if "cluster" in own and "group" not in own:
            cls.group = own["cluster"]

        # Validate name if explicitly set — must be a dotted slug
        if "name" in own and own["name"] is not None:
            _validate_resource_name(own["name"])

        has_fields = "fields" in own
        has_columns = "columns" in own
        has_filters = "filters" in own
        has_form_class = "form_class" in own

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

    def cache_spec(self) -> Any:
        """Return a CacheableSpec or None based on the cacheable field."""
        if self.cacheable is False:
            return None
        if self.cacheable is True:
            from lexigram.admin.integrations.cache import CacheableSpec

            return CacheableSpec()
        return self.cacheable

    def search_spec(self) -> Any:
        """Return a SearchableSpec or None based on the searchable field."""
        if self.searchable is False:
            return None
        if self.searchable is True:
            from lexigram.contracts.search import SearchableSpec

            return SearchableSpec(
                index_name=self.name,
                fields=tuple(self.search_fields),
            )
        return self.searchable

    def resilient_spec(self) -> Any:
        """Return a ResilientSpec or None based on the resilient field."""
        if self.resilient is False:
            return None
        if self.resilient is True:
            from lexigram.admin.integrations.resilience import ResilientSpec

            return ResilientSpec()
        return self.resilient

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

    async def before_create(self, data: dict) -> dict:
        """Hook called before a record is created.

        Args:
            data: Record data to be created

        Returns:
            Modified data
        """
        return data

    async def before_validate(self, data: dict) -> Any:
        """Validate and coerce form data against the resource model.

        Base implementation coerces HTML form strings to proper Python types
        via _coerce_form_data, then validates against ``self.model``.
        Returns Ok(coerced_data) on success, Err(AdminValidationError) with
        per-field errors on failure.

        Override in subclasses to add custom validation logic.
        """
        from lexigram.admin.exceptions import AdminValidationError
        from lexigram.admin.resources.handler import _coerce_form_data
        from lexigram.contracts.exceptions.domain import FieldError
        from lexigram.result import Err, Ok

        coerced = _coerce_form_data(data, self.model)
        if self.model is None:
            return Ok(coerced)

        if not hasattr(self.model, "model_validate"):
            return Ok(coerced)

        try:
            self.model.model_validate(coerced)
        except (ValueError, TypeError) as exc:
            msg = str(exc)
            errors: list[FieldError] = []

            is_pydantic = (
                type(exc).__name__ == "ValidationError"
                and "pydantic" in type(exc).__module__
            )
            if is_pydantic:
                for err in exc.errors():  # type: ignore[union-attr]
                    field = str(err["loc"][0]) if err.get("loc") else None
                    if field and field in coerced:
                        errors.append(FieldError(field=field, message=err["msg"]))
            else:
                field = None
                if msg.startswith("Field '"):
                    field = msg.split("'")[1]
                if field:
                    errors.append(FieldError(field=field, message=msg))

            if errors:
                return Err(
                    AdminValidationError(
                        message="Form validation failed",
                        errors=errors,
                    )
                )
            return Ok(coerced)

        return Ok(coerced)

    async def after_create(self, record: Any) -> None:
        """Hook called after a record is created.

        Args:
            record: Created record
        """

    async def before_update(self, item_id: Any, data: dict) -> dict:
        """Hook called before a record is updated.

        Args:
            item_id: Record identifier
            data: Updated record data

        Returns:
            Modified data
        """
        return data

    async def after_update(self, record: Any) -> None:
        """Hook called after a record is updated.

        Args:
            record: Updated record
        """

    async def before_delete(self, item_id: Any) -> None:
        """Hook called before a record is deleted.

        Args:
            item_id: Record identifier
        """

    async def after_delete(self, item_id: Any) -> None:
        """Hook called after a record is deleted.

        Args:
            item_id: Record identifier
        """

    @classmethod
    def get_action_hooks(cls, action_name: str) -> list[Any]:
        """Get action lifecycle hooks for the named action.

        Override in a resource subclass to attach ``ActionHookProtocol``
        hooks to registry-based actions. Hooks are collected by
        ``ActionExecutor`` and run before/after the action body and on
        failure.

        Args:
            action_name: Name of the action (e.g. ``"export"``)

        Returns:
            List of action hooks for the action.
        """
        return []

    @classmethod
    def get_table_config(cls) -> TableConfiguration:
        """Get the table configuration for this resource.

        Returns:
            TableConfiguration with columns, actions, filters
        """
        cfg = cls.config

        # Resolve configuration with priority: Config Object > Class Attribute
        per_page = (
            cls._get_config_value(cfg, "per_page", cls.page_size)
            if cfg
            else cls.page_size
        )
        default_sort = (
            cls._get_config_value(
                cfg,
                "default_sort_field",
                cls.default_sort,
            )
            if cfg
            else cls.default_sort
        )
        default_sort_order = (
            cls._get_config_value(cfg, "default_sort_order", "asc") if cfg else "asc"
        )
        action_layout = (
            cls._get_config_value(cfg, "action_layout", cls.action_layout)
            if cfg
            else cls.action_layout
        )

        resource_name = cls.label or cls.__name__.replace("Resource", "")
        if cfg and cfg.display_name:
            resource_name = cfg.display_name

        columns = list(
            cls._get_config_value(cfg, "columns", cls.columns) if cfg else cls.columns
        )
        actions = list(
            cls._get_config_value(cfg, "actions", cls.actions) if cfg else cls.actions
        )
        filters = list(
            cls._get_config_value(cfg, "filters_list", cls.filters)
            if cfg
            else cls.filters
        )

        # Check class attribute `layout_type` as fallback for legacy resources
        layout_fallback = getattr(cls, "layout_type", "stack")
        default_layout = (
            cls._get_config_value(cfg, "layout", layout_fallback)
            if cfg
            else layout_fallback
        )
        # Check class attribute `data_view` as fallback for legacy resources
        view_fallback = getattr(cls, "data_view", "tabular")
        default_view = (
            cls._get_config_value(cfg, "view", view_fallback) if cfg else view_fallback
        )

        empty_state_title = (
            cls._get_config_value(cfg, "empty_state_title", cls.empty_state_title)
            if cfg
            else cls.empty_state_title
        )
        empty_state_message = (
            cls._get_config_value(cfg, "empty_state_message", cls.empty_state_message)
            if cfg
            else cls.empty_state_message
        )
        empty_state_icon = (
            cls._get_config_value(cfg, "empty_state_icon", cls.empty_state_icon)
            if cfg
            else cls.empty_state_icon
        )
        group_by = (
            cls._get_config_value(cfg, "group_by", cls.group_by)
            if cfg
            else cls.group_by
        )

        return TableConfiguration(
            columns=columns,
            actions=actions,
            header_actions=list(cls.header_actions),
            bulk_actions=list(cls.bulk_actions),
            filter_options=filters,
            per_page=per_page,
            default_sort_by=default_sort,
            default_sort_order=default_sort_order,
            resource_name=resource_name,
            action_layout=action_layout,
            default_layout=default_layout,
            default_view=default_view,
            empty_state_title=empty_state_title,
            empty_state_message=empty_state_message,
            empty_state_icon=empty_state_icon,
            group_by=group_by,
        )

    @classmethod
    def get_form_class(cls) -> type[FormBase] | None:
        """Return the Form class to use for create/edit views.

        Returns:
            Form class or None
        """
        return cls.form_class

    @classmethod
    def get_form_display_mode(cls) -> str:
        """Return the form display mode for create/edit views.

        Returns:
            Display mode: "page", "modal", or "slider"
        """
        cfg = cls.config
        return (
            cls._get_config_value(cfg, "form_display_mode", cls.form_display_mode)
            if cfg
            else cls.form_display_mode
        )

    @classmethod
    def get_layout_manager(cls) -> LayoutManager:
        """Get layout manager with configured views.

        Returns:
            LayoutManager instance
        """
        from lexigram.admin.layout import LayoutManager

        manager = LayoutManager()
        cfg = cls.config

        if cfg and cfg.views_list:
            for view in cfg.views_list:
                if hasattr(view, "to_config"):
                    layout_config = view.to_config()
                    apply_layout_config(manager, layout_config)

            # Set default view
            if cfg.view:
                with contextlib.suppress(ValueError):
                    manager.set_default(cfg.view)

        return manager

    @staticmethod
    def _get_config_value(cfg: Any, attr: str, default: Any) -> Any:
        """Get configuration value with fallback to default or private attribute.

        Args:
            cfg: Configuration object
            attr: Attribute name
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        if cfg is None:
            return default

        # Try public attribute/property
        val = getattr(cfg, attr, None)

        # If it's the fluent method (callable) or missing, try the private attribute
        if val is None or callable(val):
            val = getattr(cfg, f"_{attr}", None)

        return val if val is not None else default


__all__ = ["Resource"]
