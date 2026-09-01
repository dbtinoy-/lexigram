#!/usr/bin/env python3
"""Generate the semantic-colour opacity utilities admin.css needs.

Tailwind cannot emit slash-opacity utilities (``bg-card/80``) for colours
defined as bare custom properties. The modifier needs raw channels to build
an ``rgb(... / <alpha>)`` value, and ``var(--card)`` is opaque to the
compiler, so the prebuilt bundle simply contains no rule for them. Class
names like ``bg-destructive/10`` then match nothing and render as no colour
at all.

This app also has no Tailwind build step -- the ``tailwind/build.sh``
referenced in ``theme/tailwind.py`` does not exist -- so the committed
``tailwind.css`` is the complete set of available classes and cannot be
regenerated from source. Rather than rewrite ~100 call sites to a
dash-spelled workaround, this script scans the source for slash-opacity
classes and emits matching ``color-mix`` rules, mirroring the form the
bundle already uses for its few dash-named equivalents (``.bg-muted-50``).

Usage::

    uv run python dev/generators/admin_opacity_utilities.py
    uv run python dev/generators/admin_opacity_utilities.py --check

``--check`` exits non-zero when the generated block is stale, which is what
CI and ``tests/unit/ui/test_design_tokens.py`` rely on.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = ROOT / "experimental/apps/lexigram-admin"
SRC = APP_ROOT / "src/lexigram/admin"
CSS_DIR = SRC / "static/css"
ADMIN_CSS = CSS_DIR / "admin.css"
TAILWIND_CSS = CSS_DIR / "tailwind.css"

BEGIN = "/* BEGIN generated: semantic colour opacity utilities */"
END = "/* END generated: semantic colour opacity utilities */"

#: Utility prefix -> the CSS property it sets.
PROPERTIES = {
    "bg": "background-color",
    "text": "color",
    "border": "border-color",
    "ring": "--tw-ring-color",
    "fill": "fill",
    "stroke": "stroke",
    "divide": "border-color",
    "placeholder": "color",
    "outline": "outline-color",
}

#: Semantic colour tokens. Longer names first so `muted-foreground` is not
#: matched as `muted` followed by a stray suffix.
TOKENS = (
    "muted-foreground",
    "card-foreground",
    "primary-foreground",
    "background",
    "foreground",
    "card",
    "popover",
    "primary",
    "secondary",
    "muted",
    "accent",
    "destructive",
    "border",
    "input",
    "ring",
    "success",
    "warning",
    "info",
)

#: Variants that need a differently shaped selector.
VARIANTS = (
    "hover",
    "focus",
    "focus-visible",
    "focus-within",
    "active",
    "disabled",
    "dark",
    "group-hover",
)

_BARE = re.compile(
    rf"\b((?:{'|'.join(PROPERTIES)})-(?:{'|'.join(TOKENS)})/\d{{1,3}})\b"
)
_VARIANT = re.compile(
    rf"\b((?:{'|'.join(VARIANTS)})):"
    rf"((?:{'|'.join(PROPERTIES)})-(?:{'|'.join(TOKENS)})/\d{{1,3}})\b"
)


def _css_var(token: str) -> str:
    """Return the custom property backing a token.

    Status colours are published by the shared UI library under a
    ``--color-`` prefix while the neutral palette is not.
    """
    if token in {"success", "warning", "info"}:
        return f"--color-{token}"
    return f"--{token}"


def _split(utility: str) -> tuple[str, str, str]:
    """Split ``bg-muted-foreground/40`` into prefix, token, percentage."""
    base, _, percent = utility.rpartition("/")
    prefix, _, token = base.partition("-")
    return prefix, token, percent


def _escape(selector: str) -> str:
    return selector.replace("/", r"\/").replace(":", r"\:")


def _existing_classes() -> set[str]:
    """Classes already provided by the prebuilt bundle."""
    css = TAILWIND_CSS.read_text(encoding="utf-8")
    return {
        match.replace("\\", "")
        for match in re.findall(r"\.((?:[a-zA-Z0-9_/:.-]|\\.)+?)(?=[{,:>~+\s])", css)
    }


def _scan() -> tuple[set[str], set[tuple[str, str]]]:
    """Return slash-opacity utilities used in source but absent from the bundle."""
    available = _existing_classes()
    bare: set[str] = set()
    variants: set[tuple[str, str]] = set()

    for path in sorted(SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for utility in _BARE.findall(text):
            if utility not in available:
                bare.add(utility)
        for variant, utility in _VARIANT.findall(text):
            if f"{variant}:{utility}" not in available:
                variants.add((variant, utility))

    # A variant implies nothing about the base class, and vice versa; keep
    # them independent so `hover:bg-card/80` alone still emits a rule.
    return bare, variants


def _rule(selector: str, prefix: str, token: str, percent: str) -> str:
    value = f"color-mix(in oklab,var({_css_var(token)}) {percent}%,transparent)"
    return f"{selector}{{{PROPERTIES[prefix]}:{value}}}"


def render() -> str:
    """Build the generated block."""
    bare, variants = _scan()
    lines = [BEGIN]
    lines.append(
        "/* Generated by dev/generators/admin_opacity_utilities.py -- do not"
        " edit by hand. */"
    )

    for utility in sorted(bare):
        prefix, token, percent = _split(utility)
        lines.append(_rule(f".{_escape(utility)}", prefix, token, percent))

    for variant, utility in sorted(variants):
        prefix, token, percent = _split(utility)
        name = _escape(f"{variant}:{utility}")
        if variant == "dark":
            # Match both a descendant of .dark and .dark itself carrying it.
            selector = f".dark .{name},.dark.{name}"
        elif variant == "group-hover":
            selector = f".group:hover .{name}"
        else:
            selector = f".{name}:{variant}"
        lines.append(_rule(selector, prefix, token, percent))

    lines.append(END)
    return "\n".join(lines) + "\n"


def _replace_block(css: str, block: str) -> str:
    if BEGIN in css and END in css:
        start = css.index(BEGIN)
        end = css.index(END) + len(END) + 1
        return css[:start] + block + css[end:]
    return css.rstrip("\n") + "\n\n" + block


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if admin.css is out of date instead of writing.",
    )
    args = parser.parse_args()

    css = ADMIN_CSS.read_text(encoding="utf-8")
    updated = _replace_block(css, render())

    if args.check:
        if updated != css:
            print(
                "admin.css opacity utilities are stale. Run:\n"
                "  uv run python dev/generators/admin_opacity_utilities.py",
                file=sys.stderr,
            )
            return 1
        print("admin.css opacity utilities are up to date.")
        return 0

    if updated != css:
        ADMIN_CSS.write_text(updated, encoding="utf-8")
        print(f"Updated {ADMIN_CSS.relative_to(ROOT)}")
    else:
        print("No changes needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
