"""
Legacy bulk-edit overlay compatibility helpers.

The active resource flow renders bulk actions through the DataTable action
pipeline and mounted bulk endpoints. No current admin route imports these
standalone organisms, so they remain only as compatibility exports while
callers migrate to the shared ``Form``/``FormActions``/``SubmitButton`` and
``render_slide_over_fragment`` contract.
"""

from __future__ import annotations

import warnings
from typing import Any

from htpy import div, form, input_, label, option, p, select, span, textarea

from lexigram.admin.actions.bulk_manager import BulkEditField
from lexigram.admin.ui.organisms.admin_slide_over import render_slide_over_fragment
from lexigram.ui import Button, el, raw


def _warn_legacy_overlay(name: str) -> None:
    """Tell downstream callers to use the mounted resource bulk flow."""
    warnings.warn(
        f"{name} is a legacy compatibility helper; use the resource "
        "DataTable bulk action pipeline instead.",
        DeprecationWarning,
        stacklevel=3,
    )


def bulk_edit_modal(
    selected_count: int,
    fields: list[BulkEditField],
    action_url: str,
    preview_items: list[str] | None = None,
) -> str:
    """
    Render a bulk-edit slide-over panel.

    Args:
        selected_count: Number of selected records
        fields: List of editable fields
        action_url: URL to submit the form to
        preview_items: Optional list of item labels for preview

    Returns:
        HTML string for the SlideOver zone (``#slide-over-container``)
    """
    _warn_legacy_overlay("bulk_edit_modal")
    preview_block: Any = ""
    if preview_items:
        preview_block = el(
            "div",
            {
                "class": "mb-5 rounded-xl bg-primary-50 dark:bg-primary-950/30 "
                "border border-primary-200 dark:border-primary-800/50 p-4",
            },
            el(
                "p",
                {
                    "class": "text-sm font-semibold text-primary-800 dark:text-primary-200 mb-2"
                },
                "Selected records:",
            ),
            el(
                "div",
                {"class": "space-y-1"},
                *[
                    el(
                        "p",
                        {
                            "class": "text-sm text-primary-700 dark:text-primary-300 truncate"
                        },
                        f"• {item}",
                    )
                    for item in preview_items[:5]
                ],
                *(
                    [
                        el(
                            "p",
                            {"class": "text-xs text-primary-500 mt-1"},
                            f"…and {len(preview_items) - 5} more",
                        )
                    ]
                    if len(preview_items) > 5
                    else []
                ),
            ),
        )

    body = el(
        "div",
        {"class": "space-y-5"},
        preview_block,
        raw(
            f'<form id="bulk-edit-form" hx-post="{action_url}" '
            'hx-target="#table-body" hx-swap="outerHTML">'
            '<div class="space-y-4">'
            + "".join(_render_field_html(f) for f in fields)
            + "</div></form>"
        ),
    )

    cancel_btn = el(
        "button",
        {
            "type": "button",
            "x-on:click": "open = false",
            "class": (
                "inline-flex items-center rounded-lg px-4 py-2 text-sm font-medium "
                "text-foreground bg-card "
                "border border-border "
                "hover:bg-muted dark:hover:bg-muted transition-colors"
            ),
        },
        "Cancel",
    )
    submit_btn = el(
        "button",
        {
            "type": "submit",
            "form": "bulk-edit-form",
            "x-on:click": "open = false",
            "class": (
                "inline-flex items-center rounded-lg px-4 py-2 text-sm font-medium "
                "text-white bg-primary-600 hover:bg-primary-700 "
                "focus:outline-none focus:ring-2 focus:ring-primary-500 "
                "transition-colors shadow-sm"
            ),
        },
        "Update Records",
    )

    return render_slide_over_fragment(
        title=f"Bulk Edit {selected_count} Record{'s' if selected_count != 1 else ''}",
        content=body,
        subtitle="Changes will be applied to all selected records.",
        footer=[cancel_btn, submit_btn],
        size="xl",
    )


def _render_field_html(field: BulkEditField) -> str:
    """Render a single form field as an HTML string (used in slide-over body)."""
    field_id = f"bulk-edit-{field.name}"
    input_cls = (
        "mt-1 block w-full rounded-lg border border-border "
        "bg-card text-foreground px-3 py-2 text-sm "
        "focus:outline-none focus:ring-2 focus:ring-primary-500 transition-colors"
    )
    required_attr = "required" if field.required else ""
    req_star = (
        '<span class="text-destructive ml-0.5">*</span>' if field.required else ""
    )
    label_html = (
        f'<label for="{field_id}" class="block text-sm font-medium '
        f'text-foreground mb-1">{field.label}{req_star}</label>'
    )

    if field.field_type == "select" and field.options:
        options_html = '<option value="">-- No change --</option>' + "".join(
            f'<option value="{v}">{lbl}</option>' for v, lbl in field.options
        )
        input_html = f'<select id="{field_id}" name="{field.name}" {required_attr} class="{input_cls}">{options_html}</select>'
    elif field.field_type == "textarea":
        input_html = f'<textarea id="{field_id}" name="{field.name}" rows="3" {required_attr} class="{input_cls}"></textarea>'
    elif field.field_type == "checkbox":
        input_html = (
            f'<input type="checkbox" id="{field_id}" name="{field.name}" value="true" '
            f'class="mt-1 h-4 w-4 rounded border-border text-primary-600 focus:ring-primary-500">'
        )
    else:
        input_html = (
            f'<input type="{field.field_type}" id="{field_id}" name="{field.name}" '
            f'{required_attr} class="{input_cls}">'
        )

    help_html = (
        f'<p class="mt-1 text-xs text-muted-foreground">{field.help_text}</p>'
        if field.help_text
        else ""
    )
    return f'<div class="space-y-1">{label_html}{input_html}{help_html}</div>'

    """Render a single form field."""
    field_id = f"bulk-edit-{field.name}"

    # Label
    label_elem = label(
        for_=field_id,
        class_="block text-sm font-medium text-foreground",
    )[
        field.label,
        span(class_="text-destructive")[" *"] if field.required else None,
    ]

    # Input element based on type
    if field.field_type == "select" and field.options:
        input_elem = select(
            id=field_id,
            name=field.name,
            required=field.required,
            class_="mt-1 block w-full rounded-md border-border dark:bg-muted dark:text-foreground shadow-sm focus:border-ring focus:ring-ring sm:text-sm",
        )[
            option(value="")["-- No change --"],
            [option(value=str(vl[0]))[vl[1]] for vl in field.options],
        ]
    elif field.field_type == "textarea":
        input_elem = textarea(
            id=field_id,
            name=field.name,
            required=field.required,
            rows="3",
            class_="mt-1 block w-full rounded-md border-border dark:bg-muted dark:text-foreground shadow-sm focus:border-ring focus:ring-ring sm:text-sm",
        )
    elif field.field_type == "checkbox":
        input_elem = input_(
            type="checkbox",
            id=field_id,
            name=field.name,
            value="true",
            class_="mt-1 h-4 w-4 rounded border-border text-primary focus:ring-ring",
        )
    else:
        input_elem = input_(
            type=field.field_type,
            id=field_id,
            name=field.name,
            required=field.required,
            class_="mt-1 block w-full rounded-md border-border dark:bg-muted dark:text-foreground shadow-sm focus:border-ring focus:ring-ring sm:text-sm",
        )

    # Help text
    help_elem = (
        p(class_="mt-1 text-sm text-muted-foreground")[field.help_text]
        if field.help_text
        else None
    )

    return div(class_="form-field")[label_elem, input_elem, help_elem]


def bulk_assign_modal(
    selected_count: int,
    field_label: str,
    options: list[tuple[Any, str]],
    action_url: str,
    field_name: str = "value",
    allow_null: bool = False,
    confirm_message: str | None = None,
) -> Any:
    """
    Render a modal for bulk assign operations (status, owner, etc.).

    Args:
        selected_count: Number of selected records
        field_label: Label for the field being assigned
        options: List of (value, label) tuples
        action_url: URL to submit the form to
        field_name: Name attribute for the select field
        allow_null: Whether to show "Unassign" option
        confirm_message: Optional custom confirmation message

    Returns:
        htpy component for the modal
    """
    _warn_legacy_overlay("bulk_assign_modal")
    return div(
        class_="fixed inset-0 bg-muted bg-opacity-50 hidden",
        id="bulk-assign-modal",
    )[
        div(class_="flex items-center justify-center min-h-screen px-4")[
            div(
                class_="bg-card rounded-lg shadow-xl max-w-lg w-full",
            )[
                # Header
                div(class_="px-6 py-4 border-b border-border")[
                    div(class_="flex items-center justify-between")[
                        p(class_="text-lg font-semibold text-foreground")[
                            f"Bulk Assign {field_label}"
                        ],
                        Button(
                            type="button",
                            color="ghost",
                            onclick="document.getElementById('bulk-assign-modal').classList.add('hidden')",
                        )["✕"],  # type: ignore[index]
                    ],
                ],
                # Body
                div(class_="px-6 py-4")[
                    (
                        div(
                            class_="mb-4 p-3 bg-warning/10 rounded-lg",
                        )[
                            p(class_="text-sm text-warning")[
                                confirm_message
                                or f"This will update {selected_count} record(s)."
                            ]
                        ]
                    ),
                    form(
                        id="bulk-assign-form",
                        hx_post=action_url,
                        hx_target="#table-body",
                        hx_swap="outerHTML",
                    )[
                        label(
                            for_="bulk-assign-value",
                            class_="block text-sm font-medium text-foreground mb-2",
                        )[f"Select {field_label}"],
                        select(
                            id="bulk-assign-value",
                            name=field_name,
                            required=not allow_null,
                            class_="block w-full rounded-md border-border dark:bg-muted dark:text-foreground shadow-sm focus:border-ring focus:ring-ring",
                        )[
                            (
                                option(value="", selected=True)["-- Unassign --"]
                                if allow_null
                                else None
                            ),
                            [
                                option(value=str(val))[label_text]
                                for val, label_text in options
                            ],
                        ],
                    ],
                ],
                # Footer
                div(
                    class_="px-6 py-4 border-t border-border flex justify-end space-x-3",
                )[
                    Button(
                        type="button",
                        color="secondary",
                        onclick="document.getElementById('bulk-assign-modal').classList.add('hidden')",
                    )["Cancel"],  # type: ignore[index]
                    Button(
                        type="submit",
                        form="bulk-assign-form",
                        color="primary",
                        onclick="document.getElementById('bulk-assign-modal').classList.add('hidden')",
                    )["Assign"],  # type: ignore[index]
                ],
            ]
        ]
    ]


def bulk_confirm_dialog(
    action_name: str,
    selected_count: int,
    preview_items: list[str] | None = None,
    is_danger: bool = False,
    action_url: str = "",
) -> Any:
    """
    Render a confirmation dialog for bulk actions.

    Args:
        action_name: Name of the action (e.g., "delete", "archive")
        selected_count: Number of selected records
        preview_items: Optional preview of affected items
        is_danger: Whether this is a dangerous action (red styling)
        action_url: URL to submit the action to

    Returns:
        htpy component for the confirmation dialog
    """
    _warn_legacy_overlay("bulk_confirm_dialog")

    return div(
        class_="fixed inset-0 bg-muted bg-opacity-50 hidden",
        id="bulk-confirm-dialog",
    )[
        div(class_="flex items-center justify-center min-h-screen px-4")[
            div(
                class_="bg-card rounded-lg shadow-xl max-w-md w-full",
            )[
                # Header
                div(class_="px-6 py-4")[
                    p(class_="text-lg font-semibold text-foreground")[
                        f"Confirm {action_name.title()}"
                    ],
                    p(class_="mt-2 text-sm text-muted-foreground")[
                        f"Are you sure you want to {action_name} {selected_count} record(s)?"
                    ],
                ],
                # Preview
                (
                    div(class_="px-6 py-2")[
                        div(
                            class_="max-h-40 overflow-y-auto border border-border rounded p-3 bg-muted dark:bg-background",
                        )[
                            [
                                p(
                                    class_="text-sm text-foreground truncate",
                                )[f"• {item}"]
                                for item in (preview_items or [])[:10]
                            ],
                            (
                                p(
                                    class_="text-sm text-muted-foreground mt-2",
                                )[f"...and {len(preview_items) - 10} more"]
                                if preview_items and len(preview_items) > 10
                                else None
                            ),
                        ]
                    ]
                    if preview_items
                    else None
                ),
                # Footer
                div(
                    class_="px-6 py-4 border-t border-border flex justify-end space-x-3",
                )[
                    Button(
                        type="button",
                        color="secondary",
                        onclick="document.getElementById('bulk-confirm-dialog').classList.add('hidden')",
                    )["Cancel"],  # type: ignore[index]
                    Button(
                        type="button",
                        color="danger" if is_danger else "primary",
                        hx_post=action_url,
                        hx_target="#table-body",
                        hx_swap="outerHTML",
                        onclick="document.getElementById('bulk-confirm-dialog').classList.add('hidden')",
                    )[action_name.title()],  # type: ignore[index]
                ],
            ]
        ]
    ]


def bulk_progress_indicator(
    action_name: str,
    progress_url: str,
) -> Any:
    """
    Render a progress indicator for slow bulk actions.

    Polls the progress_url to update the progress bar.

    Args:
        action_name: Name of the action being performed
        progress_url: URL to poll for progress updates

    Returns:
        htpy component for the progress indicator
    """
    _warn_legacy_overlay("bulk_progress_indicator")
    return div(
        class_="fixed inset-0 bg-muted bg-opacity-50 flex items-center justify-center",
        id="bulk-progress",
    )[
        div(
            class_="bg-card rounded-lg shadow-xl max-w-md w-full p-6",
        )[
            p(class_="text-lg font-semibold text-foreground mb-4")[
                f"{action_name.title()} in Progress..."
            ],
            # Progress bar
            div(class_="w-full bg-muted rounded-full h-2.5 mb-2")[
                div(
                    id="progress-bar",
                    class_="bg-primary h-2.5 rounded-full transition-all duration-300",
                    style="width: 0%",
                )
            ],
            # Status text
            div(
                id="progress-status",
                class_="text-sm text-muted-foreground text-center",
                hx_get=progress_url,
                hx_trigger="every 500ms",
                hx_swap="innerHTML",
            )["Starting..."],
            # Errors
            div(
                id="progress-errors",
                class_="mt-4 text-sm text-destructive",
            ),
        ]
    ]
