import json
import os

from shorts_creator.controllers.api.render_api import (
    RenderApiController,
    _absolutize_asset_bundle,
    _materialize_url_bundle,
)
from shorts_creator.models.asset_bundle import AssetBundle
from shorts_creator.models.project_profile import (
    EffectiveProjectProfile,
    ProfileSource,
    ResolvedSetting,
)
from shorts_creator.models.run import Run
from shorts_creator.services.asset_service import ASSETS_ROOT
from shorts_creator.services.core import AppConfig
from shorts_creator.services.run_service import RunService


class TestAbsolutizeAssetBundle:
    def test_relative_paths_become_absolute(self):
        bundle = AssetBundle(
            music_path="music/1.mp3",
            font_path="font/2.ttf",
            watermark_path="watermark/3.png",
            bg_clip_path="clip/4.mp4",
            outro_clip_path="clip/5.mp4",
        )
        out = _absolutize_asset_bundle(bundle)
        assert out.music_path == str(ASSETS_ROOT / "music" / "1.mp3")
        assert out.font_path == str(ASSETS_ROOT / "font" / "2.ttf")
        assert out.watermark_path == str(ASSETS_ROOT / "watermark" / "3.png")
        assert out.bg_clip_path == str(ASSETS_ROOT / "clip" / "4.mp4")
        assert out.outro_clip_path == str(ASSETS_ROOT / "clip" / "5.mp4")

    def test_none_fields_stay_none(self):
        out = _absolutize_asset_bundle(AssetBundle())
        assert out == AssetBundle()


class _FakeHttpClient:
    """AsyncClient stand-in that returns canned bytes per URL."""

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url):
        return _FakeHttpResponse(b"bytes:" + url.encode())


class _FakeHttpResponse:
    def __init__(self, content):
        self.content = content

    def raise_for_status(self):
        return None


class TestMaterializeUrlBundle:
    async def test_downloads_http_sources_keeps_local_paths(self, monkeypatch, tmp_path):
        import httpx

        monkeypatch.setattr(httpx, "AsyncClient", _FakeHttpClient)
        bundle = AssetBundle(
            music_path="https://cdn.example/track.mp3",
            bg_clip_path="/local/clip.mp4",
            outro_clip_path="https://cdn.example/outro.mov",
        )
        out = await _materialize_url_bundle(bundle, "test-owner")
        assert out.bg_clip_path == "/local/clip.mp4"
        assert out.font_path is None
        assert out.music_path and out.music_path.endswith("music.mp3")
        with open(out.music_path, "rb") as f:  # noqa: ASYNC230 - tiny fixture file
            assert f.read() == b"bytes:https://cdn.example/track.mp3"
        assert out.outro_clip_path and out.outro_clip_path.endswith("outro.mov")

    async def test_no_http_sources_passes_bundle_through(self):
        bundle = AssetBundle(music_path="/local/track.mp3", font_path="/local/f.ttf")
        out = await _materialize_url_bundle(bundle, "test-owner")
        assert out == bundle


class _FakeProject:
    id = "p1"
    topic = "self_improvement"
    idea_json = json.dumps(
        [
            {
                "id": "i1",
                "title": "Idea One",
                "core_message": "M",
                "script_json": json.dumps(
                    {"title": "S", "sections": [], "total_duration": 30, "word_count": 10}
                ),
            }
        ]
    )
    profile_overrides_json = None


class _FakeProjectService:
    async def get(self, project_id):
        return _FakeProject()


class _FakeProfileService:
    def __init__(self, profile):
        self._profile = profile

    async def resolve(self, project):
        return self._profile

    @staticmethod
    def validate(profile):
        return {}

    async def validate_pair_for_project(self, project):
        return []


class _FakeRunRepo:
    def __init__(self):
        self.store = {}

    async def create(self, run):
        self.store[run.id] = run
        return run

    async def update(self, run):
        self.store[run.id] = run
        return run

    async def get(self, run_id):
        return self.store.get(run_id)

    async def list_by_project(self, project_id, limit=50):
        return [r for r in self.store.values() if r.project_id == project_id][:limit]


class _FakeTask:
    def done(self):
        return True


class _FakeTaskManager:
    def track_named(self, name, coro):
        coro.close()
        return _FakeTask()


class _FakeHistory:
    async def get_recent(self, limit=3):
        return []


class _FakeScriptService:
    last_script = None


class _NoiseStore:
    """Store that fails if the render API consults a second settings source.

    Credentials (stock-video keys) are the one allowed exception; the store
    here reports none configured.
    """

    async def get_overrides(self):
        raise AssertionError("start_render must not read the settings store")

    async def get_credentials(self):
        return {}


class _SpyAssetResolver:
    def __init__(self, bundle):
        self._bundle = bundle
        self.calls = []

    async def resolve(self, project, overrides):
        self.calls.append((project, dict(overrides)))
        return self._bundle


from typing import ClassVar


class _PipelineSpy:
    instances: ClassVar[list] = []

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        _PipelineSpy.instances.append(kwargs)


class _Request:
    def __init__(self, form_data=None):
        self.headers = {"content-type": "application/x-www-form-urlencoded"}
        self._form = form_data or {}

    async def form(self):
        return self._form


def _profile_with_assets() -> EffectiveProjectProfile:
    return EffectiveProjectProfile(
        duration_seconds=ResolvedSetting(45, ProfileSource.PROJECT, True),
        caption_style=ResolvedSetting("highlight", ProfileSource.BUILT_IN, False),
        reel_width=ResolvedSetting(1080, ProfileSource.BUILT_IN, False),
        reel_height=ResolvedSetting(1920, ProfileSource.BUILT_IN, False),
        asset_music_id=ResolvedSetting("music-1", ProfileSource.PROJECT, True),
        asset_font_id=ResolvedSetting(None, ProfileSource.BUILT_IN, False),
        asset_watermark_id=ResolvedSetting("wm-2", ProfileSource.GLOBAL, False),
        asset_bg_clip_id=ResolvedSetting(None, ProfileSource.BUILT_IN, False),
        asset_outro_clip_id=ResolvedSetting(None, ProfileSource.BUILT_IN, False),
    )


def _make_controller(profile_service, asset_resolver):
    return RenderApiController(
        scripts=_FakeScriptService(),
        ideas=None,
        history=_FakeHistory(),
        project_service=_FakeProjectService(),
        task_manager=_FakeTaskManager(),
        config=AppConfig(),
        runs=RunService(repo=_FakeRunRepo()),
        store=_NoiseStore(),
        asset_resolver=asset_resolver,
        profile_service=profile_service,
    )


class TestStartRenderScriptlessIdea:
    async def test_scriptless_idea_returns_error_without_creating_run(self, monkeypatch):
        _PipelineSpy.instances = []

        class _ScriptlessProject(_FakeProject):
            idea_json = json.dumps([{"id": "i1", "title": "No script idea"}])

        class _ScriptlessProjectService(_FakeProjectService):
            async def get(self, project_id):
                return _ScriptlessProject()

        controller = _make_controller(
            _FakeProfileService(_profile_with_assets()), _SpyAssetResolver(AssetBundle())
        )
        controller.project_service = _ScriptlessProjectService()
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _PipelineSpy)
        response = await controller.start_render(
            request=_Request({"project_id": "p1", "idea_index": "0"})
        )

        assert "Script not found" in response
        assert controller.runs.repo.store == {}
        assert not _PipelineSpy.instances


class TestStartRenderMediaPreflight:
    async def test_missing_asset_file_fails_run_without_pipeline(self, monkeypatch, tmp_path):
        from shorts_creator.models.run import RunStatus

        _PipelineSpy.instances = []
        missing = tmp_path / "deleted_music.mp3"
        bundle = AssetBundle(music_path=str(missing), watermark_path="wm/ok.png")
        resolver = _SpyAssetResolver(bundle)
        controller = _make_controller(_FakeProfileService(_profile_with_assets()), resolver)
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _PipelineSpy)
        response = await controller.start_render(
            request=_Request({"project_id": "p1", "idea_index": "0"})
        )

        assert "Missing music media" in response
        assert str(missing) in response
        assert not _PipelineSpy.instances
        run = next(iter(controller.runs.repo.store.values()))
        assert run.status is RunStatus.FAILED
        assert "Missing music media" in run.error

    async def test_present_asset_files_render_unchanged(self, monkeypatch, tmp_path):
        _PipelineSpy.instances = []
        present = tmp_path / "music.mp3"
        present.write_bytes(b"fake")
        wm = tmp_path / "wm.png"
        wm.write_bytes(b"fake")
        bundle = AssetBundle(music_path=str(present), watermark_path=str(wm))
        controller = _make_controller(
            _FakeProfileService(_profile_with_assets()), _SpyAssetResolver(bundle)
        )
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _PipelineSpy)
        response = await controller.start_render(
            request=_Request({"project_id": "p1", "idea_index": "0"})
        )
        assert "Missing" not in response
        assert len(_PipelineSpy.instances) == 1


class TestStartRenderReqStyleBlocks:
    async def test_req_style_blocks_render_without_run_or_pipeline(self, monkeypatch):
        from shorts_creator.contracts.issues import ContractIssue, Severity

        _PipelineSpy.instances = []

        class _BlockingProfileService:
            def __init__(self):
                self.calls = 0

            async def resolve(self, project):
                return _profile_with_assets()

            @staticmethod
            def validate(profile):
                return {}

            async def validate_pair_for_project(self, project):
                self.calls += 1
                return [
                    ContractIssue(
                        Severity.ERROR,
                        "REQ_STYLE",
                        "resolved caption style 'list' is not supported by format "
                        "'narrated'; supported: ['highlight']",
                    )
                ]

        profile_service = _BlockingProfileService()
        controller = _make_controller(profile_service, _SpyAssetResolver(AssetBundle()))
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _PipelineSpy)
        response = await controller.start_render(
            request=_Request({"project_id": "p1", "idea_index": "0"})
        )

        assert "REQ_STYLE" in response
        assert "supported: ['highlight']" in response
        assert profile_service.calls == 1
        assert not _PipelineSpy.instances
        assert controller.runs.repo.store == {}


class TestStartRenderAssetsFromSnapshot:
    async def test_assets_resolve_from_snapshot_ids_only(self, monkeypatch, tmp_path):
        _PipelineSpy.instances = []
        music = tmp_path / "1.mp3"
        music.write_bytes(b"fake")
        wm = tmp_path / "2.png"
        wm.write_bytes(b"fake")
        bundle = AssetBundle(music_path=str(music), watermark_path=str(wm))
        resolver = _SpyAssetResolver(bundle)
        controller = _make_controller(_FakeProfileService(_profile_with_assets()), resolver)
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _PipelineSpy)
        await controller.start_render(request=_Request({"project_id": "p1", "idea_index": "0"}))

        assert len(resolver.calls) == 1
        project_arg, overrides = resolver.calls[0]
        assert project_arg is None
        assert overrides == {
            "asset_default_music_id": "music-1",
            "asset_default_watermark_id": "wm-2",
        }
        captured = _PipelineSpy.instances[-1]
        assert captured["assets"].music_path == str(music)
        assert captured["assets"].watermark_path == str(wm)

    async def test_media_url_override_downloaded_into_pipeline(self, monkeypatch, tmp_path):
        _PipelineSpy.instances = []
        import httpx

        wm = tmp_path / "2.png"
        wm.write_bytes(b"fake")

        monkeypatch.setattr(httpx, "AsyncClient", _FakeHttpClient)
        profile = _profile_with_assets()
        profile.media_url_music = ResolvedSetting(
            "https://cdn.example/track.mp3", ProfileSource.PROJECT, True
        )
        resolver = _SpyAssetResolver(
            AssetBundle(music_path="https://cdn.example/track.mp3", watermark_path=str(wm))
        )
        controller = _make_controller(_FakeProfileService(profile), resolver)
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _PipelineSpy)
        await controller.start_render(request=_Request({"project_id": "p1", "idea_index": "0"}))

        assert resolver.calls[0][1]["media_url_music"] == "https://cdn.example/track.mp3"
        captured = _PipelineSpy.instances[-1]
        assert captured["assets"].music_path.endswith("music.mp3")
        assert captured["assets"].watermark_path == str(wm)

    async def test_stock_api_keys_flow_from_store_into_pipeline(self, monkeypatch):
        _PipelineSpy.instances = []
        controller = _make_controller(
            _FakeProfileService(_profile_with_assets()), _SpyAssetResolver(AssetBundle())
        )

        class _CredStore(_NoiseStore):
            async def get_credentials(self):
                return {"pexels_api_key": "px-123", "pixabay_api_key": "pb-456"}

        controller.store = _CredStore()
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _PipelineSpy)
        await controller.start_render(request=_Request({"project_id": "p1", "idea_index": "0"}))

        captured = _PipelineSpy.instances[-1]
        assert captured["stock_api_keys"] == {
            "pexels_api_key": "px-123",
            "pixabay_api_key": "pb-456",
        }

    async def test_bg_source_follows_snapshot_into_pipeline(self, monkeypatch):
        _PipelineSpy.instances = []
        profile = _profile_with_assets()
        profile.bg_source = ResolvedSetting("api", ProfileSource.PROJECT, True)
        profile.stock_provider = ResolvedSetting("pixabay", ProfileSource.PROJECT, True)
        controller = _make_controller(
            _FakeProfileService(profile), _SpyAssetResolver(AssetBundle())
        )
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _PipelineSpy)
        await controller.start_render(request=_Request({"project_id": "p1", "idea_index": "0"}))

        captured = _PipelineSpy.instances[-1]
        assert captured["bg_source"] == "api"
        assert captured["stock_provider"] == "pixabay"

    async def test_outro_text_follows_snapshot_into_pipeline(self, monkeypatch):
        _PipelineSpy.instances = []
        profile = _profile_with_assets()
        profile.outro_text = ResolvedSetting("Keep going", ProfileSource.PROJECT, True)
        controller = _make_controller(
            _FakeProfileService(profile), _SpyAssetResolver(AssetBundle())
        )
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _PipelineSpy)
        await controller.start_render(request=_Request({"project_id": "p1", "idea_index": "0"}))

        captured = _PipelineSpy.instances[-1]
        assert captured["outro_text"] == "Keep going"

    async def test_background_queries_follow_project_topic(self, monkeypatch):
        _PipelineSpy.instances = []
        controller = _make_controller(
            _FakeProfileService(_profile_with_assets()), _SpyAssetResolver(AssetBundle())
        )
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _PipelineSpy)
        await controller.start_render(request=_Request({"project_id": "p1", "idea_index": "0"}))

        captured = _PipelineSpy.instances[-1]
        assert len(captured["background_queries"]) > 0
        assert all(isinstance(q, str) for q in captured["background_queries"])

    async def test_background_queries_empty_for_unknown_topic(self, monkeypatch):
        _PipelineSpy.instances = []
        project = _FakeProject()
        project.topic = "no_such_topic"
        controller = _make_controller(
            _FakeProfileService(_profile_with_assets()), _SpyAssetResolver(AssetBundle())
        )

        class _Proj(_FakeProjectService):
            async def get(self, project_id):
                return project

        controller.project_service = _Proj()
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _PipelineSpy)
        await controller.start_render(request=_Request({"project_id": "p1", "idea_index": "0"}))

        captured = _PipelineSpy.instances[-1]
        assert captured["background_queries"] == []

    async def test_assets_follow_existing_run_snapshot(self, monkeypatch, tmp_path):
        _PipelineSpy.instances = []
        music = tmp_path / "9.mp3"
        music.write_bytes(b"fake")
        runs = RunService(repo=_FakeRunRepo())
        run = await runs.repo.create(Run(project_id="p1"))
        await runs.update_profile_snapshot(run.id, {"asset_music_id": "music-9"})
        resolver = _SpyAssetResolver(AssetBundle(music_path=str(music)))
        controller = _make_controller(_FakeProfileService(_profile_with_assets()), resolver)
        controller.runs = runs
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _PipelineSpy)
        await controller.start_render(
            request=_Request({"project_id": "p1", "run_id": run.id, "idea_index": "0"})
        )
        assert resolver.calls[0][1] == {"asset_default_music_id": "music-9"}
        captured = _PipelineSpy.instances[-1]
        assert captured["assets"].music_path == str(music)


class TestComposerFieldsThroughSnapshot:
    async def test_composer_fields_follow_snapshot_into_pipeline(self, monkeypatch):
        _PipelineSpy.instances = []
        profile = _profile_with_assets()
        profile.layout = ResolvedSetting({"anchor": "lower_third"}, ProfileSource.PROJECT, True)
        profile.stages = ResolvedSetting({"music": True}, ProfileSource.PROJECT, True)
        profile.style = ResolvedSetting({"chunk_size": 5}, ProfileSource.PROJECT, True)
        controller = _make_controller(
            _FakeProfileService(profile), _SpyAssetResolver(AssetBundle())
        )
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _PipelineSpy)
        await controller.start_render(request=_Request({"project_id": "p1", "idea_index": "0"}))

        captured = _PipelineSpy.instances[-1]
        assert captured["stages"] == {"music": True}
        assert captured["render_config"].anchor == "lower_third"
        assert captured["render_config"].caption_max_words == 5

    async def test_legacy_snapshot_leaves_composer_kwargs_none(self, monkeypatch):
        _PipelineSpy.instances = []
        controller = _make_controller(
            _FakeProfileService(_profile_with_assets()), _SpyAssetResolver(AssetBundle())
        )
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _PipelineSpy)
        await controller.start_render(request=_Request({"project_id": "p1", "idea_index": "0"}))

        captured = _PipelineSpy.instances[-1]
        assert captured["stages"] is None
        assert captured["render_config"] is None


class TestRunKeyedOutput:
    async def test_run_output_path_is_run_keyed(self, monkeypatch):
        _PipelineSpy.instances = []
        controller = _make_controller(
            _FakeProfileService(_profile_with_assets()), _SpyAssetResolver(AssetBundle())
        )
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _PipelineSpy)
        await controller.start_render(request=_Request({"project_id": "p1", "idea_index": "0"}))
        run = next(iter(controller.runs.repo.store.values()))
        captured = _PipelineSpy.instances[-1]
        assert os.path.basename(captured["output"]) == f"{run.id}.mp4"


class TestCompletedRunNotReentered:
    async def test_second_render_of_idea_creates_new_run(self, monkeypatch):
        from shorts_creator.models.run import RunStatus

        _PipelineSpy.instances = []
        controller = _make_controller(
            _FakeProfileService(_profile_with_assets()), _SpyAssetResolver(AssetBundle())
        )
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _PipelineSpy)
        await controller.start_render(request=_Request({"project_id": "p1", "idea_index": "0"}))
        first = next(iter(controller.runs.repo.store.values()))
        await controller.runs.mark_completed(first.id, "/out/first.mp4", 12.0)

        await controller.start_render(request=_Request({"project_id": "p1", "idea_index": "0"}))
        runs = list(controller.runs.repo.store.values())
        assert len(runs) == 2
        second = next(r for r in runs if r.id != first.id)
        assert first.status is RunStatus.COMPLETED
        assert first.output_path == "/out/first.mp4"
        assert second.status is RunStatus.RENDERING
        assert len(_PipelineSpy.instances) == 2
        outputs = [os.path.basename(c["output"]) for c in _PipelineSpy.instances]
        assert outputs == [f"{first.id}.mp4", f"{second.id}.mp4"]

    async def test_legacy_run_id_does_not_restart_completed_run(self, monkeypatch):
        from shorts_creator.models.run import RunStatus

        _PipelineSpy.instances = []
        runs = RunService(repo=_FakeRunRepo())
        run = await runs.repo.create(Run(project_id="p1"))
        await runs.mark_rendering(run.id)
        await runs.mark_completed(run.id, "/out/first.mp4", 12.0)
        controller = _make_controller(
            _FakeProfileService(_profile_with_assets()), _SpyAssetResolver(AssetBundle())
        )
        controller.runs = runs
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _PipelineSpy)
        response = await controller.start_render(
            request=_Request({"project_id": "p1", "run_id": run.id, "idea_index": "0"})
        )
        assert _PipelineSpy.instances == []
        assert "already complete" in response
        after = await runs.get(run.id)
        assert after.status is RunStatus.COMPLETED
        assert after.output_path == "/out/first.mp4"

    async def test_legacy_run_id_of_draft_run_still_dispatches(self, monkeypatch, tmp_path):
        from shorts_creator.models.run import RunStatus

        _PipelineSpy.instances = []
        music = tmp_path / "m.mp3"
        music.write_bytes(b"fake")
        runs = RunService(repo=_FakeRunRepo())
        run = await runs.repo.create(Run(project_id="p1"))
        controller = _make_controller(
            _FakeProfileService(_profile_with_assets()),
            _SpyAssetResolver(AssetBundle(music_path=str(music))),
        )
        controller.runs = runs
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _PipelineSpy)
        await controller.start_render(
            request=_Request({"project_id": "p1", "run_id": run.id, "idea_index": "0"})
        )
        assert len(_PipelineSpy.instances) == 1
        assert os.path.basename(_PipelineSpy.instances[0]["output"]) == f"{run.id}.mp4"
        after = await runs.get(run.id)
        assert after.status is RunStatus.RENDERING


class TestProfileOverridesConvertedScript:
    async def test_hook_text_override_replaces_saved_hook_in_pipeline_script(self, monkeypatch):
        captured = []

        class _ScriptSpy:
            def __init__(self, **kwargs):
                captured.append(self)

        class _ProjectWithScript(_FakeProject):
            idea_json = json.dumps(
                [
                    {
                        "id": "i1",
                        "title": "Idea One",
                        "core_message": "M",
                        "script_json": json.dumps(
                            {
                                "title": "S",
                                "total_duration": 30.0,
                                "sections": [
                                    {
                                        "name": "hook",
                                        "text": "Original saved hook",
                                        "duration_seconds": 5.0,
                                    },
                                    {"name": "message", "text": "Message", "duration_seconds": 8.0},
                                ],
                            }
                        ),
                    }
                ]
            )

        class _ProjectWithScriptService(_FakeProjectService):
            async def get(self, project_id):
                return _ProjectWithScript()

        profile = _profile_with_assets()
        profile.hook_text = ResolvedSetting("Override hook", ProfileSource.PROJECT, True)
        controller = _make_controller(
            _FakeProfileService(profile), _SpyAssetResolver(AssetBundle())
        )
        controller.project_service = _ProjectWithScriptService()
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _ScriptSpy)
        await controller.start_render(request=_Request({"project_id": "p1", "idea_index": "0"}))

        assert len(captured) == 1
        assert captured[0].script.hook == "Override hook"
        assert captured[0].script.message_lines == ["Message"]

    async def test_no_override_keeps_saved_copy(self, monkeypatch):
        captured = []

        class _ScriptSpy:
            def __init__(self, **kwargs):
                captured.append(self)

        controller = _make_controller(
            _FakeProfileService(_profile_with_assets()), _SpyAssetResolver(AssetBundle())
        )
        monkeypatch.setattr("shorts_creator.pipeline.pipeline.ReelPipeline", _ScriptSpy)
        await controller.start_render(request=_Request({"project_id": "p1", "idea_index": "0"}))

        assert len(captured) == 1
        assert captured[0].script.hook == ""
