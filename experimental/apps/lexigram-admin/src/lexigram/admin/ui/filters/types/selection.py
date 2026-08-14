"""Selection-based filter types."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.data.query import EqualSpec, InSpec
from lexigram.admin.ui.filters.base import Filter
from lexigram.serialization import dumps_str
from lexigram.ui import Zones

if TYPE_CHECKING:
    from collections.abc import Callable


class SelectFilter(Filter):
    """
    Dropdown select filter.

    Example:
        SelectFilter(options={
            "active": "Active",
            "inactive": "Inactive",
            "pending": "Pending",
        })

        # Or with lambda for dynamic options
        SelectFilter(options=lambda: get_active_statuses())
    """

    def __init__(
        self,
        name: str = "",
        options: list[str] | dict[str, str] | Callable | None = None,
        label: str | None = None,
        multiple: bool = False,
        default: Any = None,
    ):
        """
        Initialize select filter.

        Args:
            name: Filter field name (auto-set by column if empty)
            options: List of values, dict of value:label pairs, or callable
            label: Display label
            multiple: Allow multiple selection
            default: Default value
        """
        super().__init__(name, label)

        # Store options or callback
        if options is None:
            self.options: dict[str, str] = {}
            self._options_callback = None
        elif callable(options):
            self.options = {}
            self._options_callback = options
        elif isinstance(options, list):
            self.options = {}
            for opt in options:
                if isinstance(opt, dict):
                    val = str(opt.get("value", opt.get("id", "")))
                    lab = str(opt.get("label", opt.get("name", val)))
                    self.options[val] = lab
                else:
                    self.options[str(opt)] = str(opt)
            self._options_callback = None
        else:
            self.options = options
            self._options_callback = None

        self._multiple = multiple
        if default is not None:
            self._default = default

    def multiple(self, multiple: bool = True) -> SelectFilter:
        """Enable multiple selection."""
        self._multiple = multiple
        return self

    def get_options(self) -> dict[str, str]:
        """Get options, calling callback if dynamic."""
        if self._options_callback:
            opts = self._options_callback()
            if isinstance(opts, list):
                result = {}
                for opt in opts:
                    if isinstance(opt, dict):
                        val = str(opt.get("value", opt.get("id", "")))
                        lab = str(opt.get("label", opt.get("name", val)))
                        result[val] = lab
                    else:
                        result[str(opt)] = str(opt)
                return result
            return opts
        return self.options

    def render(self, current_value: Any = None, url: str | None = None) -> str:
        """Render as select dropdown using atomic Select component."""
        from lexigram.ui import Select

        # Handle multiple values
        value = current_value if current_value is not None else self.value

        # Get options (dynamic or static)
        options = self.get_options()

        # Convert options dict to choices list format
        placeholder = self._placeholder or f"Select {self.label}"
        choices = [("", placeholder)]  # Add placeholder as first option
        choices.extend([(kv[0], kv[1]) for kv in options.items()])

        # Get state and resource prefix
        state = getattr(self, "_state", None)
        resource_prefix = getattr(state, "_resource_prefix", None) if state else url
        base_url = resource_prefix.rstrip("/") if resource_prefix else ""

        # Canonical HTMX attrs: prefer stored from FilterBar, else fallback
        stored = self.get_htmx_attrs()
        if stored:
            htmx_attrs = stored
        elif state:
            params = state.to_query_params()
            params.pop(self.name, None)
            params.pop("page", None)
            params.pop("cursor", None)
            htmx_attrs = {
                "hx-get": f"{base_url}/",
                "hx-target": Zones.DATA.selector,
                "hx-swap": Zones.DATA.swap_mode.value,
                "hx-select": Zones.DATA.selector,
                "hx-push-url": "true",
                "hx-vals": dumps_str(params),
            }
        else:
            htmx_attrs = {
                "hx-get": f"{base_url}/",
                "hx-trigger": "change",
                "hx-target": Zones.DATA.selector,
                "hx-swap": Zones.DATA.swap_mode.value,
                "hx-select": Zones.DATA.selector,
                "hx-push-url": "true",
                "hx-include": f"{Zones.DATA.selector} [data-state='true'], #{Zones.SEARCH.id}",
                "hx-params": "*",
            }

        # Convert to component-friendly names (hx_*)
        comp_attrs = {k.replace("-", "_"): v for k, v in htmx_attrs.items()}

        select = Select(
            name=f"filter_{self.name}",
            choices=choices,
            value=value,
            label=self.label,
            **comp_attrs,  # type: ignore[arg-type]
        )

        return select.render()

    def apply(self, query: Any, value: Any) -> Any:
        """
        Apply filter to query.
        """
        if not value:
            return query

        # Handle multiple values
        if self._multiple and isinstance(value, list):
            # Assuming SQLAlchemy-style query
            return query.filter(getattr(query.model, self.name).in_(value))
        # Single value
        return query.filter(**{self.name: value})

    def from_url_param(self, param: Any) -> Any:
        """Parse value from URL param. Handles multiple if enabled."""
        if param is None or param == "":
            return None

        if self._multiple:
            if isinstance(param, list):
                return param
            return list(
                filter(
                    lambda p: p.strip(),
                    (p.strip() for p in str(param).split(",")),
                ),
            )

        return param

    def to_spec(self, value: Any) -> Any | None:
        """Convert to EqualSpec or InSpec."""

        parsed = self.from_url_param(value)
        if parsed is None:
            return None

        if self._multiple and isinstance(parsed, list):
            return InSpec(self.name, parsed)

        return EqualSpec(self.name, parsed)


class MultiSelectFilter(Filter):
    """
    Multi-select filter with checkboxes.

    Example:
        MultiSelectFilter(
            options={
                "training": "Training",
                "grooming": "Grooming",
                "vet_visit": "Vet Visit",
            },
            label="Tags"
        )

        # Or with lambda for dynamic options
        MultiSelectFilter(
            options=lambda: get_active_tags(),
            label="Tags"
        )
    """

    def __init__(
        self,
        name: str = "",
        options: list[str] | dict[str, str] | Callable | None = None,
        label: str | None = None,
    ):
        """
        Initialize multi-select filter.

        Args:
            name: Filter field name (auto-set by column if empty)
            options: List of values, dict of value:label pairs, or callable
            label: Display label
        """
        super().__init__(name, label)

        # Convert list to dict if needed
        if options is None:
            self.options: dict[str, str] = {}
        elif isinstance(options, list):
            self.options = {}
            for opt in options:
                if isinstance(opt, dict):
                    val = str(opt.get("value", opt.get("id", "")))
                    lab = str(opt.get("label", opt.get("name", val)))
                    self.options[val] = lab
                else:
                    self.options[str(opt)] = str(opt)
        elif callable(options):
            self._options_callback = options
            self.options = {}
        else:
            self.options = options

        self._options_callback = options if callable(options) else None  # type: ignore[assignment]

    def get_consumed_params(self) -> list[str]:
        """Multi-select filter uses the name with [] suffix."""
        return [self.name, f"{self.name}[]"]

    def get_options(self) -> dict[str, str]:
        """Get options, calling callback if dynamic."""
        if self._options_callback:  # type: ignore[truthy-function]
            opts = self._options_callback()
            if isinstance(opts, list):
                result = {}
                for opt in opts:
                    if isinstance(opt, dict):
                        val = str(opt.get("value", opt.get("id", "")))
                        lab = str(opt.get("label", opt.get("name", val)))
                        result[val] = lab
                    else:
                        result[str(opt)] = str(opt)
                return result
            return opts
        return self.options

    def render(self, current_value: Any = None, url: str | None = None) -> str:
        """Render as checkboxes using atomic components."""
        from lexigram.ui import Checkbox
        from lexigram.ui.core.base import el

        # Get options (dynamic or static)
        options = self.get_options()

        # Normalize current values to list
        selected = []
        if current_value:
            if isinstance(current_value, list):
                selected = current_value
            else:
                selected = [current_value]

        # Get state and resource prefix
        state = getattr(self, "_state", None)
        resource_prefix = getattr(state, "_resource_prefix", None) if state else url
        base_url = resource_prefix.rstrip("/") if resource_prefix else ""

        # Canonical HTMX attrs: prefer stored from FilterBar, else fallback
        stored = self.get_htmx_attrs()
        if stored:
            htmx_attrs = stored
        elif state:
            params = state.to_query_params()
            params.pop(self.name, None)
            params.pop(f"{self.name}[]", None)
            params.pop("page", None)
            params.pop("cursor", None)
            htmx_attrs = {
                "hx-get": f"{base_url}/",
                "hx-target": Zones.DATA.selector,
                "hx-swap": Zones.DATA.swap_mode.value,
                "hx-select": Zones.DATA.selector,
                "hx-push-url": "true",
                "hx-vals": dumps_str(params),
            }
        else:
            htmx_attrs = {
                "hx-get": f"{base_url}/",
                "hx-trigger": "change",
                "hx-target": Zones.DATA.selector,
                "hx-swap": Zones.DATA.swap_mode.value,
                "hx-select": Zones.DATA.selector,
                "hx-push-url": "true",
                "hx-include": f"{Zones.DATA.selector} [data-state='true'], #{Zones.SEARCH.id}",
                "hx-params": "*",
            }

        # Convert to component-friendly names (hx_*)
        comp_attrs = {k.replace("-", "_"): v for k, v in htmx_attrs.items()}

        # Create checkbox for each option
        checkboxes = []
        for value, label in options.items():
            checkbox = Checkbox(
                name=f"filter_{self.name}[]",  # Array notation for multiple values
                value=value,
                label=label,
                checked=value in selected,
                **comp_attrs,
            )
            checkboxes.append(checkbox.render())

        # Wrap in container with label
        return el(
            "div",
            el(
                "label",
                self.label,
                class_="block text-sm font-medium text-foreground mb-1.5",
            ),
            el("div", *checkboxes, class_="space-y-2"),
            class_="filter-item mb-2",
        )

    def apply(self, query: Any, value: Any) -> Any:
        """
        Apply multi-select filter to query.
        """
        if not value:
            return query

        # Ensure value is a list
        if not isinstance(value, list):
            value = [value]

        # Filter with IN clause
        return query.filter(getattr(query.model, self.name).in_(value))

    def from_url_param(self, param: Any) -> Any:
        """Parse multiple values from URL param."""
        if param is None or param == "":
            return None

        if isinstance(param, list):
            return param

        # HTMX often sends multiple values as a comma-separated list or multiple params
        return list(
            filter(
                lambda p: p.strip(),
                (p.strip() for p in str(param).split(",")),
            ),
        )

    def to_spec(self, value: Any) -> Any | None:
        """Convert to InSpec."""

        parsed = self.from_url_param(value)
        if not parsed:
            return None
        return InSpec(self.name, parsed)
