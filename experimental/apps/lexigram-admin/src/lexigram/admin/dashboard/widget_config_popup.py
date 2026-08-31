"""Widget configuration popup rendering for the admin dashboard."""

from __future__ import annotations

from typing import Any

from lexigram.admin.dashboard.widget_types import ConfigField
from lexigram.ui import el


def render_widget_config_popup(
    widget_name: str,
    title: str,
    fields: list[ConfigField],
    current_values: dict[str, Any],
    enabled: bool = True,
    admin_prefix: str = "/admin",
) -> str:
    """Render HTML for a widget config dialog."""
    rows: list[Any] = [
        el(
            "label",
            el(
                "input",
                type_="checkbox",
                name="enabled",
                checked="checked" if enabled else None,
            ),
            " Show on dashboard",
            class_="flex items-center gap-2 text-sm mb-4",
        )
    ]

    for f in fields:
        if isinstance(f, dict):
            f = ConfigField(**f)
        value = current_values.get(f.name, f.default)
        rows.append(
            el(
                "div",
                el("label", f.label, class_="block text-sm font-medium mb-1"),
                _render_field_input(f, value),
                class_="mb-3",
            ),
        )

    from lexigram.admin.ui.organisms.admin_slide_over import (
        render_slide_over_fragment,
    )

    config_endpoint = (
        (admin_prefix or "/admin").rstrip("/") or "/admin"
    ) + "/core/widgets/config"
    form = el(
        "form",
        *rows,
        el("input", type_="hidden", name="widget_name", value=widget_name),
        id=f"widget-config-form-{widget_name}",
        **{
            "hx-post": config_endpoint,
            "hx-swap": "none",
            "hx-on:htmx:after-request": "if(event.detail.successful){window.location.reload();}",
        },
        class_="space-y-3",
    )

    return render_slide_over_fragment(
        title=f"Configure: {title}",
        subtitle="Update this widget's settings.",
        content=form,
        size="md",
        footer=[
            el(
                "button",
                "Cancel",
                type_="button",
                **{"x-on:click": "open = false"},
                class_="inline-flex items-center rounded-lg px-4 py-2 text-sm font-medium text-foreground bg-card border border-border hover:bg-muted transition-colors",
            ),
            el(
                "button",
                "Save",
                type_="submit",
                form=f"widget-config-form-{widget_name}",
                class_="inline-flex items-center rounded-lg px-4 py-2 text-sm font-medium text-white bg-primary hover:bg-primary/90 transition-colors",
            ),
        ],
    )


def _render_field_input(
    field: ConfigField, current: Any, widget_name: str | None = None
) -> str:
    prefix = f"param__{widget_name}__" if widget_name else "param_"
    if field.type == "select" and field.options:
        opts = [
            el(
                "option",
                label,
                value=str(val),
                selected="selected" if val == current else None,
            )
            for val, label in field.options
        ]
        return str(
            el(
                "select",
                *opts,
                name=f"{prefix}{field.name}",
                class_="w-full border rounded px-2 py-1 text-sm",
            )
        )
    if field.type == "number":
        return str(
            el(
                "input",
                type_="number",
                name=f"{prefix}{field.name}",
                value=str(current) if current is not None else "",
                class_="w-full border rounded px-2 py-1 text-sm",
            )
        )
    if field.type == "boolean":
        return str(
            el(
                "input",
                type_="checkbox",
                name=f"{prefix}{field.name}",
                checked="checked" if current else None,
            )
        )
    return str(
        el(
            "input",
            type_="text",
            name=f"{prefix}{field.name}",
            value=str(current) if current is not None else "",
            class_="w-full border rounded px-2 py-1 text-sm",
        )
    )


__all__ = ["render_widget_config_popup"]
