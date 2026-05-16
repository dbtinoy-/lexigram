"""axe-core WCAG 2.2 AA scans against the component gallery."""

from __future__ import annotations

import pytest

AXE_CDN = "https://cdn.jsdelivr.net/npm/axe-core@4.10.2/axe.min.js"

WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]

# Every component in the gallery (kept in sync with tests/a11y/gallery.py).
GALLERY_NAMES = [
    "Alert", "Badge", "Button", "Card", "Checkbox", "Divider",
    "Dropdown", "Fieldset", "Form", "Icon", "InlineToast", "Label",
    "Layout", "Link", "Modal", "NumberInput", "Pagination",
    "PasswordInput", "ProgressBar", "Radio", "Select", "Skeleton",
    "SlideOver", "Spinner", "Switch", "Tabs", "TextArea", "TextInput",
    "Tooltip",
]

# Components known to fail interactive checks until hardened (Phase 3).
# This list MUST be empty by the end of Phase 3.
KNOWN_FAILURES: set[str] = set()


def _scan_violations(page: object, html: str) -> list[dict]:
    """Load axe-core and run a WCAG-tagged scan, returning violations."""
    page.set_content(html)  # type: ignore[attr-defined]
    page.add_script_tag(url=AXE_CDN)  # type: ignore[attr-defined]
    return page.evaluate(  # type: ignore[attr-defined]
        """() => window.axe.run(document, {
            runOnly: { type: 'tag', values: %s }
        }).then(r => r.violations)"""
        % repr(WCAG_TAGS)
    )


@pytest.mark.parametrize("name", GALLERY_NAMES)
def test_axe_wcag_light(page: object, gallery: dict[str, str], name: str) -> None:
    """No WCAG 2.2 AA violations in light theme."""
    if name in KNOWN_FAILURES:
        pytest.skip("hardened in Phase 3")
    violations = _scan_violations(page, gallery[name])
    assert not violations, (
        f"{name}: {len(violations)} WCAG AA violations: "
        + "; ".join(f"{v['id']}: {v['help']}" for v in violations[:5])
    )


@pytest.mark.parametrize(
    "name",
    ["Button", "Card", "Form", "Modal", "Select", "SlideOver", "Switch", "Tabs"],
)
def test_axe_wcag_dark(page: object, gallery: dict[str, str], name: str) -> None:
    """No WCAG violations in dark theme (contrast)."""
    html = gallery[name].replace(
        "</body>",
        '<script>document.documentElement.classList.add("dark")</script></body>',
    )
    violations = _scan_violations(page, html)
    assert not violations, (
        f"{name}: dark contrast violations: "
        + "; ".join(f"{v['id']}: {v['help']}" for v in violations[:5])
    )