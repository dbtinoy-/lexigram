"""CSP promotion analysis (R48, docs/09-01-2026/44-csp-enforcement-flip.md).

Pure helpers behind the Enforcement card on the CSP tab: parse a policy
string and flag candidate directives that are known — from the doc 14
audit of the stock admin front-end — to break the bundled UI when
enforced. No I/O, no framework imports.
"""

from __future__ import annotations

__all__ = ["parse_directives", "ui_compat_blockers"]


def parse_directives(policy: str) -> dict[str, list[str]]:
    """Split a CSP policy string into a directive → sources mapping.

    Tolerant by design: empty segments and stray whitespace are ignored,
    directive names are lower-cased, duplicate directives keep the first
    occurrence (matching browser behaviour).

    Args:
        policy: Raw ``Content-Security-Policy`` value.

    Returns:
        Mapping like ``{"script-src": ["'self'", "'unsafe-eval'"]}``.
    """
    directives: dict[str, list[str]] = {}
    for segment in (policy or "").split(";"):
        parts = segment.split()
        if not parts:
            continue
        name = parts[0].lower()
        if name not in directives:
            directives[name] = parts[1:]
    return directives


def _effective_sources(directives: dict[str, list[str]], name: str) -> list[str] | None:
    """Sources for a fetch directive, honouring the default-src fallback.

    Returns ``None`` when neither the directive nor ``default-src`` is
    present (the browser applies no restriction, so nothing can break).
    """
    if name in directives:
        return directives[name]
    return directives.get("default-src")


def ui_compat_blockers(policy: str) -> list[str]:
    """Plain-language reasons enforcing ``policy`` breaks the stock UI.

    Deterministic, code-level knowledge from the doc 14 audit of the
    vendored front-end assets — not a heuristic:

    - the vendored ``alpine.min.js`` is the *standard* build, which
      compiles every directive expression through the ``Function``
      constructor → ``script-src`` needs ``'unsafe-eval'``;
    - the shell ships inline ``<script>`` blocks (Alpine component
      registrations, theme boot) and ``hx-on`` handlers → ``script-src``
      needs ``'unsafe-inline'``;
    - sticky-column offsets and dynamic widths are inline ``style=``
      attributes → ``style-src`` needs ``'unsafe-inline'``.

    Args:
        policy: Candidate policy string.

    Returns:
        Empty list when the candidate is compatible with the bundled
        UI; otherwise one human-readable blocker per missing keyword.
    """
    directives = parse_directives(policy)
    blockers: list[str] = []

    scripts = _effective_sources(directives, "script-src")
    if scripts is not None:
        if "'unsafe-eval'" not in scripts:
            blockers.append(
                "script-src lacks 'unsafe-eval' — the bundled Alpine.js "
                "(standard build) compiles every directive through the "
                "Function constructor, so all interactivity (sidebar, "
                "dropdowns, command palette, theme toggle) would throw "
                "EvalError."
            )
        if "'unsafe-inline'" not in scripts and not any(
            s.startswith(("'nonce-", "'sha256-", "'sha384-", "'sha512-"))
            for s in scripts
        ):
            blockers.append(
                "script-src lacks 'unsafe-inline' (and no nonce/hash "
                "sources) — the admin shell ships inline <script> blocks "
                "(Alpine registrations, theme boot) and htmx hx-on "
                "handlers that would be blocked."
            )

    styles = _effective_sources(directives, "style-src")
    if (
        styles is not None
        and "'unsafe-inline'" not in styles
        and not any(
            s.startswith(("'nonce-", "'sha256-", "'sha384-", "'sha512-"))
            for s in styles
        )
    ):
        blockers.append(
            "style-src lacks 'unsafe-inline' — inline style attributes "
            "(sticky column offsets, dynamic widths) and <style> blocks "
            "would be stripped."
        )
    return blockers
