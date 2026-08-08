from pathlib import Path

from lexigram.contracts.ai.llm import LLMClientProtocol
from lexigram.contracts.core.di import ContainerRegistrarProtocol, ContainerResolverProtocol
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.di.module import DynamicModule, Module, module
from lexigram.di.provider import Provider
from lexigram.sql.config import DatabaseConfig
from lexigram.sql.module import DatabaseModule
from lexigram.tasks import BackgroundTaskManager

from shorts_creator.models.run import RunStatus
from shorts_creator.repositories.asset_repository import AssetRepository
from shorts_creator.repositories.project_repository import ProjectRepository
from shorts_creator.repositories.run_repository import RunRepository
from shorts_creator.services.asset_resolver import AssetResolver
from shorts_creator.services.asset_service import AssetService
from shorts_creator.services.core import AppConfig, CoreProvider
from shorts_creator.services.critique_tools import create_critique_tools
from shorts_creator.services.history_service import HistoryService
from shorts_creator.services.idea_service import IdeaService
from shorts_creator.services.llm import LLMProvider
from shorts_creator.services.log_store import LogStore
from shorts_creator.services.progress_store import ProgressStore
from shorts_creator.services.project_profile_service import ProjectProfileService
from shorts_creator.services.project_service import ProjectService
from shorts_creator.services.render_progress import RenderProgressStore
from shorts_creator.services.render_tasks import RenderTaskRegistry
from shorts_creator.services.run_service import RunService
from shorts_creator.services.script_critique_agent import ScriptCritiqueAgent
from shorts_creator.services.script_service import ScriptService
from shorts_creator.services.settings_store import SettingsStore
from shorts_creator.services.topic_profile_service import TopicProfileService


async def _fail_stale_rendering_runs(run_service: RunService) -> None:
    """Mark any runs left in "rendering" by a previous process as failed.

    A crash or restart kills the in-process pipeline task while the DB row
    stays "rendering", which would leave the UI stuck on "Render Pipeline
    Active..." until the watchdog fires. This runs once at startup.
    """
    for run in await run_service.list_status(RunStatus.RENDERING):
        try:
            await run_service.mark_failed(run.id, "Interrupted by server restart")
        except Exception as exc:  # noqa: BLE001 - best-effort sweep; a failure here shouldn't block boot
            print(f"   stale-run sweep failed for {run.id}: {exc}")


async def _fail_stale_draft_runs(run_service: RunService) -> None:
    """Fail any DRAFT runs left behind by a previous process at startup.

    A DRAFT run only exists as a pre-render ephemeral row; if it survives a
    restart the process that created it died, so any age is stale. Mirrors
    the rendering sweep."""
    for run in await run_service.list_status(RunStatus.DRAFT):
        try:
            await run_service.mark_failed(run.id, "Interrupted before rendering")
        except Exception as exc:  # noqa: BLE001 - best-effort sweep; a failure here shouldn't block boot
            print(f"   stale-draft sweep failed for {run.id}: {exc}")


class PipelineProvider(Provider):
    name = "pipeline"

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(IdeaService, IdeaService())
        container.singleton(ScriptService, ScriptService())
        container.singleton(HistoryService, HistoryService())
        container.singleton(ProjectService, None)
        container.singleton(RunService, None)
        container.singleton(SettingsStore, None)
        container.singleton(TopicProfileService, None)
        container.singleton(ProjectProfileService, None)
        container.singleton(AssetService, None)
        container.singleton(AssetResolver, None)
        container.singleton(BackgroundTaskManager, BackgroundTaskManager())
        container.singleton(LogStore, LogStore())
        container.singleton(ProgressStore, None)
        container.singleton(RenderProgressStore, None)
        container.singleton(RenderTaskRegistry, RenderTaskRegistry())

    async def boot(self, container: ContainerResolverProtocol) -> None:
        config = await container.resolve(AppConfig)
        llm = await container.resolve(LLMClientProtocol)
        db = await container.resolve(DatabaseProviderProtocol)
        idea = await container.resolve(IdeaService)
        script = await container.resolve(ScriptService)
        idea.config = config
        idea.llm = llm
        script.config = config
        script.llm = llm
        tools = create_critique_tools(llm)
        script.critique_agent = ScriptCritiqueAgent(tools, llm)
        log_store = await container.resolve(LogStore)
        progress_store = ProgressStore(log_store=log_store)
        container.bind(ProgressStore, progress_store)
        container.bind(RenderProgressStore, progress_store)
        project_repo = ProjectRepository(db)
        project_service = ProjectService(project_repo)
        container.bind(ProjectService, project_service)
        run_repo = RunRepository(db)
        run_service = RunService(run_repo, progress_store)
        container.bind(RunService, run_service)
        container.bind(SettingsStore, SettingsStore(db))
        settings_store = await container.resolve(SettingsStore)
        topic_profiles = TopicProfileService(db)
        container.bind(TopicProfileService, topic_profiles)
        profile_service = ProjectProfileService(config, settings_store)
        container.bind(ProjectProfileService, profile_service)
        asset_repo = AssetRepository(db)
        asset_service = AssetService(asset_repo)
        container.bind(AssetService, asset_service)
        asset_resolver = AssetResolver(asset_repo)
        container.bind(AssetResolver, asset_resolver)
        await _fail_stale_rendering_runs(run_service)
        await _fail_stale_draft_runs(run_service)


@module()
class PipelineModule(Module):
    @classmethod
    def configure(cls) -> DynamicModule:
        return DynamicModule(
            module=cls,
            imports=[
                DatabaseModule.configure(
                    config=DatabaseConfig.from_yaml(
                        str(Path(__file__).resolve().parents[3] / "application.yaml"),
                    ),
                    migration_dir="migrations/primary",
                    enable_migrations=True,
                ),
            ],
            providers=[CoreProvider, LLMProvider, PipelineProvider],
            exports=[
                IdeaService,
                ScriptService,
                HistoryService,
                ProjectService,
                RunService,
                SettingsStore,
                AssetService,
                AssetResolver,
                LogStore,
                ProgressStore,
                RenderTaskRegistry,
                TopicProfileService,
                ProjectProfileService,
            ],
        )
