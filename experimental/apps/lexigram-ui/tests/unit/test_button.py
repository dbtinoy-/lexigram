"""Tests for Button and SubmitButton atoms."""

from __future__ import annotations

from lexigram.ui.atoms.button import Button, SubmitButton


class TestButton:
    def test_default_variant(self):
        html = str(Button("Save"))
        assert "bg-primary" in html
        assert "text-primary-foreground" in html
        assert "h-10" in html

    def test_secondary_variant(self):
        html = str(Button("Cancel", variant="secondary"))
        assert "bg-secondary" in html

    def test_destructive_variant(self):
        html = str(Button("Delete", variant="destructive"))
        assert "bg-destructive" in html

    def test_outline_variant(self):
        html = str(Button("Edit", variant="outline"))
        assert "border-input" in html
        assert "bg-background" in html

    def test_ghost_variant(self):
        html = str(Button("Menu", variant="ghost"))
        assert "hover:bg-accent" in html

    def test_link_variant(self):
        html = str(Button("Learn more", variant="link"))
        assert "text-primary" in html
        assert "hover:underline" in html

    def test_size_xs(self):
        html = str(Button("X Small", size="xs"))
        assert "h-7" in html

    def test_size_icon(self):
        html = str(Button("X", size="icon"))
        assert "h-10 w-10" in html

    def test_size_sm(self):
        html = str(Button("Small", size="sm"))
        assert "h-9" in html

    def test_size_lg(self):
        html = str(Button("Large", size="lg"))
        assert "h-11" in html

    def test_size_xl(self):
        html = str(Button("XL", size="xl"))
        assert "h-12" in html

    def test_disabled(self):
        html = str(Button("Disabled", disabled=True))
        assert "disabled:pointer-events-none" in html

    def test_disabled_opacity(self):
        html = str(Button("Disabled", disabled=True))
        assert "disabled:opacity-50" in html

    def test_focus_ring(self):
        html = str(Button("Focus"))
        assert "focus-visible:ring-ring" in html

    def test_current_shadcn_classes(self):
        html = str(Button("Save"))
        assert "gap-2" in html
        assert "ring-offset-background" in html
        assert "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2" in html
        assert "disabled:pointer-events-none disabled:opacity-50" in html
        assert "[&amp;_svg]:pointer-events-none [&amp;_svg]:size-4 [&amp;_svg]:shrink-0" in html

    def test_icon_size_is_h10_w10(self):
        html = str(Button("X", size="icon"))
        assert "h-10 w-10" in html

    def test_default_size_is_h10(self):
        html = str(Button("Save"))
        assert "h-10 px-4 py-2" in html

    def test_transition(self):
        html = str(Button("Trans"))
        assert "transition-colors" in html

    def test_type_button_by_default(self):
        html = str(Button("Click"))
        assert 'type="button"' in html

    def test_custom_class_merges(self):
        html = str(Button("Custom", class_="my-custom-class"))
        assert "my-custom-class" in html
        assert "bg-primary" in html

    def test_button_renders_button_tag(self):
        html = str(Button("Go"))
        assert "<button" in html

    def test_button_empty_label(self):
        html = str(Button())
        assert "<button" in html


class TestSubmitButton:
    def test_submit_button_renders(self):
        html = str(SubmitButton("Create"))
        assert 'type="submit"' in html
        assert "Create" in html

    def test_submit_button_default_label(self):
        html = str(SubmitButton())
        assert "Submit" in html

    def test_submit_button_alpine_data(self):
        html = str(SubmitButton())
        assert "x-data" in html
        assert "loading" in html

    def test_submit_button_disabled(self):
        html = str(SubmitButton(disabled=True))
        assert "disabled" in html

    def test_submit_button_variant_classes(self):
        html = str(SubmitButton("Delete", variant="destructive"))
        assert "bg-destructive" in html
