from __future__ import annotations

"""Shared Tailwind CSS runtime configuration for admin layouts.

Maps the ShadCN-compatible CSS custom properties (rendered by
:func:`lexigram.ui.styles.design_tokens.render_all_tokens`) into Tailwind
utility classes (``bg-card``, ``text-muted-foreground``, ``border-border``,
``bg-primary/20``, ``text-success``, ...) and bootstraps the ``dark`` class
on ``<html>`` before Alpine.js loads.
"""

TAILWIND_THEME_CONFIG: str = """<script>
tailwind.config = {
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: 'var(--background)',
        foreground: 'var(--foreground)',
        card: { DEFAULT: 'var(--card)', foreground: 'var(--card-foreground)' },
        popover: { DEFAULT: 'var(--popover)', foreground: 'var(--popover-foreground)' },
        primary: { DEFAULT: 'var(--primary)', foreground: 'var(--primary-foreground)' },
        secondary: { DEFAULT: 'var(--secondary)', foreground: 'var(--secondary-foreground)' },
        muted: { DEFAULT: 'var(--muted)', foreground: 'var(--muted-foreground)' },
        accent: { DEFAULT: 'var(--accent)', foreground: 'var(--accent-foreground)' },
        destructive: { DEFAULT: 'var(--destructive)', foreground: 'var(--destructive-foreground)' },
        border: 'var(--border)',
        input: 'var(--input)',
        ring: 'var(--ring)',
        success: { DEFAULT: 'var(--color-success)', foreground: 'var(--color-success-foreground)' },
        warning: { DEFAULT: 'var(--color-warning)', foreground: 'var(--color-warning-foreground)' },
        info: { DEFAULT: 'var(--color-info)', foreground: 'var(--color-info-foreground)' },
        'chart-1': 'var(--chart-1)',
        'chart-2': 'var(--chart-2)',
        'chart-3': 'var(--chart-3)',
        'chart-4': 'var(--chart-4)',
        'chart-5': 'var(--chart-5)'
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)'
      }
    }
  }
}
</script>"""

DARK_BOOTSTRAP_SCRIPT: str = """<script>
(function () {
  var stored = localStorage.getItem('darkMode');
  var dark = stored !== null ? stored === 'true' : window.matchMedia('(prefers-color-scheme: dark)').matches;
  if (dark) document.documentElement.classList.add('dark');
})();
</script>"""

THEME_BRIDGE_SCRIPT: str = """<script>
window.toggleTheme = function () {
  var dark = !document.documentElement.classList.contains('dark');
  document.documentElement.classList.toggle('dark', dark);
  localStorage.setItem('darkMode', String(dark));
  window.dispatchEvent(new CustomEvent('darkmode-change', { detail: { dark: dark } }));
};
</script>"""
