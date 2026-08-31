"""Template utilities for lexigram-admin.

Provides simple template rendering functions for standalone pages
like login, error, etc. Uses StandaloneLayout for consistent styling.
"""

from typing import Any, cast

from markupsafe import escape

from lexigram.admin.ui.layouts import (
    StandaloneLayout,
    StandaloneLayoutConfig,
    StandaloneLayoutContext,
)
from lexigram.ui import SubmitButton, TextInput, el, render_to_string


def _flash_messages(
    error: str,
    notice: str = "",
) -> list[tuple[str, str]]:
    """Build the standalone flash list from error/notice strings.

    Args:
        error: Error message to display.
        notice: Optional success notice to display.

    Returns:
        List of (category, message) tuples for the standalone layout.
    """
    messages: list[tuple[str, str]] = []
    if error:
        messages.append(("error", error))
    if notice:
        messages.append(("success", notice))
    return messages


def _standalone_card(
    page_title: str,
    heading: str,
    copy: str,
    children: list[Any],
    *,
    site_name: str = "Lexigram Admin",
    base_url: str = "/admin",
    flash_messages: list[tuple[str, str]] | None = None,
) -> str:
    """Render a centred standalone auth card inside the standalone layout.

    Args:
        page_title: Document title used by the standalone layout.
        heading: Card heading text.
        copy: Subtitle text rendered under the heading.
        children: Body elements rendered inside the card.
        site_name: Site name for branding.
        base_url: Mounted admin base URL used for shared assets.
        flash_messages: Error/success flashes rendered above the card.

    Returns:
        Full standalone HTML document.
    """
    content = el(
        "div",
        el(
            "div",
            el("h1", heading, class_="text-2xl font-bold text-foreground mb-2"),
            el("p", copy, class_="text-sm text-muted-foreground"),
            class_="text-center mb-6",
        ),
        *children,
        class_="w-full max-w-md bg-card border border-border rounded-lg shadow-lg p-8",
    )
    layout = StandaloneLayout(
        config=StandaloneLayoutConfig(
            app_name=site_name,
            show_footer=True,
            centered=True,
        ),
        context=StandaloneLayoutContext(
            page_title=page_title,
            base_url=base_url,
            flash_messages=flash_messages or [],
        ),
    )
    return layout.render(render_to_string(content))


def _auth_form(
    action: str,
    csrf_token: str,
    fields: list[Any],
    submit_label: str,
    *,
    hidden: list[tuple[str, str]] | None = None,
    submit_variant: str = "default",
    footer: Any | None = None,
) -> Any:
    """Build a standard POST form with a CSRF field and submit button.

    Args:
        action: Form action URL.
        csrf_token: CSRF token embedded as a hidden field.
        fields: Input components rendered in vertical order.
        submit_label: Submit button text.
        hidden: Extra hidden (name, value) fields.
        submit_variant: Button variant (default or destructive).
        footer: Optional element rendered after the submit button.

    Returns:
        An ``el()`` form tree.
    """
    children: list[Any] = [
        el("input", type="hidden", name="csrf_token", value=csrf_token),
    ]
    children.extend(
        el("input", type="hidden", name=name, value=value)
        for name, value in (hidden or [])
    )
    children.extend(el("div", field, class_="mb-4") for field in fields)
    children.append(
        SubmitButton(
            label=submit_label, variant=cast("Any", submit_variant), class_="w-full"
        )
    )
    if footer is not None:
        children.append(footer)
    return el("form", *children, method="post", action=action)


def _code_input(label: str) -> Any:
    """Build the standard 6-digit one-time code input.

    Args:
        label: Field label text.

    Returns:
        An ``el()`` tree with the labelled code input.
    """
    return TextInput(
        name="code",
        label=label,
        inputmode="numeric",
        autocomplete="one-time-code",
        pattern="[0-9]{6}",
        maxlength=6,
        placeholder="123456",
        required=True,
        autofocus=True,
    )


def _email_badge(verified: bool) -> Any:
    """Render an email verification status strip.

    Args:
        verified: True when the email address is verified.

    Returns:
        An ``el()`` tree with the status text.
    """
    badge_text = "verified" if verified else "not verified"
    badge_class = "text-green-600" if verified else "text-foreground"
    return el(
        "div",
        el(
            "p",
            "Email address: ",
            el("span", badge_text, class_=f"font-medium {badge_class}"),
            class_="text-sm text-foreground",
        ),
        class_="mb-6 p-3 rounded-md bg-muted",
    )


def _primary_link(label: str, href: str, extra_class: str = "") -> Any:
    """Render a primary-button-styled anchor link.

    Args:
        label: Link text.
        href: Destination URL.
        extra_class: Additional CSS classes.

    Returns:
        An ``el()`` anchor tree.
    """
    return el(
        "a",
        label,
        href=href,
        class_=(
            "inline-flex items-center justify-center gap-2 whitespace-nowrap "
            "rounded-md text-sm font-medium ring-offset-background transition-colors "
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring "
            "focus-visible:ring-offset-2 bg-primary text-primary-foreground "
            f"hover:bg-primary/90 h-10 px-4 py-2 {extra_class}"
        ),
    )


def _auth_footer(*children: Any) -> Any:
    """Render a centred footer line under an auth form.

    Args:
        *children: Link/text elements to render.

    Returns:
        An ``el()`` paragraph tree.
    """
    return el("p", *children, class_="mt-4 text-center text-sm")


def _flash(error: str, notice: str) -> str:
    """Render inline error/notice flash messages.

    Args:
        error: Error message to display (empty hides the block).
        notice: Success notice to display (empty hides the block).

    Returns:
        HTML string with the flash blocks.
    """
    parts = []
    if error:
        parts.append(f'<div class="text-sm text-destructive">{escape(error)}</div>')
    if notice:
        parts.append(f'<div class="text-sm text-emerald-600">{escape(notice)}</div>')
    return "\n".join(parts)
