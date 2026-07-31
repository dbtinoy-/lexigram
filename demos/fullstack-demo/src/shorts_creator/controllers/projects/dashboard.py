import json
from html import escape

from lexigram.ui import el, render_to_string
from markupsafe import Markup

from shorts_creator.controllers.projects.ideas import _ideas_strip
from shorts_creator.controllers.projects.profile import _profile_card
from shorts_creator.controllers.projects.runs import _dashboard_runs
from shorts_creator.controllers.projects.scripts import _scripts_block
from shorts_creator.controllers.projects.stats import _proj_stat
from shorts_creator.formats import registry as formats
from shorts_creator.models.run import RunStatus
from shorts_creator.ui.components.project_tabs import project_header, project_top_tabs
from shorts_creator.ui.icons import plus, zap


def _project_dashboard(project, state, issues=None, profile=None, asset_options=None) -> str:
    pid = project.id

    pair_banner = ""
    if issues:
        issue_list = el(
            "ul",
            *(
                el(
                    "li",
                    el("span", escape(issue.code), class_="font-mono font-bold"),
                    " — ",
                    escape(issue.message),
                )
                for issue in issues
            ),
            class_="text-xs space-y-1",
        )
        remap_form = ""
        if formats.available:
            fmt_options = [el("option", escape(f.label), value=f.name) for f in formats.available]
            remap_form = str(
                el(
                    "form",
                    el(
                        "select",
                        *fmt_options,
                        name="format_name",
                        class_="bg-background/80 border border-warning/50 rounded-lg px-2 py-1 text-xs font-mono text-warning focus:outline-none focus:border-warning/60",
                    ),
                    el(
                        "button",
                        "Re-map →",
                        type="submit",
                        class_="text-xs font-mono font-semibold text-warning-foreground bg-warning hover:bg-warning/90 px-3 py-1.5 rounded-lg transition-colors cursor-pointer",
                    ),
                    hx_post=f"/api/projects/{pid}/format/remap",
                    hx_target="#main-content",
                    hx_swap="innerHTML",
                    class_="flex items-center gap-2",
                )
            )
        pair_banner = Markup(
            '<div class="mb-4 rounded-xl border border-warning/50 bg-warning/30 '
            'px-4 py-3 text-warning">'
            '<p class="text-[11px] font-mono font-semibold uppercase tracking-widest mb-1">'
            "Topic/format contract</p>"
            f"{issue_list}"
            f"{remap_form}</div>"
        )

    # Header
    header = project_header(project, state)

    if not state.ideas:
        section = _dashboard_start(pid)
    else:
        left_cols = [
            _latest_render_card(pid, state),
            _profile_card(project, profile, asset_options or {}),
            _ideas_strip(pid, state),
            _scripts_block(pid, state),
        ]
        section = el(
            "div",
            _dashboard_stats(state),
            el(
                "div",
                el("div", *left_cols, class_="lg:col-span-2 space-y-6"),
                el("div", _dashboard_runs(project, state), class_="space-y-6"),
                class_="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6",
            ),
            class_="w-full",
        )

    content = render_to_string(
        el("div", pair_banner, header, project_top_tabs(pid, "overview"), section, class_="w-full")
    )
    return content


def _dashboard_start(pid) -> str:
    return Markup(
        str(
            el(
                "div",
                el(
                    "div",
                    zap(),
                    class_="w-10 h-10 rounded-xl bg-secondary/60 border border-border/40 flex items-center justify-center text-primary mx-auto mb-3",
                ),
                el("p", "Start Creating", class_="text-sm font-semibold text-foreground mb-1"),
                el(
                    "p",
                    "Generate ideas, write scripts, and render videos — all from one workspace.",
                    class_="text-xs text-muted-foreground max-w-xs mx-auto leading-relaxed mb-5",
                ),
                el(
                    "a",
                    plus(),
                    el("span", "Ideas & Scripts", class_="ml-1.5 font-semibold"),
                    href=f"/projects/{pid}/scripts",
                    hx_get=f"/projects/{pid}/scripts",
                    hx_target="#main-content",
                    hx_push_url=f"/projects/{pid}/scripts",
                    class_="inline-flex items-center bg-gradient-to-r from-primary to-primary hover:from-primary hover:to-primary text-primary-foreground text-xs px-5 py-2.5 rounded-xl font-semibold transition-all shadow-md shadow-primary/40",
                ),
                class_="text-center py-14 px-6 rounded-2xl border border-dashed border-border rounded-2xl",
            )
        )
    )


def _dashboard_stats(state) -> str:
    s = state.stats
    return Markup(
        str(
            el(
                "div",
                _proj_stat(str(s["ideas"]), "Ideas", "text-primary"),
                _proj_stat(str(s["scripts"]), "Scripts", "text-primary"),
                _proj_stat(
                    str(s["videos"]),
                    "Videos",
                    "text-success" if s["videos"] else "text-muted-foreground",
                ),
                _proj_stat(str(s["runs"]), "Runs", "text-muted-foreground"),
                class_="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4 pt-4 border-t border-border/60",
            )
        )
    )


def _latest_render_card(pid: str, state) -> str:
    completed = [r for r in state.recent_runs if r.status == RunStatus.COMPLETED and r.output_path]
    if not completed:
        return ""
    run = completed[0]
    idea_id = run.selected_idea_id or ""
    idea_index = None
    seo = None
    for i, idea in enumerate(state.ideas):
        if isinstance(idea, dict) and idea.get("id") == idea_id:
            idea_index = i
            sj = idea.get("script_json")
            if sj:
                try:
                    seo = (json.loads(sj).get("metadata") or {}).get("seo")
                except (json.JSONDecodeError, TypeError):
                    seo = None
            break
    group = {
        "key": idea_id or run.title or "Untitled Idea",
        "title": run.title or "Untitled Idea",
        "project_id": pid,
        "idea_id": idea_id,
        "idea_index": idea_index,
        "seo": seo,
        "versions": [
            {
                "run_id": run.id,
                "idea": run.title,
                "duration_s": run.duration_s,
                "output": run.output_path,
                "created_at": run.created_at.isoformat() if run.created_at else "",
            }
        ],
        "active_run_id": run.id,
    }
    from shorts_creator.controllers.videos import _GroupCard

    return Markup(
        f'<div id="latest-render">'
        f'<div class="flex items-center justify-between mb-3">'
        f'<h2 class="text-[11px] font-mono font-semibold text-muted-foreground">LATEST RENDER</h2>'
        f'<a href="/projects/{pid}/videos" hx-get="/projects/{pid}/videos" hx-target="#main-content" hx-push-url="/projects/{pid}/videos" '
        f'class="text-xs font-mono text-muted-foreground hover:text-primary transition-colors">View all \u2192</a>'
        f"</div>"
        f"{_GroupCard(group, hx_target='#latest-render', card=True)}"
        f"</div>"
    )
