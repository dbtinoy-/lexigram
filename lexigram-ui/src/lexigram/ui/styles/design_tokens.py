from __future__ import annotations

"""ShadCN-compatible design tokens for Lexigram UI.

All values use oklch color space for perceptually-uniform interpolation.
Overridable via CSS custom properties.
"""

SHADCN_DEFAULT_COLORS: dict[str, str] = {
    "--background": "oklch(1 0 0)",
    "--foreground": "oklch(0.145 0 0)",
    "--card": "oklch(0.992 0 0)",
    "--card-foreground": "oklch(0.145 0 0)",
    "--popover": "oklch(0.992 0 0)",
    "--popover-foreground": "oklch(0.145 0 0)",
    "--primary": "oklch(0.546 0.245 262.881)",
    "--primary-foreground": "oklch(1 0 0)",
    "--secondary": "oklch(0.94 0 0)",
    "--secondary-foreground": "oklch(0.205 0 0)",
    "--muted": "oklch(0.95 0 0)",
    "--muted-foreground": "oklch(0.45 0 0)",
    "--accent": "oklch(0.93 0 0)",
    "--accent-foreground": "oklch(0.205 0 0)",
    "--destructive": "oklch(0.577 0.245 27.325)",
    "--destructive-foreground": "oklch(1 0 0)",
    "--border": "oklch(0.85 0 0)",
    "--input": "oklch(0.82 0 0)",
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
    "--color-gray-50": "oklch(0.985 0 0)",
    "--color-gray-100": "oklch(0.967 0 0)",
    "--color-gray-200": "oklch(0.922 0 0)",
    "--color-gray-300": "oklch(0.87 0 0)",
    "--color-gray-400": "oklch(0.708 0 0)",
    "--color-gray-500": "oklch(0.556 0 0)",
    "--color-gray-600": "oklch(0.439 0 0)",
    "--color-gray-700": "oklch(0.371 0 0)",
    "--color-gray-800": "oklch(0.269 0 0)",
    "--color-gray-900": "oklch(0.205 0 0)",
    "--color-gray-950": "oklch(0.145 0 0)",
    "--radius": "0.5rem",
}

SHADCN_DARK_COLORS: dict[str, str] = {
    "--background": "oklch(0.145 0 0)",
    "--foreground": "oklch(0.985 0 0)",
    "--card": "oklch(0.18 0 0)",
    "--card-foreground": "oklch(0.985 0 0)",
    "--popover": "oklch(0.20 0 0)",
    "--popover-foreground": "oklch(0.985 0 0)",
    "--primary": "oklch(0.546 0.245 262.881)",
    "--primary-foreground": "oklch(1 0 0)",
    "--secondary": "oklch(0.22 0 0)",
    "--secondary-foreground": "oklch(0.985 0 0)",
    "--muted": "oklch(0.22 0 0)",
    "--muted-foreground": "oklch(0.65 0 0)",
    "--accent": "oklch(0.22 0 0)",
    "--accent-foreground": "oklch(0.985 0 0)",
    "--destructive": "oklch(0.577 0.245 27.325)",
    "--destructive-foreground": "oklch(1 0 0)",
    "--border": "oklch(0.32 0 0)",
    "--input": "oklch(0.37 0 0)",
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
    "--color-gray-50": "oklch(0.145 0 0)",
    "--color-gray-100": "oklch(0.205 0 0)",
    "--color-gray-200": "oklch(0.269 0 0)",
    "--color-gray-300": "oklch(0.371 0 0)",
    "--color-gray-400": "oklch(0.439 0 0)",
    "--color-gray-500": "oklch(0.556 0 0)",
    "--color-gray-600": "oklch(0.708 0 0)",
    "--color-gray-700": "oklch(0.87 0 0)",
    "--color-gray-800": "oklch(0.922 0 0)",
    "--color-gray-900": "oklch(0.967 0 0)",
    "--color-gray-950": "oklch(0.985 0 0)",
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


SEMANTIC_UTILITY_CLASSES: dict[str, str] = {
    # ── Backgrounds ──
    "bg-background": "background-color: var(--background);",
    "bg-foreground": "background-color: var(--foreground);",
    "bg-card": "background-color: var(--card);",
    "bg-card-foreground": "background-color: var(--card-foreground);",
    "bg-popover": "background-color: var(--popover);",
    "bg-popover-foreground": "background-color: var(--popover-foreground);",
    "bg-primary": "background-color: var(--primary);",
    "bg-primary-foreground": "background-color: var(--primary-foreground);",
    "bg-secondary": "background-color: var(--secondary);",
    "bg-secondary-foreground": "background-color: var(--secondary-foreground);",
    "bg-muted": "background-color: var(--muted);",
    "bg-muted-foreground": "background-color: var(--muted-foreground);",
    "bg-accent": "background-color: var(--accent);",
    "bg-accent-foreground": "background-color: var(--accent-foreground);",
    "bg-destructive": "background-color: var(--destructive);",
    "bg-destructive-foreground": "background-color: var(--destructive-foreground);",
    "bg-border": "background-color: var(--border);",
    "bg-input": "background-color: var(--input);",
    "bg-ring": "background-color: var(--ring);",
    "bg-success": "background-color: var(--color-success);",
    "bg-success-foreground": "background-color: var(--color-success-foreground);",
    "bg-warning": "background-color: var(--color-warning);",
    "bg-warning-foreground": "background-color: var(--color-warning-foreground);",
    "bg-info": "background-color: var(--color-info);",
    "bg-info-foreground": "background-color: var(--color-info-foreground);",
    # ── Text colors ──
    "text-background": "color: var(--background);",
    "text-foreground": "color: var(--foreground);",
    "text-card-foreground": "color: var(--card-foreground);",
    "text-popover-foreground": "color: var(--popover-foreground);",
    "text-primary": "color: var(--primary);",
    "text-primary-foreground": "color: var(--primary-foreground);",
    "text-secondary": "color: var(--secondary);",
    "text-secondary-foreground": "color: var(--secondary-foreground);",
    "text-muted": "color: var(--muted);",
    "text-muted-foreground": "color: var(--muted-foreground);",
    "text-accent": "color: var(--accent);",
    "text-accent-foreground": "color: var(--accent-foreground);",
    "text-destructive": "color: var(--destructive);",
    "text-destructive-foreground": "color: var(--destructive-foreground);",
    "text-success": "color: var(--color-success);",
    "text-success-foreground": "color: var(--color-success-foreground);",
    "text-warning": "color: var(--color-warning);",
    "text-warning-foreground": "color: var(--color-warning-foreground);",
    "text-info": "color: var(--color-info);",
    "text-info-foreground": "color: var(--color-info-foreground);",
    # ── Border colors ──
    "border-background": "border-color: var(--background);",
    "border-foreground": "border-color: var(--foreground);",
    "border-card": "border-color: var(--card);",
    "border-popover": "border-color: var(--popover);",
    "border-primary": "border-color: var(--primary);",
    "border-secondary": "border-color: var(--secondary);",
    "border-muted": "border-color: var(--muted);",
    "border-accent": "border-color: var(--accent);",
    "border-destructive": "border-color: var(--destructive);",
    "border-border": "border-color: var(--border);",
    "border-input": "border-color: var(--input);",
    "border-ring": "border-color: var(--ring);",
    "border-success": "border-color: var(--color-success);",
    "border-success-foreground": "border-color: var(--color-success-foreground);",
    "border-warning": "border-color: var(--color-warning);",
    "border-warning-foreground": "border-color: var(--color-warning-foreground);",
    "border-info": "border-color: var(--color-info);",
    "border-info-foreground": "border-color: var(--color-info-foreground);",
    # ── Ring / Focus ──
    "ring-ring": "box-shadow: 0 0 0 2px var(--ring);",
    "ring-destructive": "box-shadow: 0 0 0 2px var(--destructive);",
    "ring-offset-background": "--tw-ring-offset-color: var(--background);",
    # ── Radius ──
    "rounded-sm": "border-radius: calc(var(--radius) - 0.25rem);",
    "rounded-md": "border-radius: calc(var(--radius) - 0.125rem);",
    "rounded-lg": "border-radius: var(--radius);",
    "rounded-xl": "border-radius: calc(var(--radius) + 0.25rem);",
    # ── Shadows ──
    "shadow-sm": "box-shadow: var(--shadow-sm);",
    "shadow": "box-shadow: var(--shadow);",
    "shadow-md": "box-shadow: var(--shadow-md);",
    "shadow-lg": "box-shadow: var(--shadow-lg);",
    "shadow-xl": "box-shadow: var(--shadow-xl);",
    "shadow-2xl": "box-shadow: var(--shadow-2xl);",
    "shadow-inner": "box-shadow: var(--shadow-inner);",
    # ── Transitions ──
    "transition-all": "transition-property: all; transition-timing-function: var(--ease-in-out); transition-duration: var(--duration-normal);",
    "transition-colors": "transition-property: color, background-color, border-color, text-decoration-color, fill, stroke; transition-timing-function: var(--ease-in-out); transition-duration: var(--duration-normal);",
    "transition-opacity": "transition-property: opacity; transition-timing-function: var(--ease-in-out); transition-duration: var(--duration-normal);",
    "transition-shadow": "transition-property: box-shadow; transition-timing-function: var(--ease-in-out); transition-duration: var(--duration-normal);",
    "transition-transform": "transition-property: transform; transition-timing-function: var(--ease-in-out); transition-duration: var(--duration-normal);",
    # ── Ring focus (ShadCN standard focus pattern) ──
    "focus-ring": "outline: none; box-shadow: 0 0 0 2px var(--ring); outline: 2px solid transparent; outline-offset: 2px;",
    "focus-ring-destructive": "outline: none; box-shadow: 0 0 0 2px var(--destructive); outline: 2px solid transparent; outline-offset: 2px;",
}


def render_utility_classes() -> str:
    """Render CSS utility classes that map to design tokens (dark-aware)."""
    lines: list[str] = []
    for cls, rule in sorted(SEMANTIC_UTILITY_CLASSES.items()):
        lines.append(f".{cls} {{ {rule} }}")
        lines.append(f".dark .{cls} {{ {rule} }}")
    return "\n".join(lines)
