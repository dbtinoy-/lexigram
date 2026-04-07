"""
FileUpload component for file uploads with validation and preview.

Supports single file uploads with type/size validation and image previews.
"""

from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el


class FileUpload(Component):
    """
    File upload component with validation and preview.

    Example:
        FileUpload(
            name="avatar",
            label="Profile Picture",
            accept="image/*",
            max_size=5 * 1024 * 1024,  # 5MB
            preview=True
        )
    """

    def __init__(
        self,
        name: str,
        label: str | None = None,
        accept: str | None = None,  # e.g., "image/*", ".pdf,.doc"
        max_size: int | None = None,  # in bytes
        preview: bool = False,  # Show image preview
        required: bool = False,
        disabled: bool = False,
        error: str | None = None,
        help_text: str | None = None,
        **props,
    ):
        """
        Initialize file upload component.

        Args:
            name: Input name attribute
            label: Label text
            accept: Accepted file types
            max_size: Maximum file size in bytes
            preview: Show image preview
            required: Whether field is required
            disabled: Whether field is disabled
            error: Error message
            help_text: Help text
            **props: Additional properties
        """
        super().__init__(
            name=name,
            label=label,
            accept=accept,
            max_size=max_size,
            preview=preview,
            required=required,
            disabled=disabled,
            error=error,
            help_text=help_text,
            **props,
        )
        self.name = name
        self.label = label or name.replace("_", " ").title()
        self.accept = accept
        self.max_size = max_size
        self.preview = preview
        self.required = required
        self.disabled = disabled
        self.error = error
        self.help_text = help_text

    def render(self) -> Any:
        """Render the file upload component."""
        # File input classes
        input_classes = f"block w-full text-sm text-foreground border border-input rounded-lg cursor-pointer bg-card focus:outline-none focus:ring-2 focus:ring-ring {'border-destructive' if self.error else ''} disabled:opacity-50 disabled:cursor-not-allowed"

        # Build file input
        input_attrs = {
            "type": "file",
            "name": self.name,
            "id": self.name,
            "class_": input_classes,
            "disabled": self.disabled,
            "required": self.required,
        }

        if self.accept:
            input_attrs["accept"] = self.accept

        # Add data attributes for validation
        if self.max_size:
            input_attrs["data_max_size"] = str(self.max_size)

        # Add aria attributes for accessibility
        if self.help_text or self.error:
            describedby_ids = []
            if self.help_text:
                describedby_ids.append(f"{self.name}-help")
            if self.error:
                describedby_ids.append(f"{self.name}-error")
            input_attrs["aria_describedby"] = " ".join(describedby_ids)
        if self.error:
            input_attrs["aria_invalid"] = "true"

        # Pass through HTMX and other attributes
        input_attrs.update(
            {
                key: value
                for key, value in self.props.items()
                if key
                not in [
                    "name",
                    "label",
                    "accept",
                    "max_size",
                    "preview",
                    "required",
                    "disabled",
                    "error",
                    "help_text",
                ]
            }
        )

        file_input = el("input", **input_attrs)

        # Help text
        help_el = ""
        if self.help_text:
            help_el = el(
                "p",
                self.help_text,
                id=f"{self.name}-help",
                class_="mt-1 text-sm text-muted-foreground",
            )

        # Error message
        error_el = ""
        if self.error:
            error_el = el(
                "p",
                self.error,
                id=f"{self.name}-error",
                class_="mt-2 text-sm text-destructive",
            )

        # Preview container (hidden by default, shown via JS)
        preview_el = ""
        if self.preview:
            preview_el = el(
                "div",
                el("img", src="", alt="Preview", class_="max-w-xs rounded-lg"),
                id=f"{self.name}_preview",
                class_="mt-4 hidden",
            )

        # File info display
        file_info_el = el(
            "div",
            id=f"{self.name}_info",
            class_="mt-2 text-sm text-muted-foreground hidden",
        )

        return el(
            "div",
            el(
                "label",
                self.label,
                for_=self.name,
                class_="block text-sm font-medium text-foreground mb-2",
            ),
            file_input,
            help_el,
            file_info_el,
            preview_el,
            error_el,
            class_="mb-4",
        )
