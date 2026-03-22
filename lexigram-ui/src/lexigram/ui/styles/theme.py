from __future__ import annotations

from lexigram.ui.styles.design_tokens import (
    SHADCN_DARK_COLORS,
    SHADCN_DEFAULT_COLORS,
    render_all_tokens,
    render_utility_classes,
)


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
        Complete CSS string with :root and .dark variable blocks + utility classes.
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
        "",
        "/* Utility classes */",
        render_utility_classes(),
    ]
    return "\n".join(parts)
