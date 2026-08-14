"""Tests for layout HeadRenderer."""
from __future__ import annotations

from lexigram.ui.config import HeadConfig
from lexigram.ui.layouts.head import HeadRenderer


class TestHeadRenderer:
    def test_render_basic(self) -> None:
        config = HeadConfig()
        renderer = HeadRenderer(config)
        result = renderer.render()
        # Default tailwind + htmx
        assert "tailwind" in result
        assert "htmx" in result

    def test_render_with_font(self) -> None:
        config = HeadConfig(font_url="https://fonts.googleapis.com/css2?family=Inter")
        renderer = HeadRenderer(config)
        result = renderer.render()
        assert "fonts.googleapis.com" in result
        assert "Inter" in result

    def test_render_custom_css_files(self) -> None:
        config = HeadConfig(css_files=["/custom.css", "/extra.css"])
        renderer = HeadRenderer(config)
        result = renderer.render()
        assert "/custom.css" in result
        assert "/extra.css" in result

    def test_render_inline_css(self) -> None:
        config = HeadConfig(inline_css="body { margin: 0; }")
        renderer = HeadRenderer(config)
        result = renderer.render()
        assert "body { margin: 0; }" in result

    def test_render_extra_css_param(self) -> None:
        config = HeadConfig()
        renderer = HeadRenderer(config)
        result = renderer.render(extra_css=".extra { }")
        assert ".extra { }" in result

    def test_render_inline_and_extra_css(self) -> None:
        config = HeadConfig(inline_css="body { }")
        renderer = HeadRenderer(config)
        result = renderer.render(extra_css=".extra { }")
        assert "body" in result
        assert ".extra" in result

    def test_render_hyperscript_enabled(self) -> None:
        config = HeadConfig(include_hyperscript=True)
        renderer = HeadRenderer(config)
        result = renderer.render()
        assert "hyperscript" in result

    def test_render_hyperscript_disabled(self) -> None:
        config = HeadConfig(include_hyperscript=False)
        renderer = HeadRenderer(config)
        result = renderer.render()
        assert "hyperscript" not in result

    def test_css_framework_pico(self) -> None:
        config = HeadConfig(css_framework="pico")
        renderer = HeadRenderer(config)
        result = renderer.render()
        assert "picocss" in result
        assert 'rel="stylesheet"' in result

    def test_css_framework_custom_url(self) -> None:
        config = HeadConfig(css_framework_url="https://cdn.example.com/custom.css")
        renderer = HeadRenderer(config)
        result = renderer.render()
        assert "custom.css" in result

    def test_css_framework_unknown_fallback(self) -> None:
        config = HeadConfig(css_framework="nonexistent")
        renderer = HeadRenderer(config)
        result = renderer.render()
        # Should not crash, omit CSS framework
        pass

    def test_icon_library_non_lucide(self) -> None:
        config = HeadConfig(icon_library="heroicons")
        renderer = HeadRenderer(config)
        result = renderer.render()
        assert "lucide" not in result

    def test_icon_library_lucide_creates_icons(self) -> None:
        config = HeadConfig(icon_library="lucide")
        renderer = HeadRenderer(config)
        result = renderer.render()
        assert "lucide.createIcons" in result

    def test_icon_library_lucide_no_url(self) -> None:
        config = HeadConfig(icon_library="lucide", icon_library_url="")
        renderer = HeadRenderer(config)
        result = renderer.render()
        assert "lucide" not in result
