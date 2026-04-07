from lexigram.admin.ui.organisms.table.client_logic import (
    DataTableScriptRenderer,
)


def test_update_active_filters_script_checks_control_values():
    script_node = DataTableScriptRenderer.render([])
    js_text = str(script_node)

    # Ensure the updateActiveFiltersState function now checks for checkbox/radio checked state
    assert "type === 'checkbox'" in js_text or 'type === "checkbox"' in js_text
    assert "ctrl.value" in js_text
    # Also ensure SELECT controls are specifically checked for non-empty value
    assert "tag === 'SELECT'" in js_text or 'tag === "SELECT"' in js_text
