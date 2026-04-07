"""Resource Lenses — alternative filtered/customised views on a resource.

Inspired by Laravel Nova's Lens feature.  A **Lens** is a named view of a
resource that applies a pre-defined query, restricts columns, or changes
the default sort — without creating a separate resource class.

Example::

    from lexigram.admin.resources.lenses import ResourceLens
    from lexigram.admin.ui.columns import TextColumn, DateColumn, BadgeColumn

    class ActiveUsersLens(ResourceLens):
        name = "active_users"
        label = "Active Users"
        icon = "user-check"

        # Extra filters applied *on top of* the resource's base query
        query_filters: dict = {"is_active": True}

        # Optional: restrict which columns appear in this lens
        columns = [
            TextColumn("name").sortable(),
            TextColumn("email").sortable(),
            DateColumn("last_active").label("Last seen").sortable(),
        ]

        default_sort = "-last_active"

Usage in a Resource::

    class UserResource(Resource):
        lenses = [ActiveUsersLens, InactiveUsersLens]
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.admin.ui.columns import Column
    from lexigram.admin.ui.filters.base import Filter


class ResourceLens:
    """Alternative filtered/sorted view on a parent resource.

    Subclass to create a lens.  Attach to a :class:`~lexigram.admin.resources.base.Resource`
    via its ``lenses`` class attribute.

    Attributes:
        name: Machine-readable identifier (must be unique within a resource).
        label: Human-readable tab label shown in the admin UI.
        icon: Optional icon name (from the icon library configured in the admin).
        description: Optional short description shown on hover.
        query_filters: Static ``dict`` of ORM filter kwargs pre-applied to
            every query executed through this lens.
        columns: Override the parent resource's column set.  ``None`` means
            inherit the parent's columns unchanged.
        filters: Override the parent resource's sidebar filters.  ``None``
            means inherit.
        default_sort: Override the default sort field (prefix with ``-`` for
            descending).  ``None`` means inherit.
        page_size: Override rows-per-page.  ``None`` means inherit.
    """

    name: str = ""
    label: str = ""
    icon: str | None = None
    description: str | None = None

    # Pre-applied query constraints
    query_filters: dict[str, Any] = {}

    # Optional overrides (None = inherit from parent resource)
    columns: list[Column] | None = None
    filters: list[Filter] | None = None
    default_sort: str | None = None
    page_size: int | None = None

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @classmethod
    def get_name(cls) -> str:
        """Return the lens name, falling back to the class name in snake_case."""
        if cls.name:
            return cls.name
        import re

        s = cls.__name__
        return re.sub(r"(?<!^)(?=[A-Z])", "_", s).lower().removesuffix("_lens")

    @classmethod
    def get_label(cls) -> str:
        """Return the lens label, falling back to a title-cased version of the name."""
        if cls.label:
            return cls.label
        return cls.get_name().replace("_", " ").title()

    @classmethod
    def apply_to_queryset(cls, queryset: Any) -> Any:
        """Apply :attr:`query_filters` to *queryset*.

        The default implementation calls ``queryset.filter(**cls.query_filters)``
        which is compatible with Django ORM, SQLAlchemy ``Select`` objects
        that expose a ``.filter()`` method, and the Lexigram
        ``RepositoryProtocol`` query builder.

        Override for custom query logic::

            @classmethod
            def apply_to_queryset(cls, queryset):
                return queryset.filter(status="active").order_by("-created_at")

        Args:
            queryset: The base queryset from the parent resource.

        Returns:
            Modified queryset with lens constraints applied.
        """
        if cls.query_filters:
            return queryset.filter(**cls.query_filters)
        return queryset

    @classmethod
    def resolve_columns(cls, parent_columns: list[Column]) -> list[Column]:
        """Return the effective column list for this lens.

        Args:
            parent_columns: Columns from the parent resource.

        Returns:
            Lens-specific columns if defined, otherwise *parent_columns*.
        """
        return cls.columns if cls.columns is not None else parent_columns

    @classmethod
    def resolve_filters(cls, parent_filters: list[Filter]) -> list[Filter]:
        """Return the effective filter list for this lens.

        Args:
            parent_filters: Filters from the parent resource.

        Returns:
            Lens-specific filters if defined, otherwise *parent_filters*.
        """
        return cls.filters if cls.filters is not None else parent_filters

    @classmethod
    def resolve_sort(cls, parent_sort: str | None) -> str | None:
        """Return the effective default sort for this lens."""
        return cls.default_sort if cls.default_sort is not None else parent_sort

    @classmethod
    def resolve_page_size(cls, parent_page_size: int) -> int:
        """Return the effective page size for this lens."""
        return cls.page_size if cls.page_size is not None else parent_page_size

    @classmethod
    def to_dict(cls) -> dict[str, Any]:
        """Serialise lens metadata for JSON / API responses.

        Returns:
            Dict with ``name``, ``label``, ``icon``, ``description`` keys.
        """
        return {
            "name": cls.get_name(),
            "label": cls.get_label(),
            "icon": cls.icon,
            "description": cls.description,
        }


class LensRegistry:
    """Registry for lenses attached to a resource class.

    Resources that want to expose lenses declare a ``lenses`` class attribute::

        class UserResource(Resource):
            lenses = [ActiveUsersLens, InactiveUsersLens]

    :class:`LensRegistry` is then used by the controller/data layer to
    look up and apply the active lens.
    """

    def __init__(self, lenses: list[type[ResourceLens]] | None = None) -> None:
        self._lenses: dict[str, type[ResourceLens]] = {}
        for lens in lenses or []:
            self.register(lens)

    def register(self, lens: type[ResourceLens]) -> None:
        """Register a lens class.

        Args:
            lens: A :class:`ResourceLens` subclass (not an instance).

        Raises:
            ValueError: If a lens with the same name is already registered.
        """
        name = lens.get_name()
        if name in self._lenses:
            raise ValueError(f"A lens named {name!r} is already registered.")
        self._lenses[name] = lens

    def get(self, name: str) -> type[ResourceLens] | None:
        """Look up a lens by name.

        Args:
            name: Machine-readable lens name.

        Returns:
            The lens class, or ``None`` if not found.
        """
        return self._lenses.get(name)

    def all(self) -> list[type[ResourceLens]]:
        """Return all registered lenses in registration order."""
        return list(self._lenses.values())

    def names(self) -> list[str]:
        """Return all registered lens names."""
        return list(self._lenses.keys())

    def to_list(self) -> list[dict[str, Any]]:
        """Serialise all lenses to a list of metadata dicts."""
        return [lens.to_dict() for lens in self._lenses.values()]
