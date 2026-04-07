from __future__ import annotations

from pathlib import Path
from typing import ClassVar

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[import-not-found,no-redef]

from lexigram.cli import constants as cli_const
from lexigram.config import BaseConfig
from lexigram.validation import ConfigDict, Field


class CLIConfig(BaseConfig):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    config_section: ClassVar[str] = "cli"

    default_template: str = Field(default="web-api")
    default_database: str = Field(default="postgres")
    color: bool = Field(default=True)
    verbose: bool = Field(default=False)


class ConfigManager:
    config_path = Path.home() / cli_const.DEFAULT_CONFIG_FILE

    @classmethod
    def load(cls) -> CLIConfig:
        if not cls.config_path.exists():
            return CLIConfig()

        with open(cls.config_path, "rb") as f:
            data = tomllib.load(f)
            return CLIConfig(**data.get("cli", {}))

    @classmethod
    def save(cls, config: CLIConfig) -> None:
        """Persist CLI configuration to disk in TOML format.

        Preserves existing non-cli sections in the config file.
        Creates parent directories if they do not exist.

        Args:
            config: CLI configuration to save.
        """
        # Read existing file to preserve other sections
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]

        existing_data: dict[str, object] = {}
        if cls.config_path.exists():
            try:
                with open(cls.config_path, "rb") as f:
                    existing_data = tomllib.load(f)
            except Exception:  # noqa: BLE001
                existing_data = {}

        # Build [cli] section - use model_dump to get all fields automatically
        cli_data: dict[str, object] = config.model_dump()

        # Merge - overwrite [cli] while keeping everything else
        existing_data["cli"] = cli_data

        # Create parent directories if needed
        cls.config_path.parent.mkdir(parents=True, exist_ok=True)

        # Write TOML
        try:
            import tomli_w  # type: ignore[import-not-found]

            with open(cls.config_path, "wb") as f:
                tomli_w.dump(existing_data, f)
        except ImportError:
            # Fallback: manual TOML serialization
            with open(cls.config_path, "w") as f:
                for section_name, section_data in existing_data.items():
                    if isinstance(section_data, dict):
                        f.write(f"[{section_name}]\n")
                        for key, value in section_data.items():
                            f.write(f"{key} = {_toml_value(value)}\n")
                        f.write("\n")


def _toml_value(value: object) -> str:
    """Serialize a Python value to a TOML literal."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, (int, float)):
        return str(value)
    return f'"{value}"'


__all__ = ["CLIConfig", "ConfigManager"]
