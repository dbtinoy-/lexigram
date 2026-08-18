from __future__ import annotations

from pathlib import Path

from dev.core.rule_engine import RuleSeverity, run_rules


def _write_package(root: Path, name: str) -> Path:
    package_root = root / name
    package_root.mkdir()
    (package_root / "pyproject.toml").write_text(
        f'[project]\nname = "{name}"\n',
        encoding="utf-8",
    )
    return package_root


def _write_sample_workspace(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        '[project]\nname = "workspace"\n\n[tool.uv.workspace]\n'
        'members = ["lexigram", "lexigram-admin", "lexigram-auth", "lexigram-cache", '
        '"lexigram-ui", "lexigram-vector"]\n',
        encoding="utf-8",
    )

    core_root = _write_package(root, "lexigram")
    core_src = core_root / "src" / "lexigram"
    core_src.mkdir(parents=True)
    (core_src / "__init__.py").write_text("", encoding="utf-8")
    (core_src / "forbidden_extension_import.py").write_text(
        "from __future__ import annotations\n\nfrom lexigram.cache.backend import CacheBackend\n",
        encoding="utf-8",
    )

    _write_package(root, "lexigram-ui")
    _write_package(root, "lexigram-vector")

    admin_root = _write_package(root, "lexigram-admin")
    admin_src = admin_root / "src" / "lexigram" / "admin"
    admin_src.mkdir(parents=True)
    (admin_src / "__init__.py").write_text(
        "from __future__ import annotations\n\n\ndef build_admin() -> str:\n    return 'admin'\n",
        encoding="utf-8",
    )
    (admin_src / "helpers.py").write_text(
        "from __future__ import annotations\n\n\ndef helper() -> str:\n    return 'ok'\n",
        encoding="utf-8",
    )
    (admin_src / "relative_imports.py").write_text(
        "from __future__ import annotations\n\nfrom .helpers import helper\n",
        encoding="utf-8",
    )
    (admin_src / "allowed_import.py").write_text(
        "from __future__ import annotations\n\nfrom lexigram.ui.components import Button\n",
        encoding="utf-8",
    )

    ui_src = root / "lexigram-ui" / "src" / "lexigram" / "ui"
    ui_src.mkdir(parents=True)
    (ui_src / "__init__.py").write_text("", encoding="utf-8")
    (ui_src / "components.py").write_text(
        "from __future__ import annotations\n\nclass Button:\n    pass\n",
        encoding="utf-8",
    )

    auth_root = _write_package(root, "lexigram-auth")
    auth_src = auth_root / "src" / "lexigram" / "auth"
    auth_src.mkdir(parents=True)
    (auth_src / "__init__.py").write_text("", encoding="utf-8")
    (auth_src / "cross_import.py").write_text(
        "from __future__ import annotations\n\nfrom lexigram.cache.backend import CacheBackend\n",
        encoding="utf-8",
    )
    (auth_src / "pseudo_enum.py").write_text(
        "from __future__ import annotations\n\nclass Role:\n    ADMIN = 'admin'\n    USER = 'user'\n",
        encoding="utf-8",
    )
    (auth_src / "broken_syntax.py").write_text(
        "from __future__ import annotations\n\nif True print('boom')\n",
        encoding="utf-8",
    )

    cache_root = _write_package(root, "lexigram-cache")
    cache_src = cache_root / "src" / "lexigram" / "cache"
    cache_src.mkdir(parents=True)
    (cache_src / "__init__.py").write_text("", encoding="utf-8")
    (cache_src / "backend.py").write_text(
        "from __future__ import annotations\n\nclass CacheBackend:\n    pass\n",
        encoding="utf-8",
    )



def test_run_rules_detects_expected_findings_and_coverage(tmp_path: Path) -> None:
    _write_sample_workspace(tmp_path)

    result = run_rules(tmp_path)
    findings_by_rule = {finding.rule_id: finding for finding in result.findings}
    cross_import_findings = [
        finding for finding in result.findings if finding.rule_id == "no-cross-extension-import"
    ]

    assert result.coverage.missing_packages == frozenset({"lexigram-vector"})
    assert result.coverage.success is False
    assert findings_by_rule["init-no-logic"].severity is RuleSeverity.IMPORTANT
    assert findings_by_rule["init-no-logic"].line == 4
    assert findings_by_rule["import-absolute-only"].severity is RuleSeverity.IMPORTANT
    assert findings_by_rule["import-absolute-only"].line == 3
    assert cross_import_findings[0].severity is RuleSeverity.CRITICAL
    assert any("lexigram-auth directly imports lexigram-cache" in finding.message for finding in cross_import_findings)
    assert any("core lexigram directly imports lexigram-cache" in finding.message for finding in cross_import_findings)
    assert findings_by_rule["enum-must-use-enum"].severity is RuleSeverity.MINOR
    assert findings_by_rule["enum-must-use-enum"].line == 3
    assert findings_by_rule["python-syntax-error"].severity is RuleSeverity.IMPORTANT
    assert findings_by_rule["python-syntax-error"].path.as_posix().endswith("broken_syntax.py")
    assert findings_by_rule["python-syntax-error"].line == 3



def test_run_rules_allows_documented_cross_extension_exceptions(tmp_path: Path) -> None:
    _write_sample_workspace(tmp_path)

    result = run_rules(tmp_path)

    assert not any(
        finding.path.as_posix().endswith("allowed_import.py")
        and finding.rule_id == "no-cross-extension-import"
        for finding in result.findings
    )
