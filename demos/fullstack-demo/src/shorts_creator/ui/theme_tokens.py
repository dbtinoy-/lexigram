"""Graded neutral design tokens for light and dark themes.

Every surface sits on a tonal ramp instead of a single flat gray:
light mode steps from paper-white cards down to soft gray backgrounds,
dark mode steps from deep charcoal base up through elevated card panels.
Custom tokens ``--sheen`` (card top highlight) and ``--glow`` (ambient
radial wash) drive the surface gradients applied in the app shell.
"""

from lexigram.ui.styles.design_tokens import SHADCN_DARK_COLORS, SHADCN_DEFAULT_COLORS

LIGHT_TOKENS: dict[str, str] = {
    **SHADCN_DEFAULT_COLORS,
    "--background": "oklch(0.965 0.002 285)",
    "--foreground": "oklch(0.22 0.003 285)",
    "--card": "oklch(0.987 0.001 285)",
    "--card-foreground": "oklch(0.22 0.003 285)",
    "--popover": "oklch(1 0 0)",
    "--popover-foreground": "oklch(0.22 0.003 285)",
    "--primary": "oklch(0.42 0.004 285)",
    "--primary-foreground": "oklch(0.985 0.001 285)",
    "--secondary": "oklch(0.924 0.002 285)",
    "--secondary-foreground": "oklch(0.26 0.003 285)",
    "--muted": "oklch(0.938 0.002 285)",
    "--muted-foreground": "oklch(0.48 0.002 285)",
    "--accent": "oklch(0.903 0.002 285)",
    "--accent-foreground": "oklch(0.24 0.003 285)",
    "--border": "oklch(0.891 0.002 285)",
    "--input": "oklch(0.903 0.002 285)",
    "--ring": "oklch(0.6 0.005 285)",
    "--sidebar": "oklch(0.949 0.002 285)",
    "--sidebar-foreground": "oklch(0.22 0.003 285)",
    "--sidebar-primary": "oklch(0.42 0.004 285)",
    "--sidebar-primary-foreground": "oklch(0.985 0.001 285)",
    "--sidebar-accent": "oklch(0.909 0.002 285)",
    "--sidebar-accent-foreground": "oklch(0.24 0.003 285)",
    "--sidebar-border": "oklch(0.885 0.002 285)",
    "--sidebar-ring": "oklch(0.6 0.005 285)",
    "--sheen": "oklch(1 0 0)",
    "--glow": "oklch(0.9 0.002 285)",
    "--color-success-foreground": "oklch(0.15 0.03 149)",
    "--color-warning": "oklch(0.62 0.15 86)",
    "--color-warning-foreground": "oklch(0.16 0.03 90)",
    "--color-info-foreground": "oklch(0.15 0.03 270)",
}

DARK_TOKENS: dict[str, str] = {
    **SHADCN_DARK_COLORS,
    "--background": "oklch(0.135 0.003 285)",
    "--foreground": "oklch(0.955 0.002 285)",
    "--card": "oklch(0.196 0.003 285)",
    "--card-foreground": "oklch(0.955 0.002 285)",
    "--popover": "oklch(0.215 0.003 285)",
    "--popover-foreground": "oklch(0.955 0.002 285)",
    "--primary": "oklch(0.815 0.004 285)",
    "--primary-foreground": "oklch(0.15 0.003 285)",
    "--secondary": "oklch(0.278 0.003 285)",
    "--secondary-foreground": "oklch(0.955 0.002 285)",
    "--muted": "oklch(0.238 0.003 285)",
    "--muted-foreground": "oklch(0.675 0.002 285)",
    "--accent": "oklch(0.258 0.003 285)",
    "--accent-foreground": "oklch(0.955 0.002 285)",
    "--border": "oklch(0.268 0.003 285)",
    "--input": "oklch(0.29 0.003 285)",
    "--ring": "oklch(0.68 0.004 285)",
    "--sidebar": "oklch(0.156 0.003 285)",
    "--sidebar-foreground": "oklch(0.955 0.002 285)",
    "--sidebar-primary": "oklch(0.815 0.004 285)",
    "--sidebar-primary-foreground": "oklch(0.15 0.003 285)",
    "--sidebar-accent": "oklch(0.252 0.003 285)",
    "--sidebar-accent-foreground": "oklch(0.955 0.002 285)",
    "--sidebar-border": "oklch(0.275 0.003 285)",
    "--sidebar-ring": "oklch(0.68 0.004 285)",
    "--sheen": "oklch(0.42 0.005 285)",
    "--glow": "oklch(0.29 0.004 285)",
    "--color-success-foreground": "oklch(0.14 0.03 149)",
    "--color-warning-foreground": "oklch(0.16 0.03 90)",
    "--color-info-foreground": "oklch(0.14 0.03 270)",
}
