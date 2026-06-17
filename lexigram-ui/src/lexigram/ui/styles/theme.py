from __future__ import annotations

from lexigram.ui.styles.design_tokens import (
    SHADCN_DARK_COLORS,
    SHADCN_DEFAULT_COLORS,
    render_all_tokens,
)

# Opacity-modified utilities for CSS-variable colors. The Tailwind runtime
# (play CDN) does not generate ``bg-success/20``-style utilities when the
# color resolves to a custom property, so those classes silently render as
# no rule at all — leaving semantic pills/badges/toasts with no tinted
# background and, in dark mode, washed-out foregrounds. These explicit
# rules keep the same class names functional in both themes.
_OPACITY_UTILITIES_CSS = """
/* Lexigram UI — opacity utilities for CSS-variable colors (Tailwind CDN
   skips these because the colors are custom properties) */
.bg-success\\/10 { background-color: color-mix(in srgb, var(--color-success) 10%, transparent); }
.bg-success\\/20 { background-color: color-mix(in srgb, var(--color-success) 20%, transparent); }
.bg-warning\\/10 { background-color: color-mix(in srgb, var(--color-warning) 10%, transparent); }
.bg-warning\\/20 { background-color: color-mix(in srgb, var(--color-warning) 20%, transparent); }
.bg-info\\/10 { background-color: color-mix(in srgb, var(--color-info) 10%, transparent); }
.bg-info\\/20 { background-color: color-mix(in srgb, var(--color-info) 20%, transparent); }
.bg-destructive\\/10 { background-color: color-mix(in srgb, var(--destructive) 10%, transparent); }
.bg-destructive\\/20 { background-color: color-mix(in srgb, var(--destructive) 20%, transparent); }
.bg-destructive\\/25 { background-color: color-mix(in srgb, var(--destructive) 25%, transparent); }
.bg-primary\\/10 { background-color: color-mix(in srgb, var(--primary) 10%, transparent); }
.bg-primary\\/20 { background-color: color-mix(in srgb, var(--primary) 20%, transparent); }
.bg-primary\\/90 { background-color: color-mix(in srgb, var(--primary) 90%, transparent); }
.border-success\\/30 { border-color: color-mix(in srgb, var(--color-success) 30%, transparent); }
.border-warning\\/30 { border-color: color-mix(in srgb, var(--color-warning) 30%, transparent); }
.border-info\\/30 { border-color: color-mix(in srgb, var(--color-info) 30%, transparent); }
.border-destructive\\/30 { border-color: color-mix(in srgb, var(--destructive) 30%, transparent); }
.border-primary\\/20 { border-color: color-mix(in srgb, var(--primary) 20%, transparent); }
.text-warning\\/90 { color: color-mix(in srgb, var(--color-warning) 90%, transparent); }
.hover\\:bg-destructive\\/10:hover { background-color: color-mix(in srgb, var(--destructive) 10%, transparent); }
.dark .dark\\:bg-success\\/20 { background-color: color-mix(in srgb, var(--color-success) 20%, transparent); }
.dark .dark\\:bg-warning\\/20 { background-color: color-mix(in srgb, var(--color-warning) 20%, transparent); }
.dark .dark\\:bg-info\\/20 { background-color: color-mix(in srgb, var(--color-info) 20%, transparent); }
.dark .dark\\:bg-destructive\\/25 { background-color: color-mix(in srgb, var(--destructive) 25%, transparent); }
"""


def shadcn_css(
    primary: str | None = None,
    background: str | None = None,
    foreground: str | None = None,
    radius: str | None = None,
    success: str | None = None,
    warning: str | None = None,
    info: str | None = None,
) -> str:
    """Generate ShadCN-compatible CSS with optional overrides.

    Args:
        primary: Override primary color (oklch or hex value).
        background: Override background color.
        foreground: Override foreground color.
        radius: Override border radius.
        success: Override success color.
        warning: Override warning color.
        info: Override info color.

    Returns:
        Complete CSS string with :root and .dark variable blocks.
    """
    colors = dict(SHADCN_DEFAULT_COLORS)
    dark_colors = dict(SHADCN_DARK_COLORS)

    if primary:
        colors["--primary"] = primary
        colors["--ring"] = primary
        colors["--primary-foreground"] = "oklch(1 0 0)"
        dark_colors["--primary"] = primary
        dark_colors["--ring"] = primary
        dark_colors["--primary-foreground"] = "oklch(1 0 0)"
    if background:
        colors["--background"] = background
        dark_colors["--background"] = background
    if foreground:
        colors["--foreground"] = foreground
        dark_colors["--foreground"] = foreground
    if radius:
        colors["--radius"] = radius
        dark_colors["--radius"] = radius
    if success:
        colors["--color-success"] = success
        dark_colors["--color-success"] = success
    if warning:
        colors["--color-warning"] = warning
        dark_colors["--color-warning"] = warning
    if info:
        colors["--color-info"] = info
        dark_colors["--color-info"] = info

    parts = [
        "/* Lexigram UI — ShadCN-compatible design tokens */",
        render_all_tokens(colors, dark_colors),
        _OPACITY_UTILITIES_CSS,
    ]
    return "\n".join(parts)
