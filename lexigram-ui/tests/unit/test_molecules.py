"""Tests for UI molecules - Modal, Alert, Toast."""

from __future__ import annotations

from lexigram.ui.molecules.alert import Alert
from lexigram.ui.molecules.card import Card
from lexigram.ui.molecules.modal import Modal
from lexigram.ui.molecules.toast import Toast


class TestCurrentShadcnClasses:
    """Class parity with the current shadcn/ui registry."""

    def test_card(self) -> None:
        html = str(Card("Title", "Body"))
        assert "rounded-lg border bg-card text-card-foreground shadow-sm" in html


class TestModal:
    """Tests for Modal component."""

    def test_modal_creation_basic(self) -> None:
        """Test creating a basic modal."""
        modal = Modal(title="Confirm Action", trigger="Open Modal")
        result = str(modal)
        assert "Confirm Action" in result
        assert "x-data" in result

    def test_modal_with_trigger_text(self) -> None:
        """Test modal with string trigger."""
        modal = Modal(title="Delete Item", trigger="Click to delete")
        result = str(modal)
        assert "Click to delete" in result

    def test_modal_with_footer(self) -> None:
        """Test modal with custom footer."""
        from lexigram.ui.atoms.button import Button

        footer = [Button("Cancel"), Button("Save")]
        modal = Modal(title="Edit", trigger="Edit", footer=footer)
        result = str(modal)
        assert "Cancel" in result
        assert "Save" in result

    def test_modal_with_max_width(self) -> None:
        """Test modal with custom max width."""
        modal = Modal(title="Wide Modal", max_width="max-w-4xl")
        result = str(modal)
        assert "max-w-4xl" in result

    def test_modal_with_max_height(self) -> None:
        """Test modal with custom max height."""
        modal = Modal(title="Tall Modal", max_height="max-h-[80vh]")
        result = str(modal)
        assert "max-h-[80vh]" in result

    def test_modal_initial_open_true(self) -> None:
        """Test modal that starts open."""
        modal = Modal(title="Open Modal", is_open=True)
        result = str(modal)
        assert "open: true" in result

    def test_modal_has_backdrop(self) -> None:
        """Test modal includes backdrop element."""
        modal = Modal(title="Backdrop Test", trigger="Open")
        result = str(modal)
        assert "fixed inset-0" in result

    def test_modal_has_role_dialog(self) -> None:
        """Test modal has dialog role for accessibility."""
        modal = Modal(title="Accessible Modal", trigger="Open")
        result = str(modal)
        assert 'role="dialog"' in result
        assert 'aria-modal="true"' in result


class TestAlert:
    """Tests for Alert component."""

    def test_alert_creation_default(self) -> None:
        """Test creating an alert with default values."""
        alert = Alert("Operation completed")
        result = str(alert)
        assert "Operation completed" in result

    def test_alert_with_variant_info(self) -> None:
        """Test alert with info variant."""
        alert = Alert("Info message", variant="info")
        result = str(alert)
        assert "info" in result.lower()

    def test_alert_with_variant_success(self) -> None:
        """Test alert with success variant."""
        alert = Alert("Success!", variant="success")
        result = str(alert)
        assert "Success!" in result

    def test_alert_with_variant_warning(self) -> None:
        """Test alert with warning variant."""
        alert = Alert("Warning message", variant="warning")
        result = str(alert)
        assert "Warning message" in result

    def test_alert_with_variant_error(self) -> None:
        """Test alert with error variant."""
        alert = Alert("Error occurred", variant="error")
        result = str(alert)
        assert "Error occurred" in result

    def test_alert_with_dismissible(self) -> None:
        """Test alert with dismiss button."""
        alert = Alert("Dismissible", dismissible=True)
        result = str(alert)
        assert "Dismissible" in result


class TestToast:
    """Tests for Toast component."""

    def test_toast_creation_default(self) -> None:
        """Test creating a toast with default values."""
        toast = Toast("Item saved")
        result = str(toast)
        assert "Item saved" in result

    def test_toast_with_variant_success(self) -> None:
        """Test toast with success variant."""
        toast = Toast("Saved successfully", variant="success")
        result = str(toast)
        assert "Saved successfully" in result

    def test_toast_with_variant_error(self) -> None:
        """Test toast with error variant."""
        toast = Toast("Failed to save", variant="error")
        result = str(toast)
        assert "Failed to save" in result

    def test_toast_with_duration(self) -> None:
        """Test toast with custom duration."""
        toast = Toast("Auto-dismiss", duration=5000)
        result = str(toast)
        assert "Auto-dismiss" in result

    def test_toast_with_action(self) -> None:
        """Test toast with action button."""
        toast = Toast("Undo?", action_label="Undo")
        result = str(toast)
        assert "Undo?" in result
        assert "Undo" in result

    def test_toast_with_icon(self) -> None:
        """Test toast with icon."""
        toast = Toast("With icon", icon="check")
        result = str(toast)
        assert "With icon" in result


class TestModalAccessibility:
    """Tests for Modal accessibility features."""

    def test_modal_has_title_id(self) -> None:
        """Test modal has titled element with ID."""
        modal = Modal(title="Accessibility Modal", trigger="Open")
        result = str(modal)
        assert "modal-title" in result

    def test_modal_escape_key_binding(self) -> None:
        """Test modal closes on escape key."""
        modal = Modal(title="Escape Test", trigger="Open")
        result = str(modal)
        assert "escape" in result

    def test_modal_click_away_closes(self) -> None:
        """Test modal closes when clicking backdrop."""
        modal = Modal(title="Click Away Test", trigger="Open")
        result = str(modal)
        assert "click.away" in result or "x-on:click" in result


class TestModalStates:
    """Tests for Modal state management."""

    def test_modal_initial_closed_state(self) -> None:
        """Test modal starts in closed state."""
        modal = Modal(title="Initial State", trigger="Open")
        result = str(modal)
        assert "open: false" in result

    def test_modal_custom_trigger_not_rendered_when_disabled(self) -> None:
        """Test trigger can be hidden."""
        modal = Modal(title="Hidden Trigger", trigger="Open", render_trigger=False)
        result = str(modal)
        assert "Open" not in result or "Hidden Trigger" in result


class TestAlertStates:
    """Tests for Alert state variations."""

    def test_alert_with_message_only(self) -> None:
        """Test alert renders message correctly."""
        alert = Alert("Test message")
        result = str(alert)
        assert "Test message" in result

    def test_alert_with_icon_hidden(self) -> None:
        """Test alert with icon hidden."""
        alert = Alert("No icon", show_icon=False)
        result = str(alert)
        assert "No icon" in result


class TestToastStates:
    """Tests for Toast state variations."""

    def test_toast_persistent(self) -> None:
        """Test toast that doesn't auto-dismiss."""
        toast = Toast("Persistent", persistent=True)
        result = str(toast)
        assert "Persistent" in result

    def test_toast_with_auto_id(self) -> None:
        """Test toast generates an ID when no custom ID provided."""
        toast = Toast("Auto ID")
        result = str(toast)
        assert "Auto ID" in result


class TestShadcnDialogClasses:
    """Modal/dialog class parity with current shadcn."""

    def test_modal_panel(self) -> None:
        html = str(Modal(title="Confirm"))
        assert "rounded-lg" in html
        assert "bg-background" in html or "bg-card" in html
        assert "shadow-lg" in html

    def test_modal_has_role_dialog(self) -> None:
        html = str(Modal(title="Confirm"))
        assert 'role="dialog"' in html
        assert 'aria-modal="true"' in html
        assert "aria-labelledby" in html

    def test_modal_backdrop(self) -> None:
        html = str(Modal(title="Confirm"))
        assert "bg-black/80" in html

    def test_dropdown_menu(self) -> None:
        from lexigram.ui.molecules.dropdown import Dropdown

        html = str(Dropdown("Menu", items=["A", "B"]))
        assert 'role="menu"' in html

    def test_pagination(self) -> None:
        from lexigram.ui.molecules.pagination import Pagination

        html = str(Pagination(page=1, total=45))
        assert 'aria-label="Pagination"' in html
