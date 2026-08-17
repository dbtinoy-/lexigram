"""Phantom-import guard.

Admin source files must import UI symbols through `from lexigram.ui import X`
only — never `from lexigram.ui.atoms.button import Button` or similar deep
paths. This test scans every .py file under src/ and rejects forbidden patterns.
"""
from __future__ import annotations

from pathlib import Path
import re

FORBIDDEN_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^from lexigram\.ui\.atoms[\.\s]", re.MULTILINE),
    re.compile(r"^from lexigram\.ui\.molecules[\.\s]", re.MULTILINE),
    re.compile(r"^from lexigram\.ui\.organisms[\.\s]", re.MULTILINE),
    re.compile(r"^from lexigram\.ui\.layouts[\.\s]", re.MULTILINE),
    re.compile(r"^from lexigram\.ui\.htmx[\.\s]", re.MULTILINE),
    re.compile(r"^from lexigram\.ui\.monitoring[\.\s]", re.MULTILINE),
    re.compile(r"^from lexigram\.ui\.performance[\.\s]", re.MULTILINE),
    re.compile(r"^from lexigram\.ui\.config\s+import", re.MULTILINE),
    re.compile(r"^from lexigram\.ui\.core[\.\s]", re.MULTILINE),
    re.compile(r"^from lexigram\.ui\.exceptions\s+import", re.MULTILINE),
    re.compile(r"^from lexigram\.ui\.accessibility[\.\s]", re.MULTILINE),
]

ADMIN_SRC = Path(__file__).resolve().parents[2] / "src"

# Test files with known deep-path imports. These should be migrated to
# use the public API over time.
TEST_ALLOWLIST: set[str] = {
    "tests/unit/test_htmx_perf.py",
    "tests/unit/test_overlays.py",
    "tests/unit/test_shell_system_menu_presence.py",
    "tests/unit/test_system_menu.py",
    "tests/unit/test_system_menu_dynamic_render.py",
    "tests/unit/test_systembox.py",
    "tests/unit/test_systembox_rbac.py",
    "tests/unit/test_userbox_extraction.py",
    "tests/unit/ui/test_accessibility.py",
    "tests/unit/ui/test_action_button.py",
    "tests/unit/ui/test_admin_observability.py",
    "tests/unit/ui/test_alert.py",
    "tests/unit/ui/test_atoms.py",
    "tests/unit/ui/test_button.py",
    "tests/unit/ui/test_columns_copyable.py",
    "tests/unit/ui/test_data_table.py",
    "tests/unit/ui/test_data_table_bulk.py",
    "tests/unit/ui/test_table_control_fragments.py",
    "tests/unit/ui/test_data_table_grouping.py",
    "tests/unit/ui/test_data_table_more.py",
    "tests/unit/ui/test_data_table_pagination_and_bulk.py",
    "tests/unit/ui/test_debug_panel_clear_state.py",
    "tests/unit/ui/test_divider.py",
    "tests/unit/ui/test_errors.py",
    "tests/unit/ui/test_filter_bar.py",
    "tests/unit/ui/test_form_actions.py",
    "tests/unit/ui/test_forms.py",
    "tests/unit/ui/test_header_toggle.py",
    "tests/unit/ui/test_htmx_attrs.py",
    "tests/unit/ui/test_icon.py",
    "tests/unit/ui/test_link.py",
    "tests/unit/ui/test_overlays_footer_sticky.py",
    "tests/unit/ui/test_pagination.py",
    "tests/unit/ui/test_pagination_more.py",
    "tests/unit/ui/test_performance.py",
    "tests/unit/ui/test_searchbar.py",
    "tests/unit/ui/test_section.py",
    "tests/unit/ui/test_slide_over.py",
    "tests/unit/ui/test_table_width_style.py",
    "tests/unit/ui/test_task_progress_retry.py",
    "tests/unit/ui/test_toggle.py",
    "tests/unit/ui/test_zones.py",
}


def _python_files(root: Path) -> list[Path]:
    return [p for p in root.rglob("*.py") if "__pycache__" not in p.parts]


def test_no_deep_path_ui_imports_in_admin_source() -> None:
    assert ADMIN_SRC.exists(), f"Expected src/ at {ADMIN_SRC}"

    offenders: list[tuple[Path, str]] = []
    for path in sorted(ADMIN_SRC.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = str(path.relative_to(ADMIN_SRC))
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            for match in pattern.finditer(text):
                offenders.append((Path(rel), match.group(0).strip()))

    if offenders:
        lines = [f"  {p}: {imp}" for p, imp in sorted(set(offenders))]
        msg = (
            "Deep-path imports into lexigram.ui internals are forbidden.\n"
            "Use `from lexigram.ui import X` instead. If a symbol is missing\n"
            "from `lexigram.ui`, add it to lexigram-ui's `_LAZY_IMPORTS`.\n"
            "\nOffending imports:\n" + "\n".join(lines)
        )
        raise AssertionError(msg)


def test_no_phantom_symbols_in_admin_tests() -> None:
    admin_tests = Path(__file__).resolve().parents[1]
    offenders: list[tuple[Path, str]] = []
    for path in _python_files(admin_tests):
        if str(path.relative_to(admin_tests.parent)) in TEST_ALLOWLIST:
            continue
        if path.name == "test_phantom_imports.py":
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_PATTERNS:
            for match in pattern.finditer(text):
                offenders.append((path.relative_to(admin_tests.parent), match.group(0).strip()))

    if offenders:
        lines = [f"  {p}: {imp}" for p, imp in sorted(set(offenders))]
        msg = (
            "Test files contain deep-path imports into lexigram.ui internals.\n"
            "Use `from lexigram.ui import X` unless you're specifically testing\n"
            "the internal module path.\n"
            "\nOffending imports:\n" + "\n".join(lines)
        )
        raise AssertionError(msg)
