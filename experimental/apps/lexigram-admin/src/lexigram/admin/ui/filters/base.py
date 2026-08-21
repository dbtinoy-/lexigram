"""
Filter base class for DataTable filtering.

Provides a fluent API (Builder pattern) for defining filters with URL state persistence,
query application, and custom rendering. All configuration methods return `self`
to enable method chaining.

Example:
    >>> from lexigram.admin.ui.filters import SelectFilter, DateFilter
    >>>
    >>> # Fluent API with method chaining
    >>> role_filter = (SelectFilter("role")
    ...     .placeholder("Select Role")
    ...     .default("user")
    ...     .visible(lambda ctx: ctx.user.is_admin))
"""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Self

from lexigram.admin.data.filter_specs import EqualSpec

if TYPE_CHECKING:
    from collections.abc import Callable


class Filter:
    """Base class for all table filters with fluent API.

    This class implements the Builder pattern, allowing configuration
    through method chaining. All configuration methods return `self`
    to enable fluent syntax.

    Attributes:
        name: Filter field name (query parameter name)
        label: Display label for filter UI

    Example:
        >>> SelectFilter("status", options={"active": "Active"})
        >>> DateFilter("created_at").placeholder("Filter by Date")
    """

    def __init__(self, name: str, label: str | None = None):
        """
        Initialize a filter.

        Args:
            name: Filter field name (used as query parameter key)
            label: Display label (defaults to title-cased name)
        """
        # Initialize filter state
        self.name = name
        self.label = label or name.replace("_", " ").title()
        self._placeholder: str | None = None
        self._default: Any = None
        self.value: Any = None
        self.errors: list[str] = []

        # Additional Filter-specific state
        self._default_callback: Callable | None = None
        self._visible = True
        self._visible_callback: Callable | None = None

    def default(self, value: Any | Callable) -> Self:
        """Set default value for the filter.

        The default value is used when no value is present in the request
        parameters. Can be a static value or a callable that returns a value.

        Args:
            value: The default value to use, or a callable that returns it

        Returns:
            Self for method chaining

        Example:
            >>> SelectFilter("status").default("active")
            >>>
            >>> # Dynamic default
            >>> DateFilter("created").default(lambda: datetime.now() - timedelta(days=30))
        """
        if callable(value):
            self._default_callback = value
            self._default = None
        else:
            self._default = value
            self._default_callback = None
        return self

    def get_default(self) -> Any:
        """Get default value, calling callback if dynamic.

        Returns:
            Default value or result of callback
        """
        if self._default_callback:
            return self._default_callback()
        return self._default

    def placeholder(self, text: str) -> Self:
        """Set placeholder text for the filter input.

        Args:
            text: Placeholder text to display

        Returns:
            Self for method chaining

        Example:
            >>> TextFilter("search").placeholder("Search users...")
            >>> SelectFilter("role").placeholder("All Roles")
        """
        self._placeholder = text
        return self

    def visible(self, visible: bool | Callable = True) -> Self:
        """
        Control filter visibility.

        Can accept a boolean or a callable that returns a boolean,
        allowing for dynamic visibility based on context (e.g., user permissions).

        Args:
            visible: Boolean or callable that returns boolean

        Returns:
            Self for method chaining

        Example:
            >>> # Static visibility
            >>> DateFilter("archived_at").visible(False)
            >>>
            >>> # Dynamic visibility
            >>> def show_if_manager(context):
            ...     return context.user.role == "manager"
            >>> SelectFilter("department").visible(show_if_manager)
        """
        if callable(visible):
            self._visible_callback = visible
        else:
            self._visible = visible
        return self

    def is_visible(self, context: dict | None = None) -> bool:
        """Check if filter should be visible.

        Args:
            context: Context dictionary (e.g., with current user)

        Returns:
            True if filter should be displayed
        """
        if self._visible_callback:
            return self._visible_callback(context or {})
        return self._visible

    def get_value_from_request(self, request_params: dict) -> Any:
        """
        Extract filter value from request parameters.

        Args:
            request_params: Request query parameters dict

        Returns:
            Filter value or default if not present
        """
        return request_params.get(self.name, self.get_default())

    def get_consumed_params(self) -> list[str]:
        """
        Return a list of request parameter keys that this filter consumes.
        Used to prevent these parameters from being included as extra filters.
        """
        return [self.name]

    @abstractmethod
    def render(self, current_value: Any = None, url: str | None = None) -> str:
        """
        Render the filter UI as HTML.

        Args:
            current_value: Current filter value to display

        Returns:
            HTML string of the filter component
        """

    @abstractmethod
    def apply(self, query: Any, value: Any) -> Any:
        """
        Apply filter to a query.

        Args:
            query: Query object (SQLAlchemy, etc.)
            value: Filter value to apply

        Returns:
            Modified query with filter applied
        """

    def to_spec(self, value: Any) -> Any | None:
        """
        Convert filter value to a specification object.

        Args:
            value: Filter value from request

        Returns:
            SpecificationProtocol object (e.g. EqualSpec) or None
        """

        parsed = self.from_url_param(value)
        if parsed is None or parsed == "":
            return None
        return EqualSpec(self.name, parsed)

    def to_url_param(self, value: Any) -> str:
        """
        Convert filter value to URL parameter string.

        Args:
            value: Filter value

        Returns:
            String representation safe for URL parameters
        """
        if value is None:
            return ""
        return str(value)

    def from_url_param(self, param: str) -> Any:
        """
        Parse filter value from URL parameter.

        Args:
            param: URL parameter string

        Returns:
            Parsed value suitable for filtering logic
        """
        return param if param else None

    def set_state(self, state: Any) -> None:
        """Set the table state for URL generation."""
        self._state = state

    def get_state(self) -> Any:
        """Get the table state for URL generation."""
        return getattr(self, "_state", None)

    def set_htmx_attrs(self, attrs: dict[str, str]) -> None:
        """Set canonical HTMX attributes to use instead of building inline."""
        self._htmx_attrs = attrs

    def get_htmx_attrs(self) -> dict[str, str] | None:
        """Get stored canonical HTMX attributes if set."""
        return getattr(self, "_htmx_attrs", None)

    def build_state_url(self, new_value: Any = None, base_url: str = "") -> str:
        """
        Build a complete URL with all state parameters baked in.

        This follows the Pagination pattern: construct URLs that contain
        the full state, eliminating the need for hx-include.

        Args:
            new_value: The new value for this filter (replaces current)
            base_url: Base URL path (defaults to state's resource prefix)

        Returns:
            Complete URL with all query parameters
        """
        from urllib.parse import urlencode

        state = getattr(self, "_state", None)
        if not state:
            # Fallback: just return base with filter param
            if new_value:
                return f"{base_url}?{self.name}={new_value}"
            return base_url or "?"

        # Get all current state params
        params = state.to_query_params()

        # Update with new filter value
        if new_value is not None and new_value != "":
            params[self.name] = str(new_value)
        else:
            # Remove filter if value is empty
            params.pop(self.name, None)

        # Reset page when filtering
        params.pop("page", None)
        params.pop("cursor", None)

        # Construct URL
        resource_prefix = getattr(state, "_resource_prefix", None) or base_url
        query = urlencode(params, doseq=True) if params else ""

        if query:
            return f"{resource_prefix}?{query}"
        return f"{resource_prefix}/" if resource_prefix else "?"
