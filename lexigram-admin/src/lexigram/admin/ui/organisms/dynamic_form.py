"""Dynamic Form Component.

Renders a FormSchema into HTML using htpy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import htpy as h

from lexigram.admin.schema import BooleanField
from lexigram.ui import Button, Component, Form

if TYPE_CHECKING:
    from lexigram.admin.forms import FormSchema


class DynamicForm(Component):
    """Renders a form based on a schema."""

    def __init__(
        self,
        schema: FormSchema,
        action: str,
        method: str = "POST",
        submit_text: str = "Submit",
        hx_post: str | None = None,
        hx_target: str | None = None,
        hx_swap: str = "outerHTML",
    ):
        self.schema = schema
        self.action = action
        self.method = method
        self.submit_text = submit_text
        self.hx_post = hx_post or action if hx_post else None
        self.hx_target = hx_target
        self.hx_swap = hx_swap

    def render(self) -> Any:
        # We wrap the content in a list of htpy nodes
        form_content: list[Any] = []

        # Render each field via its schema render_form
        for field in self.schema.fields:
            # Skip fields hidden from forms
            if not field.visible_in_form:
                continue

            form_content.append(field.render_form(field.get_default()))

            if field.help_text and not isinstance(field, BooleanField):
                form_content.append(
                    h.p(
                        class_="mt-1 text-xs text-muted-foreground mb-4 -mt-4",
                    )[field.help_text],
                )

        # Submit Button
        form_content.append(
            h.div(class_="flex justify-end pt-4")[
                Button(self.submit_text, type="submit", color="primary")
            ],
        )

        # Determine attributes for the generic Form wrapper
        # The Wrapper handles CSRF injection automatically via the logic we added earlier
        form_attrs = {
            "action": self.action,
            "method": self.method,
            "class_": "space-y-4 bg-card p-6 rounded-lg shadow",
        }
        if self.hx_post:
            form_attrs["hx_post"] = self.hx_post
        if self.hx_target:
            form_attrs["hx_target"] = self.hx_target
        if self.hx_swap:
            form_attrs["hx_swap"] = self.hx_swap

        return Form(
            children=[
                h.h2(class_="text-lg font-medium text-foreground mb-4")[
                    self.schema.title
                ],
                form_content,
            ],
            **form_attrs,  # type: ignore[arg-type]
        )
