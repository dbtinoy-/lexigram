"""Tests for layout FooterRenderer."""
from __future__ import annotations

from lexigram.ui.config import FooterConfig
from lexigram.ui.layouts.footer import FooterLink, FooterRenderer


class TestFooterRenderer:
    def test_render_basic(self) -> None:
        config = FooterConfig()
        renderer = FooterRenderer(config)
        result = renderer.render()
        assert "<footer" in result
        assert "&copy;" in result

    def test_render_with_copyright_holder(self) -> None:
        config = FooterConfig(copyright_holder="Acme Inc")
        renderer = FooterRenderer(config)
        result = renderer.render()
        assert "Acme Inc" in result

    def test_render_with_copyright_year_range(self) -> None:
        config = FooterConfig(
            copyright_holder="Acme Inc", copyright_start_year=2020
        )
        renderer = FooterRenderer(config)
        result = renderer.render()
        assert "2020" in result or "Acme Inc" in result

    def test_render_version(self) -> None:
        config = FooterConfig(version="1.2.3")
        renderer = FooterRenderer(config)
        result = renderer.render()
        assert "1.2.3" in result

    def test_render_no_version(self) -> None:
        config = FooterConfig(show_version=True, version="")
        renderer = FooterRenderer(config)
        result = renderer.render()
        assert "footer-version" not in result

    def test_render_links(self) -> None:
        config = FooterConfig(
            links=[
                FooterLink(label="Home", url="/"),
                FooterLink(label="About", url="/about", target="_blank"),
            ]
        )
        renderer = FooterRenderer(config)
        result = renderer.render()
        assert "Home" in result
        assert "About" in result
        assert '_blank' in result

    def test_render_link_with_icon(self) -> None:
        config = FooterConfig(
            links=[FooterLink(label="GitHub", url="https://github.com", icon="github")]
        )
        renderer = FooterRenderer(config)
        result = renderer.render()
        assert "github" in result

    def test_render_sticky(self) -> None:
        config = FooterConfig(sticky=True)
        renderer = FooterRenderer(config)
        result = renderer.render()
        assert "footer-sticky" in result

    def test_render_no_divider(self) -> None:
        config = FooterConfig(show_divider=False)
        renderer = FooterRenderer(config)
        result = renderer.render()
        assert "footer-divider" not in result
        assert "<footer" in result

    def test_render_custom_left(self) -> None:
        config = FooterConfig(custom_left="<span>Custom Left</span>")
        renderer = FooterRenderer(config)
        result = renderer.render()
        assert "Custom Left" in result

    def test_render_custom_right(self) -> None:
        config = FooterConfig(custom_right="<span>Custom Right</span>")
        renderer = FooterRenderer(config)
        result = renderer.render()
        assert "Custom Right" in result

    def test_render_hides_copyright_when_disabled(self) -> None:
        config = FooterConfig(show_copyright=False)
        renderer = FooterRenderer(config)
        result = renderer.render()
        assert "footer-copyright" not in result

    def test_render_show_version_disabled(self) -> None:
        config = FooterConfig(show_version=False, version="1.0")
        renderer = FooterRenderer(config)
        result = renderer.render()
        assert "footer-version" not in result

    def test_render_no_content_when_nothing_specified(self) -> None:
        config = FooterConfig(
            show_copyright=False, show_version=False, custom_left="", custom_right=""
        )
        renderer = FooterRenderer(config)
        result = renderer.render()
        assert "<footer" in result
