import os
from pathlib import Path

from lexigram.config.base import BaseConfig
from lexigram.contracts.core.di import ContainerRegistrarProtocol, ContainerResolverProtocol
from lexigram.di.provider import Provider

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class AppConfig(BaseConfig):
    config_section = "app"

    env: str = "development"
    reel_width: int = 1080
    reel_height: int = 1920
    default_duration: float = 30.0
    database_url: str = "sqlite+aiosqlite:///data/shorts.db"


class CoreProvider(Provider):
    name = "core"

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        config = AppConfig.from_yaml(
            str(PROJECT_ROOT / "application.yaml"),
            profile=os.environ.get("LEX_PROFILE"),
        )
        container.singleton(AppConfig, config)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        pass
