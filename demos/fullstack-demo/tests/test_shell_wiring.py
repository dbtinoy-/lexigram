import re
from pathlib import Path

from shorts_creator.ui.shell import AppLayout

STATIC_JS = Path(__file__).resolve().parents[1] / "src/shorts_creator/ui/static/js"


class TestGlobalLoadingWiring:
    def test_progress_bar_wired_to_htmx_events(self):
        html = AppLayout().render_body_end()
        assert 'src="/static/js/htmx-shell.js"' in html
        assert 'src="/static/js/toasts.js"' in html
        js = (STATIC_JS / "htmx-shell.js").read_text()
        assert "htmx:beforeRequest" in js
        assert "htmx:afterRequest" in js
        assert "htmx-progress" in js

    def test_error_toasts_wired(self):
        html = AppLayout().render_body_end()
        assert 'src="/static/js/htmx-shell.js"' in html
        assert 'src="/static/js/toasts.js"' in html
        shell_js = (STATIC_JS / "htmx-shell.js").read_text()
        assert "htmx:responseError" in shell_js
        assert "htmx:sendError" in shell_js
        assert "htmx:timeoutError" in shell_js
        toasts_js = (STATIC_JS / "toasts.js").read_text()
        assert "showToast" in toasts_js


class TestThemeWiring:
    def test_head_carries_theme_tokens_and_dark_bootstrap(self):
        html = AppLayout().render()
        assert "tailwind.config" in html
        assert "darkMode: 'class'" in html
        assert "rgb(var(--primary-channels) / <alpha-value>)" in html
        assert "prefers-color-scheme: dark" in html
        assert "classList.add('dark')" in html

    def test_semantic_token_mapping_registered_for_tailwind(self):
        html = AppLayout().render()
        assert "primary: 'rgb(var(--primary-channels) / <alpha-value>)'" in html
        assert "'muted-foreground': 'rgb(var(--muted-foreground-channels) / <alpha-value>)'" in html
        assert "success: 'rgb(var(--color-success-channels) / <alpha-value>)'" in html
        assert "destructive: 'rgb(var(--destructive-channels) / <alpha-value>)'" in html
        assert "border: 'rgb(var(--border-channels) / <alpha-value>)'" in html

    def test_oklch_tokens_have_hex_and_channel_fallbacks(self):
        html = AppLayout().render()
        style_block = re.search(r"<style>(.*?)</style>", html, re.DOTALL).group(1)
        decls = re.findall(r"--[\w-]+:\s*[^;]+;", style_block)
        oklch_vars = []
        for decl in decls:
            name = decl.split(":")[0]
            value = decl.split(":", 1)[1].strip()
            if value.startswith("oklch("):
                oklch_vars.append(name)
        assert oklch_vars, "expected oklch token declarations"
        for name in oklch_vars:
            hexes = [
                d for d in decls if d.startswith(name + ":") and not d.startswith(name + ": oklch")
            ]
            assert hexes, f"missing hex fallback for {name}"
            channels = [d for d in decls if d.startswith(name + "-channels:")]
            assert channels, f"missing channel token for {name}"
        assert "--primary: #4d4d4f;" in style_block
        assert "--primary-channels: 77 77 79;" in style_block
        assert "--background-channels: 243 243 245;" in style_block
        assert "--background-channels: 8 8 9;" in style_block
