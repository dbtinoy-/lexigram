from __future__ import annotations

import re
from typing import Any

from lexigram.ui.core.base import Component, el, raw, render_to_string

# Width map for size parameter
_SIZE_WIDTHS = {
    "sm": "max-w-sm",
    "md": "max-w-md",
    "lg": "max-w-lg",
    "xl": "max-w-xl",
    "2xl": "max-w-2xl",
    "full": "max-w-full",
}


class SlideOver(Component):
    """
    A side-panel drawer component for auxiliary content or editing.

    Args:
        size: Panel width — ``sm``, ``md``, ``lg`` (default), ``xl``, ``2xl``, ``full``
        variant: ``"default"`` (indigo accent) or ``"danger"`` (red accent for delete confirms)
    """

    def __init__(
        self,
        title: str,
        trigger: str | Any = None,
        slide_id: str = "slide-over",
        is_open: bool = False,
        render_trigger: bool = True,
        footer: list[Any] | None = None,
        size: str = "lg",
        variant: str = "default",
        subtitle: str | None = None,
        **props,
    ) -> None:
        super().__init__(
            title=title,
            trigger=trigger,
            id=slide_id,
            open=is_open,
            render_trigger=render_trigger,
            footer=footer or [],
            **props,
        )
        self.title = title
        self.trigger = trigger
        self.id = slide_id
        self.initial_open = is_open
        self.render_trigger = render_trigger
        self.footer = footer or []
        self.size = size
        self.variant = variant  # "default" or "danger"
        self.subtitle = subtitle

    def render(self) -> Any:
        rendered_children = list(map(render_to_string, self.children))

        footer_html: list[Any] = []
        footer_found: list[str] = []
        if not self.footer:
            new_rendered_children: list[str] = []
            for s in rendered_children:
                m = re.search(
                    r'<div[^>]*(?:data-footer|class="[^"]*(?:actions|slide-over-actions)[^"]*")[^>]*>(.*?)</div>',
                    s,
                    re.DOTALL,
                )
                if m:
                    footer_found.append(m.group(1))
                    s = s[: m.start()] + s[m.end() :]
                new_rendered_children.append(s)
            rendered_children = new_rendered_children

        if self.footer:
            footer_html = [
                raw(render_to_string(c))
                if hasattr(c, "__html__") or hasattr(c, "render")
                else str(c)
                for c in self.footer
            ]

        if footer_found and not footer_html:
            footer_html = [raw(f) for f in footer_found]

        content_html_joined = "".join(rendered_children)
        if not footer_html:
            form_present = "<form" in content_html_joined.lower()
            form_obj = None
            for c in self.children:
                if hasattr(c, "submit_label"):
                    form_obj = c
                    break

            form_needs_actions = form_present and (
                form_obj is None or getattr(form_obj, "suppress_submit", False)
            )

            if form_needs_actions:
                from lexigram.ui.atoms.button import Button, SubmitButton

                save_label = getattr(form_obj, "submit_label", "Save")
                cancel_btn = Button(
                    "Cancel",
                    variant="outline",
                    x_on_click="open = false",
                )
                save_btn = SubmitButton(
                    label=save_label,
                )
                footer_html = [cancel_btn, save_btn]

        children_html = [
            raw(s) for s in filter(lambda s: s and s.strip(), rendered_children)
        ]

        from lexigram.ui.molecules.action_button import ActionButton

        # Resolve panel width from size
        panel_width = _SIZE_WIDTHS.get(self.size, _SIZE_WIDTHS["lg"])

        # Accent colour based on variant
        is_danger = self.variant == "danger"
        accent_bar_cls = (
            "h-1 w-full bg-gradient-to-r from-[var(--destructive)] to-[var(--destructive)]/80"
            if is_danger
            else "h-1 w-full bg-gradient-to-r from-[var(--primary)] to-[var(--primary)]/70"
        )
        title_cls = (
            "text-base font-semibold leading-6 text-destructive"
            if is_danger
            else "text-base font-semibold leading-6 text-foreground"
        )

        trigger_node = None
        if getattr(self, "render_trigger", True) and self.trigger is not None:
            if isinstance(self.trigger, str):
                trigger_node = ActionButton(
                    label=self.trigger,
                    color="ghost",
                    size="sm",
                    type="button",
                    **{  # type: ignore[arg-type]
                        "x-on:click": "open = true",
                        "class_": "text-primary hover:text-primary/80",
                    },
                ).render()
            else:
                trigger_node = el(
                    "div",
                    self.trigger,
                    **{"x-on:click": "open = true"},
                    class_="inline-block",
                    tabindex="0",
                    role="button",
                    **{"x-on:keydown.enter.prevent": "open = true"},
                    **{"x-on:keydown.space.prevent": "open = true"},
                )

        if trigger_node:
            trigger_node = el(
                "div",
                trigger_node,
                class_="flex justify-end inline-block",
            )

        # Header content
        subtitle_el = (
            el(
                "p",
                {"class": "mt-1 text-xs text-muted-foreground"},
                self.subtitle,
            )
            if self.subtitle
            else ""
        )

        return el(
            "div",
            {
                "x-data": f"{{ open: {'true' if self.initial_open else 'false'} }}",
                "class": "relative z-50",
                "x-on:keydown.window.escape": "open = false",
                "x-effect": "open ? document.body.classList.add('overflow-hidden') : document.body.classList.remove('overflow-hidden')",
                "x-cloak": True,
            },
            trigger_node if trigger_node else "",
            el(
                "div",
                {
                    "x-show": "open",
                    "class": "relative z-50",
                    "aria-labelledby": "slide-over-title",
                    "role": "dialog",
                    "aria-modal": "true",
                    "x-trap": "open",
                },
                # Backdrop
                el(
                    "div",
                    {
                        "x-on:click": "open = false",
                        "x-transition:enter": "ease-in-out duration-300",
                        "x-transition:enter-start": "opacity-0",
                        "x-transition:enter-end": "opacity-100",
                        "x-transition:leave": "ease-in-out duration-300",
                        "x-transition:leave-start": "opacity-100",
                        "x-transition:leave-end": "opacity-0",
                        "class": "fixed inset-0 bg-background/80 backdrop-blur-sm transition-opacity",
                    },
                ),
                el(
                    "div",
                    {"class": "fixed inset-0 overflow-hidden"},
                    el(
                        "div",
                        {"class": "absolute inset-0 overflow-hidden"},
                        el(
                            "div",
                            {
                                "class": f"pointer-events-none fixed inset-y-0 right-0 flex {panel_width} w-full",
                            },
                            el(
                                "div",
                                {
                                    "x-transition:enter": "transform transition ease-in-out duration-300",
                                    "x-transition:enter-start": "translate-x-full",
                                    "x-transition:enter-end": "translate-x-0",
                                    "x-transition:leave": "transform transition ease-in-out duration-300",
                                    "x-transition:leave-start": "translate-x-0",
                                    "x-transition:leave-end": "translate-x-full",
                                    "class": "pointer-events-auto w-full",
                                },
                                el(
                                    "div",
                                    {
                                        "class": "flex h-full flex-col bg-card shadow-2xl ring-1 ring-border",
                                    },
                                    # Accent bar at top
                                    el("div", {"class": accent_bar_cls}),
                                    # Header
                                    el(
                                        "div",
                                        {"class": "px-5 py-4 border-b border-border"},
                                        el(
                                            "div",
                                            {
                                                "class": "flex items-start justify-between gap-3"
                                            },
                                            el(
                                                "div",
                                                {"class": "min-w-0 flex-1"},
                                                el(
                                                    "h2",
                                                    {
                                                        "class": title_cls,
                                                        "id": "slide-over-title",
                                                    },
                                                    self.title,
                                                ),
                                                subtitle_el,
                                            ),
                                            el(
                                                "button",
                                                {
                                                    "type": "button",
                                                    "x-on:click": "open = false",
                                                    "aria-label": "Close panel",
                                                    "class": (
                                                        "flex-shrink-0 rounded-lg p-1.5 text-muted-foreground "
                                                        "hover:bg-accent hover:text-accent-foreground "
                                                        "transition-colors focus:outline-none "
                                                        "focus-visible:ring-2 focus-visible:ring-ring"
                                                    ),
                                                },
                                                raw(
                                                    '<svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" '
                                                    'stroke-width="1.5" stroke="currentColor">'
                                                    '<path stroke-linecap="round" stroke-linejoin="round" '
                                                    'd="M6 18L18 6M6 6l12 12"/>'
                                                    "</svg>"
                                                ),
                                            ),
                                        ),
                                    ),
                                    # Scrollable content
                                    el(
                                        "div",
                                        {
                                            "class": "relative flex-1 overflow-y-auto px-5 py-5",
                                        },
                                        *children_html,
                                    ),
                                    # Sticky footer
                                    (
                                        el(
                                            "div",
                                            {
                                                "class": (
                                                    "border-t border-border "
                                                    "bg-muted "
                                                    "px-5 py-4 flex items-center justify-end gap-3 "
                                                    "sticky bottom-0"
                                                ),
                                            },
                                            *footer_html,
                                        )
                                        if footer_html
                                        else ""
                                    ),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )
