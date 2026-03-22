"""Gateway CLI helper tests.

Covers ``load_gateway_config`` (JSON/TOML parsing, extension guard,
error surfacing) and ``build_gateway_app`` module composition with the
entry-point loader stubbed.
"""

from __future__ import annotations

from importlib import metadata
from pathlib import Path
from typing import Any

import pytest


def write_config(tmp_path: Path, content: str, suffix: str = ".json") -> Path:
    """Write *content* to a file under *tmp_path* and return its path."""
    path = tmp_path / f"gateway{suffix}"
    path.write_text(content, encoding="utf-8")
    return path


def valid_json() -> str:
    """A minimal valid gateway config document."""
    return """
    {
      "channels": [
        {
          "name": "claude",
          "upstream_base_url": "https://up.example/claude",
          "target_format": "CLAUDE",
          "models": ["claude-sonnet"]
        }
      ],
      "auto_disable_on_failures": true
    }
    """


class TestLoadGatewayConfig:
    """load_gateway_config parses and validates the file."""

    def test_json_config_round_trip(self, tmp_path: Path) -> None:
        from lexigram.ai.cli.gateway import load_gateway_config

        cfg = load_gateway_config(write_config(tmp_path, valid_json()))
        assert cfg.channels[0].name == "claude"
        assert cfg.channels[0].models == ("claude-sonnet",)
        assert cfg.auto_disable_on_failures is True

    def test_toml_config_round_trip(self, tmp_path: Path) -> None:
        from lexigram.ai.cli.gateway import load_gateway_config

        toml = """
        [[channels]]
        name = "gemini"
        upstream_base_url = "https://up.example/gemini"
        target_format = "GEMINI"
        models = ["gemini-pro"]
        """
        cfg = load_gateway_config(write_config(tmp_path, toml, ".toml"))
        assert cfg.channels[0].name == "gemini"

    def test_unknown_extension_rejected(self, tmp_path: Path) -> None:
        from lexigram.ai.cli.gateway import load_gateway_config

        path = write_config(tmp_path, "{}", ".yaml")
        with pytest.raises(ValueError, match=r"\.json or \.toml"):
            load_gateway_config(path)

    def test_missing_file_rejected(self, tmp_path: Path) -> None:
        from lexigram.ai.cli.gateway import load_gateway_config

        with pytest.raises(ValueError, match="cannot read"):
            load_gateway_config(tmp_path / "nope.json")

    def test_invalid_json_rejected(self, tmp_path: Path) -> None:
        from lexigram.ai.cli.gateway import load_gateway_config

        with pytest.raises(ValueError, match="invalid JSON"):
            load_gateway_config(write_config(tmp_path, "{nope"))

    def test_unknown_keys_rejected(self, tmp_path: Path) -> None:
        from lexigram.ai.cli.gateway import load_gateway_config

        with pytest.raises(ValueError, match="unknown gateway config keys"):
            load_gateway_config(write_config(tmp_path, '{"billing_url": "x"}'))


class TestBuildGatewayApp:
    """build_gateway_app composes the four modules in order."""

    def test_composes_expected_modules(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from lexigram.ai.cli import gateway as gateway_cli

        captured: list[tuple[str, str]] = []

        class FakeModule:
            def __init__(self, name: str, config: Any = None) -> None:
                self.name = name
                self.config = config

            @classmethod
            def configure(cls, *args: Any, **kwargs: Any) -> FakeModule:
                return cls(cls.__name__, config=kwargs.get("config"))

        def fake_load(group: str, name: str) -> type[FakeModule]:
            captured.append((group, name))
            return FakeModule

        monkeypatch.setattr(gateway_cli, "_load_module", fake_load)
        app = gateway_cli.build_gateway_app(object(), host="0.0.0.0")
        assert captured == [
            ("lexigram.ai.modules", "relay"),
            ("lexigram.ai.modules", "relay-gateway"),
            ("lexigram.modules", "http"),
            ("lexigram.modules", "web"),
        ]
        module_app = app._modules  # noqa: SLF001
        assert [m.name for m in module_app] == [
            "FakeModule",
            "FakeModule",
            "FakeModule",
            "FakeModule",
        ]

    def test_missing_entry_point_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from lexigram.ai.cli import gateway as gateway_cli

        real_entry_points = metadata.entry_points

        def empty_entry_points(**params: Any) -> Any:
            if params:
                return ()
            return real_entry_points()

        monkeypatch.setattr(gateway_cli.metadata, "entry_points", empty_entry_points)
        with pytest.raises(ModuleNotFoundError, match="not found"):
            gateway_cli._load_module(  # noqa: SLF001
                "lexigram.ai.modules", "relay-gateway"
            )
