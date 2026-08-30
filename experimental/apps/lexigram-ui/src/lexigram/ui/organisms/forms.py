from __future__ import annotations

from typing import Any

from lexigram.ui.atoms.button import SubmitButton
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
        hx_indicator: str | None = None,
        htmx_enabled: bool = True,
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
            hx_indicator=hx_indicator,
            htmx_enabled=htmx_enabled,
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
        self.hx_indicator = hx_indicator
        self.htmx_enabled = htmx_enabled

    def render(self) -> Any:
        attrs = {
            "method": self.method,
            "class": "space-y-6",
        }
        if self.form_id:
            attrs["id"] = self.form_id

        submit_button_attrs: dict[str, str] = {}
        if self.action_url:
            if self.method.lower() == "get":
                attrs["action"] = self.action_url
                if self.htmx_enabled:
                    attrs["hx-get"] = self.action_url
                    attrs["hx-target"] = self.hx_target
                    attrs["hx-swap"] = self.hx_swap
            elif self.autosave and self.form_id:
                # Autosave mode: the form posts to the draft endpoint on a
                # debounced change trigger; the submit button stays native so
                # the final save uses a standard POST.
                attrs["action"] = self.action_url
                attrs["method"] = "post"
            else:
                # HTMX-enhanced POST: the form is intercepted by htmx when
                # available; without JavaScript the native POST still works
                # (progressive enhancement). No onclick JS required.
                attrs["action"] = self.action_url
                attrs["method"] = "post"
                if self.htmx_enabled:
                    attrs["hx-post"] = self.action_url
                    attrs["hx-target"] = self.hx_target
                    attrs["hx-swap"] = self.hx_swap
                    if self.hx_indicator:
                        attrs["hx-indicator"] = self.hx_indicator

        # Handle Auto-save logic
        autosave_indicator = ""
        if self.autosave and self.form_id and self.htmx_enabled:
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
                    SubmitButton(
                        self.submit_label,
                        class_="w-full sm:w-auto",
                        type=submit_button_attrs.get("type", "submit"),
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
