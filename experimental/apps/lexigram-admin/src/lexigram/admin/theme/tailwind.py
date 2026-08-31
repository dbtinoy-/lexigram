from __future__ import annotations

"""Shared Tailwind CSS runtime scripts for admin layouts.

Bootstrap scripts for the ``dark`` class on ``<html>`` before Alpine.js
loads. The Tailwind utility stylesheet itself is prebuilt statically
(see ``tailwind/build.sh``) and referenced via ``admin/static/css/tailwind.css``.
"""

DARK_BOOTSTRAP_SCRIPT: str = """<script>
(function () {
  var stored = localStorage.getItem('darkMode');
  var dark = stored !== null ? stored === 'true' : window.matchMedia('(prefers-color-scheme: dark)').matches;
  if (dark) document.documentElement.classList.add('dark');
  // Marks scripting as available before first paint so progressively
  // enhanced controls can hide their no-JS fallbacks without a flash.
  // Set here rather than on load: a control whose fallback disappears
  // after the page is interactive would visibly shift.
  document.documentElement.classList.add('js');
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
