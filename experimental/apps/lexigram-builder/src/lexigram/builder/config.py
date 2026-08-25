"""Builder configuration model."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import ClassVar

from lexigram.builder.constants import (
    BUILDER_DEFAULT_HOST,
    BUILDER_DEFAULT_PORT,
    ENV_BUILDER_PORT,
    ENV_PROJECTS_DIR,
)


@dataclass(frozen=True, slots=True)
class BuilderConfig:
    """Runtime configuration for the builder server.

    Attributes:
        host: Bind host for the builder server.
        port: Bind port for the builder server.
        projects_dir: Directory holding generated projects; empty string
            means "resolve at service construction" (package-local
            ``projects/`` default).
    """

    config_section: ClassVar[str] = "builder"

    host: str = BUILDER_DEFAULT_HOST
    port: int = BUILDER_DEFAULT_PORT
    projects_dir: str = ""

    @classmethod
    def from_env(cls) -> BuilderConfig:
        """Build a config honoring ``LEX_BUILDER_*`` environment overrides."""
        raw_port = os.getenv(ENV_BUILDER_PORT, str(BUILDER_DEFAULT_PORT))
        try:
            port = int(raw_port)
        except ValueError:
            port = BUILDER_DEFAULT_PORT
        return cls(
            port=port,
            projects_dir=os.getenv(ENV_PROJECTS_DIR, ""),
        )

    def resolved_projects_dir(self, package_root: Path) -> Path:
        """Return the effective projects directory.

        Args:
            package_root: Package root used for the default location when
                no explicit directory is configured.
        """
        if self.projects_dir:
            return Path(self.projects_dir)
        return package_root / "projects"
