"""AppLayout — the main UI shell for the Shorts Creator application."""

import math
import re

from lexigram.ui import BaseLayoutConfig, BaseLayoutContext, LayoutBase, el
from markupsafe import Markup

from shorts_creator.ui.components.log_panel import LogPanel
from shorts_creator.ui.icons import (
    chevron_right,
    clock,
    folder,
    lightbulb,
    moon,
    settings_icon,
    sun,
    zap,
)

_OKLCH_DECL_RE = re.compile(r"(--[\w-]+:\s*)oklch\(([\d.]+) ([\d.]+) ([\d.]+)(?:\s*/\s*[\d.]+)?\)")


def _oklch_to_rgb(l: float, c: float, h: float) -> tuple:
    h_rad = math.radians(h)
    a = c * math.cos(h_rad)
    b = c * math.sin(h_rad)
    l3 = (l + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m3 = (l - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s3 = (l - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = (
        4.0767416621 * l3 - 3.3077115913 * m3 + 0.2309699292 * s3,
        -1.2684380046 * l3 + 2.6097574011 * m3 - 0.3413193965 * s3,
        -0.0041960863 * l3 - 0.7034186147 * m3 + 1.7076147010 * s3,
    )

    def enc(v: float) -> int:
        v = max(0.0, min(1.0, v))
        v = 12.92 * v if v <= 0.0031308 else 1.055 * (v ** (1 / 2.4)) - 0.055
        return round(v * 255)

    return tuple(enc(v) for v in rgb)


def _oklch_to_hex(l: float, c: float, h: float) -> str:
    return "#{:02x}{:02x}{:02x}".format(*_oklch_to_rgb(l, c, h))


def _with_hex_fallbacks(css: str) -> str:
    def repl(m):
        var = m.group(1)
        name = var.rstrip()[:-1]
        r, g, b = _oklch_to_rgb(float(m.group(2)), float(m.group(3)), float(m.group(4)))
        hexv = f"#{r:02x}{g:02x}{b:02x}"
        return f"{var}{hexv}; {name}-channels: {r} {g} {b}; {m.group(0)}"

    return _OKLCH_DECL_RE.sub(repl, css)


class AppLayout(LayoutBase):
    def __init__(self):
        config = BaseLayoutConfig(
            site_name="Shorts Creator",
            theme="system",
            htmx_enabled=True,
            htmx_version="2",
            htmx_boost=False,
            extra_head=(
                '<script src="/static/js/vendor/tailwindcss.js"></script>'
                "<script>"
                "tailwind.config = { darkMode: 'class', theme: { extend: { colors: {"
                "background: 'rgb(var(--background-channels) / <alpha-value>)', foreground: 'rgb(var(--foreground-channels) / <alpha-value>)',"
                "card: 'rgb(var(--card-channels) / <alpha-value>)', 'card-foreground': 'rgb(var(--card-foreground-channels) / <alpha-value>)',"
                "popover: 'rgb(var(--popover-channels) / <alpha-value>)', 'popover-foreground': 'rgb(var(--popover-foreground-channels) / <alpha-value>)',"
                "primary: 'rgb(var(--primary-channels) / <alpha-value>)', 'primary-foreground': 'rgb(var(--primary-foreground-channels) / <alpha-value>)',"
                "secondary: 'rgb(var(--secondary-channels) / <alpha-value>)', 'secondary-foreground': 'rgb(var(--secondary-foreground-channels) / <alpha-value>)',"
                "muted: 'rgb(var(--muted-channels) / <alpha-value>)', 'muted-foreground': 'rgb(var(--muted-foreground-channels) / <alpha-value>)',"
                "accent: 'rgb(var(--accent-channels) / <alpha-value>)', 'accent-foreground': 'rgb(var(--accent-foreground-channels) / <alpha-value>)',"
                "destructive: 'rgb(var(--destructive-channels) / <alpha-value>)', 'destructive-foreground': 'rgb(var(--destructive-foreground-channels) / <alpha-value>)',"
                "success: 'rgb(var(--color-success-channels) / <alpha-value>)', 'success-foreground': 'rgb(var(--color-success-foreground-channels) / <alpha-value>)',"
                "warning: 'rgb(var(--color-warning-channels) / <alpha-value>)', 'warning-foreground': 'rgb(var(--color-warning-foreground-channels) / <alpha-value>)',"
                "info: 'rgb(var(--color-info-channels) / <alpha-value>)', 'info-foreground': 'rgb(var(--color-info-foreground-channels) / <alpha-value>)',"
                "border: 'rgb(var(--border-channels) / <alpha-value>)', input: 'rgb(var(--input-channels) / <alpha-value>)', ring: 'rgb(var(--ring-channels) / <alpha-value>)'"
                "} } } };"
                "</script>"
                "<style>"
                ".theme-icon-sun{display:none}"
                "html.dark .theme-icon-sun{display:inline-block}"
                "html.dark .theme-icon-moon{display:none}"
                "html{background-color:var(--background)}"
                "#app-shell{"
                "background-color:var(--background);"
                "background-image:radial-gradient(70rem 36rem at 110% -15%,var(--glow) 0%,transparent 60%),"
                "linear-gradient(180deg,var(--card) 0%,var(--background) 46rem)}"
                '#main-content [class~="bg-card"],#main-content [class~="bg-popover"]{'
                "background-image:linear-gradient(180deg,color-mix(in oklch,var(--sheen) 34%,transparent),transparent 60%)}"
                "#app-shell aside.sidebar-collapsed{width:4rem;overflow:hidden;padding-left:.375rem;padding-right:.375rem}"
                "#app-shell aside.sidebar-collapsed .side-label,#app-shell aside.sidebar-collapsed .side-heading,#app-shell aside.sidebar-collapsed .side-text-only{display:none}"
                "#app-shell aside.sidebar-collapsed .side-icon-link{justify-content:center;padding-left:0;padding-right:0}"
                "#app-shell aside .chevron-wrap{transform:rotate(180deg)}"
                "#app-shell aside.sidebar-collapsed .chevron-wrap{transform:rotate(0deg)}"
                "</style>"
                '<link rel="stylesheet" href="/static/css/indicators.css">'
                '<link rel="stylesheet" href="/static/css/toasts.css">'
                '<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎬</text></svg>">'
            ),
        )
        context = BaseLayoutContext(title="Shorts Creator — AI Video Studio")
        super().__init__(config=config, context=context)
        self.htmx_indicator = ""

    def render_htmx_head(self) -> str:
        """Serve htmx from local static assets instead of the unpkg CDN."""
        return '<script src="/static/js/vendor/htmx.min.js"></script>'

    def get_theme_css_variables(self) -> str:
        """Emit graded neutral ShadCN design tokens for both themes."""
        from lexigram.ui.styles.design_tokens import render_all_tokens

        from shorts_creator.ui.theme_tokens import DARK_TOKENS, LIGHT_TOKENS

        return _with_hex_fallbacks(render_all_tokens(LIGHT_TOKENS, DARK_TOKENS))

    def get_dark_mode_script(self) -> str:
        """Apply saved/OS theme before paint (prevents FOUC) and expose the toggle bridge."""
        return """<script>
(function () {
    var stored = localStorage.getItem('darkMode');
    var dark = stored !== null ? stored === 'true' : window.matchMedia('(prefers-color-scheme: dark)').matches;
    if (dark) document.documentElement.classList.add('dark');
})();
window.toggleTheme = function () {
    var dark = !document.documentElement.classList.contains('dark');
    document.documentElement.classList.toggle('dark', dark);
    localStorage.setItem('darkMode', String(dark));
    window.dispatchEvent(new CustomEvent('darkmode-change', { detail: { dark: dark } }));
};
</script>"""

    def render(self, content="", title=None, request=None, **extra_context):
        if request and request.headers.get("HX-Request") == "true":
            return Markup(content)
        return super().render(content=content, title=title, **extra_context)

    def render_body_content(self, content: str = "", **context) -> str:
        return str(
            el(
                "div",
                Markup(self._navbar()),
                el(
                    "div",
                    Markup(self._sidebar()),
                    el(
                        "main",
                        Markup(content),
                        id="main-content",
                        class_="flex-1 p-6 md:p-8 overflow-y-auto",
                    ),
                    class_="flex flex-1 overflow-hidden",
                ),
                el("div", id="toast-container", class_="toast-container"),
                el(
                    "div",
                    id="htmx-progress",
                    class_="fixed top-0 left-0 h-0.5 bg-gradient-to-r from-primary via-primary to-primary transition-all duration-300",
                    style="width:0;z-index:9999",
                ),
                el(
                    "footer",
                    el(
                        "div",
                        el(
                            "div",
                            el("span", "●", class_="text-success text-xs mr-1.5"),
                            el(
                                "span",
                                "All Systems Operational",
                                class_="text-muted-foreground font-mono",
                            ),
                            class_="flex items-center",
                        ),
                        el(
                            "div",
                            el(
                                "span",
                                "Storage: SQLite Active",
                                class_="text-muted-foreground text-xs font-mono",
                            ),
                            el("span", "·", class_="text-muted-foreground mx-2"),
                            el(
                                "span",
                                "Shorts Creator Studio v1.0",
                                class_="text-muted-foreground text-xs font-mono",
                            ),
                            class_="flex items-center",
                        ),
                        class_="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2 px-6 py-3 text-xs",
                    ),
                    class_="border-t border-border/80 bg-background/90 text-muted-foreground shrink-0",
                ),
                Markup(LogPanel()),
                id="app-shell",
                class_="h-screen bg-background text-foreground flex flex-col font-sans overflow-hidden selection:bg-primary/30 selection:text-primary",
            )
        )

    def _navbar(self):
        return el(
            "nav",
            el(
                "div",
                el(
                    "a",
                    el(
                        "span",
                        "🎬",
                        class_="text-2xl hover:scale-110 transition-transform duration-200 inline-block",
                    ),
                    el(
                        "span",
                        "Shorts Creator",
                        class_="font-bold text-lg tracking-tight bg-gradient-to-r from-primary via-foreground to-primary bg-clip-text text-transparent ml-2.5",
                    ),
                    href="/projects",
                    hx_get="/projects",
                    hx_target="#main-content",
                    hx_push_url="/projects",
                    class_="flex items-center hover:opacity-90 transition-opacity",
                ),
                class_="flex items-center gap-2",
            ),
            el(
                "div",
                el(
                    "div",
                    el(
                        "span",
                        "Loading…",
                        class_="text-xs text-muted-foreground animate-pulse font-mono",
                    ),
                    id="provider-status",
                    hx_get="/api/health/header",
                    hx_trigger="load delay:1s",
                    hx_swap="innerHTML",
                ),
                el(
                    "a",
                    zap(),
                    el("span", "New Project", class_="ml-1 font-medium"),
                    href="/projects/new",
                    hx_get="/projects/new",
                    hx_target="#main-content",
                    hx_push_url="/projects/new",
                    class_="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-primary-foreground bg-gradient-to-r from-primary to-primary hover:from-primary hover:to-primary shadow-md shadow-primary/50 transition-all duration-200 hover:scale-[1.02]",
                ),
                el(
                    "button",
                    el("span", moon(), class_="theme-icon-moon", aria_hidden="true"),
                    el("span", sun(), class_="theme-icon-sun", aria_hidden="true"),
                    onclick="toggleTheme()",
                    aria_label="Toggle theme",
                    class_="flex items-center justify-center h-7 px-2.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/60 border border-border/50 transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                ),
                class_="flex items-center gap-3",
            ),
            class_="border-b border-border/80 px-6 py-3 flex items-center justify-between bg-background/90 backdrop-blur-md sticky top-0 z-50 shadow-sm",
        )

    def _nav_link(self, icon_fn, label, href, **extra):
        return el(
            "a",
            icon_fn(),
            el("span", label, class_="truncate side-label"),
            href=href,
            hx_get=href,
            hx_target="#main-content",
            hx_push_url=href,
            class_="side-icon-link group flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-secondary/60 border border-transparent hover:border-border/50 transition-all duration-150",
            **(extra or {}),
        )

    def _sidebar(self):
        s_link = self._nav_link(settings_icon, "Settings", "/settings")
        vt_link = self._nav_link(lightbulb, "Topics", "/topics")
        as_link = self._nav_link(folder, "Assets", "/assets")

        groups = [
            el(
                "div",
                el(
                    "div",
                    el(
                        "h3",
                        "PROJECT",
                        class_="side-heading text-[10px] font-bold tracking-widest text-muted-foreground uppercase font-mono",
                    ),
                    el(
                        "a",
                        "See All",
                        href="/projects",
                        hx_get="/projects",
                        hx_target="#main-content",
                        hx_push_url="/projects",
                        class_="side-text-only text-[10px] font-mono text-primary hover:text-primary transition-colors whitespace-nowrap",
                    ),
                    class_="flex items-center justify-between px-3 pb-1",
                ),
                el(
                    "div",
                    el(
                        "span",
                        "Loading…",
                        class_="side-text-only text-xs text-muted-foreground animate-pulse font-mono",
                    ),
                    id="sidebar-recent-projects",
                    hx_get="/api/sidebar/recent-projects",
                    hx_trigger="load delay:0.1s",
                    hx_swap="innerHTML",
                ),
                el(
                    "div",
                    el(
                        "h3",
                        "RUNS",
                        class_="side-heading px-3 pb-1 text-[10px] font-bold tracking-widest text-muted-foreground uppercase font-mono",
                    ),
                    el(
                        "div",
                        el(
                            "span",
                            "Loading…",
                            class_="side-text-only text-xs text-muted-foreground animate-pulse font-mono",
                        ),
                        id="sidebar-recent-runs",
                        hx_get="/api/sidebar/recent-runs",
                        hx_vals='js:{project_id:(new URLSearchParams(window.location.search).get("project_id"))||(window.location.pathname.match(/^\\/projects\\/([0-9a-f-]{36})/)||[])[1]||""}',
                        hx_trigger="load delay:0.1s, sidebarRunsChanged from:body",
                        hx_swap="innerHTML",
                    ),
                    class_="border-t border-border/40 mt-3 pt-3",
                ),
                class_="space-y-2",
            ),
            el(
                "div",
                el(
                    "h3",
                    "LIBRARY",
                    class_="side-heading px-3 pt-3 pb-1.5 text-[10px] font-bold tracking-widest text-muted-foreground uppercase font-mono",
                ),
                el(
                    "div",
                    self._nav_link(clock, "History", "/history"),
                    as_link,
                    class_="space-y-0.5",
                ),
                class_="mb-2",
            ),
            el(
                "div",
                el(
                    "h3",
                    "CONFIGURE",
                    class_="side-heading px-3 pt-3 pb-1.5 text-[10px] font-bold tracking-widest text-muted-foreground uppercase font-mono",
                ),
                el("div", vt_link, s_link, class_="space-y-0.5"),
                class_="pt-3 mt-auto",
            ),
        ]

        return str(
            el(
                "aside",
                el("nav", *groups[:2], class_="side-nav space-y-3 flex-1 overflow-y-auto"),
                el("div", groups[2], class_="border-t border-border/40 pt-3 shrink-0"),
                el(
                    "button",
                    el(
                        "span",
                        chevron_right(),
                        id="sidebar-chevron",
                        class_="chevron-wrap transition-transform duration-200",
                    ),
                    el("span", "Collapse", class_="truncate side-label rounded-e"),
                    type="button",
                    id="sidebar-toggle",
                    onclick="toggleSidebar()",
                    aria_label="Toggle sidebar",
                    class_="side-icon-link flex items-center gap-3 px-3 py-2 mt-3 rounded-lg text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-secondary/60 border border-border/40 hover:border-border/50 transition-colors cursor-pointer shrink-0 w-full",
                ),
                class_="w-60 border-r border-border/80 p-4 shrink-0 bg-background/40 backdrop-blur-sm flex flex-col h-full transition-[width] duration-200",
            )
        )

    def render_body_end(self, **context):
        body_end = super().render_body_end(**context)
        return (
            body_end
            + '<script src="/static/js/toasts.js"></script>'
            + '<script src="/static/js/htmx-shell.js"></script>'
        )
