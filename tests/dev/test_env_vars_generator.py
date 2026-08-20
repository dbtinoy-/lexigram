from __future__ import annotations

from pathlib import Path

from dev.audit.generators.env_vars import EnvVarsAuditGenerator


def _write_sample_workspace(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        '[project]\nname = "workspace"\n\n[tool.uv.workspace]\nmembers = ["lexigram"]\n',
        encoding="utf-8",
    )
    package_root = root / "lexigram"
    package_root.mkdir()
    (package_root / "pyproject.toml").write_text(
        '[project]\nname = "lexigram"\n',
        encoding="utf-8",
    )
    config_dir = package_root / "src" / "lexigram"
    config_dir.mkdir(parents=True)
    (config_dir / "config.py").write_text(
        """
from __future__ import annotations

from typing import ClassVar

from pydantic import ConfigDict, Field


class NestedConfig:
    enabled: bool = True


class AppConfig:
    model_config: ClassVar[ConfigDict] = ConfigDict(
        env_prefix="LEX_APP__",
        env_nested_delimiter="__",
    )
    debug: bool = Field(default=False, description="Enable debug mode.")
    nested: NestedConfig = NestedConfig()
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_env_vars_generator_emits_non_config_section_and_known_variable(
    tmp_path: Path,
) -> None:
    _write_sample_workspace(tmp_path)
    generator = EnvVarsAuditGenerator()

    result = generator.run(root=tmp_path)
    markdown = (tmp_path / "docs/audit" / "AUDIT_ENV_VARS.md").read_text(encoding="utf-8")

    assert result.success is True
    assert "## Non-Config ENV Sources" in markdown
    assert "LEX_DEBUG" in markdown
    assert "LEX_APP__DEBUG" in markdown
