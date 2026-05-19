"""
Standard Action implementations for common operations.

These classes provide pre-configured defaults for Edit, View, Delete,
and Create actions, while allowing full customization via the fluent API.
"""

from __future__ import annotations

from typing import Self

from lexigram.ui import Zones
from lexigram.ui.actions.base import Action, BulkAction


class EditAction(Action):
    """Standard Edit action implementation."""

    def __init__(self, name: str = "edit", label: str = "Edit"):
        super().__init__(name, label)
        self._icon = "pencil"
        self._color = "primary"
        self._hx_target = "body"
        self._hx_swap = "beforeend"
        self.slide_over()

    def using_form_modal(self) -> Self:
        """Configure to open in a modal."""
        self._open_modal = True
        return self


class ViewAction(Action):
    """Standard View action implementation."""

    def __init__(self, name: str = "view", label: str = "View"):
        super().__init__(name, label)
        self._icon = "eye"
        self._color = "gray"


class DeleteAction(Action):
    """Standard Delete action implementation."""

    def __init__(self, name: str = "delete", label: str = "Delete"):
        super().__init__(name, label)
        self._icon = "trash"
        self._color = "danger"
        self._requires_confirmation = True
        # Load delete confirmation into the slide-over instead of browser confirm
        self._hx_target = Zones.SLIDE_OVER.selector
        self._hx_swap = Zones.SLIDE_OVER.swap_mode.value
        self._hx_push_url = "false"


class CreateAction(Action):
    """Standard Create action implementation (Header Action)."""

    def __init__(self, name: str = "create", label: str = "Create"):
        super().__init__(name, label)
        self._icon = "plus"
        self._color = "primary"
        self._hx_target = Zones.SLIDE_OVER.selector
        self._hx_swap = Zones.SLIDE_OVER.swap_mode.value

    def using_form_modal(self) -> Self:
        """Configure to open in a modal."""
        self._open_modal = True
        return self


class ExportAction(Action):
    """Standard Export action implementation."""

    def __init__(self, name: str = "export", label: str = "Export"):
        super().__init__(name, label)
        self._icon = "download"
        self._color = "gray"


class DeleteBulkAction(BulkAction):
    """Standard Bulk Delete action."""

    def __init__(self, name: str = "delete", label: str = "Delete Selected"):
        super().__init__(name, label)
        self._icon = "trash"
        self._color = "danger"
        self._requires_confirmation = True
        self._confirmation_title = "Delete Selected Records"
        self._confirmation_message = "Are you sure you would like to delete the selected records? This action cannot be undone."
        from lexigram.ui import Zones

        self._hx_target = Zones.SLIDE_OVER.selector
        self._deselect_after = True


class ExportBulkAction(BulkAction):
    """Standard Bulk Export action."""

    def __init__(self, name: str = "export", label: str = "Export Selected"):
        super().__init__(name, label)
        self._icon = "download"
        self._color = "gray"
        self._deselect_after = True
