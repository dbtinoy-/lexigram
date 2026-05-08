from __future__ import annotations

from typing import Any

from lexigram.ui.atoms.button import Button
from lexigram.ui.core.base import Component, el


class Form(Component):
    """
    A container for form fields with HTMX submission support.
    """

    def __init__(
        self,
        action_url: str | None = None,
        method: str = "post",
        submit_label: str = "Save",
        hx_target: str = "#main-content",
        hx_swap: str = "innerHTML",
        autosave: bool = False,
        form_id: str | None = None,
        suppress_submit: bool = False,
        **props: Any,
    ) -> None:
        super().__init__(
            action_url=action_url,
            method=method,
            submit_label=submit_label,
            hx_target=hx_target,
            hx_swap=hx_swap,
            autosave=autosave,
            form_id=form_id,
            suppress_submit=suppress_submit,
            **props,
        )
        self.action_url = action_url
        self.method = method
        self.submit_label = submit_label
        self.hx_target = hx_target
        self.hx_swap = hx_swap
        self.autosave = autosave
        self.form_id = form_id
        self.suppress_submit = suppress_submit

    def render(self) -> Any:
        attrs = {
            "method": self.method,
            "class": "space-y-6",
        }

        submit_button_attrs = {}
        if self.action_url:
            if self.method.lower() == "get":
                attrs["hx-get"] = self.action_url
            elif self.autosave and self.form_id:
                attrs["action"] = self.action_url
                attrs["method"] = "post"
                submit_button_attrs["type"] = "button"
                submit_button_attrs["onclick"] = (
                    "var f=this.closest('form');f.submit();"
                )
            else:
                attrs["action"] = self.action_url
                attrs["method"] = "post"
                submit_button_attrs["type"] = "button"
                submit_button_attrs["onclick"] = "var f=this.closest('form');f.submit()"

        # Handle Auto-save logic
        autosave_indicator = ""
        if self.autosave and self.form_id:
            pulse_url = f"/api/forms/draft/{self.form_id}"

            # Additional attributes for autosave
            attrs["hx-target"] = self.hx_target
            attrs["hx-swap"] = self.hx_swap
            attrs["hx-trigger"] = "change delay:2s, autosave-pulse from:window"

            # The pulse should target a specific indicator to show "Saving..."
            indicator_id = f"autosave-status-{self.form_id}"
            attrs["hx-indicator"] = f"#{indicator_id}"

            # If autosave is enabled, we use a different endpoint for the FORM's automatic pulses
            attrs["hx-post"] = pulse_url

            autosave_indicator = el(
                "div",
                el("div", "", id=indicator_id, class_="htmx-indicator"),
                el("span", "", id=f"{indicator_id}-result"),
                class_="flex items-center gap-2",
            )

        footer = (
            el(
                "div",
                el(
                    "div",
                    Button(
                        self.submit_label,
                        type=submit_button_attrs.get("type", "submit"),
                        class_="w-full sm:w-auto",
                        onclick=submit_button_attrs.get("onclick"),
                    ),
                    autosave_indicator,
                    class_="flex items-center justify-between w-full",
                ),
                class_="pt-4 border-t border-border mt-6",
            )
            if self.submit_label and not getattr(self, "suppress_submit", False)
            else ""
        )

        # Inject CSRF token if available in request context
        csrf_input = ""
        try:
            request = getattr(self, "_request", None)
            if (
                request
                and hasattr(request, "state")
                and hasattr(request.state, "csrf_token")
            ):
                csrf_input = el(
                    "input",
                    type="hidden",
                    name="csrf_token",
                    value=request.state.csrf_token,
                )
        except AttributeError as e:
            from lexigram.logging import get_logger

            logger = get_logger(__name__)
            logger.debug(
                "Failed to retrieve request/CSRF token from context: %s",
                e,
                exc_info=True,
            )

        return el("form", csrf_input, *self.children, footer, **attrs)
