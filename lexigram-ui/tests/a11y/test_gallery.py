"""Verify the gallery produces valid pages for every component."""

from __future__ import annotations


def test_gallery_has_all_components(gallery: dict[str, str]) -> None:
    """Every expected component must be in the gallery."""
    expected = {
        "Alert", "Badge", "Button", "Card", "Checkbox", "Divider",
        "Dropdown", "Fieldset", "Form", "Icon", "InlineToast", "Label",
        "Layout", "Link", "Modal", "NumberInput", "Pagination",
        "PasswordInput", "ProgressBar", "Radio", "Select", "Skeleton",
        "SlideOver", "Spinner", "Switch", "Tabs", "TextArea", "TextInput",
        "Tooltip",
    }
    assert expected.issubset(gallery.keys())


def test_gallery_pages_are_html(gallery: dict[str, str]) -> None:
    """Every page must be a full document with design tokens."""
    for name, html in gallery.items():
        assert html.startswith("<!DOCTYPE html>"), name
        assert "--background" in html, name