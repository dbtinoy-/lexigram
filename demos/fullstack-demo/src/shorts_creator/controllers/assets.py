import os
from html import escape

from lexigram.ui import RawHTML, el, raw, render_to_string
from lexigram.web import Controller, HTMLContent, get, html_response
from markupsafe import Markup

from shorts_creator.models.asset import ASSET_TYPES, CLIP_ROLES
from shorts_creator.models.run import Run, RunStatus
from shorts_creator.services.asset_service import AssetService
from shorts_creator.services.project_service import ProjectService
from shorts_creator.services.run_service import RunService
from shorts_creator.ui.button import ActionButton
from shorts_creator.ui.icons import chevron_right, download_icon, plus, video_icon
from shorts_creator.ui.shell import AppLayout

TYPE_LABELS = {
    "music": "Music",
    "font": "Fonts",
    "image": "Images",
    "clip": "Clips",
    "watermark": "Watermarks",
}


def _generated_card(run: Run, project_title: str | None = None) -> str:
    run_id = run.id
    title = run.title or "Untitled Video"
    duration = run.duration_s
    duration_str = f"{duration:.1f}s" if isinstance(duration, (int, float)) and duration else "—"
    date = run.created_at.strftime("%Y-%m-%d") if run.created_at else "—"
    video_attrs = {
        "controls": "",
        "preload": "metadata",
        "playsinline": "",
        "poster": f"/api/videos/poster/{run_id}",
        "class_": "w-full aspect-[9/16] object-contain bg-foreground/10",
    }
    return Markup(
        el(
            "div",
            el(
                "div",
                el(
                    "video",
                    el("source", src=f"/api/videos/preview/{run_id}", type="video/mp4"),
                    **video_attrs,
                ),
                class_="rounded-lg overflow-hidden border border-border/60 bg-foreground/20 mb-2",
            ),
            el(
                "div",
                escape(title),
                class_="text-sm font-semibold text-foreground truncate",
                title=title,
            ),
            el(
                "div",
                el(
                    "span",
                    escape(project_title or "Unknown project"),
                    class_="text-[10px] font-mono text-muted-foreground truncate",
                ),
                class_="mt-0.5",
            ),
            el(
                "div",
                el(
                    "span",
                    f"⏱ {duration_str}",
                    class_="text-primary text-[11px] font-mono bg-primary/40 px-2 py-0.5 rounded border border-primary/30",
                ),
                el("span", date, class_="text-muted-foreground text-[11px] font-mono ml-auto"),
                class_="flex items-center gap-2 mt-2",
            ),
            el(
                "div",
                el(
                    "a",
                    download_icon(),
                    el("span", "Download MP4", class_="ml-1.5 font-semibold"),
                    href=f"/api/videos/download/{run_id}",
                    class_="flex items-center justify-center gap-2 w-full text-xs font-mono rounded-lg border border-primary/40 bg-primary/20 px-3 py-2 text-primary hover:bg-primary/30 transition-colors",
                ),
                el(
                    "a",
                    el("span", "Open Project", class_="font-semibold mr-1"),
                    chevron_right(),
                    href=f"/projects/{run.project_id}",
                    hx_get=f"/projects/{run.project_id}",
                    hx_target="#main-content",
                    hx_push_url=f"/projects/{run.project_id}",
                    class_="flex items-center justify-center gap-2 w-full text-xs font-mono rounded-lg border border-border/60 bg-card/40 px-3 py-2 text-foreground hover:bg-secondary/50 transition-colors mt-1.5",
                ),
                class_="mt-3 flex flex-col gap-1.5",
            ),
            class_="border border-border rounded-xl p-3 bg-background/40",
        )
    )


def _card(asset) -> RawHTML:
    if asset.type in ("image", "watermark"):
        thumb = el(
            "img",
            src=f"/api/assets/{asset.id}/file",
            alt=asset.name,
            class_="max-h-[50px] max-w-full object-contain",
        )
    else:
        glyph = "♪" if asset.type == "music" else "Aa" if asset.type == "font" else "▶"
        thumb = el("span", glyph, class_="text-2xl text-primary")
    role_badge = (
        f'<span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-primary/60 '
        f'text-primary border border-primary/40">{asset.role}</span>'
        if asset.role
        else ""
    )
    return raw(
        el(
            "div",
            el(
                "div",
                thumb,
                class_="h-[70px] rounded-lg bg-card border border-border flex items-center justify-center mb-2",
            ),
            el("div", escape(asset.name), class_="text-sm font-semibold text-foreground truncate"),
            el(
                "div",
                el(
                    "span",
                    TYPE_LABELS.get(asset.type, asset.type),
                    class_="text-[10px] font-mono text-muted-foreground",
                ),
                role_badge,
                class_="flex items-center gap-1.5 mt-1",
            ),
            el(
                "a",
                "Edit",
                href=f"/assets/{asset.id}/edit",
                hx_get=f"/assets/{asset.id}/edit",
                hx_target="#main-content",
                hx_push_url=f"/assets/{asset.id}/edit",
                class_="text-[10px] font-mono text-primary hover:text-primary mt-2 inline-block",
            ),
            class_="border border-border rounded-xl p-3 bg-background/40",
        )
    )


class AssetsController(Controller):
    def __init__(
        self,
        service: AssetService,
        runs: RunService | None = None,
        projects: ProjectService | None = None,
    ):
        self.layout = AppLayout()
        self.service = service
        self.runs = runs
        self.projects = projects

    @get("/assets")
    async def library(self, request=None) -> HTMLContent:
        qp = getattr(request, "query_params", {}) if request else {}
        tab = qp.get("tab", "")
        current = qp.get("type", "")
        upload_query = f"?type={current}" if current else ""

        if tab == "generated":
            body = await self._generated_videos_html()
            content = render_to_string(
                el(
                    "div",
                    el(
                        "div",
                        el(
                            "h1",
                            "Asset Library",
                            class_="text-2xl font-bold text-foreground tracking-tight",
                        ),
                        class_="flex items-center justify-between pb-4 border-b border-border/80",
                    ),
                    el(
                        "div",
                        *self._top_tabs(tab),
                        class_="flex items-center gap-2 mt-4 mb-5 flex-wrap",
                    ),
                    Markup(body),
                    class_="w-full space-y-2",
                )
            )
            html = self.layout.render(content=content, title="Assets", request=request)
            return HTMLContent(html)

        assets = (
            await self.service.list_by_type(current) if current else await self.service.list_all()
        )

        tabs = self._top_tabs(tab) + [
            el(
                "a",
                "All",
                href="/assets",
                hx_get="/assets",
                hx_target="#main-content",
                hx_push_url="/assets",
                class_=(
                    "px-3 py-1.5 text-xs font-semibold rounded-full border transition-colors "
                    + (
                        "bg-primary text-primary-foreground border-primary"
                        if not current
                        else "text-muted-foreground border-border hover:text-foreground"
                    )
                ),
            )
        ]
        for t in ASSET_TYPES:
            tabs.append(
                el(
                    "a",
                    TYPE_LABELS[t],
                    href=f"/assets?type={t}",
                    hx_get=f"/assets?type={t}",
                    hx_target="#main-content",
                    hx_push_url=f"/assets?type={t}",
                    class_=(
                        "px-3 py-1.5 text-xs font-semibold rounded-full border transition-colors "
                        + (
                            "bg-primary text-primary-foreground border-primary"
                            if current == t
                            else "text-muted-foreground border-border hover:text-foreground"
                        )
                    ),
                )
            )

        empty = el(
            "p",
            "No assets yet. Upload your first one to customize renders.",
            class_="text-muted-foreground text-xs py-10 text-center",
        )
        grid = el(
            "div",
            *([_card(a) for a in assets] or [empty]),
            class_="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mt-4 pt-4 border-t border-border/60",
        )

        content = render_to_string(
            el(
                "div",
                el(
                    "div",
                    el(
                        "h1",
                        "Asset Library",
                        class_="text-2xl font-bold text-foreground tracking-tight",
                    ),
                    el(
                        "a",
                        plus(),
                        " Upload",
                        href=f"/assets/new{upload_query}",
                        hx_get=f"/assets/new{upload_query}",
                        hx_target="#main-content",
                        hx_push_url=f"/assets/new{upload_query}",
                        class_="bg-primary hover:bg-primary text-primary-foreground px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all",
                    ),
                    class_="flex items-center justify-between pb-4 border-b border-border/80",
                ),
                el("div", *tabs, class_="flex items-center gap-2 mt-4 mb-5 flex-wrap"),
                grid,
                class_="w-full space-y-2",
            )
        )
        html = self.layout.render(content=content, title="Assets", request=request)
        return HTMLContent(html)

    def _top_tabs(self, active: str) -> list:
        return [
            el(
                "a",
                "Uploaded",
                href="/assets",
                hx_get="/assets",
                hx_target="#main-content",
                hx_push_url="/assets",
                class_=(
                    "px-3 py-1.5 text-xs font-semibold rounded-full border transition-colors "
                    + (
                        "bg-primary text-primary-foreground border-primary"
                        if not active
                        else "text-muted-foreground border-border hover:text-foreground"
                    )
                ),
            ),
            el(
                "a",
                "Generated Videos",
                href="/assets?tab=generated",
                hx_get="/assets?tab=generated",
                hx_target="#main-content",
                hx_push_url="/assets?tab=generated",
                class_=(
                    "px-3 py-1.5 text-xs font-semibold rounded-full border transition-colors "
                    + (
                        "bg-primary text-primary-foreground border-primary"
                        if active == "generated"
                        else "text-muted-foreground border-border hover:text-foreground"
                    )
                ),
            ),
        ]

    async def _generated_empty(self) -> str:
        empty = el(
            "div",
            el(
                "div",
                video_icon(),
                class_="w-12 h-12 rounded-full bg-secondary/80 border border-border/50 flex items-center justify-center text-primary mx-auto mb-3",
            ),
            el(
                "h3", "No generated videos yet", class_="text-sm font-semibold text-foreground mb-1"
            ),
            el(
                "p",
                "Render videos in any project and they will be collected here.",
                class_="text-muted-foreground text-xs max-w-xs mx-auto leading-relaxed",
            ),
            class_="text-center py-16 px-6 rounded-2xl border border-dashed border-border w-full",
        )
        return str(empty)

    async def _generated_videos_html(self) -> str:
        if self.runs is None or self.projects is None:
            return await self._generated_empty()
        completed = [
            r
            for r in await self.runs.list_status(RunStatus.COMPLETED, limit=10_000)
            if r.output_path and os.path.exists(r.output_path)
        ]
        completed.sort(key=lambda r: r.created_at, reverse=True)
        if not completed:
            return await self._generated_empty()

        project_cache: dict[str, str | None] = {}
        for r in completed:
            if r.project_id not in project_cache:
                project = await self.projects.get(r.project_id)
                project_cache[r.project_id] = project.title if project else None
        cards = [_generated_card(r, project_cache.get(r.project_id)) for r in completed]
        return render_to_string(
            el(
                "div",
                el(
                    "div",
                    el(
                        "h2",
                        "Generated Videos",
                        class_="text-sm font-semibold uppercase tracking-wider text-muted-foreground font-mono",
                    ),
                    el(
                        "span",
                        str(len(cards)),
                        class_="text-muted-foreground text-[11px] font-mono bg-secondary/60 px-2 py-0.5 rounded-full border border-border/50",
                    ),
                    class_="flex items-center gap-2 mb-3",
                ),
                el("div", *cards, class_="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"),
                class_="w-full mt-4 pt-4 border-t border-border/60",
            )
        )

    @get("/assets/new")
    async def new_asset(self, request=None) -> HTMLContent:
        qp = getattr(request, "query_params", {}) if request else {}
        asset_type = qp.get("type", "music")

        SINGULAR_LABELS = {
            "music": "Music",
            "font": "Font",
            "image": "Image",
            "clip": "Clip",
            "watermark": "Watermark",
        }
        if asset_type in SINGULAR_LABELS:
            heading_text = f"Upload {SINGULAR_LABELS[asset_type]} Asset"
        else:
            heading_text = "Upload Asset"

        if asset_type not in ASSET_TYPES:
            asset_type = "music"

        role_field = ""
        if asset_type == "clip":
            role_field = str(
                el(
                    "div",
                    el(
                        "label",
                        "Role",
                        class_="block text-foreground text-xs font-semibold mb-1.5",
                        for_="role",
                    ),
                    el(
                        "select",
                        *(el("option", r, value=r) for r in CLIP_ROLES),
                        name="role",
                        class_="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground font-mono text-xs focus:border-primary focus:outline-none transition-colors",
                    ),
                    class_="mb-3.5",
                )
            )

        content = render_to_string(
            el(
                "div",
                el(
                    "a",
                    "← Back to Assets",
                    href="/assets",
                    hx_get="/assets",
                    hx_target="#main-content",
                    hx_push_url="/assets",
                    class_="text-primary hover:text-primary text-xs font-semibold transition-colors",
                ),
                el(
                    "h1",
                    heading_text,
                    class_="text-2xl font-bold text-foreground tracking-tight mt-4",
                ),
                el(
                    "form",
                    el("input", type="hidden", name="type", value=asset_type),
                    el(
                        "div",
                        el(
                            "label",
                            "File",
                            class_="block text-foreground text-xs font-semibold mb-1.5",
                            for_="file",
                        ),
                        el(
                            "input",
                            type="file",
                            name="file",
                            required=True,
                            class_="w-full text-xs text-foreground file:mr-3 file:rounded-lg file:border-0 file:bg-primary file:px-3 file:py-1.5 file:text-primary-foreground file:text-xs file:font-semibold",
                        ),
                        class_="mb-3.5",
                    ),
                    el(
                        "div",
                        el(
                            "label",
                            "Name",
                            class_="block text-foreground text-xs font-semibold mb-1.5",
                            for_="name",
                        ),
                        el(
                            "input",
                            type="text",
                            name="name",
                            class_="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground font-mono text-xs focus:border-primary focus:outline-none transition-colors",
                        ),
                        class_="mb-3.5",
                    ),
                    el(
                        "div",
                        el(
                            "label",
                            "Description",
                            class_="block text-foreground text-xs font-semibold mb-1.5",
                            for_="description",
                        ),
                        el(
                            "input",
                            type="text",
                            name="description",
                            class_="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground font-mono text-xs focus:border-primary focus:outline-none transition-colors",
                        ),
                        class_="mb-3.5",
                    ),
                    el(
                        "div",
                        el(
                            "label",
                            "Tags (comma separated)",
                            class_="block text-foreground text-xs font-semibold mb-1.5",
                            for_="tags",
                        ),
                        el(
                            "input",
                            type="text",
                            name="tags",
                            placeholder="chill, morning",
                            class_="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground font-mono text-xs focus:border-primary focus:outline-none transition-colors",
                        ),
                        class_="mb-3.5",
                    ),
                    Markup(role_field),
                    ActionButton(
                        "Upload Asset",
                        hx_post="/api/assets/upload",
                        hx_target="#save-msg",
                        hx_swap="innerHTML",
                        class_extra="mt-3",
                    ),
                    id="asset-upload-form",
                    class_="mt-4 pt-4 border-t border-border/60",
                ),
                el("div", id="save-msg", class_="mt-2"),
                class_="w-full space-y-6",
            )
        )
        html = self.layout.render(content=content, title=heading_text, request=request)
        return HTMLContent(html)

    @get("/assets/{id}/edit")
    async def edit(self, request=None, id: str = "") -> HTMLContent:
        asset = await self.service.get(id)
        if not asset:
            return html_response("Asset not found", status_code=404)

        role_field = ""
        if asset.type == "clip":
            role_field = str(
                el(
                    "div",
                    el(
                        "label",
                        "Role",
                        class_="block text-foreground text-xs font-semibold mb-1.5",
                        for_="role",
                    ),
                    el(
                        "select",
                        el(
                            "option",
                            "None (built-in)",
                            value="",
                            **({"selected": True} if not asset.role else {}),
                        ),
                        *(
                            el(
                                "option",
                                r,
                                value=r,
                                **({"selected": True} if asset.role == r else {}),
                            )
                            for r in CLIP_ROLES
                        ),
                        name="role",
                        class_="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground font-mono text-xs focus:border-primary focus:outline-none transition-colors",
                    ),
                    class_="mb-3.5",
                )
            )

        content = render_to_string(
            el(
                "div",
                el(
                    "a",
                    "← Back to Assets",
                    href="/assets",
                    hx_get="/assets",
                    hx_target="#main-content",
                    hx_push_url="/assets",
                    class_="text-primary hover:text-primary text-xs font-semibold transition-colors",
                ),
                el(
                    "h1",
                    "Edit Asset",
                    class_="text-2xl font-bold text-foreground tracking-tight mt-4",
                ),
                el(
                    "form",
                    el(
                        "div",
                        el(
                            "label",
                            "Name",
                            class_="block text-foreground text-xs font-semibold mb-1.5",
                            for_="name",
                        ),
                        el(
                            "input",
                            type="text",
                            name="name",
                            value=asset.name,
                            class_="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground font-mono text-xs focus:border-primary focus:outline-none transition-colors",
                        ),
                        class_="mb-3.5",
                    ),
                    el(
                        "div",
                        el(
                            "label",
                            "Description",
                            class_="block text-foreground text-xs font-semibold mb-1.5",
                            for_="description",
                        ),
                        el(
                            "input",
                            type="text",
                            name="description",
                            value=asset.description,
                            class_="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground font-mono text-xs focus:border-primary focus:outline-none transition-colors",
                        ),
                        class_="mb-3.5",
                    ),
                    el(
                        "div",
                        el(
                            "label",
                            "Tags (comma separated)",
                            class_="block text-foreground text-xs font-semibold mb-1.5",
                            for_="tags",
                        ),
                        el(
                            "input",
                            type="text",
                            name="tags",
                            value=", ".join(asset.tags),
                            class_="w-full bg-background border border-border rounded-lg px-3 py-2 text-foreground font-mono text-xs focus:border-primary focus:outline-none transition-colors",
                        ),
                        class_="mb-3.5",
                    ),
                    Markup(role_field),
                    ActionButton(
                        "Save Changes",
                        hx_post=f"/api/assets/{id}/update",
                        hx_target="#save-msg",
                        hx_swap="innerHTML",
                        class_extra="mt-3",
                    ),
                    ActionButton(
                        "Delete",
                        variant="danger",
                        hx_post=f"/api/assets/{id}/delete",
                        hx_target="#main-content",
                        hx_swap="innerHTML",
                        class_extra="mt-3 ml-2",
                    ),
                    id="asset-edit-form",
                    class_="mt-4 pt-4 border-t border-border/60",
                ),
                el("div", id="save-msg", class_="mt-2"),
                class_="w-full space-y-6",
            )
        )
        html = self.layout.render(content=content, title="Edit Asset", request=request)
        return HTMLContent(html)
