from __future__ import annotations

import itertools
import re
from typing import Any

from lexigram.ui.atoms.button import Button, ButtonVariant, SubmitButton
from lexigram.ui.core.base import Component, el, raw, render_to_string

_counter = itertools.count()


def _first_form_id(html: str) -> str | None:
    """Return the ``id`` of the first ``<form>`` element in *html*."""
    match = re.search(r"<form[^>]*\bid=[\"']([^\"']+)[\"']", html, re.IGNORECASE)
    return match.group(1) if match else None


def _inject_form_id(html: str, form_id: str) -> str:
    """Inject ``id=`` into the first ``<form>`` element of *html*.

    Used for raw form fragments without an id so a footer SubmitButton can
    be bound with the ``form`` attribute.
    """
    return re.sub(
        r"<form(?![^>]*\bid=)",
        f'<form id="{form_id}"',
        html,
        count=1,
        flags=re.IGNORECASE,
    )


class Modal(Component):
    """
    A FAANG-level modal dialog powered by Alpine.js.
    """

    # Modal panel styling constants
    PANEL_MAX_WIDTH = "max-w-[33.333vw]"
    PANEL_MAX_HEIGHT = "max-h-[66vh]"
    PANEL_CLASSES = (
        "relative transform overflow-hidden rounded-lg bg-card "
        "text-left shadow-lg transition-all w-full"
    )

    # Backdrop constants
    BACKDROP_CLASSES = "fixed inset-0 z-50 bg-black/80 transition-opacity"

    # Transition timing
    TRANSITION_ENTER = "ease-out duration-300"
    TRANSITION_LEAVE = "ease-in duration-200"

    # Default button variants
    DEFAULT_CANCEL_VARIANT: ButtonVariant = "outline"
    DEFAULT_CREATE_VARIANT: ButtonVariant = "default"

    def __init__(
        self,
        title: str,
        trigger: str | Any = None,
        footer: list[Any] | None = None,
        is_open: bool = False,
        render_trigger: bool = True,
        max_width: str | None = None,
        max_height: str | None = None,
        **props: Any,
    ) -> None:
        super().__init__(
            title=title,
            trigger=trigger,
            footer=footer or [],
            open=is_open,
            render_trigger=render_trigger,
            **props,
        )
        self.title = title
        self.trigger = trigger
        self.footer = footer or []
        self.initial_open = is_open
        self.render_trigger = render_trigger
        self.max_width = max_width or self.PANEL_MAX_WIDTH
        self.max_height = max_height or self.PANEL_MAX_HEIGHT
        self.id_suffix = next(_counter)

    def _build_panel_classes(self) -> str:
        """Build the panel classes with configurable max width/height."""
        return f"{self.PANEL_CLASSES} {self.max_width} {self.max_height} flex flex-col"

    def render(self) -> Any:
        trigger_node = None
        if getattr(self, "render_trigger", True) and self.trigger is not None:
            if isinstance(self.trigger, str):
                trigger_props: dict[str, Any] = {"x-on:click": "open = true"}
                trigger_node = Button(self.trigger, **trigger_props)
            else:
                trigger_node = el(
                    "div",
                    self.trigger,
                    **{"x-on:click": "open = true"},
                    class_="inline-block cursor-pointer",
                    tabindex="0",
                    role="button",
                    **{"x-on:keydown.enter.prevent": "open = true"},
                    **{"x-on:keydown.space.prevent": "open = true"},
                )

        rendered_children = list(map(render_to_string, self.children))

        footer_html: list[Any] = []
        if self.footer:
            footer_html = [
                (
                    raw(render_to_string(c))
                    if hasattr(c, "__html__") or hasattr(c, "render")
                    else str(c)
                )
                for c in self.footer
            ]

        footer_found: list[str] = []
        if not footer_html:
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

        if footer_found and not footer_html:
            footer_html = list(map(raw, footer_found))

        if not footer_html:
            # Match SlideOver's form contract: a delegated form action bar
            # needs a real form binding, while a form that already owns its
            # submit control must not receive a duplicate footer submit.
            content_html = "".join(rendered_children)
            form_present = "<form" in content_html.lower()
            form_obj = next(
                (c for c in self.children if hasattr(c, "submit_label")),
                None,
            )
            form_suppresses = bool(getattr(form_obj, "suppress_submit", False))
            form_id = getattr(form_obj, "form_id", None) or _first_form_id(content_html)
            has_own_submit = bool(
                re.search(r'<button[^>]*type=["\\\']submit', content_html)
            )

            # Modal footers are owned by a form component that explicitly
            # delegates its actions (``suppress_submit``). A raw HTML form is
            # intentionally left untouched: callers that provide raw markup
            # also own its submit/cancel semantics and should not receive
            # invisible, out-of-form controls injected by the container.
            if form_obj and form_suppresses and not form_id:
                auto_form_id = "modal-form"
                rendered_children = [
                    _inject_form_id(s, auto_form_id) if isinstance(s, str) else s
                    for s in rendered_children
                ]
                form_id = auto_form_id

            if form_obj and form_suppresses and form_id:
                cancel_props: dict[str, Any] = {"x-on:click": "open = false"}
                cancel_btn = Button(
                    "Cancel",
                    variant=self.DEFAULT_CANCEL_VARIANT,
                    **cancel_props,
                )
                save_btn = SubmitButton(
                    label=getattr(form_obj, "submit_label", "Save"),
                    variant=self.DEFAULT_CREATE_VARIANT,
                    form=form_id,
                )
                footer_html = [cancel_btn, save_btn]

        children_html = list(
            map(raw, filter(lambda s: s and s.strip(), rendered_children)),
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
                    "x-transition:enter": self.TRANSITION_ENTER,
                    "x-transition:leave": self.TRANSITION_LEAVE,
                    "class": "fixed inset-0 z-50",
                },
                el(
                    "div",
                    {
                        "x-on:click": "open = false",
                        "x-transition:enter": self.TRANSITION_ENTER,
                        "x-transition:enter-start": "opacity-0",
                        "x-transition:enter-end": "opacity-100",
                        "x-transition:leave": self.TRANSITION_LEAVE,
                        "x-transition:leave-start": "opacity-100",
                        "x-transition:leave-end": "opacity-0",
                        "class": self.BACKDROP_CLASSES,
                        "aria_hidden": "true",
                    },
                ),
                el(
                    "div",
                    {
                        "class": "fixed inset-0 z-10 w-screen overflow-y-auto",
                        "role": "dialog",
                        "aria-modal": "true",
                        "aria-labelledby": f"modal-title-{self.id_suffix}",
                        "aria-describedby": f"modal-description-{self.id_suffix}",
                    },
                    el(
                        "div",
                        {
                            "class": "flex min-h-screen items-center justify-center p-4 text-center sm:p-0",
                        },
                        el(
                            "div",
                            {
                                "x-trap": "open",
                                "x-transition:enter": self.TRANSITION_ENTER,
                                "x-transition:enter-start": "opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95",
                                "x-transition:enter-end": "opacity-100 translate-y-0 sm:scale-100",
                                "x-transition:leave": self.TRANSITION_LEAVE,
                                "x-transition:leave-start": "opacity-100 translate-y-0 sm:scale-100",
                                "x-transition:leave-end": "opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95",
                                "class": self._build_panel_classes(),
                            },
                            # Header (keeps title)
                            el(
                                "div",
                                {"class": "px-4 pb-0 pt-5 sm:p-6 sm:pb-0"},
                                el(
                                    "div",
                                    {"class": "sm:flex sm:items-start"},
                                    el(
                                        "div",
                                        {
                                            "class": "mt-3 text-center sm:ml-4 sm:mt-0 sm:text-left w-full",
                                        },
                                        el(
                                            "h3",
                                            {
                                                "class": "text-base font-semibold leading-6 text-foreground",
                                                "id": f"modal-title-{self.id_suffix}",
                                            },
                                            self.title,
                                        ),
                                    ),
                                ),
                            ),
                            # Scrollable Content
                            el(
                                "div",
                                {
                                    "class": "relative mt-2 flex-1 overflow-y-auto px-4 sm:px-6",
                                    "id": f"modal-description-{self.id_suffix}",
                                },
                                *children_html,
                            ),
                            # Sticky Footer (no default buttons; caller supplies footer). Add gap between buttons
                            el(
                                "div",
                                {
                                    "class": "bg-muted px-4 py-3 sm:flex sm:flex-row-reverse sm:px-6 sticky bottom-0 gap-3 items-center",
                                },
                                *footer_html,
                            ),
                        ),
                    ),
                ),
            ),
        )
