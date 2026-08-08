from lexigram.ui import el
from markupsafe import Markup

from shorts_creator.ui.button import ActionButton
from shorts_creator.ui.icons import check


def IdeaEditor(idea, idea_index: int, run_id: str = ""):
    title = getattr(idea, "title", "")
    core_msg = getattr(idea, "core_message", "")
    hook = getattr(idea, "hook_line", "")
    identity = getattr(idea, "identity_signal", "")
    permission = getattr(idea, "permission_given", "")
    arc = getattr(idea, "emotional_arc", "")
    audience = getattr(idea, "target_audience", "")
    share = getattr(idea, "share_trigger", "")
    score = getattr(idea, "quotability_score", 5.0)

    fields_json = (
        'js:{"run_id":"' + run_id + '","idea_index":' + str(idea_index) + ',"fields":{'
        '"title":document.getElementById("ie-title-{0}").value,'
        '"core_message":document.getElementById("ie-msg-{0}").value,'
        '"hook_line":document.getElementById("ie-hook-{0}").value,'
        '"identity_signal":document.getElementById("ie-id-{0}").value,'
        '"permission_given":document.getElementById("ie-perm-{0}").value,'
        '"emotional_arc":document.getElementById("ie-arc-{0}").value,'
        '"target_audience":document.getElementById("ie-aud-{0}").value,'
        '"share_trigger":document.getElementById("ie-share-{0}").value,'
        '"quotability_score":parseFloat(document.getElementById("ie-score-{0}").value)}}'
    ).replace("{0}", str(idea_index))

    def _field(label, el_id, input_el):
        return el(
            "div",
            el(
                "label",
                label,
                class_="text-[10px] uppercase tracking-widest font-bold text-primary font-mono block mb-0.5",
            ),
            input_el,
            class_="mb-2",
        )

    inputs = [
        _field(
            "Title",
            f"ie-title-{idea_index}",
            el(
                "input",
                id=f"ie-title-{idea_index}",
                type="text",
                value=title,
                class_="w-full text-xs bg-background border border-border rounded-lg px-2.5 py-1.5 text-foreground font-mono",
            ),
        ),
        _field(
            "Core Message",
            f"ie-msg-{idea_index}",
            el(
                "textarea",
                core_msg,
                id=f"ie-msg-{idea_index}",
                rows=2,
                class_="w-full text-xs bg-background border border-border rounded-lg px-2.5 py-1.5 text-foreground font-mono resize-none",
            ),
        ),
        _field(
            "Hook Line",
            f"ie-hook-{idea_index}",
            el(
                "input",
                id=f"ie-hook-{idea_index}",
                type="text",
                value=hook,
                class_="w-full text-xs bg-background border border-border rounded-lg px-2.5 py-1.5 text-foreground font-mono",
            ),
        ),
        _field(
            "Identity Signal",
            f"ie-id-{idea_index}",
            el(
                "input",
                id=f"ie-id-{idea_index}",
                type="text",
                value=identity,
                class_="w-full text-xs bg-background border border-border rounded-lg px-2.5 py-1.5 text-foreground font-mono",
            ),
        ),
        _field(
            "Permission Given",
            f"ie-perm-{idea_index}",
            el(
                "input",
                id=f"ie-perm-{idea_index}",
                type="text",
                value=permission,
                class_="w-full text-xs bg-background border border-border rounded-lg px-2.5 py-1.5 text-foreground font-mono",
            ),
        ),
        _field(
            "Emotional Arc",
            f"ie-arc-{idea_index}",
            el(
                "input",
                id=f"ie-arc-{idea_index}",
                type="text",
                value=arc,
                class_="w-full text-xs bg-background border border-border rounded-lg px-2.5 py-1.5 text-foreground font-mono",
            ),
        ),
        _field(
            "Target Audience",
            f"ie-aud-{idea_index}",
            el(
                "input",
                id=f"ie-aud-{idea_index}",
                type="text",
                value=audience,
                class_="w-full text-xs bg-background border border-border rounded-lg px-2.5 py-1.5 text-foreground font-mono",
            ),
        ),
        _field(
            "Share Trigger",
            f"ie-share-{idea_index}",
            el(
                "input",
                id=f"ie-share-{idea_index}",
                type="text",
                value=share,
                class_="w-full text-xs bg-background border border-border rounded-lg px-2.5 py-1.5 text-foreground font-mono",
            ),
        ),
        _field(
            "Quotability Score",
            f"ie-score-{idea_index}",
            el(
                "input",
                id=f"ie-score-{idea_index}",
                type="number",
                value=str(score),
                step="0.1",
                min="0",
                max="10",
                class_="w-full text-xs bg-background border border-border rounded-lg px-2.5 py-1.5 text-foreground font-mono",
            ),
        ),
    ]

    return Markup(
        el(
            "div",
            el("div", *inputs, class_="p-3 space-y-0"),
            el(
                "div",
                ActionButton(
                    "Save",
                    icon=check(),
                    variant="success",
                    hx_post="/api/ideas/update",
                    hx_target="#concept-list",
                    hx_swap="innerHTML",
                    hx_vals=fields_json,
                ),
                ActionButton(
                    "Cancel",
                    variant="ghost",
                    onclick=f"document.getElementById('ie-editor-{idea_index}').remove()",
                    class_extra="ml-2",
                ),
                class_="flex justify-end px-3 pb-3",
            ),
            id=f"ie-editor-{idea_index}",
            class_="border-t border-border/50 bg-card/80 rounded-b-lg mt-1",
        )
    )
