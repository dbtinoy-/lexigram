import json

from lexigram.ui import el

from shorts_creator.pipeline.render_config import STAGE_ACCENT_PALETTE
from shorts_creator.ui.pages.new_project_panels.core import _composer_value, _panel
from shorts_creator.ui.pages.new_project_profile import _fmt_number


def _phase2_panel(profile=None, builtin_profile=None):
    holds = _composer_value(profile, "section_holds", {})
    holds = holds if isinstance(holds, dict) else {}
    builtin_holds = _composer_value(builtin_profile, "section_holds", {})
    builtin_holds = builtin_holds if isinstance(builtin_holds, dict) else {}
    accents = _composer_value(profile, "stage_accents", {})
    accents = accents if isinstance(accents, dict) else {}
    motion = _composer_value(profile, "background_motion", "none")
    emphasis = _composer_value(profile, "emphasis_style", "accent")
    lufs = _fmt_number(_composer_value(profile, "loudness_target_lufs", -14.0))
    normalize = _composer_value(profile, "audio_normalize", True)
    hook_hold = _fmt_number(holds.get("hook", 0.0))
    message_pacing = _fmt_number(float(holds.get("message", 0.0)) + 1.0)
    conclusion_hold = _fmt_number(holds.get("conclusion", 0.0))
    hook_hold_builtin = _fmt_number(builtin_holds.get("hook", 0.0))
    message_pacing_builtin = _fmt_number(float(builtin_holds.get("message", 0.0)) + 1.0)
    conclusion_hold_builtin = _fmt_number(builtin_holds.get("conclusion", 0.0))
    audio_non_default = lufs != "-14" or normalize is not True

    def group_heading(title: str):
        return el(
            "h3",
            title,
            class_="text-[11px] font-mono font-semibold text-muted-foreground uppercase tracking-widest",
        )

    def knob(
        label: str,
        widget_id: str,
        widget_type: str,
        min_value: str,
        max_value: str,
        step: str,
        value: str,
        unit: str,
        input_class: str = "w-full accent-primary",
        data_builtin: str | None = None,
    ):
        input_attrs = {
            "id": widget_id,
            "type": widget_type,
            "min": min_value,
            "max": max_value,
            "step": step,
            "value": value,
            "data_default": value,
            "class_": input_class,
        }
        if data_builtin is not None:
            input_attrs["data_builtin"] = data_builtin
        return el(
            "div",
            el(
                "div",
                el("label", label, class_="text-[11px] text-muted-foreground"),
                el(
                    "span",
                    el("span", f"{value} {unit}", id=f"{widget_id}-readout", class_="text-primary"),
                    el(
                        "button",
                        "reset",
                        type="button",
                        onclick=f"resetComposerKnob('{widget_id}')",
                        title=f"Reset {label} to default",
                        class_="underline underline-offset-2 hover:text-primary",
                    ),
                    class_="text-[10px] font-mono text-muted-foreground flex items-center gap-1.5",
                ),
                class_="flex items-center justify-between mb-1",
            ),
            el("input", **input_attrs),
        )

    def motion_btn(name: str, label: str):
        active = motion == name
        cls = "motion-btn px-3 py-1.5 text-xs rounded-lg cursor-pointer transition-colors " + (
            "bg-primary text-primary-foreground" if active else "bg-secondary text-foreground"
        )
        return el("button", label, type="button", data_motion=name, class_=cls)

    def emphasis_btn(name: str, label: str):
        active = emphasis == name
        cls = "emphasis-btn px-3 py-1.5 text-xs rounded-lg cursor-pointer transition-colors " + (
            "bg-primary text-primary-foreground" if active else "bg-secondary text-foreground"
        )
        return el("button", label, type="button", data_emphasis=name, class_=cls)

    def accent_chips(stage: str):
        current = accents.get(stage, "")
        chips = [
            el(
                "button",
                "\u2014",
                type="button",
                title="None",
                class_="accent-chip w-7 h-7 rounded-full cursor-pointer transition-colors "
                "bg-secondary grid place-items-center text-[10px] font-mono text-foreground "
                + ("ring-2 ring-primary ring-offset-1" if not current else "ring-1 ring-border"),
            )
        ]
        for name, colour in STAGE_ACCENT_PALETTE.items():
            active = str(current) == colour
            cls = "accent-chip w-7 h-7 rounded-full cursor-pointer transition-colors " + (
                "ring-2 ring-primary ring-offset-1" if active else "ring-1 ring-border"
            )
            chips.append(
                el(
                    "button",
                    type="button",
                    data_accent=name,
                    data_colour=colour,
                    style_=f"background:{colour}",
                    title=name.title(),
                    aria_label=name.title(),
                    class_=cls,
                )
            )
        return el(
            "div",
            *chips,
            id=f"new-project-stage-accent-{stage}",
            role="group",
            aria_label=f"{stage.title()} accent",
            class_="flex flex-wrap gap-1.5",
        )

    return _panel(
        "Pacing & Motion — reel feel",
        el(
            "div",
            group_heading("Pacing"),
            knob(
                "Hook hold (s)",
                "new-project-hold-hook",
                "range",
                "0",
                "1",
                "0.1",
                hook_hold,
                "s",
                data_builtin=hook_hold_builtin,
            ),
            knob(
                "Message pacing (s/line)",
                "new-project-message-pacing",
                "range",
                "0.5",
                "3",
                "0.1",
                message_pacing,
                "s/line",
                data_builtin=message_pacing_builtin,
            ),
            knob(
                "Conclusion hold (s)",
                "new-project-hold-conclusion",
                "range",
                "0",
                "2",
                "0.1",
                conclusion_hold,
                "s",
                data_builtin=conclusion_hold_builtin,
            ),
            group_heading("Motion"),
            el(
                "div",
                motion_btn("none", "None"),
                motion_btn("pan", "Pan"),
                motion_btn("zoom", "Zoom"),
                id="new-project-motion",
                class_="flex gap-2",
            ),
            group_heading("Emphasis"),
            el(
                "div",
                emphasis_btn("off", "Off"),
                emphasis_btn("accent", "Accent"),
                emphasis_btn("scale", "Scale"),
                id="new-project-emphasis",
                class_="flex gap-2",
            ),
            el(
                "details",
                el(
                    "summary",
                    "Audio",
                    class_="cursor-pointer text-[11px] font-mono font-semibold text-muted-foreground uppercase tracking-widest",
                ),
                el(
                    "div",
                    knob(
                        "Loudness target (LUFS)",
                        "new-project-loudness",
                        "number",
                        "-20",
                        "-8",
                        "0.5",
                        lufs,
                        "LUFS",
                        input_class="w-full rounded-lg bg-secondary/80 border border-border px-3 py-1.5 text-xs text-foreground",
                    ),
                    el(
                        "label",
                        el(
                            "input",
                            id="new-project-audio-normalize",
                            type="checkbox",
                            checked=normalize,
                            class_="accent-primary",
                        ),
                        el("span", "Normalize audio (loudnorm)", class_="text-xs text-foreground"),
                        class_="flex items-center gap-2",
                    ),
                    class_="mt-2 space-y-3",
                ),
                open=audio_non_default,
                class_="rounded-lg border border-border/60 px-3 py-2",
            ),
            group_heading("Stage accents"),
            el(
                "div",
                *[
                    el(
                        "div",
                        el(
                            "span",
                            f"{stage.title()} accent",
                            class_="block text-[10px] font-mono text-muted-foreground mb-1",
                        ),
                        accent_chips(stage),
                        class_="mb-2",
                    )
                    for stage in ("hook", "message", "metaphor", "conclusion")
                ],
            ),
            el(
                "input",
                id="new-project-background-motion-json",
                type="hidden",
                name="background_motion",
                value=motion,
            ),
            el(
                "input",
                id="new-project-emphasis-json",
                type="hidden",
                name="emphasis_style",
                value=emphasis,
            ),
            el(
                "input",
                id="new-project-loudness-json",
                type="hidden",
                name="loudness_target_lufs",
                value=lufs if lufs != "-14" else "",
            ),
            el(
                "input",
                id="new-project-audio-normalize-json",
                type="hidden",
                name="audio_normalize",
                value="" if normalize is True else "false",
            ),
            el(
                "input",
                id="new-project-section-holds-json",
                type="hidden",
                name="section_holds",
                value=json.dumps(holds) if any(v for v in holds.values()) else "",
            ),
            el(
                "input",
                id="new-project-stage-accents-json",
                type="hidden",
                name="stage_accents",
                value=json.dumps(accents) if any(v for v in accents.values()) else "",
            ),
            class_="space-y-3",
        ),
        "composer-phase2-panel",
        open_default=False,
    )
