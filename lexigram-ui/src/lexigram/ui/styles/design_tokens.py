from __future__ import annotations

"""ShadCN-compatible design tokens for Lexigram UI.

All values use oklch color space for perceptually-uniform interpolation.
Overridable via CSS custom properties.
"""

SHADCN_DEFAULT_COLORS: dict[str, str] = {
    "--background": "oklch(0.98 0 0)",
    "--foreground": "oklch(0.17 0 0)",
    "--card": "oklch(1 0 0)",
    "--card-foreground": "oklch(0.17 0 0)",
    "--popover": "oklch(1 0 0)",
    "--popover-foreground": "oklch(0.17 0 0)",
    "--primary": "oklch(0.546 0.245 262.881)",
    "--primary-foreground": "oklch(1 0 0)",
    "--secondary": "oklch(0.94 0 0)",
    "--secondary-foreground": "oklch(0.22 0 0)",
    "--muted": "oklch(0.95 0 0)",
    "--muted-foreground": "oklch(0.46 0 0)",
    "--accent": "oklch(0.94 0 0)",
    "--accent-foreground": "oklch(0.22 0 0)",
    "--destructive": "oklch(0.577 0.245 27.325)",
    "--destructive-foreground": "oklch(1 0 0)",
    "--border": "oklch(0.87 0 0)",
    "--input": "oklch(0.84 0 0)",
    "--ring": "oklch(0.546 0.245 262.881)",
    "--chart-1": "oklch(0.646 0.222 41.116)",
    "--chart-2": "oklch(0.6 0.118 184.704)",
    "--chart-3": "oklch(0.398 0.07 227.392)",
    "--chart-4": "oklch(0.828 0.189 84.429)",
    "--chart-5": "oklch(0.769 0.188 70.08)",
    "--color-success": "oklch(0.52 0.18 149.214)",
    "--color-success-foreground": "oklch(1 0 0)",
    "--color-warning": "oklch(0.795 0.184 86.047)",
    "--color-warning-foreground": "oklch(0.145 0 0)",
    "--color-info": "oklch(0.56 0.23 277.117)",
    "--color-info-foreground": "oklch(1 0 0)",
    "--radius": "0.5rem",
}

SHADCN_DARK_COLORS: dict[str, str] = {
    "--background": "oklch(0.23 0 0)",
    "--foreground": "oklch(0.95 0 0)",
    "--card": "oklch(0.27 0 0)",
    "--card-foreground": "oklch(0.95 0 0)",
    "--popover": "oklch(0.29 0 0)",
    "--popover-foreground": "oklch(0.95 0 0)",
    "--primary": "oklch(0.623 0.214 259.815)",
    "--primary-foreground": "oklch(0.97 0 0)",
    "--secondary": "oklch(0.31 0 0)",
    "--secondary-foreground": "oklch(0.95 0 0)",
    "--muted": "oklch(0.31 0 0)",
    "--muted-foreground": "oklch(0.68 0 0)",
    "--accent": "oklch(0.31 0 0)",
    "--accent-foreground": "oklch(0.95 0 0)",
    "--destructive": "oklch(0.62 0.25 27.325)",
    "--destructive-foreground": "oklch(0.97 0 0)",
    "--border": "oklch(0.38 0 0)",
    "--input": "oklch(0.42 0 0)",
    "--ring": "oklch(0.623 0.214 259.815)",
    "--chart-1": "oklch(0.646 0.222 41.116)",
    "--chart-2": "oklch(0.6 0.118 184.704)",
    "--chart-3": "oklch(0.398 0.07 227.392)",
    "--chart-4": "oklch(0.828 0.189 84.429)",
    "--chart-5": "oklch(0.769 0.188 70.08)",
    "--color-success": "oklch(0.76 0.14 149.214)",
    "--color-success-foreground": "oklch(0.97 0 0)",
    "--color-warning": "oklch(0.82 0.15 86.047)",
    "--color-warning-foreground": "oklch(0.2 0 0)",
    "--color-info": "oklch(0.74 0.135 277.116)",
    "--color-info-foreground": "oklch(0.97 0 0)",
}

# ── Spacing tokens ─────────────────────────────────────────────
SPACING_TOKENS: dict[str, str] = {
    "--spacing-0": "0px",
    "--spacing-1": "0.25rem",
    "--spacing-2": "0.5rem",
    "--spacing-3": "0.75rem",
    "--spacing-4": "1rem",
    "--spacing-5": "1.25rem",
    "--spacing-6": "1.5rem",
    "--spacing-8": "2rem",
    "--spacing-10": "2.5rem",
    "--spacing-12": "3rem",
    "--spacing-16": "4rem",
    "--spacing-20": "5rem",
    "--spacing-24": "6rem",
}

# ── Typography tokens ──────────────────────────────────────────
TYPOGRAPHY_TOKENS: dict[str, str] = {
    "--font-sans": "Inter, ui-sans-serif, system-ui, sans-serif",
    "--font-mono": "JetBrains Mono, ui-monospace, SFMono-Regular, monospace",
    "--font-size-xs": "0.75rem",
    "--font-size-sm": "0.875rem",
    "--font-size-base": "1rem",
    "--font-size-lg": "1.125rem",
    "--font-size-xl": "1.25rem",
    "--font-size-2xl": "1.5rem",
    "--font-size-3xl": "1.875rem",
    "--font-weight-normal": "400",
    "--font-weight-medium": "500",
    "--font-weight-semibold": "600",
    "--font-weight-bold": "700",
    "--line-height-tight": "1.25",
    "--line-height-normal": "1.5",
    "--line-height-relaxed": "1.625",
    "--letter-spacing-tight": "-0.025em",
    "--letter-spacing-normal": "0em",
    "--letter-spacing-wide": "0.025em",
}

# ── Shadow tokens ──────────────────────────────────────────────
SHADOW_TOKENS: dict[str, str] = {
    "--shadow-xs": "0 1px 2px 0 rgb(0 0 0 / 0.05)",
    "--shadow-sm": "0 1px 2px 0 rgb(0 0 0 / 0.05)",
    "--shadow": "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
    "--shadow-md": "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
    "--shadow-lg": "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
    "--shadow-xl": "0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)",
    "--shadow-2xl": "0 25px 50px -12px rgb(0 0 0 / 0.25)",
    "--shadow-inner": "inset 0 2px 4px 0 rgb(0 0 0 / 0.05)",
}

# ── Animation tokens ───────────────────────────────────────────
ANIMATION_TOKENS: dict[str, str] = {
    "--duration-fast": "150ms",
    "--duration-normal": "200ms",
    "--duration-slow": "300ms",
    "--ease-in": "cubic-bezier(0.4, 0, 1, 1)",
    "--ease-out": "cubic-bezier(0, 0, 0.2, 1)",
    "--ease-in-out": "cubic-bezier(0.4, 0, 0.2, 1)",
}


def render_all_tokens(
    colors: dict[str, str] | None = None,
    dark_colors: dict[str, str] | None = None,
) -> str:
    """Render complete :root and .dark CSS blocks with all token types."""
    c = colors if colors is not None else SHADCN_DEFAULT_COLORS
    dc = dark_colors if dark_colors is not None else SHADCN_DARK_COLORS
    lines = [":root {"]
    for var, value in {
        **c,
        **SPACING_TOKENS,
        **TYPOGRAPHY_TOKENS,
        **SHADOW_TOKENS,
        **ANIMATION_TOKENS,
    }.items():
        lines.append(f"  {var}: {value};")
    lines.append("  color-scheme: light;")
    lines.append("}")
    lines.append("")
    lines.append(".dark {")
    for var, value in dc.items():
        lines.append(f"  {var}: {value};")
    lines.append("  color-scheme: dark;")
    lines.append("}")
    return "\n".join(lines)
