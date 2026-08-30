"""Page-level dashboard filter state (session-persisted) and form rendering.

A page declares a filter schema (``PageFilterField`` list), and this module
owns reading/merging that state (schema defaults → session → query params,
query wins), persisting it per page in the request session, rendering the
apply/reset filter form, and building widget fetch URLs annotated with the
current filter values.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from lexigram.contracts.admin.types import PageFilterField
from lexigram.ui import el

_SESSION_PREFIX = "admin_page_filters."
_RESET_PARAM = "reset_page_filters"


def _session(request: Any) -> Any:
    """Return the request session, or ``None`` when no session support exists."""
    return getattr(request, "session", None)


def _coerce(field: PageFilterField, raw: str) -> Any:
    """Coerce a query-param string to the field's declared type."""
    if field.type == "boolean":
        return raw in ("1", "true", "on")
    if field.type == "number":
        try:
            return int(raw)
        except ValueError:
            return raw
    return raw


def read_page_filters(
    request: Any,
    page_name: str,
    schema: list[PageFilterField] | tuple[PageFilterField, ...],
) -> dict[str, Any]:
    """Merge persisted state with request inputs for a page's filter schema.

    Resolution order (later wins): schema defaults, then session state, then
    query params. A ``reset_page_filters`` query param clears the session state
    and returns only schema defaults.

    Args:
        request: Asgi request exposing ``session`` and ``query_params``.
        page_name: Stable per-page key for session persistence.
        schema: Declared filter fields for the page.

    Returns:
        Mapping of ``{field_name: value}`` for every schema field.
    """
    merged: dict[str, Any] = {}
    for field in schema:
        if field.default is not None:
            merged[field.name] = field.default

    key = f"{_SESSION_PREFIX}{page_name}"
    session = _session(request)
    if session is not None:
        stored = session.get(key)
        if isinstance(stored, dict):
            merged.update({k: v for k, v in stored.items() if k in merged})

    params = request.query_params
    if params.get(_RESET_PARAM) in ("1", "true"):
        clear_page_filters(request, page_name)
        return {f.name: f.default for f in schema if f.default is not None}

    for field in schema:
        if field.name in params:
            merged[field.name] = _coerce(field, params[field.name])
    return merged


def save_page_filters(request: Any, page_name: str, values: dict[str, Any]) -> None:
    """Persist filter values for a page in the request session.

    Args:
        request: Asgi request exposing ``session``.
        page_name: Per-page persistence key.
        values: Filter values to store.
    """
    session = _session(request)
    if session is not None:
        session[f"{_SESSION_PREFIX}{page_name}"] = dict(values)


def clear_page_filters(request: Any, page_name: str) -> None:
    """Drop persisted filter values for a page from the session.

    Args:
        request: Asgi request exposing ``session``.
        page_name: Per-page persistence key.
    """
    session = _session(request)
    if session is not None:
        session.pop(f"{_SESSION_PREFIX}{page_name}", None)


def applied_from_query(
    request: Any, schema: list[PageFilterField] | tuple[PageFilterField, ...]
) -> bool:
    """Return whether any query param targeted a declared filter field.

    Args:
        request: Asgi request exposing ``query_params``.
        schema: Declared filter fields for the page.

    Returns:
        ``True`` if at least one schema field name appears in the query params.
    """
    return any(f.name in request.query_params for f in schema)


def widget_fetch_url(
    endpoint: str,
    page_filters: dict[str, Any] | None,
) -> str:
    """Append current page filter values to a widget fetch URL.

    Args:
        endpoint: The widget's ``hx-get`` render endpoint.
        page_filters: Current filter values, or ``None``.

    Returns:
        The endpoint with filter values appended as query parameters.
    """
    if not page_filters:
        return endpoint
    pairs = {k: v for k, v in page_filters.items() if v is not None and v != ""}
    if not pairs:
        return endpoint
    encoded = urlencode(pairs)
    sep = "&" if "?" in endpoint else "?"
    return f"{endpoint}{sep}{encoded}"


def render_page_filter_form(
    schema: list[PageFilterField] | tuple[PageFilterField, ...],
    current: dict[str, Any],
    action_url: str,
) -> Any:
    """Render an apply/reset filter form for a page.

    Args:
        schema: Declared filter fields for the page.
        current: Current filter values (used to prefill the controls).
        action_url: GET target for apply (the page URL itself).

    Returns:
        An ``el`` form node, or ``None`` when there is nothing to render.
    """
    if not schema:
        return None

    fields: list[Any] = []
    for field in schema:
        value = current.get(field.name, field.default)
        common_attrs: dict[str, Any] = {
            "name": field.name,
            "class": "bg-card border border-border rounded-md px-2 py-1 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary",
        }
        if field.description:
            common_attrs["title"] = field.description
        if field.type == "select" and field.options:
            options = []
            for option_value, option_label in field.options:
                option_attrs: dict[str, Any] = {}
                if value is not None and str(option_value) == str(value):
                    option_attrs["selected"] = True
                options.append(
                    el(
                        "option",
                        option_label,
                        value=str(option_value),
                        **option_attrs,
                    )
                )
            input_el = el("select", *options, **common_attrs)
        elif field.type == "boolean":
            input_el = el(
                "input",
                type="checkbox",
                checked=bool(value),
                **common_attrs,
            )
        elif field.type == "number":
            input_el = el(
                "input",
                type="number",
                value=str(value) if value is not None else "",
                **common_attrs,
            )
        else:
            input_el = el(
                "input",
                type="text",
                value=str(value) if value is not None else "",
                **common_attrs,
            )
        fields.append(
            el(
                "label",
                el(
                    "span",
                    field.label,
                    class_="block text-xs text-muted-foreground mb-1",
                ),
                input_el,
                class_="block",
            )
        )

    fields.extend(
        [
            el(
                "button",
                "Apply",
                type="submit",
                class_="px-3 py-1 text-sm rounded-md bg-primary text-primary-foreground hover:opacity-90",
            ),
            el(
                "a",
                "Reset",
                href=_with_reset_param(action_url),
                class_="px-3 py-1 text-sm rounded-md border border-border text-muted-foreground hover:bg-muted",
            ),
        ]
    )

    return el(
        "form",
        *fields,
        method="get",
        action=action_url,
        class_="chart-filters flex flex-wrap gap-3 items-end",
    )


def _with_reset_param(action_url: str) -> str:
    """Return ``action_url`` carrying the reset filter query param."""
    sep = "&" if "?" in action_url else "?"
    return f"{action_url}{sep}{_RESET_PARAM}=1"


__all__ = [
    "applied_from_query",
    "clear_page_filters",
    "read_page_filters",
    "render_page_filter_form",
    "save_page_filters",
    "widget_fetch_url",
]
