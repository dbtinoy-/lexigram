from __future__ import annotations

from pathlib import Path

from dev.audit.generators.registry import build_audit_registry


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
        '"lexigram-vector", "lexigram-ui"]\n',
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

    admin_root = _write_package(root, "lexigram-admin")
    admin_src = admin_root / "src" / "lexigram" / "admin"
    admin_src.mkdir(parents=True)
    (admin_src / "__init__.py").write_text(
        "from __future__ import annotations\n\n\ndef build_admin() -> str:\n    return 'admin'\n",
        encoding="utf-8",
    )
    (admin_src / "relative_imports.py").write_text(
        "from __future__ import annotations\n\nfrom .helpers import helper\n",
        encoding="utf-8",
    )
    (admin_src / "helpers.py").write_text(
        "from __future__ import annotations\n\n\ndef helper() -> str:\n    return 'ok'\n",
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

    vector_root = _write_package(root, "lexigram-vector")
    (vector_root / "README.md").write_text("placeholder\n", encoding="utf-8")



def test_rules_generator_is_registered_and_writes_expected_sections(tmp_path: Path) -> None:
    _write_sample_workspace(tmp_path)

    registry = build_audit_registry()
    generator = registry.get("rules")

    assert generator is not None
    result = generator.run(root=tmp_path)
    markdown = (tmp_path / "docs/lexigram-docs/audit" / "AUDIT_RULES.md").read_text(encoding="utf-8")

    assert result.success is True
    assert "## Severity Summary" in markdown
    assert "| Severity | Count |" in markdown
    assert "critical" in markdown.lower()
    assert "important" in markdown.lower()
    assert "minor" in markdown.lower()
    assert "## Findings" in markdown
    assert "| File | Line | Rule ID | Severity | Message |" in markdown
    assert "init-no-logic" in markdown
    assert "import-absolute-only" in markdown
    assert "no-cross-extension-import" in markdown
    assert "python-syntax-error" in markdown
    assert "core lexigram directly imports lexigram-cache" in markdown
    assert "## Rule Diagnostics" in markdown
    assert "| Rule ID | Severity | Findings | Detected Error About |" in markdown
    assert "## Package Coverage" in markdown
    assert "lexigram-vector" in markdown
    assert "## Resolution Guide" in markdown
    assert "`no-cross-extension-import`" in markdown
