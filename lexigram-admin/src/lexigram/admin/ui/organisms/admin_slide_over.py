"""
AdminSlideOver — Unified slide-over panel for all overlay interactions.

Replaces all modal/popup usage in the admin UI with a consistent right-side
sliding panel. Supports three modes:
  - ``form``   : Create / Edit form (default)
  - ``confirm``: Delete / destructive action confirmation
  - ``info``   : Read-only detail view

All three modes render into ``Zones.SLIDE_OVER`` (``#slide-over-container``)
via HTMX ``innerHTML`` swap, which is already wired in the AdminShell.
"""

from __future__ import annotations

from typing import Any

from lexigram.ui import SlideOver, Zones, el, raw, render_to_string

# ---------------------------------------------------------------------------
# Helper: render a SlideOver fragment into the SLIDE_OVER zone
# ---------------------------------------------------------------------------


def render_slide_over_fragment(
    title: str,
    content: Any,
    *,
    subtitle: str | None = None,
    footer: list[Any] | None = None,
    size: str = "xl",
    variant: str = "default",
) -> str:
    """
    Render an AdminSlideOver fragment for direct HTMX ``innerHTML`` injection
    into ``#slide-over-container``.

    Args:
        title: Panel heading text.
        content: Any renderable component or HTML string for the body.
        subtitle: Optional secondary heading text.
        footer: Optional list of footer components (buttons, etc.).
        size: SlideOver width — ``sm``, ``md``, ``lg``, ``xl``, ``2xl``, ``full``.
        variant: ``"default"`` or ``"danger"`` (red accent for destructive actions).

    Returns:
        HTML string ready to swap into ``#slide-over-container``.
    """
    content_html = (
        raw(render_to_string(content))
        if hasattr(content, "render")
        else raw(content)
        if isinstance(content, str)
        else content
    )

    panel = SlideOver(
        title=title,
        subtitle=subtitle,
        trigger=None,
        render_trigger=False,
        is_open=True,
        size=size,
        variant=variant,
        footer=footer or [],
        children=[content_html],
    )
    return render_to_string(panel)


# ---------------------------------------------------------------------------
# Delete Confirmation Panel
# ---------------------------------------------------------------------------


def render_delete_confirm(
    *,
    record_label: str,
    delete_url: str,
    cancel_label: str = "Cancel",
    confirm_label: str = "Delete",
    message: str | None = None,
    extra_warning: str | None = None,
    hx_target: str | None = None,
    hx_swap: str | None = None,
) -> str:
    """
    Render a delete-confirmation slide-over fragment.

    The confirmation panel includes a danger warning block, the record name,
    a "Type DELETE to confirm" text input, and Cancel / Delete buttons.

    Args:
        record_label: Human-readable label for the record being deleted.
        delete_url: HTMX DELETE endpoint URL.
        cancel_label: Cancel button label.
        confirm_label: Confirm button label.
        message: Custom body message (overrides default).
        extra_warning: Optional secondary warning paragraph.
        hx_target: HTMX target zone after deletion (default: DATA zone).
        hx_swap: HTMX swap mode (default: DATA zone swap mode).
    """
    target = hx_target or Zones.DATA.selector
    swap = hx_swap or Zones.DATA.swap_mode.value

    default_message = (
        f"You are about to permanently delete <strong>{record_label}</strong>. "
        "This action <strong>cannot be undone</strong>."
    )

    body = el(
        "div",
        {"x-data": "{ confirmText: '' }", "class": "space-y-4"},
        # Danger icon + message block
        el(
            "div",
            {
                "class": "flex items-start gap-4 rounded-xl bg-destructive/10 border border-destructive/30 p-4"
            },
            raw(
                '<div class="flex-shrink-0 mt-0.5">'
                '<svg class="h-6 w-6 text-destructive" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">'
                '<path stroke-linecap="round" stroke-linejoin="round" '
                'd="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/>'
                "</svg>"
                "</div>"
            ),
            el(
                "div",
                {"class": "flex-1 min-w-0"},
                el(
                    "p",
                    {"class": "text-sm font-semibold text-destructive"},
                    "Confirm Deletion",
                ),
                el(
                    "p",
                    {"class": "mt-1 text-sm text-destructive leading-relaxed"},
                    raw(message or default_message),
                ),
            ),
        ),
        *(
            [
                el(
                    "p",
                    {
                        "class": "text-sm text-muted-foreground dark:text-muted-foreground italic"
                    },
                    extra_warning,
                )
            ]
            if extra_warning
            else []
        ),
        # Type "DELETE" to confirm
        el(
            "div",
            {"class": "mt-4"},
            el(
                "label",
                {
                    "for": "delete-confirm-input",
                    "class": "block text-sm font-medium text-foreground mb-1",
                },
                'Type <span class="font-bold tracking-wider">DELETE</span> to confirm:',
            ),
            el(
                "input",
                {
                    "type": "text",
                    "id": "delete-confirm-input",
                    "name": "delete_confirm",
                    "x-model": "confirmText",
                    "placeholder": "Type DELETE here",
                    "class": (
                        "block w-full rounded-lg border border-border "
                        "bg-background px-3 py-2 text-sm "
                        "text-foreground "
                        "placeholder-muted-foreground dark:placeholder-muted-foreground "
                        "focus:outline-none focus:ring-2 focus:ring-destructive focus:border-destructive "
                        "transition-colors"
                    ),
                    "autocomplete": "off",
                },
            ),
        ),
    )

    # Footer buttons
    cancel_btn = el(
        "button",
        {
            "type": "button",
            "x-on:click": "open = false",
            "class": (
                "inline-flex items-center rounded-lg px-4 py-2 text-sm font-medium "
                "text-foreground bg-card "
                "border border-border "
                "hover:bg-muted dark:hover:bg-muted "
                "focus:outline-none focus:ring-2 focus:ring-primary-500 "
                "transition-colors"
            ),
        },
        cancel_label,
    )
    confirm_btn = el(
        "button",
        {
            "type": "button",
            "hx-delete": delete_url,
            "hx-target": target,
            "hx-swap": swap,
            "x-on:click": "open = false",
            "x-bind:disabled": "confirmText !== 'DELETE'",
            "class": (
                "inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium "
                "text-white bg-destructive hover:bg-destructive/90 "
                "focus:outline-none focus:ring-2 focus:ring-destructive focus:ring-offset-2 "
                "transition-colors shadow-sm "
                "disabled:opacity-50 disabled:cursor-not-allowed"
            ),
        },
        raw(
            '<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">'
            '<path stroke-linecap="round" stroke-linejoin="round" '
            'd="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"/>'
            "</svg>"
        ),
        confirm_label,
    )

    return render_slide_over_fragment(
        title="Delete Record",
        content=body,
        subtitle=f'Deleting: "{record_label}"',
        footer=[cancel_btn, confirm_btn],
        size="md",
        variant="danger",
    )


# ---------------------------------------------------------------------------
# Bulk Delete Confirmation Panel
# ---------------------------------------------------------------------------


def render_bulk_delete_confirm(
    *,
    record_count: int,
    bulk_url: str,
    action: str = "delete",
    title: str = "Delete Records",
    heading: str = "Confirm Bulk Deletion",
    confirm_phrase: str = "DELETE",
    subtitle: str | None = None,
    cancel_label: str = "Cancel",
    confirm_label: str = "Delete",
    message: str | None = None,
    extra_warning: str | None = None,
    hx_target: str | None = None,
    hx_swap: str | None = None,
    variant: str = "danger",
    confirm_button_class: str | None = None,
) -> str:
    """
    Render a bulk-delete-confirmation slide-over fragment.

    Like ``render_delete_confirm`` but for multiple records — the confirm
    button issues an ``hx-post`` with ``hx-include`` for the checked IDs
    rather than a single ``hx-delete``. Reusable for any bulk action via
    the ``action``, ``title``, ``heading``, ``confirm_phrase``, ``variant``,
    and ``confirm_button_class`` parameters.

    Args:
        record_count: Number of records being affected.
        bulk_url: HTMX POST endpoint for the bulk action.
        action: Value posted in the ``action`` field (default ``"delete"``).
        title: Slide-over panel title (default ``"Delete Records"``).
        heading: Body heading text (default ``"Confirm Bulk Deletion"``).
        confirm_phrase: Phrase the user must type to confirm (default ``"DELETE"``).
        subtitle: Secondary heading text (default ``"Deleting N records"``).
        cancel_label: Cancel button label.
        confirm_label: Confirm button label.
        message: Custom body message (overrides default).
        extra_warning: Optional secondary warning paragraph.
        hx_target: HTMX target zone after the action (default: DATA zone).
        hx_swap: HTMX swap mode (default: DATA zone swap mode).
        variant: Slide-over variant (``"default"`` or ``"danger"``).
        confirm_button_class: Tailwind classes for the confirm button
            (default: destructive styling).
    """
    target = hx_target or Zones.DATA.selector
    swap = hx_swap or Zones.DATA.swap_mode.value

    suffix = "s" if record_count != 1 else ""
    default_message = (
        f"You are about to permanently delete <strong>{record_count}</strong> "
        f"record{suffix}. This action <strong>cannot be undone</strong>."
    )

    body = el(
        "div",
        {"x-data": "{ confirmText: '' }", "class": "space-y-4"},
        # Danger icon + message block
        el(
            "div",
            {
                "class": "flex items-start gap-4 rounded-xl bg-destructive/10 border border-destructive/30 p-4"
            },
            raw(
                '<div class="flex-shrink-0 mt-0.5">'
                '<svg class="h-6 w-6 text-destructive" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">'
                '<path stroke-linecap="round" stroke-linejoin="round" '
                'd="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/>'
                "</svg>"
                "</div>"
            ),
            el(
                "div",
                {"class": "flex-1 min-w-0"},
                el(
                    "p",
                    {"class": "text-sm font-semibold text-destructive"},
                    heading,
                ),
                el(
                    "p",
                    {"class": "mt-1 text-sm text-destructive leading-relaxed"},
                    raw(message or default_message),
                ),
            ),
        ),
        *(
            [
                el(
                    "p",
                    {
                        "class": "text-sm text-muted-foreground dark:text-muted-foreground italic"
                    },
                    extra_warning,
                )
            ]
            if extra_warning
            else []
        ),
        # Type "DELETE" to confirm
        el(
            "div",
            {"class": "mt-4"},
            el(
                "label",
                {
                    "for": "bulk-delete-confirm-input",
                    "class": "block text-sm font-medium text-foreground mb-1",
                },
                f'Type <span class="font-bold tracking-wider">{confirm_phrase}</span> to confirm:',
            ),
            el(
                "input",
                {
                    "type": "text",
                    "id": "bulk-delete-confirm-input",
                    "name": "delete_confirm",
                    "x-model": "confirmText",
                    "placeholder": f"Type {confirm_phrase} here",
                    "class": (
                        "block w-full rounded-lg border border-border "
                        "bg-background px-3 py-2 text-sm "
                        "text-foreground "
                        "placeholder-muted-foreground dark:placeholder-muted-foreground "
                        "focus:outline-none focus:ring-2 focus:ring-destructive focus:border-destructive "
                        "transition-colors"
                    ),
                    "autocomplete": "off",
                },
            ),
        ),
    )

    # Footer buttons
    cancel_btn = el(
        "button",
        {
            "type": "button",
            "x-on:click": "open = false",
            "class": (
                "inline-flex items-center rounded-lg px-4 py-2 text-sm font-medium "
                "text-foreground bg-card "
                "border border-border "
                "hover:bg-muted dark:hover:bg-muted "
                "focus:outline-none focus:ring-2 focus:ring-primary-500 "
                "transition-colors"
            ),
        },
        cancel_label,
    )
    default_button_class = (
        "inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium "
        "text-white bg-destructive hover:bg-destructive/90 "
        "focus:outline-none focus:ring-2 focus:ring-destructive focus:ring-offset-2 "
        "transition-colors shadow-sm "
        "disabled:opacity-50 disabled:cursor-not-allowed"
    )
    confirm_btn = el(
        "button",
        {
            "type": "button",
            "hx-post": bulk_url,
            "hx-target": target,
            "hx-swap": swap,
            "hx-vals": f'{{"action":"{action}"}}',
            "hx-include": "#lexigram-table [name='ids']:checked",
            "x-on:click": "open = false",
            "x-bind:disabled": f"confirmText !== '{confirm_phrase}'",
            "class": confirm_button_class or default_button_class,
        },
        raw(
            '<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">'
            '<path stroke-linecap="round" stroke-linejoin="round" '
            'd="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"/>'
            "</svg>"
        ),
        confirm_label,
    )

    return render_slide_over_fragment(
        title=title,
        content=body,
        subtitle=subtitle
        or f"Deleting {record_count} record{'s' if record_count != 1 else ''}",
        footer=[cancel_btn, confirm_btn],
        size="md",
        variant=variant,
    )


__all__ = [
    "render_bulk_delete_confirm",
    "render_delete_confirm",
    "render_slide_over_fragment",
]
