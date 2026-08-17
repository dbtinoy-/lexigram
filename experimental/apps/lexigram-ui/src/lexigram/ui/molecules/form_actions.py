"""
FormActions component for form buttons.

Provides primary/secondary action buttons with loading states.
"""

from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el


class FormActions(Component):
    """
    Form actions component for submit/cancel buttons.

    Example:
        FormActions(
            primary_text="Save Changes",
            secondary_text="Cancel",
            primary_loading=False,
            cancel_url="/admin/users"
        )
    """

    def __init__(
        self,
        primary_text: str = "Save",
        secondary_text: str | None = "Cancel",
        primary_loading: bool = False,
        primary_disabled: bool = False,
        cancel_url: str | None = None,
        align: str = "right",  # left, center, right
        **props: Any,
    ) -> None:
        """
        Initialize form actions.

        Args:
            primary_text: Primary button text
            secondary_text: Secondary button text (None to hide)
            primary_loading: Show loading state on primary button
            primary_disabled: Disable primary button
            cancel_url: URL for cancel button (if not provided, uses history.back())
            align: Button alignment (left, center, right)
            **props: Additional properties
        """
        super().__init__(
            primary_text=primary_text,
            secondary_text=secondary_text,
            primary_loading=primary_loading,
            primary_disabled=primary_disabled,
            cancel_url=cancel_url,
            align=align,
            **props,
        )
        self.primary_text = primary_text
        self.secondary_text = secondary_text
        self.primary_loading = primary_loading
        self.primary_disabled = primary_disabled
        self.cancel_url = cancel_url
        self.align = align

    def render(self) -> Any:
        """Render the form actions."""
        from lexigram.ui.atoms.button import SubmitButton

        # Primary button (submit)
        primary_btn = SubmitButton(
            self.primary_text,
            disabled=self.primary_disabled or self.primary_loading,
            class_="px-6 py-2",
        )

        # Secondary button (cancel)
        secondary_btn = ""
        if self.secondary_text:
            if self.cancel_url:
                # Link to cancel URL
                secondary_btn = el(
                    "a",
                    self.secondary_text,
                    href=self.cancel_url,
                    class_="inline-flex items-center px-6 py-2 border border-border "
                    "rounded-md shadow-sm text-sm font-medium text-foreground "
                    "bg-card hover:bg-accent "
                    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-ring",
                )
            else:
                # JavaScript back button -> use standardized ActionButton for consistent styling
                from lexigram.ui.molecules.action_button import (
                    ActionButton,
                )

                secondary_btn = ActionButton(
                    label=self.secondary_text,
                    color="secondary",
                    size="md",
                    hx_on_click="history.back()",
                    class_="inline-flex items-center px-6 py-2 border border-border rounded-md shadow-sm text-sm font-medium text-foreground bg-card hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-ring",
                ).render()

        # Alignment classes
        align_classes = {
            "left": "justify-start",
            "center": "justify-center",
            "right": "justify-end",
        }

        return el(
            "div",
            el(
                "div",
                secondary_btn,
                primary_btn.render(),
                class_=f"flex gap-3 {align_classes.get(self.align, 'justify-end')}",
            ),
            class_="mt-6 pt-6 border-t border-border",
        )
