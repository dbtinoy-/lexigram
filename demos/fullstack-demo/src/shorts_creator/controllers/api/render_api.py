import asyncio
import json
import os
import re
import shutil
import subprocess
import time
from typing import Any

from lexigram.tasks import BackgroundTaskManager
from lexigram.ui import el
from lexigram.web import (
    Controller,
    FileResponse,
    HTMLContent,
    StreamingResponse,
    get,
    html_response,
    post,
)

from shorts_creator.contracts.issues import ContractIssue, Severity
from shorts_creator.controllers.render import render_active_html
from shorts_creator.models.asset_bundle import AssetBundle
from shorts_creator.models.run import RunStatus
from shorts_creator.services.asset_resolver import AssetResolver
from shorts_creator.services.asset_service import ASSETS_ROOT
from shorts_creator.services.core import AppConfig
from shorts_creator.services.history_service import HistoryService
from shorts_creator.services.idea_service import IdeaService
from shorts_creator.services.project_profile_service import ProjectProfileService
from shorts_creator.services.project_service import ProjectService
from shorts_creator.services.render_progress import RenderProgressStore
from shorts_creator.services.render_tasks import RenderTaskRegistry
from shorts_creator.services.run_service import RunService
from shorts_creator.services.script_service import ScriptService
from shorts_creator.services.settings_store import SettingsStore
from shorts_creator.topics.base import Idea


def _absolutize_asset_bundle(bundle: AssetBundle) -> AssetBundle:
    """Map ASSETS_ROOT-relative paths onto absolute paths the pipeline can open.

    Public-URL sources (media_url_*) pass through untouched; the caller may
    download them via _materialize_url_bundle.
    """
    root = str(ASSETS_ROOT)
    values: dict[str, str | None] = {}
    for name in ("music_path", "font_path", "watermark_path", "bg_clip_path", "outro_clip_path"):
        path = getattr(bundle, name)
        if not path:
            values[name] = None
        elif path.lower().startswith(("http://", "https://")):
            values[name] = path
        else:
            values[name] = os.path.join(root, path)
    return AssetBundle(**values)


def _write_file(dest: str, data: bytes) -> None:
    """Write downloaded media bytes to a local temp file."""
    with open(dest, "wb") as f:
        f.write(data)


async def _materialize_url_bundle(bundle: AssetBundle, owner: str) -> AssetBundle:
    """Download URL-sourced media (bg clip / music / outro / watermark) into a
    per-owner temp dir so the pipeline can loop and seek them like local files.
    A failed download drops the role so the pipeline falls back to its defaults."""
    from urllib.parse import urlparse

    import httpx

    roles = {
        "music_path": "music",
        "bg_clip_path": "bg_clip",
        "outro_clip_path": "outro",
        "watermark_path": "watermark",
    }
    urls = {
        name: getattr(bundle, name)
        for name in roles
        if getattr(bundle, name)
        and str(getattr(bundle, name)).lower().startswith(("http://", "https://"))
    }
    if not urls:
        return bundle
    tmp_dir = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "..", "data", "renders", "tmp", owner
    )
    os.makedirs(tmp_dir, exist_ok=True)
    values = {name: getattr(bundle, name) for name in roles if name not in urls}
    timeout = httpx.Timeout(60.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            for name, role in roles.items():
                url = urls.get(name)
                if not url:
                    continue
                parsed = urlparse(url)
                ext = (
                    os.path.splitext(parsed.path)[1]
                    or {
                        "music_path": ".mp3",
                        "bg_clip_path": ".mp4",
                        "outro_clip_path": ".mp4",
                        "watermark_path": ".png",
                    }[name]
                )
                dest = os.path.join(tmp_dir, f"{role}{ext}")
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    _write_file(dest, resp.content)
                    values[name] = dest
                except Exception as exc:  # noqa: BLE001 - fall back to defaults
                    print(f"[render] failed to download {role} from {url}: {exc}")
    except Exception as exc:  # noqa: BLE001
        print(f"[render] URL media download failed: {exc}")
    return AssetBundle(
        music_path=values.get("music_path"),
        font_path=bundle.font_path,
        watermark_path=values.get("watermark_path"),
        bg_clip_path=values.get("bg_clip_path"),
        outro_clip_path=values.get("outro_clip_path"),
    )


from shorts_creator.ui.icons import alert, check

STALE_RENDER_SECONDS = 15 * 60
STAGE_STALE_SECONDS = 12 * 60
WATCHDOG_INTERVAL = 30.0

# Serializes the "claim" section of start_render per project+idea so two
# concurrent identical POSTs can't both pass the dedupe scan before either
# marks its run as rendering (they would double-render the same output file).
_START_LOCKS: dict[str, asyncio.Lock] = {}


def _start_lock(key: str) -> asyncio.Lock:
    return _START_LOCKS.setdefault(key, asyncio.Lock())


def probe_duration(path: str) -> float:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError, FileNotFoundError, OSError):
        return 0.0


def _poster_brightness(poster_path: str) -> float:
    """Mean luma (YAVG, 0-255) of an image via ffmpeg signalstats."""
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-loglevel",
                "error",
                "-i",
                poster_path,
                "-vf",
                "signalstats,metadata=print:file=-",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        for line in result.stdout.splitlines():
            if "YAVG" in line:
                return float(line.split("=")[-1])
    except (
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        FileNotFoundError,
        OSError,
        ValueError,
    ):
        pass
    return -1.0


def extract_poster_frame(output_path: str) -> str:
    """Best-effort poster frame next to the master video (``<stem>.jpg``).

    Reels fade in from black, so the first frame is useless as a poster.
    Write a candidate frame at successive offsets, keeping the first
    bright-enough one. Returns the poster path, or ``""`` when extraction
    fails so renders are never blocked or marked failed by poster
    generation.
    """
    poster = os.path.splitext(output_path)[0] + ".jpg"
    if not os.path.exists(output_path):
        return ""
    duration = probe_duration(output_path) or 60.0
    candidates = [0.5, 1.5, 3.0, 6.0, 12.0, 20.0, 30.0]
    candidates += [i * duration for i in (0.5, 0.75)]
    seen: set[float] = set()
    last = ""
    try:
        for offset in candidates:
            if offset >= duration or offset in seen:
                continue
            seen.add(offset)
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-loglevel",
                    "error",
                    "-ss",
                    f"{offset}",
                    "-i",
                    output_path,
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=360:-2",
                    poster,
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
            )
            if os.path.exists(poster):
                last = poster
                if _poster_brightness(poster) >= 15.0:
                    return poster
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return last


def _RenderError(msg):
    return str(
        el(
            "div",
            alert(),
            el("span", f" {msg}", class_="ml-2 font-medium"),
            class_="flex items-center p-4 bg-destructive/40 rounded-xl border border-destructive/50 text-destructive text-xs font-mono shadow-sm",
        )
    )


def _RenderSuccess(path):
    return str(
        el(
            "div",
            check(),
            el(
                "div",
                el("span", " Render Complete!", class_="text-success font-semibold text-sm"),
                el(
                    "p",
                    f"Exported Output: {path}",
                    class_="text-muted-foreground text-xs mt-0.5 font-mono truncate",
                ),
                class_="ml-2.5",
            ),
            class_="flex items-center p-4 bg-success/40 rounded-xl border border-success/50 text-success shadow-sm",
        )
    )


def _ProfileErrorFragment(errors: dict[str, str]):
    details = "; ".join(f"{key}: {msg}" for key, msg in errors.items())
    return HTMLContent(_RenderError(f"Project settings are invalid - {details}"))


def _PairErrorFragment(issues: list[ContractIssue]):
    details = "; ".join(f"{issue.code}: {issue.message}" for issue in issues)
    return HTMLContent(_RenderError(f"Topic/format contract violation - {details}"))


def _missing_media_paths(bundle) -> list[str]:
    """Absolute-path existence pre-flight for every non-None media role."""
    missing: list[str] = []
    for role, path in (
        ("music", bundle.music_path),
        ("font", bundle.font_path),
        ("watermark", bundle.watermark_path),
        ("bg_clip", bundle.bg_clip_path),
        ("outro_clip", bundle.outro_clip_path),
    ):
        if path and not os.path.exists(path):
            missing.append(f"Missing {role} media: {path}")
    return missing


class RenderApiController(Controller):
    def __init__(
        self,
        scripts: ScriptService,
        ideas: IdeaService,
        history: HistoryService,
        project_service: ProjectService,
        task_manager: BackgroundTaskManager,
        config: AppConfig,
        progress_store: RenderProgressStore | None = None,
        runs: RunService | None = None,
        tasks: RenderTaskRegistry | None = None,
        store: SettingsStore | None = None,
        asset_resolver: AssetResolver | None = None,
        profile_service: ProjectProfileService | None = None,
    ):
        self.scripts = scripts
        self.ideas = ideas
        self.history = history
        self.project_service = project_service
        self.task_manager = task_manager
        self.config = config
        self.progress_store = progress_store or RenderProgressStore()
        self.runs = runs or None
        self.tasks = tasks or RenderTaskRegistry()
        self.store = store
        self.asset_resolver = asset_resolver
        self.profile_service = profile_service

    @post("/api/render/start")
    async def start_render(self, request=None) -> HTMLContent:
        project_id = ""
        db_run_id = ""
        idea_index = None
        if request:
            try:
                ct = request.headers.get("content-type", "")
                if "json" in ct:
                    body = await request.json()
                    project_id = body.get("project_id", "")
                    db_run_id = body.get("run_id", "")
                    idea_index = body.get("idea_index")
                else:
                    form = await request.form()
                    project_id = form.get("project_id", "")
                    db_run_id = form.get("run_id", "")
                    ii = form.get("idea_index", "")
                    idea_index = int(ii) if ii.isdigit() else None
            except (AttributeError, TypeError, ValueError):
                pass

        saved = None
        idea: Idea | None = None
        idea_id = None
        pid = project_id
        if db_run_id and self.runs:
            run0 = await self.runs.get(db_run_id)
            if run0:
                if not pid:
                    pid = run0.project_id
                # Completed runs are terminal; reject before any snapshot,
                # link, or pipeline work so a legacy run_id POST cannot
                # overwrite the finished run's video artifact.
                if run0.status == RunStatus.COMPLETED:
                    return HTMLContent(
                        _RenderError(
                            f"Run {run0.id} is already complete and cannot be re-rendered; start a fresh render."
                        )
                    )
        if idea_index is not None and pid and self.runs:
            project = await self.project_service.get(pid)
            if project and project.idea_json:
                try:
                    raw_data = json.loads(project.idea_json)
                    if isinstance(raw_data, list) and 0 <= idea_index < len(raw_data):
                        idea_id = raw_data[idea_index].get("id")
                        sj = raw_data[idea_index].get("script_json")
                        if sj:
                            saved = json.loads(sj)
                        idea = Idea.from_dict(raw_data[idea_index])
                except (json.JSONDecodeError, TypeError):
                    pass

        # Resolve the effective profile once, from the shared resolver. The
        # snapshot written at run creation is the single source of truth the
        # pipeline renders from - nothing downstream re-reads config or the
        # global settings store.
        project = None
        if pid and self.project_service:
            project = await self.project_service.get(pid)
        profile = None
        if project is not None and self.profile_service is not None:
            profile = await self.profile_service.resolve(project)
            errors = self.profile_service.validate(profile)
            if errors:
                return _ProfileErrorFragment(errors)
            pair_issues = await self.profile_service.validate_pair_for_project(project)
            if any(issue.severity is Severity.ERROR for issue in pair_issues):
                return _PairErrorFragment(pair_issues)

        if saved is None:
            return HTMLContent(_RenderError("Script not found for this idea."))

        # Reuse a live render of the same idea instead of starting a duplicate
        # pipeline (they would collide on the same output files). A stale
        # "rendering" run whose task died is marked failed and replaced.
        # The whole claim section (scan -> create -> link -> mark_rendering)
        # runs under one per-idea lock so two concurrent identical POSTs
        # cannot both pass the scan before either run is marked rendering.
        async with _start_lock(f"{project_id}:{idea_id or ''}"):
            if not db_run_id and idea_id and self.runs and project_id:
                for r in await self.runs.list_by_project(project_id, limit=20):
                    if r.selected_idea_id == idea_id and r.status == "rendering":
                        task = self.tasks.get(r.id)
                        if task is not None and not task.done():
                            return HTMLContent(render_active_html(r.id, pid or project_id))
                        await self.runs.mark_failed(r.id, "Superseded by a new render")
                        break

            # Create a run if none provided; its settings snapshot freezes the
            # resolved profile before any status transition.
            if not db_run_id and project_id and self.runs:
                if profile is not None:
                    run = await self.runs.create_with_profile(
                        project_id=project_id,
                        title=idea.title if idea else "Render Run",
                        profile=profile,
                    )
                    notes = [
                        {"code": issue.code, "message": issue.message}
                        for issue in pair_issues
                        if issue.severity is not Severity.ERROR
                    ]
                    snapshot_updates: dict[str, Any] = {}
                    if notes:
                        snapshot_updates["pair_issues"] = notes
                    emphasis_words = (saved or {}).get("emphasis")
                    if isinstance(emphasis_words, list):
                        emphasis_words = ", ".join(
                            w for w in emphasis_words if isinstance(w, str) and w.strip()
                        )
                    if emphasis_words:
                        snapshot_updates["emphasis_words"] = emphasis_words
                    if snapshot_updates:
                        await self.runs.update_profile_snapshot(run.id, snapshot_updates)
                else:
                    run = await self.runs.create(
                        project_id=project_id, title=idea.title if idea else "Render Run"
                    )
                db_run_id = run.id

            # Link the run to the idea it renders, so each idea's render page
            # can show its own latest video instead of the project's most
            # recent one.
            if db_run_id and idea_id and self.runs:
                run_obj = await self.runs.get(db_run_id)
                if run_obj and run_obj.selected_idea_id != idea_id:
                    await self.runs.link_idea(db_run_id, idea_id)

            # The run's settings snapshot is authoritative for what gets
            # rendered; fall back to the freshly resolved profile (fresh-start
            # race) and then to config defaults only when no snapshot
            # machinery is available.
            snapshot = None
            if db_run_id and self.runs:
                snapshot = await self.runs.get_snapshot(db_run_id)
                if not snapshot and profile is not None:
                    snapshot = profile.snapshot_dict()

            if saved:
                from shorts_creator.pipeline.script_parser import (
                    apply_profile_overrides,
                )

                script = apply_profile_overrides(saved, snapshot)

            if db_run_id and self.runs:
                try:
                    await self.runs.mark_rendering(db_run_id)
                except Exception:  # noqa: BLE001, S110 - best-effort; pipeline below reports real failures
                    pass

        topic = idea.title if idea else script.title

        output_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "..", "data", "renders"
        )
        output_dir = os.path.abspath(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        os.chmod(output_dir, 0o755)
        stream_run_id = re.sub(r"[^a-z0-9_]", "", topic.lower().replace(" ", "_"))
        run_output = os.path.join(output_dir, f"{db_run_id or stream_run_id}.mp4")
        alias_output = os.path.join(output_dir, f"{stream_run_id}.mp4")
        output_path = run_output

        from shorts_creator.pipeline.pipeline import ReelPipeline, add_log_tee, remove_log_tee

        duration_seconds = self.config.default_duration
        caption_style = "highlight"
        reel_width = self.config.reel_width
        reel_height = self.config.reel_height
        assets = None
        if snapshot:
            duration_seconds = snapshot.get("duration_seconds") or duration_seconds
            caption_style = snapshot.get("caption_style") or caption_style
            reel_width = snapshot.get("reel_width") or reel_width
            reel_height = snapshot.get("reel_height") or reel_height
            if self.asset_resolver is not None:
                overrides = {
                    override_key: str(snapshot.get(project_key))
                    for project_key, override_key, _, _ in AssetResolver.REFS
                    if snapshot.get(project_key)
                }
                for url_key in (
                    "media_url_music",
                    "media_url_bg_clip",
                    "media_url_outro",
                    "media_url_watermark",
                ):
                    if snapshot.get(url_key):
                        overrides[url_key] = snapshot[url_key]
                bundle = await self.asset_resolver.resolve(None, overrides)
                if bundle:
                    assets = _absolutize_asset_bundle(bundle)
                    assets = await _materialize_url_bundle(assets, db_run_id or stream_run_id)
                    missing = _missing_media_paths(assets)
                    if missing:
                        message = "; ".join(missing)
                        if db_run_id and self.runs:
                            try:
                                await self.runs.mark_failed(db_run_id, message)
                            except Exception:  # noqa: BLE001, S110 - failure is already being reported
                                pass
                        return HTMLContent(_RenderError(message))

        owner = db_run_id or stream_run_id
        from shorts_creator.formats import registry as format_registry
        from shorts_creator.pipeline.music_beat import build_beat_provider
        from shorts_creator.pipeline.render_config import RenderConfig

        format_name = snapshot.get("format_name") if snapshot else None
        fmt = format_registry.get(format_name) if format_name else None
        caption_styles = list(fmt.caption_styles) if fmt else ["highlight"]
        rank_style = "check" if format_name == "steps" else "number"
        beat_provider = None
        if fmt and "music_beat" in (fmt.requires.get("pipeline") or []):
            beat_provider = build_beat_provider()
        stages = snapshot.get("stages") if snapshot else None
        render_config = None
        if snapshot and any(
            snapshot.get(key)
            for key in (
                "layout",
                "palette",
                "style",
                "stage_accents",
                "section_holds",
                "background_motion",
                "loudness_target_lufs",
                "audio_normalize",
                "emphasis_style",
            )
        ):
            render_config = RenderConfig.resolve(fmt, snapshot)
        stock_api_keys = {}
        if self.store is not None:
            stock_api_keys = await self.store.get_credentials()
        from shorts_creator.topics import registry as topic_registry

        bg_queries: list[str] = []
        if project is not None:
            topic_obj = topic_registry.get(project.topic)
            bg_queries = list(getattr(topic_obj, "background_queries", None) or [])
        pipeline = ReelPipeline(
            topic=topic,
            output=output_path,
            dev=False,
            caption_style=caption_style,
            caption_styles=caption_styles,
            reel_width=reel_width,
            reel_height=reel_height,
            duration_seconds=duration_seconds,
            owner=owner,
            assets=assets,
            beat_provider=beat_provider,
            render_config=render_config,
            stages=stages,
            stock_api_keys=stock_api_keys,
            bg_source=(snapshot or {}).get("bg_source", ""),
            bg_mode=(snapshot or {}).get("bg_mode", ""),
            stock_provider=(snapshot or {}).get("stock_provider", "auto"),
            outro_text=(snapshot or {}).get("outro_text", ""),
            background_queries=bg_queries,
            voice_preset=(snapshot or {}).get("voice_preset", "natural"),
            hook_lead_in_seconds=(snapshot or {}).get("hook_lead_in_seconds", 0.0) or 0.0,
            rank_style=rank_style,
        )
        pipeline.idea = idea
        pipeline.script = script

        self.progress_store.create_queue(db_run_id)

        async def _on_pipeline_stage(stage: str, progress: float, message: str):
            self.progress_store.push(
                db_run_id,
                {
                    "event": "progress",
                    "data": {"stage": stage, "progress": progress, "message": message},
                },
            )
            if db_run_id and self.runs:
                try:
                    await self.runs.on_stage(db_run_id, stage, progress, message)
                except Exception:  # noqa: BLE001, S110 - stage tracking is best-effort
                    pass

        pipeline.progress_callback = _on_pipeline_stage

        async def _run():
            try:
                await _on_pipeline_stage("outputs", 0.0, "Starting render...")
                pipeline.run_dir = os.path.dirname(output_path)
                runs_log_dir = os.path.normpath(
                    os.path.join(os.path.dirname(output_path), "..", "runs")
                )
                os.makedirs(runs_log_dir, exist_ok=True)
                run_log_path = os.path.join(runs_log_dir, f"{db_run_id}.log")
                # Tee the pipeline's stage traces into a per-run file so a
                # failure is diagnosable after the fact; docker logs rotate
                # and the in-memory LogStore ring buffer overwrites old runs.
                # A per-stream tee (not a process-wide redirect) keeps
                # concurrent renders from clobbering sys.stdout for every
                # other request in the app.
                run_log = open(run_log_path, "a", buffering=1, encoding="utf-8")  # noqa: SIM115, ASYNC230 - background task; blocking tee is intentional
                try:
                    add_log_tee(run_log)
                    ok = await pipeline.run()
                finally:
                    remove_log_tee(run_log)
                    run_log.close()
                if ok:
                    duration = probe_duration(output_path) or (
                        getattr(script, "total_duration", 0) if script else 0
                    )
                    extract_poster_frame(output_path)
                    if alias_output != output_path and not os.path.exists(alias_output):
                        try:
                            shutil.copy2(output_path, alias_output)
                            run_720 = output_path.replace(".mp4", "_720p.mp4")
                            alias_720 = alias_output.replace(".mp4", "_720p.mp4")
                            if os.path.exists(run_720) and not os.path.exists(alias_720):
                                shutil.copy2(run_720, alias_720)
                        except OSError as exc:
                            print(f"   alias copy failed for {db_run_id}: {exc}")
                    db_failed = ""
                    if db_run_id and self.runs:
                        try:
                            await self.runs.mark_completed(db_run_id, output_path, duration)
                        except Exception as exc:  # noqa: BLE001 - DB is the source of truth; a failure must surface
                            db_failed = str(exc)
                    self.progress_store.push(
                        db_run_id,
                        {
                            "event": "complete",
                            "data": {
                                "output": output_path,
                                "run_id": db_run_id,
                                "duration_s": duration,
                            },
                        },
                    )
                    try:
                        await self.history.record_run(
                            {
                                "run_id": db_run_id,
                                "status": "failed" if db_failed else "completed",
                                "idea": topic,
                                "output": output_path,
                                "duration_s": duration,
                                "error": db_failed or None,
                            }
                        )
                    except Exception:  # noqa: BLE001 - JSON history is a log; DB already committed
                        print(f"   history write failed for {db_run_id}")
                    if db_failed:
                        raise RuntimeError(db_failed)
                else:
                    if db_run_id and self.runs:
                        try:
                            await self.runs.mark_failed(db_run_id, "Pipeline returned failure")
                        except Exception as exc:  # noqa: BLE001 - fall through to history + event
                            print(f"   mark_failed error: {exc}")
                    self.progress_store.push(
                        db_run_id,
                        {
                            "event": "failed",
                            "data": {"error": "Pipeline returned failure", "run_id": db_run_id},
                        },
                    )
                    try:
                        await self.history.record_run(
                            {
                                "run_id": db_run_id,
                                "status": "failed",
                                "idea": topic,
                                "output": output_path,
                                "error": "Pipeline returned failure",
                            }
                        )
                    except Exception as exc:  # noqa: BLE001 - best-effort
                        print(f"   history write failed for {db_run_id}: {exc}")
            except asyncio.CancelledError:
                still_rendering = True
                if db_run_id and self.runs:
                    run_obj = await self.runs.get(db_run_id)
                    still_rendering = run_obj is not None and run_obj.status == "rendering"
                if still_rendering:
                    self.progress_store.push(db_run_id, {"event": "cancelled", "data": {}})
                    await self.history.record_run(
                        {
                            "run_id": db_run_id,
                            "status": "cancelled",
                            "idea": topic,
                            "output": output_path,
                        }
                    )
                    if db_run_id and self.runs:
                        await self.runs.mark_failed(db_run_id, "Cancelled")
            except Exception as exc:  # noqa: BLE001 - record every failure mode
                await self.history.record_run(
                    {
                        "run_id": db_run_id,
                        "status": "failed",
                        "idea": topic,
                        "error": str(exc),
                    }
                )
                self.progress_store.push(
                    db_run_id, {"event": "failed", "data": {"error": str(exc)}}
                )
                if db_run_id and self.runs:
                    try:
                        await self.runs.mark_failed(db_run_id, str(exc))
                    except Exception as mark_err:  # noqa: BLE001 - the render error is already recorded; the DB write is best-effort
                        print(f"   mark_failed error: {mark_err}")
            finally:
                self.tasks.pop(db_run_id)

        task = self.task_manager.track_named(f"render:{db_run_id}", _run())
        self.tasks.register(db_run_id, task)
        self._start_watchdog(db_run_id, task, owner)

        return HTMLContent(render_active_html(db_run_id, pid or project_id))

    def _start_watchdog(self, run_id: str, task: asyncio.Task, owner: str = "") -> None:
        """Fail a run whose pipeline has made no progress for a long time.

        A pipeline stage that hangs (e.g. a subprocess that died without
        raising) would otherwise leave the run in "rendering" forever with
        the UI stuck on "Render Pipeline Active...".
        """

        async def watchdog() -> None:
            try:
                while True:
                    await asyncio.sleep(WATCHDOG_INTERVAL)
                    if task.done():
                        return
                    last = self.progress_store.last_activity(run_id)
                    if last is None:
                        return
                    stage_elapsed = self.progress_store.stage_elapsed(run_id) or 0.0
                    if (
                        time.monotonic() - last < STALE_RENDER_SECONDS
                        and stage_elapsed < STAGE_STALE_SECONDS
                    ):
                        continue
                    from shorts_creator.pipeline import subprocess_guard

                    subprocess_guard.kill_all(owner=owner or run_id)
                    if not task.done():
                        task.cancel()
                    msg = "Render stalled: no progress for 15 minutes"
                    self.progress_store.push(
                        run_id,
                        {
                            "event": "failed",
                            "data": {"error": msg, "run_id": run_id},
                        },
                    )
                    if self.runs:
                        try:
                            await self.runs.mark_failed(run_id, msg)
                        except Exception:  # noqa: BLE001, S110 - watchdog cleanup is best-effort
                            pass
                    return
            except asyncio.CancelledError:
                return

        self.task_manager.track_named(f"watchdog:{run_id}", watchdog())

    @get("/api/render/progress/{run_id}")
    async def render_progress_sse(self, request=None, run_id: str = "") -> StreamingResponse:
        async def event_gen():
            run = None
            if self.runs:
                run = await self.runs.get(run_id)
            if run is None:
                yield f"event: failed\ndata: {json.dumps({'error': 'Render not found'})}\n\n"
                return
            if run.status == "completed" and run.output_path:
                yield f"event: complete\ndata: {json.dumps({'output': run.output_path, 'run_id': run_id, 'duration_s': run.duration_s or 0})}\n\n"
                return
            if run.status == "failed":
                yield f"event: failed\ndata: {json.dumps({'error': run.error or 'Render failed', 'run_id': run_id})}\n\n"
                return
            async for event in self.progress_store.subscribe(run_id):
                if isinstance(event, str):
                    yield event
                    continue
                data = json.dumps(event.get("data", {}))
                event_type = event.get("event", "message")
                yield f"event: {event_type}\ndata: {data}\n\n"

        return StreamingResponse(event_gen(), media_type="text/event-stream")

    @get("/api/render/status")
    async def render_status(self, request=None) -> HTMLContent:
        recent = await self.history.get_recent(3)
        last = recent[0] if recent else None
        if last and last.get("status") == "completed":
            return HTMLContent(_RenderSuccess(last.get("output", "")))
        elif last and last.get("status") == "failed":
            return HTMLContent(_RenderError(last.get("error", "Unknown error")))
        return HTMLContent(_RenderError("No render running"))

    @post("/api/render/cancel/{run_id}")
    async def cancel_render(self, request=None, run_id: str = "") -> HTMLContent:
        from shorts_creator.pipeline import subprocess_guard

        subprocess_guard.kill_all(owner=run_id)
        task = self.tasks.get(run_id)
        if task and not task.done():
            task.cancel()
            self.progress_store.push(
                run_id, {"event": "cancelled", "data": {"message": "Cancelled by user"}}
            )
            return HTMLContent(_RenderError("Render cancelled"))
        return HTMLContent(_RenderError("No active render to cancel"))

    @post("/api/render/generate-seo")
    async def generate_seo(self, request=None) -> HTMLContent:
        qp = getattr(request, "query_params", {}) if request else {}
        project_id = qp.get("project_id", "")
        idea_id = qp.get("idea_id", "")
        from shorts_creator.topics import ParsedScript, ScriptSection

        script: ParsedScript | None = None
        targeted = bool(project_id and idea_id)
        if targeted:
            saved = await self.project_service.get_script(project_id, idea_id)
            if saved:
                script = ParsedScript(
                    title=saved.get("title", ""),
                    sections=[ScriptSection(**s) for s in saved.get("sections", [])],
                    total_duration=saved.get("total_duration", 0),
                    word_count=saved.get("word_count", 0),
                    pacing_wps=saved.get("pacing_wps", 0),
                    emotional_arc=saved.get("emotional_arc"),
                    metadata=saved.get("metadata"),
                )
        if not script:
            script = self.scripts.last_script
        if not script:
            projects = await self.project_service.list_recent(10)
            for project in projects:
                if not project or not project.idea_json:
                    continue
                try:
                    raw_data = json.loads(project.idea_json)
                    if not isinstance(raw_data, list):
                        continue
                    for idea_dict in raw_data:
                        sj = idea_dict.get("script_json")
                        if not sj:
                            continue
                        saved = json.loads(sj)
                        sections = [ScriptSection(**s) for s in saved.get("sections", [])]
                        script = ParsedScript(
                            title=saved.get("title", ""),
                            sections=sections,
                            total_duration=saved.get("total_duration", 0),
                            word_count=saved.get("word_count", 0),
                            pacing_wps=saved.get("pacing_wps", 0),
                            emotional_arc=saved.get("emotional_arc"),
                            metadata=saved.get("metadata"),
                        )
                        self.scripts._last_script = script
                        break
                    if script:
                        break
                except (json.JSONDecodeError, TypeError):
                    continue

        if not script:
            return HTMLContent(
                str(
                    el(
                        "p",
                        "No script available. Generate a script first.",
                        class_="text-muted-foreground text-sm italic",
                    )
                )
            )

        from shorts_creator.ui.components.script_viewer import SeoPanel

        meta = await self.scripts.generate_seo(script)
        if not script.metadata:
            script.metadata = {}
        script.metadata["seo"] = meta
        if not meta:
            return HTMLContent(
                str(
                    el(
                        "div",
                        el(
                            "p",
                            "SEO generation failed \u2014 the LLM provider may be unavailable.",
                            class_="text-destructive text-sm font-semibold",
                        ),
                        el(
                            "p",
                            "Check that Ollama is running and the model is loaded.",
                            class_="text-muted-foreground text-xs mt-1",
                        ),
                        class_="p-4 bg-card/40 rounded-xl border border-destructive/60 text-center",
                    )
                )
            )
        if targeted:
            self.scripts._last_script = script
            if saved is not None:
                saved["metadata"] = {**(saved.get("metadata") or {}), "seo": meta}
                await self.project_service.save_script(project_id, idea_id, saved)
            if qp.get("card") == "1":
                from shorts_creator.controllers.videos import _build_groups, _GroupCard

                recent = await self.history.get_recent(100)
                completed = [r for r in recent if r.get("status") == "completed"]
                groups = await _build_groups(completed, self.runs, self.project_service)
                for g in groups:
                    if g["project_id"] == project_id:
                        return HTMLContent(_GroupCard(g, hx_target="#latest-render", card=True))
                return HTMLContent("")
            from shorts_creator.controllers.videos import videos_body_html

            return HTMLContent(
                await videos_body_html(
                    self.history, self.runs, self.project_service, self.scripts, project_id
                )
            )
        return HTMLContent(SeoPanel(meta))

    @get("/api/videos/download/{run_id}")
    async def download_video(self, request=None, run_id: str = "") -> FileResponse:
        run = await self.history.get_run(run_id)
        if not run:
            return html_response("Run not found", status_code=404)
        output = run.get("output", "")
        if not output or not os.path.exists(output):
            return html_response("Video file not found", status_code=404)
        return FileResponse(output, media_type="video/mp4", filename=os.path.basename(output))

    @get("/api/videos/poster/{run_id}")
    async def video_poster(self, request=None, run_id: str = "") -> FileResponse:
        run = await self.history.get_run(run_id)
        if not run:
            return html_response("Run not found", status_code=404)
        master = run.get("output", "")
        if not master or not os.path.exists(master):
            return html_response("Video file not found", status_code=404)
        poster = os.path.splitext(master)[0] + ".jpg"
        if not os.path.exists(poster):
            extract_poster_frame(master)
        if not os.path.exists(poster):
            return html_response("Poster not found", status_code=404)
        return FileResponse(poster, media_type="image/jpeg")

    @get("/api/videos/preview/{run_id}")
    async def preview_video(self, request=None, run_id: str = "") -> FileResponse:
        run = await self.history.get_run(run_id)
        if not run:
            return html_response("Run not found", status_code=404)
        master = run.get("output", "")
        if not master:
            return html_response("Video file not found", status_code=404)
        preview = master.replace(".mp4", "_720p.mp4")
        if os.path.exists(preview):
            return FileResponse(preview, media_type="video/mp4")
        if os.path.exists(master):
            return FileResponse(master, media_type="video/mp4")
        return html_response("Video file not found", status_code=404)
