from lexigram.ui import el
from markupsafe import Markup

from shorts_creator.ui.icons import check, file_text, lightbulb, video_icon

STAGES = [
    ("ideas", "Ideas", "scripts", file_text),
    ("script", "Script", "scripts", lightbulb),
    ("render", "Render", "render", video_icon),
]


def _stage_href(subpath: str, project_id: str, run_id: str) -> str:
    if project_id:
        return f"/projects/{project_id}/{subpath}"
    return "/projects"


def _stage_icon(stage_key, done):
    if done:
        return check()
    for sk, _, _, icon_fn in STAGES:
        if sk == stage_key:
            return icon_fn()
    return check()


def PipelineTracker(
    current: str = "scripts",
    run_id: str = "",
    project_id: str = "",
    density: str = "compact",
    stage_state: list | None = None,
) -> str:
    current_idx = next((i for i, s in enumerate(STAGES) if s[0] == current), 0)

    items = []
    for i, (stage_key, label, base_path, icon_fn) in enumerate(STAGES):
        is_active = stage_key == current
        is_done = i < current_idx

        if stage_state and i < len(stage_state):
            s = stage_state[i]
            is_done = s.get("done", is_done)
            is_active = s.get("active", is_active)

        path = _stage_href(base_path, project_id, run_id)

        if density == "full":
            preview = stage_state[i].get("preview", "") if stage_state else ""
            dot_color = "bg-success" if is_done else ("bg-primary" if is_active else "bg-secondary")
            text_color = (
                "text-success"
                if is_done
                else ("text-foreground" if is_active else "text-muted-foreground")
            )
            preview_color = "text-success/70" if is_done else "text-muted-foreground"
            items.append(
                el(
                    "a",
                    el("div", class_=f"w-2.5 h-2.5 rounded-full {dot_color} shrink-0"),
                    el(
                        "span",
                        label,
                        class_=f"text-[11px] font-bold font-mono tracking-wider uppercase {text_color} mt-1",
                    ),
                    el("span", preview, class_=f"text-[10px] font-mono {preview_color} mt-0.5"),
                    href=path,
                    hx_get=path,
                    hx_target="#main-content",
                    hx_push_url=path,
                    class_="flex flex-col items-center px-3 py-2",
                )
            )
            if i < len(STAGES) - 1:
                next_done = (
                    stage_state[i + 1].get("done", False) if stage_state else (i + 1 < current_idx)
                )
                connector_done = is_done and next_done
                items.append(
                    el(
                        "div",
                        class_=f"flex-1 h-px self-center {'bg-success/40' if connector_done else 'bg-secondary'}",
                    )
                )
        else:
            if is_done:
                icon = check()
                style = (
                    "bg-success/15 border-success/30 text-success "
                    "hover:bg-success/25 hover:border-success/40"
                )
            elif is_active:
                icon = icon_fn()
                style = "bg-gradient-to-r from-primary to-primary border-primary text-primary-foreground shadow-md shadow-primary/50"
            else:
                icon = icon_fn()
                style = (
                    "bg-card/70 border-border text-muted-foreground "
                    "hover:bg-secondary/80 hover:text-foreground hover:border-border"
                )

            items.append(
                el(
                    "a",
                    el("span", icon, class_="mr-1.5 shrink-0"),
                    el("span", label, class_="font-mono text-xs font-semibold tracking-tight"),
                    href=path,
                    hx_get=path,
                    hx_target="#main-content",
                    hx_push_url=path,
                    class_=f"flex items-center px-3 py-1.5 rounded-lg border transition-all duration-150 {style}",
                )
            )

            if i < len(STAGES) - 1:
                items.append(
                    el(
                        "div",
                        class_=f"flex-1 min-w-4 max-w-16 h-0.5 rounded-full transition-colors hidden sm:block {('bg-success/50' if is_done else 'bg-secondary')}",
                    )
                )

    return Markup(
        el(
            "div",
            el(
                "div",
                *items,
                class_="flex items-center justify-between sm:justify-start gap-2 overflow-x-auto py-1",
            ),
        )
    )
