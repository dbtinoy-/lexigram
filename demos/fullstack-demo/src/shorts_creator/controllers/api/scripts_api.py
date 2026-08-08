import json
import uuid
from dataclasses import asdict

from lexigram.tasks import BackgroundTaskManager
from lexigram.ui import el
from lexigram.web import Controller, HTMLContent, post
from starlette.requests import Request

from shorts_creator.controllers.api.ideas_api import _field_str, toast
from shorts_creator.services.core import AppConfig
from shorts_creator.services.idea_service import IdeaService
from shorts_creator.services.progress_store import ProgressStore
from shorts_creator.services.project_profile_service import ProjectProfileService
from shorts_creator.services.project_service import ProjectService
from shorts_creator.services.run_service import RunService
from shorts_creator.services.script_service import ScriptService
from shorts_creator.ui.components.script_viewer import seo_field_wrapper
from shorts_creator.ui.icons import alert, loader


class ScriptsApiController(Controller):
    def __init__(
        self,
        scripts: ScriptService,
        ideas: IdeaService,
        config: AppConfig,
        runs: RunService,
        projects: ProjectService,
        progress_store: ProgressStore,
        task_manager: BackgroundTaskManager,
        profile_service: ProjectProfileService | None = None,
    ):
        self.scripts = scripts
        self.ideas = ideas
        self.config = config
        self.runs = runs
        self.projects = projects
        self.progress_store = progress_store
        self.task_manager = task_manager
        self.profile_service = profile_service

    @post("/api/scripts/generate")
    async def generate(self, request: Request) -> HTMLContent:
        idea_index = 0
        project_id = ""

        ct = request.headers.get("content-type", "")
        if "json" in ct:
            try:
                body = await request.json()
                idea_index = int(body.get("idea_index", 0))
                project_id = body.get("project_id", "")
            except (AttributeError, TypeError, ValueError):
                pass
        else:
            try:
                form = await request.form()
                idea_index = int(_field_str(form.get("idea_index", "0")))
                project_id = _field_str(form.get("project_id"))
            except (AttributeError, TypeError, ValueError):
                pass

        cached = []
        if project_id:
            project = await self.projects.get(project_id)
            if project and project.idea_json:
                try:
                    data = json.loads(project.idea_json)
                    if isinstance(data, list):
                        from shorts_creator.topics.base import Idea

                        cached = [Idea.from_dict(d) for d in data]
                except (json.JSONDecodeError, TypeError):
                    pass

        if not cached:
            return HTMLContent(
                str(
                    el(
                        "div",
                        alert(),
                        el(
                            "span",
                            " No ideas available. Generate ideas first using the Generate Ideas button.",
                            class_="ml-2 font-medium",
                        ),
                        class_="flex items-center text-warning p-4 bg-warning/40 rounded-xl border border-warning/50 text-xs font-mono",
                    )
                )
            )

        if idea_index < 0 or idea_index >= len(cached):
            idea_index = 0
        idea = cached[idea_index]

        idea_id = ""
        if project_id:
            project = await self.projects.get(project_id)
            if project and project.idea_json:
                try:
                    raw_data = json.loads(project.idea_json)
                    if isinstance(raw_data, list) and 0 <= idea_index < len(raw_data):
                        idea_id = raw_data[idea_index].get("id", "")
                        if not idea_id:
                            idea_id = str(uuid.uuid4())
                            raw_data[idea_index]["id"] = idea_id
                            project.idea_json = json.dumps(raw_data)
                            await self.projects.repo.update(project)
                except (json.JSONDecodeError, TypeError):
                    pass

        op_id = f"script:{project_id or 'project'}:{idea_index}:{uuid.uuid4().hex[:6]}"
        self.progress_store.create_queue(op_id)

        async def _run():
            try:
                self.progress_store.push(
                    op_id,
                    {
                        "event": "progress",
                        "data": {
                            "stage": "research",
                            "progress": 0.0,
                            "message": "Researching content angles...",
                        },
                    },
                )
                fmt_name = project.format if project else ""
                pacing_wps = None
                voice = None
                if self.profile_service is not None and project is not None:
                    profile = await self.profile_service.resolve(project)
                    pacing = profile.pacing_wps
                    pacing_wps = pacing.value if pacing and pacing.value else None
                    voice = {
                        "audience_persona": (
                            profile.audience_persona.value if profile.audience_persona else None
                        ),
                        "banned_topics": (
                            profile.banned_topics.value if profile.banned_topics else None
                        ),
                        "tone_rules": (profile.tone_rules.value if profile.tone_rules else None),
                    }
                    if not any(voice.values()):
                        voice = None
                script = await self.scripts.generate_script(
                    idea,
                    format_name=fmt_name,
                    pacing_wps=pacing_wps,
                    voice=voice,
                )
                if project_id and idea_id:
                    await self.projects.save_script(project_id, idea_id, asdict(script))
                self.progress_store.push(
                    op_id,
                    {
                        "event": "complete",
                        "data": {"message": f"Script generated: {script.title}"},
                    },
                )
            except Exception as exc:  # noqa: BLE001 - report background-task failure to the UI
                self.progress_store.push(
                    op_id,
                    {
                        "event": "failed",
                        "data": {"error": str(exc)},
                    },
                )

        self.task_manager.track_named(f"script:{op_id}", _run())

        refresh_url = (
            f"/projects/{project_id}/scripts?idea_index={idea_index}"
            if project_id
            else f"/scripts?idea_index={idea_index}"
        )
        return HTMLContent(
            str(
                el(
                    "div",
                    el(
                        "div",
                        loader(),
                        el(
                            "span",
                            "Generating Script...",
                            class_="text-primary font-semibold text-xs font-mono animate-pulse",
                        ),
                        id="script-status",
                        class_="flex items-center gap-2",
                    ),
                    el(
                        "script",
                        f"""var btn = document.querySelector('button[hx-post="/api/scripts/generate"]');
if (btn) {{ btn.classList.add('busy'); btn.setAttribute('aria-disabled', 'true');
function lockBtn() {{ btn.disabled = true; }}
lockBtn();
document.addEventListener('htmx:afterRequest', function onDone(e) {{ if (e.detail.elt === btn) {{ document.removeEventListener('htmx:afterRequest', onDone); lockBtn(); }} }}); }}
window.__lp.connect('{op_id}', function(err){{ if (err) {{ window.showToast(err.message || 'Script generation failed', 'error'); }} htmx.ajax('GET', '{refresh_url}', {{target:'#main-content', swap:'innerHTML', pushUrl:true}}); }});""",
                    ),
                )
            )
        )

    def _section_wrapper(
        self, project_id: str, idea_index: int, section_name: str, text: str
    ) -> str:
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        kid = f"sec-{section_name}-{idea_index}"
        return (
            f'<div id="sec-wrapper-{section_name}-{idea_index}">'
            f'<textarea id="{kid}" '
            f'class="w-full text-foreground text-sm mt-2 leading-relaxed bg-background/80 border border-border/60 rounded-lg p-2 focus:outline-none focus:border-primary/60 font-sans resize-y min-h-[60px]" rows=3>'
            f"{escaped}</textarea>"
            "</div>"
        )

    @post("/api/scripts/section/update")
    async def update_section(self, request: Request) -> HTMLContent:
        try:
            body = await request.json()
            project_id = body.get("project_id", "")
            idea_index = int(body.get("idea_index", 0))
            section_name = body.get("section_name", "")
            new_text = body.get("text", "")
        except (AttributeError, TypeError, ValueError):
            return HTMLContent('<div class="text-destructive text-xs">Invalid request</div>')
        if not project_id or not section_name:
            return HTMLContent('<div class="text-destructive text-xs">Missing fields</div>')
        try:
            project = await self.projects.get(project_id)
            if not project or not project.idea_json:
                return HTMLContent('<div class="text-destructive text-xs">Project not found</div>')
            raw_data = json.loads(project.idea_json)
            if not isinstance(raw_data, list) or not (0 <= idea_index < len(raw_data)):
                return HTMLContent('<div class="text-destructive text-xs">Idea not found</div>')
            idea_id = raw_data[idea_index].get("id", "")
            if not idea_id:
                return HTMLContent('<div class="text-destructive text-xs">Idea has no id</div>')

            script = await self.projects.get_script(project_id, idea_id)
            if not script:
                return HTMLContent('<div class="text-destructive text-xs">Script not found</div>')
            sections = script.get("sections", [])
            for sec in sections:
                if sec.get("name", "").lower() == section_name.lower():
                    sec["text"] = new_text
                    break
            script["sections"] = sections
            await self.projects.save_script(project_id, idea_id, script)
        except Exception as exc:  # noqa: BLE001 - surface save failure to the user
            return HTMLContent(
                self._section_wrapper(project_id, idea_index, section_name, new_text)
                + toast(f"Save failed: {exc}", "error")
            )
        return HTMLContent(
            self._section_wrapper(project_id, idea_index, section_name, new_text)
            + toast("Section saved")
        )

    @post("/api/scripts/seo/update")
    async def update_seo(self, request: Request) -> HTMLContent:
        SEO_FIELDS = {
            "youtube_title": "YouTube Title",
            "youtube_description": "YouTube Description",
            "youtube_tags": "YouTube Tags",
            "facebook_caption": "Facebook Caption",
        }
        try:
            body = await request.json()
            project_id = body.get("project_id", "")
            idea_id = body.get("idea_id", "")
            key = body.get("key", "")
            new_text = body.get("text", "")
        except (AttributeError, TypeError, ValueError):
            return HTMLContent('<div class="text-destructive text-xs">Invalid request</div>')
        label = SEO_FIELDS.get(key)
        if not project_id or not idea_id or not label:
            return HTMLContent('<div class="text-destructive text-xs">Missing fields</div>')
        try:
            script = await self.projects.get_script(project_id, idea_id)
            if not script:
                return HTMLContent('<div class="text-destructive text-xs">Script not found</div>')
            metadata = dict(script.get("metadata") or {})
            seo = dict(metadata.get("seo") or {})
            seo[key] = new_text
            metadata["seo"] = seo
            script["metadata"] = metadata
            await self.projects.save_script(project_id, idea_id, script)
        except Exception as exc:  # noqa: BLE001 - surface save failure to the user
            return HTMLContent(
                seo_field_wrapper(key, label, new_text, project_id, idea_id)
                + toast(f"Save failed: {exc}", "error")
            )
        return HTMLContent(
            seo_field_wrapper(key, label, new_text, project_id, idea_id) + toast("SEO saved")
        )
