"""Toggle filter type."""

from __future__ import annotations

from typing import Any

from lexigram.admin.data.filter_specs import EqualSpec
from lexigram.admin.ui.filters.base import Filter
from lexigram.ui import Zones


class ToggleFilter(Filter):
    """
    Boolean toggle filter.

    Example:
        ToggleFilter(
            label="Neutered Status",
            true_label="Neutered/Spayed",
            false_label="Not Neutered"
        )
    """

    def __init__(
        self,
        name: str = "",
        label: str | None = None,
        true_label: str = "Yes",
        false_label: str = "No",
    ):
        """
        Initialize toggle filter.

        Args:
            name: Filter field name (auto-set by column if empty)
            label: Display label
            true_label: Label for true option
            false_label: Label for false option
        """
        super().__init__(name, label)
        self._true_label = true_label
        self._false_label = false_label

    def render(self, current_value: Any = None, url: str | None = None) -> str:
        """Render as checkbox or radio buttons using atomic components."""
        from lexigram.ui import Select

        # Convert to select with three options: All, True, False
        choices = [
            ("", "All"),
            ("true", self._true_label),
            ("false", self._false_label),
        ]

        # Normalize current value
        value = ""
        current = current_value if current_value is not None else self.value

        if current is not None:
            if isinstance(current, bool):
                value = "true" if current else "false"
            elif str(current).lower() in ["true", "1", "yes"]:
                value = "true"
            elif str(current).lower() in ["false", "0", "no"]:
                value = "false"

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

        select = Select(
            name=f"filter_{self.name}",
            choices=choices,
            value=value,
            label=self.label,
            **comp_attrs,  # type: ignore[arg-type]
        )

        return select.render()

    def from_url_param(self, param: Any) -> Any:
        """Convert string param to boolean."""
        if param is None or param == "":
            return None

        s = str(param).lower()
        if s in ["true", "1", "yes"]:
            return True
        if s in ["false", "0", "no"]:
            return False
        return None

    def apply(self, query: Any, value: Any) -> Any:
        """
        Apply toggle filter to query.

        Converts string value to boolean.
        """
        parsed = self.from_url_param(value)
        if parsed is None:
            return query

        return query.filter(**{self.name: parsed})

    def to_spec(self, value: Any) -> Any | None:
        """Convert to EqualSpec with boolean value."""

        parsed = self.from_url_param(value)
        if parsed is None:
            return None
        return EqualSpec(self.name, parsed)
