from pathlib import Path

import yaml

from shorts_creator.services.core import AppConfig

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TestAppConfigYamlShape:
    def test_app_section_has_no_nested_reel_block(self):
        raw = yaml.safe_load((PROJECT_ROOT / "application.yaml").read_text())
        assert "reel" not in raw["app"], (
            "app.reel.* is never read by AppConfig (flat dataclass fields) — "
            "nest was silently ignored. Keys must live directly under app:."
        )

    def test_app_section_has_no_cta_keys(self):
        raw = yaml.safe_load((PROJECT_ROOT / "application.yaml").read_text())
        assert "cta_enabled" not in raw["app"]
        assert "cta_lead_in" not in raw["app"]
        assert "cta_display" not in raw["app"]

    def test_from_yaml_reads_real_application_yaml_flat(self):
        config = AppConfig.from_yaml(str(PROJECT_ROOT / "application.yaml"), env_override=False)
        raw = yaml.safe_load((PROJECT_ROOT / "application.yaml").read_text())["app"]

        assert config.reel_width == raw["reel_width"]
        assert config.reel_height == raw["reel_height"]
        assert config.default_duration == raw["default_duration"]
