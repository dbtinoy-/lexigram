"""AppConfig must actually read the repo's application.yaml.

Regressions here silently fall back to the field defaults (1080x1920),
which previously made `app.reel_width` / `app.reel_height` dead config.
"""

import yaml

from shorts_creator.services.core import PROJECT_ROOT, AppConfig


class TestAppConfigReadsApplicationYaml:
    def test_reel_dimensions_follow_application_yaml(self):
        cfg = AppConfig.from_yaml(str(PROJECT_ROOT / "application.yaml"))
        with open(PROJECT_ROOT / "application.yaml") as fh:
            app_section = yaml.safe_load(fh)["app"]
        assert cfg.reel_width == app_section["reel_width"]
        assert cfg.reel_height == app_section["reel_height"]

    def test_project_root_points_at_repo_root_with_yaml(self):
        assert (PROJECT_ROOT / "application.yaml").exists()
