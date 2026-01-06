"""Phantom-import guard.

Admin source files must import UI symbols through `from lexigram.ui import X`
only — never `from lexigram.ui.atoms.button import Button` or similar deep
paths. This test scans every .py file under src/ and rejects forbidden patterns.
"""
from __future__ import annotations

import re
from pathlib import Path

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

ALLOWLIST: set[str] = {
    # Known deep-path imports — legacy, will be migrated over time.
    "lexigram/admin/controllers/dashboard.py",
    "lexigram/admin/controllers/resource.py",
    "lexigram/admin/dashboard/widgets.py",
    "lexigram/admin/forms/builder.py",
    "lexigram/admin/forms/components.py",
    "lexigram/admin/forms/fields/_advanced.py",
    "lexigram/admin/forms/fields/_text.py",
    "lexigram/admin/forms/layout.py",
    "lexigram/admin/forms/wizard.py",
    "lexigram/admin/middleware/error.py",
    "lexigram/admin/rbac/ui/permission_gate.py",
    "lexigram/admin/resources/detail_renderer.py",
    "lexigram/admin/resources/field_renderer.py",
    "lexigram/admin/resources/form_renderer.py",
    "lexigram/admin/resources/list_renderer.py",
    "lexigram/admin/settings/panel/layout.py",
    "lexigram/admin/settings/panel/ui.py",
    "lexigram/admin/ui/actions/base.py",
    "lexigram/admin/ui/actions/standard.py",
    "lexigram/admin/ui/columns/column/rendering.py",
    "lexigram/admin/ui/columns/types.py",
    "lexigram/admin/ui/debug.py",
    "lexigram/admin/ui/filters/types/selection.py",
    "lexigram/admin/ui/filters/types/standard.py",
    "lexigram/admin/ui/filters/types/toggle.py",
    "lexigram/admin/ui/htmx_attrs.py",
    "lexigram/admin/ui/layouts/__init__.py",
    "lexigram/admin/ui/layouts/admin_layout.py",
    "lexigram/admin/ui/layouts/components/__init__.py",
    "lexigram/admin/ui/layouts/standalone_layout.py",
    "lexigram/admin/ui/molecules/__init__.py",
    "lexigram/admin/ui/molecules/date_hierarchy.py",
    "lexigram/admin/ui/molecules/date_range_filter.py",
    "lexigram/admin/ui/molecules/debug_panel.py",
    "lexigram/admin/ui/molecules/filter_bar.py",
    "lexigram/admin/ui/molecules/filter_dropdown.py",
    "lexigram/admin/ui/molecules/inline_edit_cell.py",
    "lexigram/admin/ui/molecules/jump_to_page.py",
    "lexigram/admin/ui/molecules/layout_switcher.py",
    "lexigram/admin/ui/molecules/page_size_selector.py",
    "lexigram/admin/ui/molecules/pagination.py",
    "lexigram/admin/ui/molecules/pagination_links.py",
    "lexigram/admin/ui/molecules/search_bar.py",
    "lexigram/admin/ui/molecules/view_switcher.py",
    "lexigram/admin/ui/observability.py",
    "lexigram/admin/ui/organisms/bulk_edit_modal.py",
    "lexigram/admin/ui/organisms/command_palette.py",
    "lexigram/admin/ui/organisms/components.py",
    "lexigram/admin/ui/organisms/dashboard/widgets.py",
    "lexigram/admin/ui/organisms/dashboard/chart_widget.py",
    "lexigram/admin/ui/organisms/data_table/coordinator.py",
    "lexigram/admin/ui/organisms/data_table/layout.py",
    "lexigram/admin/ui/organisms/data_table/rendering.py",
    "lexigram/admin/ui/organisms/data_table/states.py",
    "lexigram/admin/ui/organisms/dynamic_form.py",
    "lexigram/admin/ui/organisms/filter_drawer.py",
    "lexigram/admin/ui/organisms/form_registry.py",
    "lexigram/admin/ui/organisms/live_polling.py",
    "lexigram/admin/ui/organisms/pagination.py",
    "lexigram/admin/ui/organisms/sidebar.py",
    "lexigram/admin/ui/organisms/simple_pagination.py",
    "lexigram/admin/ui/organisms/sortable_list.py",
    "lexigram/admin/ui/organisms/systembox.py",
    "lexigram/admin/ui/organisms/table/client_logic.py",
    "lexigram/admin/ui/organisms/table/toolbar.py",
    "lexigram/admin/ui/organisms/table/views/calendar.py",
    "lexigram/admin/ui/organisms/table/views/grid.py",
    "lexigram/admin/ui/organisms/table/views/stacked.py",
    "lexigram/admin/ui/organisms/table/views/tabular.py",
    "lexigram/admin/ui/organisms/task_progress.py",
    "lexigram/admin/ui/organisms/topbar.py",
    "lexigram/admin/ui/organisms/userbox.py",
    "lexigram/admin/ui/templates/shell.py",
    "lexigram/admin/views/_views.py",
}

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
    "tests/unit/ui/test_table_width_filament_style.py",
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
        if rel in ALLOWLIST:
            continue
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
