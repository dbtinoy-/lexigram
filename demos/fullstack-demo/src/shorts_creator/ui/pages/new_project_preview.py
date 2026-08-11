import random
from pathlib import Path

from lexigram.ui import el
from markupsafe import Markup

from shorts_creator.pipeline.render_config import (
    _DEFAULTS as _PIPELINE_DEFAULTS,
)
from shorts_creator.services.asset_service import ASSETS_ROOT
from shorts_creator.ui.pages.new_project_wizard import _SKELETONS

# ──────────────────────────────────────────────
# Guided project creation
# ──────────────────────────────────────────────


def _pick_preview_background() -> tuple[str, str]:
    """Local nature clip whenever bundled footage exists, stock-style image only
    as a last resort (the real pipeline is always nature clips, so random
    subject images would misrepresent the final reel)."""
    clips = sorted(Path(ASSETS_ROOT, "clip").glob("*.mp4"))
    if clips:
        return "video", "/api/preview/clip"
    return "image", f"https://picsum.photos/seed/{random.randrange(10**9)}/540/960"


_PREVIEW_SCALE = 360.0 / 1080.0
_CAPTION_FONT_PX = round(56 * _PREVIEW_SCALE, 2)  # CAPTION_FONT_SIZE
_CAPTION_STROKE_PX = round(2 * _PREVIEW_SCALE, 2)  # CAPTION_OUTLINE_WIDTH
_CAPTION_PILL_COLOR = (
    "#" + str(_PIPELINE_DEFAULTS["caption_highlight_colour"])[2:-2]
)  # CAPTION_HIGHLIGHT_COLOUR
_CAPTION_PILL_PAD_PX = round(8 * _PREVIEW_SCALE, 2)  # _HIGHLIGHT_PAD_PX
_HOOK_PILL_COLOR = (
    "rgba(0,0,0," + f"{int(str(_PIPELINE_DEFAULTS['pill_bg_colour'])[-2:], 16) / 255:.2f}" + ")"
)  # pill 0x000000C0
_HOOK_PILL_PAD_PX = round(12 * _PREVIEW_SCALE, 2)  # _draw_pill pad
_HOOK_GAP_PX = round(18 * _PREVIEW_SCALE, 2)  # HOOK_LINE_GAP_PX


def _preview_hook_font_px(texts: list[str]) -> float:
    """Same fit as compose.hook_font_size, scaled for the preview screen."""
    max_chars = max(len(t) for t in texts)
    width_fit = (0.80 * 1080) / (max_chars * 0.55)
    height_fit = (0.70 * 1920) / (len(texts) * 1.3)
    size = max(40, min(110, width_fit, height_fit))
    return round(size * _PREVIEW_SCALE, 2)


def _hook_pills(text: str, style: str) -> list:
    """One pill per hook word, mirroring the real hook screen: the pipeline
    chunks the hook line with HOOK_LINE_TARGET_SIZE = 1 so every word is its
    own row (pipeline.py _render_hook_clip / captions.group_for_hook_display)."""
    return [el("span", word, class_="pv-hook block", style_=style) for word in text.split()]


preview_styles = f"""
<style>
@font-face {{
  font-family: 'PreviewDejaVu';
  src: url('/api/preview/font') format('truetype');
}}
.pv-font {{ font-family: 'PreviewDejaVu', ui-sans-serif, system-ui, sans-serif; }}
.pv-hook {{
  display: inline-block;
  font-family: 'PreviewDejaVu', ui-sans-serif, system-ui, sans-serif;
  font-weight: 800;
  color: #fff;
  background: {_HOOK_PILL_COLOR};
  border-radius: {_HOOK_PILL_PAD_PX}px;
  padding: {_HOOK_PILL_PAD_PX}px;
  line-height: 1.3;
}}
.pv-cap {{
  font-family: 'PreviewDejaVu', ui-sans-serif, system-ui, sans-serif;
  color: #fff;
  font-size: {_CAPTION_FONT_PX}px;
  line-height: 1.3;
  white-space: nowrap;
  -webkit-text-stroke: {_CAPTION_STROKE_PX}px #000;
  text-shadow: -0.5px 0 0 #000, 0.5px 0 0 #000, 0 -0.5px 0 #000, 0 0.5px 0 #000;
}}
.pv-pill {{
  background: {_CAPTION_PILL_COLOR};
  border-radius: {_CAPTION_PILL_PAD_PX}px;
  padding: {_CAPTION_PILL_PAD_PX}px;
}}
</style>
"""


def _picker_fallback_chip() -> str:
    """Tiny hint under the phone when the preview runs the fallback clip."""
    return Markup(
        str(
            el(
                "button",
                el(
                    "span",
                    "i",
                    class_="w-3.5 h-3.5 grid place-items-center rounded-full bg-foreground/10 text-[8px] font-bold",
                ),
                el("span", "Fallback clip — set your background in Composer · Media"),
                type="button",
                onclick=(
                    "switchCreateTab('composer');"
                    "var el=document.getElementById('composer-media-panel-wrapper');"
                    "if (el) el.scrollIntoView({behavior:'smooth', block:'start'});"
                ),
                class_=(
                    "mt-2 inline-flex items-center gap-1.5 text-[10px] font-mono "
                    "text-muted-foreground/70 bg-secondary/40 border border-border/60 "
                    "rounded-full px-3 py-1 hover:text-foreground hover:border-border transition-colors"
                ),
            )
        )
    )


def _preview_phone(active_classes=None, background_src=None) -> str:
    """9:16 phone mockup with live mirrors of the form fields.

    `background_src` switches the phone into playback mode: the rendered
    video fills the screen with native controls, and the preview
    overlays/buttons are omitted so both states share the same frame.
    """
    playback = bool(background_src)
    if playback:
        kind, src = "video", background_src
    else:
        kind, src = _pick_preview_background()
    hook_text = _SKELETONS["narrated"][0]["text"]
    hook_style = f"font-size:{_preview_hook_font_px(hook_text.split())}px"
    hook_pills = _hook_pills(hook_text, hook_style)
    background = (
        el(
            "video",
            src=src,
            id="preview-bg-video",
            class_="absolute inset-0 w-full h-full object-cover",
            autoplay=True,
            muted=True,
            loop=True,
            playsinline=True,
            preload="metadata",
            controls=playback,
        )
        if kind == "video"
        else el(
            "img",
            src=src,
            alt="",
            class_="absolute inset-0 w-full h-full object-cover",
            loading="lazy",
        )
    )
    top_row = (
        [
            el(
                "div",
                el(
                    "span",
                    id="preview-topic-dot",
                    class_="w-2.5 h-2.5 rounded-full bg-secondary inline-block",
                ),
                el(
                    "span",
                    "PREVIEW",
                    class_="text-[9px] font-mono tracking-[0.2em] text-muted-foreground",
                ),
                el(
                    "div",
                    *(
                        el(
                            "button",
                            label,
                            type="button",
                            data_preview_section=name,
                            onclick=f"setPreviewSection('{name}')",
                            aria_pressed="true" if name == "full" else "false",
                            class_="px-2 py-1 rounded-full text-[9px] font-mono tracking-wider uppercase transition-colors "
                            + (
                                "bg-primary text-primary-foreground"
                                if name == "full"
                                else "bg-secondary/80 text-muted-foreground hover:bg-secondary"
                            ),
                        )
                        for name, label in (
                            ("intro", "Intro"),
                            ("mid", "Mid"),
                            ("outro", "Outro"),
                            ("full", "Full"),
                        )
                    ),
                    id="preview-section-tabs",
                    class_="flex items-center gap-1 ml-2",
                ),
                class_="flex items-center gap-2",
            ),
        ]
        if not playback
        else []
    )
    return Markup(
        str(
            el(
                "div",
                el(
                    "div",
                    *top_row,
                    el(
                        "div",
                        el(
                            "div",
                            class_="absolute -left-[3px] top-24 w-[3px] h-8 bg-foreground/5 rounded-l-md",
                        ),
                        el(
                            "div",
                            class_="absolute -left-[3px] top-36 w-[3px] h-14 bg-foreground/5 rounded-l-md",
                        ),
                        el(
                            "div",
                            class_="absolute -right-[3px] top-28 w-[3px] h-16 bg-foreground/5 rounded-r-md",
                        ),
                        el(
                            "div",
                            class_="absolute -right-[3px] top-52 w-[3px] h-10 bg-foreground/5 rounded-r-md",
                        ),
                        el(
                            "div",
                            el(
                                "div",
                                background,
                                el("div", class_="absolute inset-0 bg-foreground/20")
                                if not playback
                                else None,
                                id="preview-bg-layer",
                                class_="absolute inset-0",
                            ),
                            el(
                                "div",
                                el(
                                    "span",
                                    "Thanks for watching",
                                    id="preview-outro-text",
                                    class_="pv-font absolute inset-0 flex items-center justify-center text-primary-foreground text-[32px]",
                                ),
                                id="preview-outro",
                                style_="display:none;background:#0a0a32",
                                class_="absolute inset-0",
                            )
                            if not playback
                            else None,
                            el(
                                "div",
                                el(
                                    "div",
                                    el(
                                        "span",
                                        "9:41",
                                        class_="text-[8px] font-mono text-muted-foreground",
                                    ),
                                    el("div", class_="w-24 h-6 bg-card rounded-full"),
                                    el(
                                        "span",
                                        el("span", class_="w-full h-full bg-muted rounded-[1px]"),
                                        class_="w-4 h-2 rounded-[2px] border border-border flex items-end p-[1px]",
                                    ),
                                    class_="flex items-center justify-between px-2 pt-1.5",
                                ),
                                el(
                                    "div",
                                    el(
                                        "div",
                                        *hook_pills,
                                        id="preview-hook-block",
                                        class_="text-center",
                                    ),
                                    el(
                                        "div",
                                        el(
                                            "div",
                                            el(
                                                "div",
                                                el("span", "First", class_="pv-cap"),
                                                el("span", "practice,", class_="pv-cap pv-pill"),
                                                el("span", "kept", class_="pv-cap"),
                                                el("span", "concrete", class_="pv-cap"),
                                                id="preview-caption-highlight",
                                                class_="text-center",
                                            ),
                                            el(
                                                "div",
                                                "First practice, kept concrete",
                                                id="preview-caption-plain",
                                                class_="pv-cap text-center",
                                            ),
                                            id="preview-caption",
                                            class_="flex flex-col justify-center gap-1",
                                        ),
                                        el(
                                            "div",
                                            id="preview-ranking-block",
                                            class_="text-center flex flex-col items-center justify-center gap-1",
                                            style_="display:none",
                                        ),
                                        id="preview-mid-block",
                                        class_="flex flex-col justify-center",
                                    ),
                                    class_="flex-1 flex flex-col justify-center gap-8 px-1",
                                )
                                if not playback
                                else None,
                                el(
                                    "div",
                                    el(
                                        "div",
                                        id="preview-duration-fill",
                                        class_="h-1 rounded-full bg-gradient-to-r from-muted to-foreground",
                                    ),
                                    el(
                                        "div",
                                        el(
                                            "div", class_="absolute inset-y-0 w-px bg-foreground/50"
                                        ),
                                        el(
                                            "div", class_="absolute inset-y-0 w-px bg-foreground/50"
                                        ),
                                        id="preview-timeline-ticks",
                                        class_="absolute inset-0",
                                    ),
                                    id="preview-duration-bar",
                                    class_="relative h-1 rounded-full bg-secondary overflow-hidden",
                                )
                                if not playback
                                else None,
                                el(
                                    "div",
                                    el(
                                        "span",
                                        "0:00 / 0:30",
                                        id="preview-position-display",
                                        class_="text-[10px] text-muted-foreground/60 tabular-nums",
                                    ),
                                    class_="w-full flex justify-end",
                                )
                                if not playback
                                else None,
                                el(
                                    "div",
                                    class_="w-24 h-1 bg-secondary/80 rounded-full mx-auto mt-3 mb-1",
                                )
                                if not playback
                                else None,
                                class_="relative z-10 flex-1 flex flex-col",
                            ),
                            el(
                                "button",
                                el(
                                    "span",
                                    el(
                                        "svg",
                                        el("path", d="M8 5v14l11-7z"),
                                        viewBox="0 0 24 24",
                                        fill="white",
                                        class_="w-5 h-5 ml-0.5",
                                    ),
                                    id="preview-play-icon",
                                ),
                                el(
                                    "span",
                                    el(
                                        "svg",
                                        el("rect", x="6", y="5", width="4", height="14"),
                                        el("rect", x="14", y="5", width="4", height="14"),
                                        viewBox="0 0 24 24",
                                        fill="white",
                                        class_="w-5 h-5",
                                    ),
                                    id="preview-pause-icon",
                                    style_="display:none",
                                ),
                                id="preview-play-btn",
                                type="button",
                                onclick="togglePreviewPlay()",
                                aria_label="Play or pause preview",
                                class_="absolute inset-0 m-auto z-30 w-14 h-14 rounded-full bg-foreground/20 text-primary-foreground grid place-items-center",
                            )
                            if not playback
                            else None,
                            el(
                                "div",
                                class_="absolute inset-0 rounded-[2.8rem] pointer-events-none bg-gradient-to-b from-white/5 via-transparent to-transparent",
                            ),
                            class_="relative w-[360px] h-full min-h-[700px] bg-foreground/5 rounded-[2.8rem] overflow-hidden px-4 pb-5 pt-2 flex flex-col",
                        ),
                        id="preview-phone-frame",
                        class_="relative flex-1 w-fit rounded-[3.4rem] bg-foreground/5 border-4 border-foreground/10 p-3.5 shadow-2xl",
                        data_topic_accents="true",
                    ),
                    _picker_fallback_chip() if not playback else None,
                    class_="w-full h-full flex flex-col items-center gap-3",
                ),
                id="new-project-preview-phone",
                class_="flex items-start justify-center max-h-[740px]",
            )
        )
    )
