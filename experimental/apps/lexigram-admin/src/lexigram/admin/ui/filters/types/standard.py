"""Standard filter types (range, toggle)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.data.filter_specs import GreaterThanOrEqualSpec, LessThanOrEqualSpec
from lexigram.admin.ui.filters.base import Filter
from lexigram.ui import Zones, el

if TYPE_CHECKING:
    from collections.abc import Callable


class RangeFilter(Filter):
    """
    Generic range filter for dates and numbers.
    Base class for specialized range filters.
    """

    def __init__(
        self,
        name: str = "",
        label: str | None = None,
        min_value: Any | None = None,
        max_value: Any | None = None,
        step: Any | None = None,
        default: Any | Callable | None = None,
        input_type: str = "text",
    ):
        super().__init__(name, label)
        self._min = min_value
        self._max = max_value
        self._step = step
        self._input_type = input_type
        if callable(default):
            self._default_callback = default
            self._default = None
        else:
            self._default = default
            self._default_callback = None

    def get_consumed_params(self) -> list[str]:
        """Range filter uses two fields in the request."""
        return [f"{self.name}_from", f"{self.name}_to"]

    def get_default(self) -> Any:
        if self._default_callback:
            return self._default_callback()
        return self.default

    def _render_input(
        self,
        suffix: str,
        value: Any,
        placeholder: str,
        url: str | None,
    ) -> str:
        """Internal helper to render an input field."""
        from lexigram.ui import NumberInput, TextInput

        name = f"filter_{self.name}_{suffix}"

        # Get state and resource prefix
        state = getattr(self, "_state", None)
        resource_prefix = getattr(state, "_resource_prefix", None) if state else url
        base_url = resource_prefix.rstrip("/") if resource_prefix else ""

        # Canonical HTMX attrs: prefer stored from FilterBar, else fallback.
        # Always use hx-include (not hx-vals) so the filter dynamically picks
        # up the current search, sort, and other filter values at request time.
        stored = self.get_htmx_attrs()
        if stored:
            htmx_attrs = stored
        else:
            htmx_attrs = {
                "hx-get": f"{base_url}/",
                "hx-trigger": "change",
                "hx-target": Zones.DATA.selector,
                "hx-swap": Zones.DATA.swap_mode.value,
                "hx-select": Zones.DATA.selector,
                "hx-push-url": "true",
                "hx-include": f"{Zones.DATA.selector} [data-state='true'], #{Zones.SEARCH.id}, #{Zones.FILTERS.id}",
                "hx-params": "*",
            }

        # Convert to component-friendly names (hx_*)
        comp_attrs = {k.replace("-", "_"): v for k, v in htmx_attrs.items()}

        common = {
            "name": name,
            "value": value,
            "label": None,
            "placeholder": placeholder,
            **comp_attrs,
        }

        if self._input_type == "number":
            return NumberInput(
                min=self._min,
                max=self._max,
                step=self._step,
                **common,
            ).render()

        return TextInput(input_type=self._input_type, **common).render()

    def render(self, current_value: Any = None, url: str | None = None) -> str:
        from_value = ""
        to_value = ""

        if isinstance(current_value, dict):
            from_value = current_value.get("from", "")
            to_value = current_value.get("to", "")
        elif isinstance(self.value, dict):
            from_value = self.value.get("from", "")
            to_value = self.value.get("to", "")

        from_input = self._render_input("from", from_value, "From", url)
        to_input = self._render_input("to", to_value, "To", url)

        return el(
            "div",
            el(
                "label",
                self.label,
                class_="block text-sm font-medium text-foreground mb-1.5",
            ),
            el("div", from_input, to_input, class_="flex flex-col sm:flex-row gap-2"),
            class_="filter-item mb-2",
        )

    def apply(self, query: Any, value: Any) -> Any:
        if not value or not isinstance(value, dict):
            return query

        from_val = value.get("from")
        to_val = value.get("to")

        if from_val:
            query = query.filter(getattr(query.model, self.name) >= from_val)
        if to_val:
            query = query.filter(getattr(query.model, self.name) <= to_val)

        return query

    def get_value_from_request(self, request_params: dict) -> Any:
        from_val = request_params.get(f"{self.name}_from")
        to_val = request_params.get(f"{self.name}_to")

        # Only return the range if BOTH values are present and non-empty
        if not from_val or not to_val:
            return None

        return {"from": from_val, "to": to_val}

    def from_url_param(self, param: Any) -> Any:
        return param

    def to_spec(self, value: Any) -> Any | None:
        if not isinstance(value, dict):
            return None

        from_val = value.get("from")
        to_val = value.get("to")

        specs = []
        if from_val:
            specs.append(GreaterThanOrEqualSpec(self.name, from_val))
        if to_val:
            specs.append(LessThanOrEqualSpec(self.name, to_val))  # type: ignore[arg-type]

        if not specs:
            return None

        if len(specs) == 1:
            return specs[0]

        return specs[0] & specs[1]


class NumericRangeFilter(RangeFilter):
    """Filter for numeric ranges."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["input_type"] = "number"
        super().__init__(*args, **kwargs)
