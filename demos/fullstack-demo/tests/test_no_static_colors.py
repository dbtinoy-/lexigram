"""Guard: the UI must stay fully theme-driven — no static color literals.

The only sanctioned exceptions are pipeline-mirror preview constants
(new_project.py phone mock) and JS fallback arguments (composer-preview.js).
Anything new must derive from the lexigram-ui ShadCN theme tokens.
"""

import re
from pathlib import Path

UI_ROOT = Path(__file__).resolve().parents[1] / "src/shorts_creator/ui"

CLASS_RE = re.compile(
    r"\b(?:bg|text|border|from|via|to|divide|accent|fill|stroke|ring|outline|shadow|placeholder|caret|decoration)"
    r"-(?:slate|indigo|purple|emerald|rose|amber|pink|sky|teal|yellow|red|blue|green|orange|violet|fuchsia|cyan|zinc|gray|grey|neutral|stone)-[0-9]{2,3}\b"
)
PLAIN_RE = re.compile(r"\b(?:bg|text|border)-(?:black|white)\b")
LITERAL_RE = re.compile(r"\brgba?\((?=[0-9])|\b0x[0-9A-Fa-f]{8}\b|#[0-9a-fA-F]{3,8}\b")

ALLOWED = {
    "pages/new_project.py": {
        "#7C5CFA",
        "rgba(0,0,0,0.75)",
    },
    "pages/new_project_preview.py": {
        "#fff",
        "#000",
        "#0a0a32",
        "rgba(",
        "0x000000C0",
    },
    "static/js/preview-render.js": {"0x7C5CFAFF", "#000"},
    "static/js/form-sync.js": {"0x7C5CFAFF", "0x000000C0"},
}


class TestNoStaticColors:
    def test_no_static_tailwind_color_classes(self):
        for path in sorted(UI_ROOT.rglob("*")):
            if "vendor" in path.parts:
                continue
            if path.suffix not in (".py", ".js", ".css"):
                continue
            text = path.read_text()
            rel = path.relative_to(UI_ROOT).as_posix()
            found = sorted(set(CLASS_RE.findall(text) + PLAIN_RE.findall(text)))
            assert not found, f"{rel}: static class colors: {found}"

    def test_no_hex_rgba_literals_outside_preview_mirrors(self):
        for path in sorted(UI_ROOT.rglob("*")):
            if "vendor" in path.parts:
                continue
            if path.suffix not in (".py", ".js", ".css"):
                continue
            text = path.read_text()
            rel = path.relative_to(UI_ROOT).as_posix()
            allowed = ALLOWED.get(rel, set())
            found = sorted(set(LITERAL_RE.findall(text)) - allowed)
            assert not found, f"{rel}: static color literals: {found}"
