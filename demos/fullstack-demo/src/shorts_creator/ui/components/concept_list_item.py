import json

from lexigram.ui import el
from markupsafe import Markup

from shorts_creator.ui.button import ActionButton
from shorts_creator.ui.icons import edit_icon, trash_icon, video_icon


def ConceptListItem(
    idea,
    index: int,
    idea_index: int | None = None,
    run_id: str = "",
    project_id: str = "",
    selected: bool = False,
    sort: str = "",
    has_script: bool = False,
    has_video: bool = False,
    page: int = 0,
):
    if idea_index is None:
        idea_index = index - 1

    score = getattr(idea, "quotability_score", 5.0)
    title = getattr(idea, "title", "Untitled Idea")

    score_color = (
        "text-success" if score >= 8.5 else "text-warning" if score >= 6.5 else "text-destructive"
    )

    params = []
    ctx_id = project_id or run_id
    ctx_key = "project_id" if project_id else "run_id"
    params.append(f"idea_index={idea_index}")
    if sort:
        params.append(f"sort={sort}")
    if page:
        params.append(f"page={page}")
    qp = "?" + "&".join(params) if params else ""

    base_path = f"/projects/{project_id}/scripts" if project_id else "/scripts"
    link = f"{base_path}{qp}"
    if run_id and not project_id:
        run_qp = "&" + "&".join(params) if params else ""
        link = f"/scripts?run_id={run_id}{run_qp}"

    hx_vals = json.dumps({ctx_key: ctx_id, "idea_index": idea_index, "sort": sort, "page": page})

    status_dot = el(
        "span",
        "",
        class_="w-1.5 h-1.5 rounded-full bg-success shrink-0"
        if has_script
        else "w-1.5 h-1.5 rounded-full bg-secondary shrink-0",
        title="Script ready" if has_script else "No script",
    )

    script_badge = (
        el(
            "span",
            "Script ready",
            class_="text-[10px] text-success font-semibold font-mono tracking-wide",
        )
        if has_script
        else ""
    )

    video_badge = (
        el(
            "span",
            video_icon(),
            el("span", "Video rendered", class_="ml-1"),
            class_="text-[10px] text-primary font-semibold font-mono tracking-wide inline-flex items-center",
        )
        if has_video
        else ""
    )

    row_style = (
        "border-primary/60 bg-secondary/60"
        if selected
        else "border-transparent hover:border-border/60 hover:bg-secondary/30"
    )

    body_style = "pb-1" if (has_script or has_video) else ""

    return Markup(
        el(
            "div",
            el(
                "a",
                el(
                    "div",
                    el(
                        "div",
                        status_dot,
                        el(
                            "span",
                            title,
                            class_="text-sm font-bold text-foreground leading-snug truncate",
                        ),
                        el(
                            "span",
                            f"\u26a1{score:.1f}",
                            class_=f"text-[10px] font-mono font-bold {score_color} shrink-0 ml-auto",
                        ),
                        class_="flex items-center gap-2 flex-1 min-w-0",
                    ),
                    script_badge,
                    video_badge,
                    class_="flex flex-col gap-0",
                ),
                href=link,
                hx_get=link,
                hx_target="#main-content",
                hx_push_url=link,
                class_=f"flex flex-col flex-1 min-w-0 {body_style}",
            ),
            el(
                "div",
                el(
                    "button",
                    edit_icon(),
                    hx_get=f"/api/ideas/edit/{ctx_id}/{idea_index}" if ctx_id else "",
                    hx_target=f"#concept-{idea_index}",
                    hx_swap="outerHTML",
                    title="Edit idea",
                    class_="p-1 rounded text-muted-foreground hover:text-primary hover:bg-secondary/60 transition-colors cursor-pointer",
                ),
                el(
                    "button",
                    trash_icon(),
                    hx_post="/api/ideas/delete",
                    hx_target="#concept-list",
                    hx_swap="innerHTML",
                    hx_vals=hx_vals,
                    hx_confirm="Delete this idea?",
                    hx_disabled_elt="this",
                    title="Delete idea",
                    class_="p-1 rounded text-muted-foreground hover:text-destructive hover:bg-secondary/60 transition-colors",
                ),
                class_="flex items-center gap-0.5 shrink-0",
            ),
            id=f"concept-{idea_index}",
            class_=f"flex items-start gap-1 py-2 px-3 -mx-3 rounded-lg border transition-all duration-150 {row_style}",
        )
    )


def IdeaEditForm(idea, idea_index: int, run_id: str = "", project_id: str = ""):
    hook = getattr(idea, "hook_line", "")
    audience = getattr(idea, "target_audience", "")
    core_msg = getattr(idea, "core_message", "")
    title = getattr(idea, "title", "Untitled Idea")
    ctx_id = project_id or run_id

    return Markup(
        el(
            "div",
            el(
                "form",
                el(
                    "label",
                    "Title",
                    class_="text-[10px] font-mono font-bold text-muted-foreground uppercase tracking-wider",
                ),
                el(
                    "input",
                    name="title",
                    value=title,
                    class_="w-full text-xs bg-card border border-border rounded px-2 py-1 text-foreground mb-2",
                ),
                el(
                    "label",
                    "Hook Line",
                    class_="text-[10px] font-mono font-bold text-muted-foreground uppercase tracking-wider",
                ),
                el(
                    "input",
                    name="hook_line",
                    value=hook,
                    class_="w-full text-xs bg-card border border-border rounded px-2 py-1 text-foreground mb-2",
                ),
                el(
                    "label",
                    "Core Message",
                    class_="text-[10px] font-mono font-bold text-muted-foreground uppercase tracking-wider",
                ),
                el(
                    "input",
                    name="core_message",
                    value=core_msg,
                    class_="w-full text-xs bg-card border border-border rounded px-2 py-1 text-foreground mb-2",
                ),
                el(
                    "label",
                    "Target Audience",
                    class_="text-[10px] font-mono font-bold text-muted-foreground uppercase tracking-wider",
                ),
                el(
                    "input",
                    name="target_audience",
                    value=audience,
                    class_="w-full text-xs bg-card border border-border rounded px-2 py-1 text-foreground mb-2",
                ),
                el("input", type="hidden", name="project_id", value=project_id),
                el("input", type="hidden", name="idea_index", value=str(idea_index)),
                el(
                    "div",
                    ActionButton(
                        "Save",
                        type="submit",
                    ),
                    ActionButton(
                        "Cancel",
                        variant="ghost",
                        hx_get=f"/api/ideas/cancel-edit/{ctx_id}/{idea_index}",
                        hx_target=f"#concept-{idea_index}",
                        hx_swap="outerHTML",
                        class_extra="ml-2",
                    ),
                    class_="flex justify-end mt-2",
                ),
                id=f"edit-form-{idea_index}",
                hx_post="/api/ideas/update",
                hx_target=f"#concept-{idea_index}",
                hx_swap="outerHTML",
                hx_disabled_elt=f"#edit-form-{idea_index} button",
                class_="space-y-1",
            ),
            id=f"concept-{idea_index}",
            class_="py-2.5 px-3 -mx-3 rounded-lg border border-primary/40 bg-secondary/60",
        )
    )
