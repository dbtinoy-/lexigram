from __future__ import annotations

from pathlib import Path

import pytest

from scripts.audit.generators import build_audit_registry
from scripts.audit.generators.base import AuditGeneratorProtocol
from scripts.core.context import resolve_workspace_root
from scripts.core.models import AuditReport
from scripts.core.registry import GeneratorRegistry

EXPECTED_GENERATOR_NAMES = (
    "docs-claims",
    "docs-defaults",
    "docs-imports",
    "docs-links",
    "env_vars",
    "index",
    "integrations",
    "optional-imports",
    "overview",
    "protocols",
    "quality",
    "rules",
    "security",
    "tests",
)


def test_resolve_workspace_root_returns_monorepo_root_from_nested_package(
    tmp_path: Path,
) -> None:
    root = tmp_path / "lexigram"
    root.mkdir()
    (root / "pyproject.toml").write_text(
        '[project]\nname = "lexigram"\n',
        encoding="utf-8",
    )
    package_root = root / "lexigram-admin"
    package_root.mkdir()
    (package_root / "pyproject.toml").write_text(
        '[project]\nname = "lexigram-admin"\n',
        encoding="utf-8",
    )
    nested_file = package_root / "src" / "lexigram" / "admin" / "module.py"
    nested_file.parent.mkdir(parents=True)
    nested_file.write_text("pass\n", encoding="utf-8")

    assert resolve_workspace_root(nested_file) == root


def test_audit_report_has_required_metadata() -> None:
    report = AuditReport(
        name="env_vars",
        title="Environment Variables",
        generated_at="2026-04-22T00:00:00",
        output_markdown="AUDIT_ENV_VARS.md",
        output_json="AUDIT_ENV_VARS.json",
        records=[],
    )

    assert report.name == "env_vars"
    assert report.output_markdown == "AUDIT_ENV_VARS.md"


def test_registry_rejects_duplicate_names() -> None:
    registry = GeneratorRegistry[object]()
    registry.register("env_vars", object())

    with pytest.raises(ValueError, match="duplicate generator: env_vars"):
        registry.register("env_vars", object())


def test_audit_registry_contains_expected_generators() -> None:
    registry = build_audit_registry()

    assert registry.names() == EXPECTED_GENERATOR_NAMES
    for name in registry.names():
        generator = registry.get(name)
        assert generator is not None
        assert isinstance(generator, AuditGeneratorProtocol)
