import dataclasses
import json
import uuid

from lexigram.tasks import BackgroundTaskManager
from lexigram.ui import el
from lexigram.web import Controller, HTMLContent, get, post
from starlette.datastructures import UploadFile
from starlette.requests import Request

from shorts_creator.services.core import AppConfig
from shorts_creator.services.idea_service import IdeaService
from shorts_creator.services.progress_store import ProgressStore
from shorts_creator.services.project_profile_service import ProjectProfileService
from shorts_creator.services.project_service import ProjectService
from shorts_creator.ui.components.concept_list_item import ConceptListItem, IdeaEditForm
from shorts_creator.ui.icons import loader


def _field_str(value: str | UploadFile | None) -> str:
    """Starlette form fields are ``str | UploadFile``; this API only sends text."""
    if isinstance(value, UploadFile):
        return ""
    return value or ""


class IdeasApiController(Controller):
    def __init__(
        self,
        ideas: IdeaService,
        config: AppConfig,
        projects: ProjectService,
        progress_store: ProgressStore,
        task_manager: BackgroundTaskManager,
        profile_service: ProjectProfileService | None = None,
    ):
        self.ideas = ideas
        self.config = config
        self.projects = projects
        self.progress_store = progress_store
        self.task_manager = task_manager
        self.profile_service = profile_service

    @post("/api/ideas/generate")
    async def generate(self, request: Request) -> HTMLContent:
        st = "self_improvement"
        project_id = ""
        ct = request.headers.get("content-type", "")
        if "json" in ct:
            try:
                body = await request.json()
                st = body.get("topic", st)
                project_id = body.get("project_id", "")
            except (AttributeError, TypeError, ValueError):
                pass
        else:
            try:
                form = await request.form()
                st = _field_str(form.get("topic")) or st
                project_id = _field_str(form.get("project_id"))
            except (AttributeError, TypeError, ValueError):
                pass

        op_id = f"ideas:{project_id or uuid.uuid4().hex[:8]}"
        self.progress_store.create_queue(op_id)

        async def _run():
            try:
                self.progress_store.push(
                    op_id,
                    {
                        "event": "progress",
                        "data": {
                            "stage": "ideas",
                            "progress": 0.0,
                            "message": "Generating ideas...",
                        },
                    },
                )
                voice = None
                if self.profile_service is not None and project_id:
                    project_obj = await self.projects.get(project_id)
                    if project_obj:
                        profile = await self.profile_service.resolve(project_obj)
                        voice = {
                            "audience_persona": (
                                profile.audience_persona.value if profile.audience_persona else None
                            ),
                            "banned_topics": (
                                profile.banned_topics.value if profile.banned_topics else None
                            ),
                            "tone_rules": (
                                profile.tone_rules.value if profile.tone_rules else None
                            ),
                        }
                        if not any(voice.values()):
                            voice = None
                ideas = await self.ideas.generate_ideas(
                    count=10, focus="all categories", topic=st, voice=voice
                )
                if project_id:
                    await self.projects.prepend_ideas(
                        project_id, [dataclasses.asdict(i) for i in ideas]
                    )
                self.progress_store.push(
                    op_id,
                    {
                        "event": "complete",
                        "data": {"message": f"Generated {len(ideas)} new ideas"},
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

        self.task_manager.track_named(f"ideas:{op_id}", _run())

        refresh_url = f"/projects/{project_id}/scripts" if project_id else "/projects"
        return HTMLContent(
            str(
                el(
                    "div",
                    el(
                        "div",
                        loader(),
                        el(
                            "span",
                            "Generating Ideas...",
                            class_="text-primary font-semibold text-xs font-mono animate-pulse",
                        ),
                        id="ideas-status",
                        class_="flex items-center gap-2",
                    ),
                    el(
                        "script",
                        f"""var btn = document.querySelector('button[hx-post="/api/ideas/generate"]');
if (btn) {{ btn.classList.add('busy'); btn.setAttribute('aria-disabled', 'true');
function lockBtn() {{ btn.disabled = true; }}
lockBtn();
document.addEventListener('htmx:afterRequest', function onDone(e) {{ if (e.detail.elt === btn) {{ document.removeEventListener('htmx:afterRequest', onDone); lockBtn(); }} }}); }}
window.__lp.connect('{op_id}', function(err){{ if (err) {{ window.showToast(err.message || 'Idea generation failed', 'error'); }} htmx.ajax('GET', '{refresh_url}', {{target:'#main-content', swap:'innerHTML', pushUrl:true}}); }});""",
                    ),
                )
            )
        )

    @post("/api/ideas/delete")
    async def delete(self, request: Request) -> HTMLContent:
        project_id = ""
        idea_index = 0
        sort = ""
        page = 0
        ct = request.headers.get("content-type", "")
        if "json" in ct:
            try:
                body = await request.json()
                idea_index = int(body.get("idea_index", 0))
                project_id = body.get("project_id", body.get("run_id", ""))
                sort = body.get("sort", "")
                page = int(body.get("page", 0)) if body.get("page", "").isdigit() else 0
            except (AttributeError, TypeError, ValueError):
                pass
        else:
            try:
                form = await request.form()
                idea_index = int(_field_str(form.get("idea_index", "0")))
                project_id = _field_str(form.get("project_id") or form.get("run_id"))
                sort = _field_str(form.get("sort"))
                page_raw = _field_str(form.get("page", ""))
                page = int(page_raw) if page_raw.isdigit() else 0
            except (AttributeError, TypeError, ValueError):
                pass
        deleted = False
        if project_id:
            project = await self.projects.get(project_id)
            if project:
                try:
                    idea_dicts = json.loads(project.idea_json) if project.idea_json else []
                    if isinstance(idea_dicts, list) and 0 <= idea_index < len(idea_dicts):
                        idea_id = idea_dicts[idea_index].get("id", "")
                        if idea_id:
                            await self.projects.delete_idea(project_id, idea_id)
                            deleted = True
                except (json.JSONDecodeError, TypeError):
                    pass

        ideas = []
        if project_id:
            project = await self.projects.get(project_id)
            if project and project.idea_json:
                try:
                    raw = json.loads(project.idea_json)
                    if isinstance(raw, list):
                        from shorts_creator.topics.base import Idea

                        ideas = [Idea(**d) for d in raw]
                except (json.JSONDecodeError, TypeError):
                    pass
        if sort == "score":
            ideas = sorted(ideas, key=lambda x: getattr(x, "quotability_score", 0), reverse=True)
        page_size = 10
        total_pages = max(1, (len(ideas) + page_size - 1) // page_size)
        if page >= total_pages:
            page = total_pages - 1
        offset = page * page_size
        page_ideas = ideas[offset : offset + page_size]
        items = [
            ConceptListItem(idea, i + 1, idea_index=i, project_id=project_id, sort=sort, page=page)
            for i, idea in enumerate(page_ideas)
        ]
        if not items:
            return HTMLContent(
                str(
                    el(
                        "p",
                        "No ideas. Generate ideas to start.",
                        class_="text-muted-foreground text-xs italic p-3 border border-border text-center",
                    )
                )
                + (toast("Idea deleted") if deleted else "")
            )
        return HTMLContent("".join(items) + (toast("Idea deleted") if deleted else ""))

    @get("/api/ideas/edit/{project_id}/{idea_index}")
    async def edit_form(
        self, request=None, project_id: str = "", idea_index: int = 0
    ) -> HTMLContent:
        idea = None
        if project_id:
            project = await self.projects.get(project_id)
            if project and project.idea_json:
                try:
                    data = json.loads(project.idea_json)
                    if isinstance(data, list) and 0 <= idea_index < len(data):
                        from shorts_creator.topics.base import Idea

                        idea = Idea.from_dict(data[idea_index])
                except (json.JSONDecodeError, TypeError):
                    pass
        if not idea:
            return HTMLContent(str(el("p", "Idea not found", class_="text-destructive text-xs")))
        return HTMLContent(str(IdeaEditForm(idea, idea_index, project_id=project_id)))

    @post("/api/ideas/update")
    async def update(self, request: Request) -> HTMLContent:
        project_id = ""
        idea_index = 0
        sort = ""
        data: dict = {}
        ct = request.headers.get("content-type", "")
        if "json" in ct:
            try:
                data = await request.json()
            except (AttributeError, TypeError, ValueError):
                data = {}
        else:
            try:
                data = dict(await request.form())
            except (AttributeError, TypeError, ValueError):
                data = {}
        project_id = str(data.get("project_id", data.get("run_id", "")))
        try:
            idea_index = int(data.get("idea_index", 0))
        except (TypeError, ValueError):
            idea_index = 0
        sort = str(data.get("sort", ""))
        updates = {}
        for key in ("title", "hook_line", "core_message", "target_audience"):
            if key in data:
                updates[key] = str(data[key])
        updated = False
        if project_id and updates:
            project = await self.projects.get(project_id)
            if project and project.idea_json:
                try:
                    idea_dicts = json.loads(project.idea_json)
                    if isinstance(idea_dicts, list) and 0 <= idea_index < len(idea_dicts):
                        idea_id = idea_dicts[idea_index].get("id", "")
                        if idea_id:
                            await self.projects.update_idea(project_id, idea_id, updates)
                            updated = True
                except (json.JSONDecodeError, TypeError):
                    pass
        return HTMLContent(
            await self._render_one(project_id, idea_index, sort)
            + (toast("Idea saved") if updated else "")
        )

    async def _render_one(self, project_id: str, idea_index: int, sort: str, page: int = 0) -> str:
        ideas = []
        if project_id:
            project = await self.projects.get(project_id)
            if project and project.idea_json:
                try:
                    raw = json.loads(project.idea_json)
                    if isinstance(raw, list):
                        from shorts_creator.topics.base import Idea

                        ideas = [Idea(**d) for d in raw]
                except (json.JSONDecodeError, TypeError):
                    pass
        if ideas and 0 <= idea_index < len(ideas):
            return str(
                ConceptListItem(
                    ideas[idea_index],
                    idea_index + 1,
                    idea_index=idea_index,
                    project_id=project_id,
                    sort=sort,
                    page=page,
                )
            )
        return '<p class="text-muted-foreground text-xs italic">Idea not found</p>'

    @get("/api/ideas/cancel-edit/{project_id}/{idea_index}")
    async def cancel_edit(
        self, request=None, project_id: str = "", idea_index: int = 0
    ) -> HTMLContent:
        return HTMLContent(await self._render_one(project_id, idea_index, ""))


def toast(msg, type="success"):
    return f'<script>window.showToast("{msg}","{type}")</script>'
