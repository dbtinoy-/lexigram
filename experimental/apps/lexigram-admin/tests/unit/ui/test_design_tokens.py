"""Every CSS custom property the admin renders against must be defined.

The prebuilt tailwind.css compiles semantic utilities into variable
references (``.bg-muted { background-color: var(--muted) }``) but ships no
definitions for them. Only tailwind.css and admin.css are linked by the
layouts, so a token defined in neither resolves to nothing.

An undefined ``var()`` is not a no-op: the declaration becomes invalid at
computed-value time, so ``background-color`` and ``border-color`` fall back
to their initial values and inherited properties like ``color`` fall through
to the parent. A missing token therefore silently removes colour rather than
raising anything, which is exactly the kind of regression a test has to
catch.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_CSS_DIR = (
    Path(__file__).resolve().parents[3]
    / "src/lexigram/admin/static/css"
)
_STYLESHEETS = ("tailwind.css", "admin.css")

#: Tailwind's own internal plumbing, which it defines itself at use sites.
_INTERNAL_PREFIX = "--tw-"

#: Deliberately theme-independent: the documented light and dark values for
#: these are identical, so redeclaring them under .dark would be noise.
_THEME_INDEPENDENT = {
    "--radius",
    "--chart-1",
    "--chart-2",
    "--chart-3",
    "--chart-4",
    "--chart-5",
}


def _read(name: str) -> str:
    return (_CSS_DIR / name).read_text(encoding="utf-8")


def _all_css() -> str:
    return "\n".join(_read(name) for name in _STYLESHEETS)


def _referenced(css: str) -> set[str]:
    return {
        token
        for token in re.findall(r"var\((--[a-z0-9-]+)", css)
        if not token.startswith(_INTERNAL_PREFIX)
    }


def _defined(css: str) -> set[str]:
    return {
        token
        for token in re.findall(r"(--[a-z0-9-]+)\s*:", css)
        if not token.startswith(_INTERNAL_PREFIX)
    }


def _block(css: str, selector: str) -> str:
    """Return the body of the first top-level ``selector`` block."""
    match = re.search(
        rf"(?:^|\n){re.escape(selector)}\s*\{{(.*?)\n\}}", css, re.S
    )
    assert match is not None, f"no {selector} block found in admin.css"
    return match.group(1)


class TestTokenResolution:
    def test_stylesheets_exist(self) -> None:
        for name in _STYLESHEETS:
            assert (_CSS_DIR / name).is_file(), f"{name} is not shipped"

    def test_every_referenced_token_is_defined(self) -> None:
        """The bug this file exists for: 31 semantic tokens were referenced
        by the compiled utilities and defined nowhere, so backgrounds,
        borders, and text colour collapsed across the admin.

        Resolution is checked against the unconditional scopes only. A token
        defined solely under ``.dark`` is still undefined in light mode, so
        counting it as resolved would hide exactly half of this bug.
        """
        css = _all_css()
        unconditional = _defined(_block(_read("admin.css"), ":root"))
        # :root appears twice (tokens, then the admin-specific layout vars).
        for extra in re.findall(r"(?:^|\n):root\s*\{(.*?)\n\}", css, re.S):
            unconditional |= _defined(extra)

        undefined = sorted(_referenced(css) - unconditional)

        assert not undefined, (
            "CSS variables are used but never defined outside .dark, so "
            f"these utilities render with no colour in light mode: {undefined}"
        )

    @pytest.mark.parametrize(
        "token",
        [
            "--background",
            "--foreground",
            "--card",
            "--muted",
            "--muted-foreground",
            "--accent",
            "--border",
            "--input",
            "--ring",
            "--primary",
            "--destructive",
        ],
    )
    def test_core_semantic_tokens_are_defined(self, token: str) -> None:
        """These back the utilities used most across admin templates."""
        assert token in _defined(_all_css())


class TestDarkMode:
    """The dark class must actually have something to switch."""

    def test_dark_block_exists(self) -> None:
        assert _block(_read("admin.css"), ".dark").strip()

    def test_dark_overrides_every_themed_token(self) -> None:
        """A token defined only in :root keeps its light value in dark mode,
        which is how light-on-light text happens."""
        admin_css = _read("admin.css")
        light = _defined(_block(admin_css, ":root"))
        dark = _defined(_block(admin_css, ".dark"))

        themed = {
            token
            for token in light
            if not token.startswith("--admin-")
            and token not in _THEME_INDEPENDENT
        }

        assert not sorted(themed - dark), (
            "these tokens have no dark-mode value: "
            f"{sorted(themed - dark)}"
        )

    def test_dark_defines_no_orphan_tokens(self) -> None:
        """A token in .dark with no :root counterpart is undefined in light
        mode -- the same collapse, only harder to notice."""
        admin_css = _read("admin.css")
        light = _defined(_block(admin_css, ":root"))
        dark = _defined(_block(admin_css, ".dark"))

        orphans = {
            token for token in dark - light if not token.startswith("--admin-")
        }

        assert not sorted(orphans), f"only defined under .dark: {sorted(orphans)}"


class TestStatusColours:
    """Status colours must be tokens, not raw palette values."""

    def test_success_warning_info_tokens_exist(self) -> None:
        defined = _defined(_all_css())

        for token in ("--color-success", "--color-warning", "--color-info"):
            assert token in defined
            assert f"{token}-foreground" in defined

    def test_status_tokens_are_theme_aware(self) -> None:
        """A status colour picked for a light background is usually wrong on
        a dark one."""
        dark = _defined(_block(_read("admin.css"), ".dark"))

        for token in ("--color-success", "--color-warning", "--color-info"):
            assert token in dark


class TestUtilityClassesExist:
    """Tailwind is prebuilt, so a class not in the bundle simply does nothing.

    There is no build step wired into this app -- ``tailwind/build.sh`` named
    in theme/tailwind.py does not exist -- so the committed tailwind.css is
    the whole universe of available classes. A hand-written arbitrary value
    like ``text-[11px]`` looks correct in review and renders as nothing.
    """

    _SRC = Path(__file__).resolve().parents[3] / "src/lexigram/admin"

    #: Utilities that carry a colour or size and so must resolve to a rule.
    _ARBITRARY = re.compile(
        r"(?<![\w-])((?:bg|text|border|ring|fill|stroke|shadow)"
        r"-\[[^\]\s\"']+\])"
    )

    def _compiled(self) -> str:
        return _read("tailwind.css")

    def test_no_arbitrary_classes_missing_from_the_bundle(self) -> None:
        compiled = self._compiled()
        missing: dict[str, str] = {}

        for path in sorted(self._SRC.rglob("*.py")):
            text = path.read_text(encoding="utf-8", errors="ignore")
            for cls in self._ARBITRARY.findall(text):
                escaped = re.escape(cls).replace("/", r"\\/")
                if not re.search(rf"\.{escaped}[{{:,]", compiled):
                    missing.setdefault(cls, str(path.relative_to(self._SRC)))

        assert not missing, (
            "these arbitrary Tailwind classes are not in the prebuilt "
            f"tailwind.css and render as nothing: {missing}"
        )
