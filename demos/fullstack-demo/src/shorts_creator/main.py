import asyncio
import os
from pathlib import Path

from lexigram.app import Application
from lexigram.di.module import DynamicModule, Module, module
from lexigram.web import WebModule
from lexigram.web.config import CSPConfig, SecurityConfig, WebConfig
from lexigram.web.middleware.static import StaticFilesMiddleware
from lexigram.web.server.runner import run_server_async as _run_server_async

from shorts_creator.controllers.api.assets_api import AssetsApiController
from shorts_creator.controllers.api.composer_presets_api import ComposerPresetsApi
from shorts_creator.controllers.api.health_api import HealthApiController
from shorts_creator.controllers.api.ideas_api import IdeasApiController
from shorts_creator.controllers.api.logs_api import LogsApiController
from shorts_creator.controllers.api.preview_api import PreviewMediaController
from shorts_creator.controllers.api.progress_api import ProgressApiController
from shorts_creator.controllers.api.render_api import RenderApiController
from shorts_creator.controllers.api.scripts_api import ScriptsApiController
from shorts_creator.controllers.api.settings_api import SettingsApiController
from shorts_creator.controllers.api.sidebar_api import SidebarApiController
from shorts_creator.controllers.assets import AssetsController
from shorts_creator.controllers.history import HistoryController
from shorts_creator.controllers.homepage import HomepageController
from shorts_creator.controllers.project_runs import ProjectRunsController
from shorts_creator.controllers.project_settings import ProjectSettingsController
from shorts_creator.controllers.projects import ProjectsController
from shorts_creator.controllers.render import RenderController
from shorts_creator.controllers.scripts import ScriptsController
from shorts_creator.controllers.settings import SettingsController
from shorts_creator.controllers.topics import TopicsController
from shorts_creator.controllers.videos import VideosController
from shorts_creator.middleware.auth import TokenAuthMiddleware
from shorts_creator.services.module import PipelineModule

STATIC_DIR = str(Path(__file__).resolve().parents[2] / "static")
UI_STATIC_DIR = str(Path(__file__).resolve().parent / "ui" / "static")


@module()
class RootModule(Module):
    @classmethod
    def configure(cls) -> DynamicModule:
        web_config = WebConfig.from_yaml(
            str(Path(__file__).resolve().parents[2] / "application.yaml"),
            profile=os.environ.get("LEX_PROFILE"),
        )
        web_config = web_config.model_copy(
            update={
                "security": SecurityConfig(
                    csp=CSPConfig(
                        directives={
                            "default-src": "'self'",
                            "script-src": "'self' 'unsafe-inline' 'unsafe-eval'",
                            "script-src-elem": "'self' 'unsafe-inline'",
                            "style-src": "'self' 'unsafe-inline'",
                            "img-src": "'self' data: https: blob:",
                            "font-src": "'self' data:",
                            "connect-src": "'self' https: wss: ws:",
                            "frame-ancestors": "'none'",
                            "base-uri": "'self'",
                            "form-action": "'self'",
                        },
                    ),
                ),
            }
        )
        return DynamicModule(
            module=cls,
            imports=[
                PipelineModule.configure(),
                WebModule.configure(
                    controllers=[
                        HomepageController,
                        ProjectsController,
                        ProjectRunsController,
                        ScriptsController,
                        HistoryController,
                        SettingsController,
                        AssetsController,
                        ProjectSettingsController,
                        RenderController,
                        VideosController,
                        IdeasApiController,
                        LogsApiController,
                        ProgressApiController,
                        ComposerPresetsApi,
                        ScriptsApiController,
                        HealthApiController,
                        RenderApiController,
                        SettingsApiController,
                        AssetsApiController,
                        SidebarApiController,
                        PreviewMediaController,
                        TopicsController,
                    ],
                    port=int(os.environ.get("DSM_PORT", "8080")),
                    web_config=web_config,
                    middleware=[
                        (TokenAuthMiddleware, {}),
                        (
                            StaticFilesMiddleware,
                            {
                                "directory": UI_STATIC_DIR,
                                "prefix": "/static",
                                "cache_max_age": 0,
                            },
                        ),
                    ],
                ),
            ],
        )


async def main() -> None:
    port = int(os.environ.get("DSM_PORT", "8080"))
    async with Application.boot(name="shorts-creator", modules=[RootModule.configure()]) as app:
        from lexigram.web.di.provider import WebProvider

        web = await app.container.resolve(WebProvider)
        await _run_server_async(web.starlette, host="127.0.0.1", port=port)


if __name__ == "__main__":
    asyncio.run(main())
