"""Tests for additional molecule components."""
from __future__ import annotations

import pytest

from lexigram.ui.molecules.form_actions import FormActions
from lexigram.ui.molecules.input_group import InputGroup
from lexigram.ui.molecules.loading_overlay import LoadingOverlay
from lexigram.ui.molecules.section import Section
from lexigram.ui.molecules.simple_alert import SimpleAlert
from lexigram.ui.styles.tokens import get_alert_classes


class TestSimpleAlert:
    def test_render_info(self) -> None:
        a = SimpleAlert("Something happened")
        result = str(a)
        assert "Something happened" in result
        assert get_alert_classes("info") in result

    def test_render_success(self) -> None:
        a = SimpleAlert("Done!", alert_type="success")
        result = str(a)
        assert get_alert_classes("success") in result

    def test_render_warning(self) -> None:
        a = SimpleAlert("Watch out", alert_type="warning")
        result = str(a)
        assert get_alert_classes("warning") in result

    def test_render_error(self) -> None:
        a = SimpleAlert("Failed", alert_type="error")
        result = str(a)
        assert get_alert_classes("error") in result

    def test_render_with_title(self) -> None:
        a = SimpleAlert("Body", alert_type="info", title="Title")
        result = str(a)
        assert "Title" in result
        assert "Body" in result

    def test_render_without_title(self) -> None:
        a = SimpleAlert("Just body")
        result = str(a)
        assert "Just body" in result


class TestFormActions:
    def test_render_with_defaults(self) -> None:
        fa = FormActions()
        result = str(fa)
        assert "Save" in result
        assert "Cancel" in result

    def test_render_custom_text(self) -> None:
        fa = FormActions(primary_text="Update", secondary_text="Back")
        result = str(fa)
        assert "Update" in result
        assert "Back" in result

    def test_render_no_secondary(self) -> None:
        fa = FormActions(secondary_text=None)
        result = str(fa)
        assert "Save" in result
        assert "Cancel" not in result

    def test_render_with_cancel_url(self) -> None:
        fa = FormActions(cancel_url="/admin/users")
        result = str(fa)
        assert "/admin/users" in result

    def test_render_primary_disabled(self) -> None:
        fa = FormActions(primary_disabled=True)
        result = str(fa)
        assert "disabled" in result

    def test_render_alignment_left(self) -> None:
        fa = FormActions(align="left")
        result = str(fa)
        assert "justify-start" in result

    def test_render_alignment_center(self) -> None:
        fa = FormActions(align="center")
        result = str(fa)
        assert "justify-center" in result

    def test_render_alignment_right_default(self) -> None:
        fa = FormActions(align="right")
        result = str(fa)
        assert "justify-end" in result


class TestInputGroup:
    def test_render_basic(self) -> None:
        ig = InputGroup(label="Email", name="email")
        result = str(ig)
        assert "Email" in result
        assert "email" in result

    def test_render_with_prefix(self) -> None:
        ig = InputGroup(label="Price", name="price", prefix="$")
        result = str(ig)
        assert "$" in result

    def test_render_with_suffix(self) -> None:
        ig = InputGroup(label="Size", name="size", suffix="MB")
        result = str(ig)
        assert "MB" in result

    def test_render_with_placeholder(self) -> None:
        ig = InputGroup(label="Name", name="name", placeholder="Enter name")
        result = str(ig)
        assert "Enter name" in result

    def test_render_with_value(self) -> None:
        ig = InputGroup(label="Name", name="name", value="John")
        result = str(ig)
        assert 'value="John"' in result

    def test_render_with_error(self) -> None:
        ig = InputGroup(label="Email", name="email", error="Required")
        result = str(ig)
        assert "Required" in result
        assert "destructive" in result


class TestLoadingOverlay:
    def test_render_default(self) -> None:
        lo = LoadingOverlay()
        result = str(lo)
        assert "Loading..." in result
        assert "fixed" in result

    def test_render_custom_message(self) -> None:
        lo = LoadingOverlay(message="Processing...")
        result = str(lo)
        assert "Processing..." in result

    def test_render_not_fullscreen(self) -> None:
        lo = LoadingOverlay(fullscreen=False)
        result = str(lo)
        assert "absolute" in result

    def test_render_empty_message(self) -> None:
        lo = LoadingOverlay(message="")
        result = str(lo)
        assert "mt-4" not in result or "Spinner" in result


class TestSection:
    def test_render_basic(self) -> None:
        s = Section(title="Details")
        result = str(s)
        assert "Details" in result

    def test_render_with_description(self) -> None:
        s = Section(title="Details", description="Enter your details")
        result = str(s)
        assert "Enter your details" in result

    def test_render_with_icon(self) -> None:
        s = Section(title="Details", icon="📋")
        result = str(s)
        assert "📋" in result

    def test_render_collapsible_default_open(self) -> None:
        s = Section(title="Details", collapsible=True)
        result = str(s)
        assert "▼" in result  # arrow down

    def test_render_collapsible_collapsed(self) -> None:
        s = Section(title="Details", collapsible=True, collapsed=True)
        result = str(s)
        assert "collapsed: true" in result

    def test_render_with_children(self) -> None:
        from lexigram.ui.core.base import el

        s = Section(title="Details")
        s.children = [el("p", "Content")]
        result = str(s)
        assert "Content" in result
