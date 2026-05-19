"""Dynamic Form Component.

Renders a FormSchema into HTML using htpy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import htpy as h

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
        from lexigram.admin.forms import FieldType as FormFieldType

        # We wrap the content in a list of htpy nodes
        form_content = []

        # Render each field
        from lexigram.admin.ui.organisms.form_registry import _form_field_registry

        for field in self.schema.fields:
            # RBAC: Skip invisible fields
            if not getattr(field, "visible", True):
                continue

            # RBAC: Handle masking
            current_value = field.default
            if getattr(field, "masked", False) and current_value:
                current_value = "********"

            renderer = _form_field_registry.get_renderer(field.type)
            form_content.append(renderer.render(field, current_value))  # type: ignore[arg-type]

            if field.help_text and field.type != FormFieldType.CHECKBOX:
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
