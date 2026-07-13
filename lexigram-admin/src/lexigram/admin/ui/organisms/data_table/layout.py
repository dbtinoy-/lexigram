"""Layout composition logic for data table component."""

from __future__ import annotations

from typing import Any

from lexigram.admin.config import TableConfiguration
from lexigram.ui import TableState, el, raw


class LayoutComposer:
    """Composes layout for data table component."""

    def __init__(self, config: TableConfiguration, state: TableState):
        self.config = config
        self.state = state

    def compose(
        self,
        search_section: Any,
        filter_section: Any,
        inner_form: Any,
    ) -> Any:
        """Compose the layout based on state and configuration."""
        if self.state.layout == "sidebar" and self.config.resource_prefix:
            aside_content = ""
            if search_section:
                aside_content += str(el("div", search_section, class_="mb-4"))
            if filter_section:
                aside_content += str(el("div", filter_section, class_=""))
            left_sidebar = el(
                "aside",
                raw(aside_content),
                class_="w-full lg:w-72 lg:mr-6 flex-shrink-0 lg:sticky lg:top-4 lg:self-start",
            )
            main_content = el(
                "div",
                inner_form,
                class_="flex-1 min-w-0",
            )
            return el(
                "div",
                left_sidebar,
                main_content,
                class_="flex flex-col lg:flex-row items-start lexigram-data-table-container",
            )
        return el(
            "div",
            el("div", raw(search_section), class_="mb-4") if search_section else "",
            el("div", raw(filter_section), class_="mb-4") if filter_section else "",
            inner_form,
            class_="block lexigram-data-table-container",
        )
