"""Schema smoke test for data/e2e_matrix.yaml (composition E2E matrix)."""

from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MATRIX = _REPO_ROOT / "data" / "e2e_matrix.yaml"


def _load_matrix() -> dict:
    return yaml.safe_load(_MATRIX.read_text())


def test_matrix_has_top_level_schema():
    matrix = _load_matrix()
    assert matrix["project"]
    assert isinstance(matrix["ideas"], list) and matrix["ideas"]
    assert isinstance(matrix["timeout_s"], (int, float)) and matrix["timeout_s"] > 0
    assert isinstance(matrix["combos"], list) and matrix["combos"]


def test_every_combo_has_name_compose_and_idea_index():
    matrix = _load_matrix()
    for combo in matrix["combos"]:
        assert combo.get("name"), "combo missing name"
        assert isinstance(combo.get("compose"), dict), f"{combo.get('name')} missing compose"
        assert combo["compose"].get("format"), f"{combo.get('name')} missing compose.format"
        assert isinstance(combo.get("idea_index"), int), f"{combo.get('name')} missing idea_index"


def test_combo_idea_indices_are_in_matrix_ideas():
    matrix = _load_matrix()
    for combo in matrix["combos"]:
        assert combo["idea_index"] >= 0
        assert combo["idea_index"] in matrix["ideas"], (
            f"combo {combo['name']} references idea_index {combo['idea_index']} "
            f"outside the matrix ideas {matrix['ideas']}"
        )
