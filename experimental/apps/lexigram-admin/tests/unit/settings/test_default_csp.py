"""Doc-03 regression tests: the default CSP is fully first-party.

Every asset the admin ships (htmx, Alpine, lucide, Sortable, Trix,
Tailwind build) is vendored under the static mount, so the default
Content-Security-Policy must not allow any third-party origin. Operators
who opt into external chart CDNs extend the CSP via the settings panel.
"""

from __future__ import annotations

from lexigram.admin.settings.panel.models import DEFAULT_CSP


class TestDefaultCsp:
    def test_no_third_party_origins(self) -> None:
        assert "unpkg.com" not in DEFAULT_CSP
        assert "jsdelivr" not in DEFAULT_CSP
        assert "https://" not in DEFAULT_CSP  # no external origin at all

    def test_core_directives_present(self) -> None:
        assert "default-src 'self'" in DEFAULT_CSP
        assert "script-src 'self'" in DEFAULT_CSP
        assert "style-src 'self'" in DEFAULT_CSP
        assert "connect-src 'self'" in DEFAULT_CSP
        assert "frame-ancestors 'none'" in DEFAULT_CSP

    def test_script_src_allows_eval_for_standard_alpine_build(self) -> None:
        """B14 regression: the vendored alpine.min.js is the STANDARD build.

        It compiles every directive expression through the AsyncFunction
        constructor (and htmx `hx-on-*` uses `new Function`), which CSP
        classifies as eval. Without 'unsafe-eval' every Alpine/htmx
        expression throws EvalError in enforcing browsers and the entire
        admin UI is dead. Do NOT remove this source until the Alpine
        CSP-build migration lands (docs/09-01-2026/14, "CSP v2").
        """
        directives = {
            d.strip().split(" ")[0]: d.strip()
            for d in DEFAULT_CSP.split(";")
            if d.strip()
        }
        assert "'unsafe-eval'" in directives["script-src"]
        # eval must stay scoped to script-src, never granted globally.
        assert "'unsafe-eval'" not in directives["default-src"]

    def test_hardening_directives_present(self) -> None:
        """R18: zero-cost hardening — no plugins, no <base>, same-origin forms."""
        assert "object-src 'none'" in DEFAULT_CSP
        assert "base-uri 'self'" in DEFAULT_CSP
        assert "form-action 'self'" in DEFAULT_CSP

    def test_security_headers_default_to_csp(self) -> None:
        from lexigram.admin.middleware.security_headers import (
            AdminSecurityHeaders,
        )

        headers = AdminSecurityHeaders().apply({})
        assert headers["Content-Security-Policy"] == DEFAULT_CSP
