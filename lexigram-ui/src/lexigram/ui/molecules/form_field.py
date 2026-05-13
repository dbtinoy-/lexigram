"""FieldSchema molecule component - wrapper for form inputs with label and error."""

from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el


class FormField(Component):
    """Form field wrapper with label, input, error message, and help text."""

    """Form field wrapper with label, input, error message, and help text."""

    def __init__(
        self,
        input_component: Component,
        label: str | None = None,
        error: str | None = None,
        help_text: str | None = None,
        hint: str | None = None,
        required: bool = False,
        hidden: bool = False,
        visible_condition: str | None = None,
        **props,
    ) -> None:
        super().__init__(
            input_component=input_component,
            label=label,
            error=error,
            help_text=help_text,
            hint=hint,
            required=required,
            hidden=hidden,
            visible_condition=visible_condition,
            **props,
        )
        self.input_component = input_component
        self.label = label
        self.error = error
        self.help_text = help_text
        self.hint = hint
        self.required = required
        self.hidden = hidden
        self.visible_condition = visible_condition

    def render(self) -> Any:
        # Build container attributes
        container_attrs: dict[str, Any] = {"class": "mb-6"}
        if self.error:
            error_id = f"{getattr(self.input_component, 'id', None) or getattr(self.input_component, 'name', None) or 'field'}-error"
            container_attrs["aria_describedby"] = error_id
            container_attrs["aria_invalid"] = "true"

        # Handle hidden state
        if self.hidden:
            container_attrs["style"] = "display: none"

        # Handle conditional visibility (Alpine.js)
        if self.visible_condition:
            container_attrs["x-show"] = self.visible_condition
            container_attrs["x-cloak"] = True

        elements = []

        # Header (Label + Hint)
        if self.label or self.hint:
            header_parts = []

            if self.label:
                label_text = self.label

                # Dynamic requirement asterisk
                required_if = self.props.get("required_if")
                if required_if:
                    header_parts.append(
                        el(
                            "label",
                            label_text,
                            el(
                                "span",
                                "*",
                                class_="text-destructive ml-1",
                                **{"x-show": required_if},
                            ),
                            for_=getattr(self.input_component, "id", None)
                            or getattr(self.input_component, "name", None),
                            class_="block text-sm font-medium text-foreground",
                        ),
                    )
                elif self.required:
                    header_parts.append(
                        el(
                            "label",
                            label_text
                            + el("span", "*", class_="text-destructive ml-1"),
                            for_=getattr(self.input_component, "id", None)
                            or getattr(self.input_component, "name", None),
                            class_="block text-sm font-medium text-foreground",
                        ),
                    )
                else:
                    header_parts.append(
                        el(
                            "label",
                            label_text,
                            for_=getattr(self.input_component, "id", None)
                            or getattr(self.input_component, "name", None),
                            class_="block text-sm font-medium text-foreground",
                        ),
                    )

            if self.hint:
                header_parts.append(
                    el(
                        "span",
                        self.hint,
                        class_="text-xs text-muted-foreground italic",
                        title=self.hint,
                    ),
                )

            elements.append(
                el(
                    "div",
                    *header_parts,
                    class_="flex items-center justify-between mb-2",
                ),
            )

        # Input
        try:
            rendered_input = self.input_component.render()
            elements.append(rendered_input)
        except (AttributeError, ValueError, TypeError):
            # Fail-safe: avoid bubbling render errors to outer HTML rendering
            from lexigram.logging import get_logger

            logger = get_logger(__name__)
            logger.exception(
                "Error rendering input component %s",
                getattr(self.input_component, "__class__", None),
            )
            elements.append(
                el(
                    "div",
                    "Error rendering field",
                    class_="mb-2 p-2 rounded bg-destructive/10 text-destructive",
                ),
            )

        # Error message
        if self.error:
            error_id = f"{getattr(self.input_component, 'id', None) or getattr(self.input_component, 'name', None) or 'field'}-error"
            elements.append(
                el(
                    "p",
                    self.error,
                    id=error_id,
                    class_="mt-2 text-sm text-destructive font-medium",
                ),
            )

        # Help text
        if self.help_text and not self.error:
            elements.append(
                el(
                    "p",
                    self.help_text,
                    class_="mt-2 text-sm text-muted-foreground",
                ),
            )

        return el("div", *elements, **container_attrs)


FieldSchema = FormField
