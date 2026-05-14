"""Tests for the optional-imports audit generator."""

from __future__ import annotations

from pathlib import Path


def _write_workspace(root: Path) -> None:
    (root / "pyproject.toml").write_text('[project]\nname = "workspace"\n', encoding="utf-8")
    package_dir = root / "lexigram-demo"
    package_dir.mkdir()
    (package_dir / "pyproject.toml").write_text(
        '[project]\nname = "lexigram-demo"\ndependencies = ["rich"]\n'
        '[project.optional-dependencies]\nextra = ["requests"]\n',
        encoding="utf-8",
    )
    src = package_dir / "src" / "lexigram_demo"
    src.mkdir(parents=True)

    (src / "declared.py").write_text(
        "from rich import print\n\n"
        "try:\n    import requests\nexcept ImportError:\n    pass\n\n"
        "try:\n    import yaml\nexcept ImportError:\n    pass\n",
        encoding="utf-8",
    )
    (src / "violation.py").write_text(
        "import yaml  # optional-only and unguarded\n",
        encoding="utf-8",
    )
    (src / "type_checking.py").write_text(
        "from typing import TYPE_CHECKING\n\nif TYPE_CHECKING:\n    import strawberry\n",
        encoding="utf-8",
    )


def test_optional_imports_generator_flags_unguarded_optional_import(tmp_path: Path) -> None:
    from scripts.audit.generators.optional_imports import OptionalImportsAuditGenerator

    _write_workspace(tmp_path)

    generator = OptionalImportsAuditGenerator()
    result = generator.run(root=tmp_path, all_mode=True)
    markdown = (tmp_path / "AUDIT_OPTIONAL_IMPORTS.md").read_text(encoding="utf-8")

    assert result.success is False
    assert result.message.startswith("1 violation(s)")
    assert "## Summary" in markdown
    assert "violation.py" in markdown
    assert "yaml" in markdown


def test_optional_imports_generator_ignores_guarded_and_type_checking_imports(
    tmp_path: Path,
) -> None:
    from scripts.audit.generators.optional_imports import OptionalImportsAuditGenerator

    _write_workspace(tmp_path)
    (tmp_path / "lexigram-demo" / "src" / "lexigram_demo" / "violation.py").unlink()

    generator = OptionalImportsAuditGenerator()
    result = generator.run(root=tmp_path, all_mode=True)

    assert result.success is True
    assert "violation" not in (tmp_path / "AUDIT_OPTIONAL_IMPORTS.md").read_text(
        encoding="utf-8"
    )
