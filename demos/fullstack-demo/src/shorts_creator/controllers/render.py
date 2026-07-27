import json
import os

from lexigram.ui import el, raw, render_to_string
from lexigram.web import Controller, HTMLContent, get
from markupsafe import Markup

from shorts_creator.formats import registry as formats
from shorts_creator.services.core import AppConfig
from shorts_creator.services.idea_service import IdeaService
from shorts_creator.services.project_profile_service import ProjectProfileService
from shorts_creator.services.project_service import ProjectService
from shorts_creator.services.project_state import ProjectStateService
from shorts_creator.services.run_service import RunService
from shorts_creator.services.script_service import ScriptService
from shorts_creator.services.settings_store import SettingsStore
from shorts_creator.ui.button import ActionButton
from shorts_creator.ui.components.pipeline_tracker import PipelineTracker
from shorts_creator.ui.components.settings_profile import caption_style_label
from shorts_creator.ui.icons import alert, video_icon, zap
from shorts_creator.ui.pages.new_project import _preview_phone, composer_preview_js, preview_styles
from shorts_creator.ui.shell import AppLayout

RENDER_STAGES = [
    ("outputs", "Save Outputs", "Write idea, script, caption, and SEO files"),
    ("project", "Create Project", "Prepare ffmpeg compose plan (vertical profile)"),
    (
        "timeline",
        "Build Timeline",
        "Fetch background, synthesize narration, group captions, assemble clips",
    ),
    ("render", "Render Video", "GPU-accelerated H.265 export via NVENC"),
    ("finalize", "Finalize", "Extract screenshots and transcode 720p preview"),
]


class RenderController(Controller):
    def __init__(
        self,
        ideas: IdeaService,
        scripts: ScriptService,
        config: AppConfig,
        runs: RunService,
        project_service: ProjectService,
        store: SettingsStore,
        profile_service: ProjectProfileService | None = None,
    ):
        self.layout = AppLayout()
        self.ideas = ideas
        self.scripts = scripts
        self.config = config
        self.runs = runs
        self.project_service = project_service
        self.store = store
        self.profile_service = profile_service
        self.state = ProjectStateService(project_service, runs)

    @get("/projects/{id}/render")
    async def render_page(self, request=None, id: str = "") -> HTMLContent:
        qp = getattr(request, "query_params", {}) if request else {}
        project_id = id
        run_id = qp.get("run_id", "")
        idea_index_q = qp.get("idea_index")
        idea_index = (
            int(idea_index_q) if idea_index_q is not None and idea_index_q.isdigit() else None
        )

        if not project_id:
            from starlette.responses import RedirectResponse

            return RedirectResponse(url="/projects", status_code=302)

        project = await self.project_service.get(project_id)
        if not project:
            from starlette.responses import RedirectResponse

            return RedirectResponse(url="/projects", status_code=302)

        state = await self.state.for_project(project_id)
        cached = state.ideas if state else []

        saved = None
        if idea_index is not None and 0 <= idea_index < len(cached):
            sj = (
                cached[idea_index].get("script_json")
                if isinstance(cached[idea_index], dict)
                else None
            )
            if sj:
                try:
                    saved = json.loads(sj)
                except (json.JSONDecodeError, TypeError):
                    pass
        elif cached:
            for i, idea in enumerate(cached):
                sj = idea.get("script_json") if isinstance(idea, dict) else None
                if sj:
                    try:
                        saved = json.loads(sj)
                        break
                    except (json.JSONDecodeError, TypeError):
                        pass

        if saved:
            from shorts_creator.topics import ParsedScript, ScriptSection

            sections = [ScriptSection(**s) for s in saved.get("sections", [])]
            self.scripts._last_script = ParsedScript(
                title=saved.get("title", ""),
                sections=sections,
                total_duration=saved.get("total_duration", 0),
                word_count=saved.get("word_count", 0),
                pacing_wps=saved.get("pacing_wps", 0),
                emotional_arc=saved.get("emotional_arc"),
                metadata=saved.get("metadata"),
            )

        # The specs tab resolves the same effective profile the render API
        # snapshots, so what the page previews is what the pipeline renders.
        profile = None
        if self.profile_service is not None:
            profile = await self.profile_service.resolve(project)

        last_script = self.scripts.last_script

        completed_run = None
        active_run = None
        try:
            idea_id = None
            if idea_index is not None and 0 <= idea_index < len(cached):
                idea_id = cached[idea_index].get("id")
            recent = await self.runs.list_by_project(project_id, limit=20)
            completed_run = next(
                (
                    r
                    for r in recent
                    if r.status == "completed"
                    and r.output_path
                    and os.path.exists(r.output_path)
                    and (idea_id is None or r.selected_idea_id == idea_id)
                ),
                None,
            )
            active_run = next(
                (
                    r
                    for r in recent
                    if r.status == "rendering"
                    and (idea_id is None or r.selected_idea_id == idea_id)
                ),
                None,
            )
        except Exception:  # noqa: BLE001, S110 - best-effort run lookup; page must render regardless
            pass

        stage_state = state.stage_state if state else []
        preview_html = ""
        empty_state_html = ""
        render_content: Markup | str = ""
        if active_run:
            render_content = Markup(render_active_html(active_run.id, project_id))
            preview_html = str(preview_styles) + composer_preview_js() + _preview_phone()
        elif completed_run:
            render_content = ""
            preview_html = str(preview_styles) + _preview_phone(
                background_src=f"/api/videos/preview/{completed_run.id}"
            )
        else:
            render_content = ""
            empty_state_html = Markup(
                _RenderEmptyState(last_script, cached, project_id=project_id, idea_index=idea_index)
            )
            preview_html = str(preview_styles) + composer_preview_js() + _preview_phone()
        content = render_to_string(
            el(
                "div",
                el(
                    "div",
                    el(
                        "h1",
                        "Render Engine Studio",
                        class_="text-2xl font-bold text-foreground tracking-tight",
                    ),
                    el(
                        "p",
                        "Video rendering pipeline — launch, monitor, and export",
                        class_="text-muted-foreground text-xs mt-1 font-mono",
                    ),
                    PipelineTracker("render", project_id=project_id, stage_state=stage_state),
                    class_="flex items-center justify-between gap-4 border-b border-border/80 pb-2 mb-6",
                ),
                el(
                    "div",
                    el("div", _PipelineStages(RENDER_STAGES)),
                    el(
                        "div",
                        el(
                            "h2",
                            "Video Player",
                            class_="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3 font-mono",
                        ),
                        el("div", render_content, id="render-output"),
                        Markup(preview_html),
                        class_="space-y-4",
                    ),
                    el(
                        "div",
                        el(
                            "h2",
                            "Specifications",
                            class_="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3 font-mono",
                        ),
                        _PipelineConfig(self.config, profile, project_id=project_id, run_id=run_id),
                        Markup(empty_state_html),
                        class_="space-y-4",
                    ),
                    class_="grid grid-cols-1 lg:grid-cols-3 gap-8 w-full mt-6",
                ),
                class_="w-full space-y-6",
            )
        )
        html = self.layout.render(content=content, title="Render Video", request=request)
        return HTMLContent(html)


def _source_badge(source: str) -> str:
    colors = {
        "project": "bg-success/60 text-success border-success/50",
        "topic": "bg-warning/60 text-warning border-warning/50",
        "global": "bg-primary/60 text-primary border-primary/50",
        "built_in": "bg-secondary text-foreground border-border",
        "config (yaml)": "bg-secondary text-foreground border-border",
        "global (db)": "bg-primary/60 text-primary border-primary/50",
    }
    cls = colors.get(source, "bg-secondary text-foreground border-border")
    return f'<span class="text-[10px] font-mono px-1.5 py-0.5 rounded border {cls}">{source}</span>'


_PROFILE_ASSET_LABELS = (
    ("asset_music_id", "Music"),
    ("asset_font_id", "Font"),
    ("asset_watermark_id", "Watermark"),
    ("asset_bg_clip_id", "Background Clip"),
    ("asset_outro_clip_id", "Outro Clip"),
)


def _PipelineConfig(config, profile, project_id: str = "", run_id: str = ""):
    rows = []
    if profile is not None:
        duration = profile.duration_seconds
        if duration is not None:
            rows.append(("Target Duration", f"{duration.value}s", duration.source.value))
        else:
            rows.append(("Target Duration", "—", "built_in"))
        if profile.caption_style is not None:
            fmt_def = formats.get(profile.format_name.value) if profile.format_name else None
            rows.append(
                (
                    "Caption Style",
                    caption_style_label(fmt_def, profile.caption_style.value) or "—",
                    profile.caption_style.source.value,
                )
            )
        else:
            rows.append(("Caption Style", "—", "built_in"))
        if profile.reel_width and profile.reel_height:
            rows.append(
                (
                    "Target Resolution",
                    f"{profile.reel_width.value}x{profile.reel_height.value} (9:16)",
                    profile.reel_width.source.value,
                )
            )
        else:
            rows.append(("Target Resolution", "—", "built_in"))
        chosen = [
            (label, setting)
            for key, label in _PROFILE_ASSET_LABELS
            for setting in [getattr(profile, key)]
            if setting is not None and setting.value
        ]
        if chosen:
            for label, setting in chosen:
                rows.append((f"Selected: {label}", str(setting.value), setting.source.value))
        else:
            rows.append(("Selected Assets", "None (global defaults)", "built_in"))
    else:
        rows = [
            (
                "Target Resolution",
                f"{config.reel_width}x{config.reel_height} (9:16)",
                "config (yaml)",
            ),
            ("Target Duration", f"{config.default_duration}s", "config (yaml)"),
        ]
    settings_href = f"/projects/{project_id}/settings"
    if run_id:
        settings_href += f"?run_id={run_id}"
    return raw(
        el(
            "div",
            el(
                "div",
                el(
                    "a",
                    "Project Settings →",
                    href=settings_href,
                    class_="text-[11px] font-mono font-semibold text-primary hover:text-primary",
                ),
                class_="flex justify-end gap-3 mb-3",
            ),
            el(
                "div",
                *(
                    el(
                        "div",
                        el(
                            "span", label, class_="text-xs font-mono text-muted-foreground shrink-0"
                        ),
                        el(
                            "div",
                            el(
                                "span",
                                value,
                                class_="text-xs font-mono text-foreground truncate max-w-[12rem]",
                            ),
                            Markup(_source_badge(source)),
                            class_="flex items-center gap-2 min-w-0",
                        ),
                        class_="flex items-center justify-between gap-3 py-2 border-b border-border/40 last:border-0",
                    )
                    for label, value, source in rows
                ),
                class_="rounded-xl border border-border/60 bg-background/50 px-4 py-2",
            ),
            class_="rounded-2xl border border-border/60 bg-card/40 p-4",
        )
    )


def _RenderEmptyState(script, ideas, project_id: str = "", idea_index: int | str | None = None):
    return raw(
        el(
            "div",
            el(
                "div",
                el(
                    "div",
                    video_icon(),
                    class_="w-12 h-12 rounded-full bg-secondary/80 border border-border/50 flex items-center justify-center text-primary mx-auto mb-3",
                ),
                el(
                    "h3",
                    "No video rendered yet",
                    class_="text-sm font-semibold text-foreground mb-1",
                ),
                el(
                    "p",
                    "Launch the pipeline to render your video. The preview and download will appear here.",
                    class_="text-muted-foreground text-xs max-w-xs mx-auto leading-relaxed mb-5",
                ),
                _RenderButton(script, ideas, project_id=project_id, idea_index=idea_index),
                class_="text-center py-20 px-6 rounded-2xl border border-dashed border-border w-full",
            ),
        )
    )


def _PipelineStages(stages, stage_status=None):
    stage_status = stage_status or {}
    return raw(
        el(
            "div",
            el(
                "h2",
                "Pipeline Execution Stages",
                class_="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3 font-mono",
            ),
            el(
                "div",
                *(
                    el(
                        "div",
                        _stage_badge(i + 1, key, stage_status.get(key, "pending")),
                        el(
                            "div",
                            el(
                                "span",
                                label,
                                class_=f"stage-label {_stage_label_class(stage_status.get(key, 'pending'))}",
                            ),
                            el(
                                "p",
                                desc,
                                class_="text-muted-foreground text-[11px] mt-0.5 leading-snug",
                            ),
                            class_="flex flex-col",
                        ),
                        class_="pipeline-stage-item flex items-center gap-3 py-2.5 border-b border-border/30 last:border-0",
                    )
                    for i, (key, label, desc) in enumerate(stages)
                ),
                class_="flex flex-col",
            ),
            id="pipeline-stages",
            class_="w-full",
        )
    )


def _stage_badge(num, key, status):
    if status == "completed":
        return el(
            "span",
            "\u2713",
            class_="stage-badge w-6 h-6 rounded-full bg-success/80 border border-success/60 text-success text-xs font-bold flex items-center justify-center shrink-0",
        )
    elif status == "failed":
        return el(
            "span",
            "\u2717",
            class_="stage-badge w-6 h-6 rounded-full bg-destructive/80 border border-destructive/60 text-destructive text-xs font-bold flex items-center justify-center shrink-0",
        )
    elif status == "active":
        return el(
            "span",
            "\u25b6",
            class_="stage-badge w-6 h-6 rounded-full bg-primary/80 border border-primary/60 text-primary-foreground text-xs font-bold flex items-center justify-center shrink-0 animate-pulse",
        )
    else:
        return el(
            "span",
            str(num),
            class_="stage-badge w-6 h-6 rounded-full bg-secondary/80 border border-border/50 text-muted-foreground text-xs font-mono font-bold flex items-center justify-center shrink-0",
        )


def _stage_label_class(status):
    if status == "completed":
        return "text-success text-xs font-semibold"
    elif status == "failed":
        return "text-destructive text-xs font-semibold"
    elif status == "active":
        return "text-primary text-xs font-semibold"
    return "text-muted-foreground text-xs font-semibold"


def _RenderButton(script, ideas, project_id: str = "", idea_index: int | str | None = None):
    disabled = not script
    vals: dict[str, int | str] = {}
    if project_id:
        vals["project_id"] = project_id
    if idea_index is not None:
        vals["idea_index"] = idea_index
    hx_vals_str = json.dumps(vals) if vals else ""
    return raw(
        ActionButton(
            "Launch Video Render Pipeline",
            icon=zap() if not disabled else alert(),
            variant="primary",
            size="lg",
            hx_post="/api/render/start" if not disabled else "",
            hx_target="#render-output",
            hx_swap="innerHTML",
            hx_vals=hx_vals_str,
            disabled=disabled,
            class_extra="w-full",
        )
    )


def render_active_html(run_key: str, project_id: str = "") -> str:
    render_url_base = f"/projects/{project_id}/render" if project_id else "/projects"
    return f"""
    <div id="render-status">
      <div class="flex items-center justify-between p-4 bg-primary/40 rounded-xl border border-primary/50 shadow-sm">
        <div class="flex items-center">
          <svg class="animate-spin w-5 h-5 text-primary" viewBox="0 0 24 24" fill="none">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
          </svg>
          <span class="ml-2 text-primary font-semibold text-xs font-mono animate-pulse">Render Pipeline Active...</span>
        </div>
        <button onclick="this.disabled=true;cancelRender('{run_key}')" class="text-xs text-destructive hover:text-destructive bg-destructive/40 hover:bg-destructive/40 border border-destructive/50 px-3 py-1.5 rounded-lg transition-all font-mono font-semibold cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed">Cancel</button>
      </div>
    </div>
    <script>
    (function(){{
      var attempts = 0;
      function wire(es) {{
        es.addEventListener('progress', function(e) {{
          try {{
            var d = JSON.parse(e.data);
            if (d.stage && d.progress !== undefined) {{
              updatePipelineStages(d.stage, d.progress, d.message || '');
            }}
          }} catch(ex) {{}}
        }});
        es.addEventListener('complete', function(e) {{
          try {{
            var d = JSON.parse(e.data);
            var out = d.output || '';
            var rid = d.run_id || '';
            var dur = d.duration_s || 0;
            es.close();
            showRenderComplete(out, rid, dur);
            if (rid) {{
              htmx.ajax('GET', '{render_url_base}?run_id=' + encodeURIComponent(rid), {{
                target: '#main-content',
                swap: 'innerHTML',
                pushUrl: '{render_url_base}?run_id=' + encodeURIComponent(rid)
              }});
            }}
            resetPipelineStages();
          }} catch(ex) {{}}
        }});
        es.addEventListener('failed', function(e) {{
          try {{
            var d = JSON.parse(e.data);
            var err = d.error || 'Unknown error';
            var rid = d.run_id || '';
            es.close();
            showRenderFailed(err, rid);
            resetPipelineStages();
          }} catch(ex) {{}}
        }});
        es.addEventListener('cancelled', function(e) {{
          es.close();
          showRenderCancelled();
          resetPipelineStages();
        }});
        es.onerror = function() {{
          es.close();
          if (attempts < 5) {{
            attempts++;
            setTimeout(connect, Math.min(1000 * attempts, 5000));
          }} else {{
            htmx.ajax('GET', '{render_url_base}?run_id={run_key}', {{
              target: '#main-content',
              swap: 'innerHTML',
              pushUrl: '{render_url_base}?run_id={run_key}'
            }});
          }}
        }};
      }}
      function connect() {{
        var es = new EventSource('/api/render/progress/{run_key}');
        wire(es);
      }}
      connect();
      var stageOrder = {json.dumps([s[0] for s in RENDER_STAGES])};
      function updatePipelineStages(stage, progress, message) {{
        var container = document.getElementById('pipeline-stages');
        if (!container) return;
        var idx = stageOrder.indexOf(stage);
        var items = container.querySelectorAll('.pipeline-stage-item');
        for (var i = 0; i < items.length; i++) {{
          var badge = items[i].querySelector('.stage-badge');
          var label = items[i].querySelector('.stage-label');
          if (!badge) continue;
          if (i < idx) {{
            badge.innerHTML = '\\u2713';
            badge.className = 'stage-badge w-6 h-6 rounded-full bg-success/80 border border-success/60 text-success text-xs font-bold flex items-center justify-center shrink-0';
            if (label) label.className = 'stage-label text-success text-xs font-semibold';
          }} else if (i === idx) {{
            if (progress >= 1.0) {{
              badge.innerHTML = '\\u2713';
              badge.className = 'stage-badge w-6 h-6 rounded-full bg-success/80 border border-success/60 text-success text-xs font-bold flex items-center justify-center shrink-0';
              if (label) label.className = 'stage-label text-success text-xs font-semibold';
            }} else {{
              badge.innerHTML = '\\u25B6';
              badge.className = 'stage-badge w-6 h-6 rounded-full bg-primary/80 border border-primary/60 text-primary-foreground text-xs font-bold flex items-center justify-center shrink-0 animate-pulse';
              if (label) label.className = 'stage-label text-primary text-xs font-semibold';
            }}
          }} else {{
            badge.innerHTML = (i + 1).toString();
            badge.className = 'stage-badge w-6 h-6 rounded-full bg-secondary/80 border border-border/50 text-muted-foreground text-xs font-mono font-bold flex items-center justify-center shrink-0';
            if (label) label.className = 'stage-label text-muted-foreground text-xs font-semibold';
          }}
        }}
      }}
      function resetPipelineStages() {{
        var container = document.getElementById('pipeline-stages');
        if (!container) return;
        var items = container.querySelectorAll('.pipeline-stage-item');
        for (var i = 0; i < items.length; i++) {{
          var badge = items[i].querySelector('.stage-badge');
          var label = items[i].querySelector('.stage-label');
          if (badge) {{
            badge.innerHTML = (i + 1).toString();
            badge.className = 'stage-badge w-6 h-6 rounded-full bg-secondary/80 border border-border/50 text-muted-foreground text-xs font-mono font-bold flex items-center justify-center shrink-0';
          }}
          if (label) label.className = 'stage-label text-muted-foreground text-xs font-semibold';
        }}
      }}
      function showRenderComplete(output, runId, duration) {{
        var el = document.getElementById('render-status');
        if (el) el.innerHTML = '';
        if (!window.showToast) return;
        var msg = 'Render Complete!' + (duration ? ' <span class="text-xs opacity-75">' + duration.toFixed(1) + 's</span>' : '');
        if (runId) msg += ' <a href="/api/videos/download/' + encodeURIComponent(runId) + '" download class="toast-link">Download</a>';
        window.showToast(msg, 'success');
      }}
      function showRenderFailed(error, runId) {{
        var el = document.getElementById('render-status');
        if (!el) return;
        el.innerHTML = '<div class="space-y-3">' +
          '<div class="flex items-center p-4 bg-destructive/40 rounded-xl border border-destructive/50 text-destructive text-xs font-mono shadow-sm">' +
          '<svg class="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0zm-9 3.75h.008v.008H12v-.008z"/></svg>' +
          '<span class="ml-2 font-medium">Render Failed</span>' +
          '</div>' +
          '<div class="p-3 bg-card/60 rounded-lg border border-border/60 text-destructive text-xs font-mono">' + escapeHtml(error) + '</div>' +
          (runId ? '<button onclick="retryRender(\\'' + runId + '\\')" class="inline-flex items-center text-xs text-warning hover:text-warning bg-warning/20 hover:bg-warning/30 border border-warning/40 px-3 py-1.5 rounded-lg transition-all font-mono font-semibold cursor-pointer">Retry Render</button>' : '') +
          '</div>';
      }}
      function showRenderCancelled() {{
        var el = document.getElementById('render-status');
        if (!el) return;
        el.innerHTML = '<div class="flex items-center p-4 bg-secondary/40 rounded-xl border border-border/50 text-muted-foreground text-xs font-mono shadow-sm">' +
          '<span class="font-medium">Render Cancelled</span>' +
          '</div>';
      }}
      function escapeHtml(str) {{
        if (!str) return '';
        return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
      }}
      window.cancelRender = function(id) {{
        fetch('/api/render/cancel/' + id, {{method:'POST'}}).catch(function(){{}});
      }};
      window.retryRender = function(runId) {{
        htmx.ajax('GET', '{render_url_base}?run_id=' + runId, {{
          target: '#main-content',
          swap: 'innerHTML',
          pushUrl: '{render_url_base}?run_id=' + runId
        }});
      }};
    }})();
    </script>
    """
