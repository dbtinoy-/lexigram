from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el, raw

__all__ = ["RichSelect"]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_TRIGGER_CLS = (
    "w-full flex items-center justify-between gap-2 px-3 py-2 text-sm "
    "bg-background text-foreground "
    "border border-input rounded-lg shadow-sm "
    "focus:outline-none focus:ring-2 focus:ring-ring "
    "hover:border-ring transition-colors duration-150"
)
_DROPDOWN_CLS = (
    "absolute z-50 mt-1 w-full bg-card border "
    "border-border rounded-lg shadow-lg overflow-hidden"
)
_SEARCH_CLS = (
    "w-full px-3 py-2 text-sm border-b border-border "
    "bg-background text-foreground "
    "placeholder:text-muted-foreground focus:outline-none"
)
_OPTION_CLS = (
    "flex items-center gap-2 px-3 py-2 text-sm cursor-pointer "
    "text-foreground "
    "hover:bg-accent transition-colors duration-100"
)
_GROUP_LABEL_CLS = (
    "px-3 pt-3 pb-1 text-xs font-semibold uppercase tracking-wide "
    "text-muted-foreground"
)
_SELECTED_OPTION_CLS = "bg-accent text-accent-foreground"
_EMPTY_CLS = "px-3 py-4 text-sm text-center text-muted-foreground"
_ERROR_CLS = "mt-1.5 text-sm text-destructive"


def _js_str(value: str) -> str:
    """Escape *value* for safe embedding in a JS single-quoted string literal."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


class RichSelect(Component):
    """Full-featured accessible select component powered by Alpine.js.

    Supports:

    * **Single-select** (default) — click an option to choose it; dropdown closes.
    * **Multi-select** (``multi=True``) — checkbox-style; multiple values selectable.
    * **Grouped options** (``groups``) — render labelled option groups.
    * **Async search** (``search_url``) — HTMX ``hx-get`` fires on the search input;
      the response should return a ``<ul id="{name}-options">`` fragment.
    * **Client-side filter** (no ``search_url``) — shown when there are more than
      ``SEARCH_THRESHOLD`` options or ``groups`` are present.

    Args:
        label: Visible label for the control.
        name: HTML ``name`` attribute used for form submission.
        options: Flat list of ``{"value": ..., "label": ...}`` dicts.
        multi: Enable multi-select behaviour.
        search_url: HTMX URL for server-side search.  Receives ``?q=<term>``.
        groups: Grouped options: ``[{"label": "Group", "options": [...]}]``.
        error: Validation error message shown below the control.
        placeholder: Trigger button placeholder text when nothing is selected.
    """

    SEARCH_THRESHOLD = 8

    def __init__(
        self,
        label: str,
        name: str,
        options: list[dict[str, Any]] | None = None,
        multi: bool = False,
        search_url: str = "",
        groups: list[dict[str, Any]] | None = None,
        error: str | None = None,
        placeholder: str = "Select an option",
        **props: Any,
    ) -> None:
        super().__init__(
            label=label,
            name=name,
            multi=multi,
            search_url=search_url,
            error=error,
            placeholder=placeholder,
            **props,
        )
        self.label = label
        self.name = name
        self.options: list[dict[str, Any]] = options or []
        self.multi = multi
        self.search_url = search_url
        self.groups: list[dict[str, Any]] = groups or []
        self.error = error
        self.placeholder = placeholder

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _needs_search(self) -> bool:
        flat_count = len(self.options) + sum(
            len(g.get("options", [])) for g in self.groups
        )
        return (
            bool(self.search_url)
            or flat_count > self.SEARCH_THRESHOLD
            or bool(self.groups)
        )

    def _alpine_data(self) -> str:
        ph = _js_str(self.placeholder)
        if self.multi:
            return (
                "{ open: false, search: '', selected: [], "
                f"getLabel() {{ return this.selected.length ? this.selected.length + ' selected' : '{ph}'; }}, "
                "isSelected(v) { return this.selected.includes(v); }, "
                "toggle(v) { const i = this.selected.indexOf(v); if (i > -1) this.selected.splice(i, 1); else this.selected.push(v); } }"
            )
        return (
            "{ open: false, search: '', selected: '', selectedLabel: '', "
            f"getLabel() {{ return this.selectedLabel || '{ph}'; }}, "
            "isSelected(v) { return this.selected === v; }, "
            "pick(v, lbl) { this.selected = v; this.selectedLabel = lbl; this.open = false; } }"
        )

    # ------------------------------------------------------------------
    # Option rendering
    # ------------------------------------------------------------------

    def _render_option(self, opt: dict[str, Any]) -> Any:
        value = str(opt.get("value", ""))
        label = str(opt.get("label", ""))
        vs = _js_str(value)
        ls = _js_str(label)

        # Client-side visibility filter (only active when no search_url)
        show_expr = (
            f"!search || '{ls}'.toLowerCase().includes(search.toLowerCase())"
            if not self.search_url
            else None
        )

        if self.multi:
            selected_cls = (
                f":class=\"isSelected('{vs}') ? '{_SELECTED_OPTION_CLS}' : ''\""
            )
            click_handler = f"toggle('{vs}')"
            checkbox = raw(
                f'<span class="flex-shrink-0 w-4 h-4 border-2 rounded flex items-center justify-center '
                f'transition-colors" '
                f":class=\"isSelected('{vs}') ? 'bg-primary border-primary' : 'border-input'\">"
                f'<svg x-show="isSelected(\'{vs}\')" class="w-3 h-3 text-white" fill="none" '
                f'viewBox="0 0 24 24" stroke="currentColor" stroke-width="3">'
                f'<path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg></span>'
            )
            children: list[Any] = [checkbox, el("span", label)]
        else:
            selected_cls = (
                f":class=\"isSelected('{vs}') ? '{_SELECTED_OPTION_CLS}' : ''\""
            )
            click_handler = f"pick('{vs}', '{ls}')"
            tick = raw(
                f'<svg x-show="isSelected(\'{vs}\')" class="ml-auto w-4 h-4 text-primary flex-shrink-0" '
                f'fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">'
                f'<path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>'
            )
            children = [el("span", label, class_="flex-1"), tick]

        attrs: dict[str, Any] = {
            "class_": _OPTION_CLS,
            "@click": click_handler,
            "role": "option",
        }
        if selected_cls:
            # Inject raw Alpine binding alongside class_ using dict child pattern
            attrs[":class"] = f"isSelected('{vs}') ? '{_SELECTED_OPTION_CLS}' : ''"
        if self.multi:
            attrs[":aria-selected"] = f"isSelected('{vs}')"
        else:
            attrs[":aria-selected"] = f"isSelected('{vs}') ? 'true' : 'false'"
        if show_expr:
            attrs["x-show"] = show_expr

        return el("div", *children, **attrs)

    # ------------------------------------------------------------------
    # render
    # ------------------------------------------------------------------

    def render(self) -> Any:
        options_list_id = f"{self.name}-options"

        # ---- trigger button ------------------------------------------
        trigger = el(
            "button",
            el(
                "span",
                **{
                    "x-text": "getLabel()",
                    "class_": "truncate",
                },
            ),
            raw(
                '<svg class="w-4 h-4 flex-shrink-0 text-muted-foreground transition-transform duration-200" '
                ":class=\"open ? 'rotate-180' : ''\" "
                'fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">'
                '<path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/></svg>'
            ),
            type="button",
            **{
                "@click": "open = !open",
                "class_": _TRIGGER_CLS,
                "role": "combobox",
                "aria-haspopup": "listbox",
                "aria-controls": options_list_id,
                ":aria-expanded": "open",
                "aria-label": self.label,
                "@keydown.down.prevent": "open = true; $nextTick(() => $el.querySelector('[role=option]')?.focus())",
                "@keydown.enter.prevent": "open = true",
            },
        )

        # ---- search input --------------------------------------------
        search_input: Any = ""
        if self._needs_search():
            search_attrs: dict[str, Any] = {
                "type": "text",
                "placeholder": "Search…",
                "class_": _SEARCH_CLS,
                "x-model": "search",
                "autocomplete": "off",
            }
            if self.search_url:
                search_attrs["hx-get"] = self.search_url
                search_attrs["hx-trigger"] = "input changed delay:300ms"
                search_attrs["hx-target"] = f"#{options_list_id}"
                search_attrs["hx-include"] = "this"
                search_attrs["name"] = "q"
            search_input = el("input", **search_attrs)

        # ---- options list --------------------------------------------
        option_nodes: list[Any] = []

        if self.groups:
            for group in self.groups:
                option_nodes.append(
                    el("div", group.get("label", ""), class_=_GROUP_LABEL_CLS)
                )
                for opt in group.get("options", []):
                    option_nodes.append(self._render_option(opt))
        else:
            for opt in self.options:
                option_nodes.append(self._render_option(opt))

        if not option_nodes and not self.search_url:
            option_nodes.append(el("div", "No options available", class_=_EMPTY_CLS))

        options_container = el(
            "div",
            *option_nodes,
            id=options_list_id,
            class_="max-h-56 overflow-y-auto py-1",
            role="listbox",
        )

        # ---- dropdown panel -----------------------------------------
        dropdown = el(
            "div",
            search_input,
            options_container,
            **{
                "x-show": "open",
                "x-transition:enter": "transition ease-out duration-100",
                "x-transition:enter-start": "opacity-0 scale-95",
                "x-transition:enter-end": "opacity-100 scale-100",
                "x-transition:leave": "transition ease-in duration-75",
                "x-transition:leave-start": "opacity-100 scale-100",
                "x-transition:leave-end": "opacity-0 scale-95",
                "class_": _DROPDOWN_CLS,
                "x-cloak": True,
            },
        )

        # ---- hidden inputs for form submission ----------------------
        if self.multi:
            hidden_inputs = raw(
                f'<template x-for="val in selected" :key="val">'
                f'<input type="hidden" name="{self.name}[]" :value="val">'
                f"</template>"
            )
        else:
            hidden_inputs = el(
                "input",
                type="hidden",
                name=self.name,
                **{":value": "selected"},
            )

        # ---- label ---------------------------------------------------
        label_el = el(
            "label",
            self.label,
            for_=f"{self.name}-trigger",
            class_="block text-sm font-medium text-foreground mb-1",
        )

        # ---- error message ------------------------------------------
        error_el: Any = el("p", self.error, class_=_ERROR_CLS) if self.error else ""

        ring_cls = (
            "ring-destructive focus-within:ring-destructive"
            if self.error
            else "ring-[var(--input)] focus-within:ring-ring"
        )

        return el(
            "div",
            label_el,
            el(
                "div",
                trigger,
                dropdown,
                hidden_inputs,
                class_=f"relative block w-full rounded-lg ring-1 ring-inset {ring_cls}",
            ),
            error_el,
            class_="mb-6",
            **{
                "x-data": self._alpine_data(),
                "@keydown.escape.window": "open = false",
                "@click.outside": "open = false",
            },
        )
