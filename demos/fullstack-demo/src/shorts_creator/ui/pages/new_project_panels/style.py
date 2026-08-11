from lexigram.ui import el

from shorts_creator.pipeline.render_config import _DEFAULTS as _PIPELINE_DEFAULTS
from shorts_creator.ui.pages.new_project_panels.core import _composer_value, _panel
from shorts_creator.ui.pages.new_project_profile import _fmt_number


def _style_panel(profile=None):
    style = _composer_value(profile, "style", {})
    chunk = style.get("chunk_size", 3) if isinstance(style, dict) else 3
    caption_size = style.get("caption_font_size", 56) if isinstance(style, dict) else 56
    outline = style.get("caption_outline_width", 2) if isinstance(style, dict) else 2
    uppercase = style.get("uppercase", False) if isinstance(style, dict) else False
    scrim = style.get("scrim_alpha", 0) if isinstance(style, dict) else 0
    palette = _composer_value(profile, "palette", {})
    colour = (
        "#" + str(_PIPELINE_DEFAULTS["caption_highlight_colour"]).removeprefix("0x")[:6].lower()
    )
    if isinstance(palette, dict) and palette.get("highlight_colour"):
        hex_str = str(palette["highlight_colour"]).removeprefix("0x")
        if len(hex_str) >= 6:
            colour = "#" + hex_str[:6].lower()
    pill_colour = "#" + str(_PIPELINE_DEFAULTS["pill_bg_colour"]).removeprefix("0x")[:6].lower()
    if isinstance(palette, dict) and palette.get("pill_bg_colour"):
        hex_str = str(palette["pill_bg_colour"]).removeprefix("0x")
        if len(hex_str) >= 6:
            pill_colour = "#" + hex_str[:6].lower()
    return _panel(
        "Style — captions, chunking, palette",
        el(
            "div",
            el(
                "label",
                "Caption chunk size (words)",
                class_="block text-[11px] text-muted-foreground mb-1",
            ),
            el(
                "input",
                id="new-project-chunk-size",
                type="range",
                min="1",
                max="6",
                step="1",
                value=chunk,
                class_="w-full accent-primary",
            ),
            el(
                "label",
                "Caption font size",
                class_="block text-[11px] text-muted-foreground mb-1 mt-3",
            ),
            el(
                "input",
                id="new-project-caption-size",
                type="range",
                min="32",
                max="80",
                step="2",
                value=caption_size,
                class_="w-full accent-primary",
            ),
            el(
                "label",
                "Caption outline width (px)",
                class_="block text-[11px] text-muted-foreground mb-1 mt-3",
            ),
            el(
                "input",
                id="new-project-outline-width",
                type="range",
                min="0",
                max="8",
                step="1",
                value=outline,
                class_="w-full accent-primary",
            ),
            el(
                "label",
                "Highlight colour",
                class_="block text-[11px] text-muted-foreground mb-1 mt-3",
            ),
            el(
                "div",
                el(
                    "input",
                    id="new-project-highlight-colour",
                    type="color",
                    value=colour,
                    class_="w-10 h-8 rounded border border-border",
                ),
                el(
                    "input",
                    id="new-project-pill-colour",
                    type="color",
                    value=pill_colour,
                    class_="w-10 h-8 rounded border border-border ml-2",
                    title="Hook pill background",
                ),
                class_="flex items-center",
            ),
            el(
                "label",
                el(
                    "input",
                    id="new-project-uppercase",
                    type="checkbox",
                    checked=uppercase,
                    class_="accent-primary",
                ),
                el("span", "Uppercase captions", class_="text-xs text-foreground"),
                class_="flex items-center gap-2 mt-3",
            ),
            el(
                "label",
                "Caption scrim alpha",
                class_="block text-[11px] text-muted-foreground mb-1 mt-3",
            ),
            el(
                "input",
                id="new-project-scrim",
                type="range",
                min="0",
                max="1",
                step="0.05",
                value=scrim,
                class_="w-full accent-primary",
            ),
        ),
        "composer-style-panel",
        open_default=False,
    )


def _placement_panel(profile=None):
    layout = _composer_value(profile, "layout", {})
    layout = layout if isinstance(layout, dict) else {}
    anchor = layout.get("anchor", "center")
    block_width = layout.get("block_width_pct", 80)
    numbered_scale = layout.get("numbered_scale", 1.6)
    pill_per_word = layout.get("pill_per_word", True)
    watermark_corner = layout.get("watermark_corner", "bottom_right")
    watermark_size = layout.get("watermark_size_pct", 10)
    watermark_opacity = layout.get("watermark_opacity", 0.85)
    music_volume = layout.get("music_volume", 0.2)
    music_fade = layout.get("music_fade_seconds", 2.0)
    fade_out = layout.get("fade_out_seconds", 1.0)

    def anchor_btn(name: str, label: str):
        active = anchor == name
        cls = "anchor-btn px-3 py-1.5 text-xs rounded-lg cursor-pointer transition-colors " + (
            "bg-primary text-primary-foreground" if active else "bg-secondary text-foreground"
        )
        return el("button", label, type="button", data_anchor=name, class_=cls)

    return _panel(
        "Placement — anchor, block size, numbered screens",
        el(
            "div",
            el("label", "Anchor", class_="block text-[11px] text-muted-foreground mb-1"),
            el(
                "div",
                anchor_btn("center", "Center"),
                anchor_btn("lower_third", "Lower third"),
                id="new-project-anchor",
                class_="flex gap-2",
            ),
            el(
                "label", "Block width %", class_="block text-[11px] text-muted-foreground mb-1 mt-3"
            ),
            el(
                "input",
                id="new-project-block-width",
                type="range",
                min="40",
                max="100",
                step="5",
                value=block_width,
                class_="w-full accent-primary",
            ),
            el(
                "label",
                "Numbered screen scale",
                class_="block text-[11px] text-muted-foreground mb-1 mt-3",
            ),
            el(
                "input",
                id="new-project-numbered-scale",
                type="range",
                min="1.2",
                max="2.5",
                step="0.1",
                value=numbered_scale,
                class_="w-full accent-primary",
            ),
            el(
                "label",
                el(
                    "input",
                    id="new-project-pill-mode",
                    type="checkbox",
                    checked=pill_per_word,
                    class_="accent-primary",
                ),
                el("span", "One word per pill (hook)", class_="text-xs text-foreground"),
                class_="flex items-center gap-2 mt-3",
            ),
            el(
                "label",
                "Watermark corner",
                class_="block text-[11px] text-muted-foreground mb-1 mt-3",
            ),
            el(
                "select",
                el(
                    "option",
                    "Bottom right",
                    value="bottom_right",
                    selected=watermark_corner == "bottom_right",
                ),
                el(
                    "option",
                    "Bottom left",
                    value="bottom_left",
                    selected=watermark_corner == "bottom_left",
                ),
                el(
                    "option",
                    "Top right",
                    value="top_right",
                    selected=watermark_corner == "top_right",
                ),
                el("option", "Top left", value="top_left", selected=watermark_corner == "top_left"),
                id="new-project-watermark-corner",
                class_="w-full rounded-lg bg-secondary/80 border border-border px-3 py-1.5 text-xs text-foreground",
            ),
            el(
                "label",
                "Watermark size %",
                class_="block text-[11px] text-muted-foreground mb-1 mt-3",
            ),
            el(
                "input",
                id="new-project-watermark-size",
                type="range",
                min="5",
                max="30",
                step="1",
                value=watermark_size,
                class_="w-full accent-primary",
            ),
            el(
                "label",
                "Watermark opacity",
                class_="block text-[11px] text-muted-foreground mb-1 mt-3",
            ),
            el(
                "input",
                id="new-project-watermark-opacity",
                type="range",
                min="0.1",
                max="1",
                step="0.05",
                value=watermark_opacity,
                class_="w-full accent-primary",
            ),
            el("label", "Music volume", class_="block text-[11px] text-muted-foreground mb-1 mt-3"),
            el(
                "input",
                id="new-project-music-volume",
                type="range",
                min="0.05",
                max="0.5",
                step="0.05",
                value=music_volume,
                class_="w-full accent-primary",
            ),
            el(
                "label",
                "Music fade (s)",
                class_="block text-[11px] text-muted-foreground mb-1 mt-3",
            ),
            el(
                "input",
                id="new-project-music-fade",
                type="range",
                min="0.5",
                max="6",
                step="0.5",
                value=_fmt_number(music_fade),
                class_="w-full accent-primary",
            ),
            el("label", "Fade out (s)", class_="block text-[11px] text-muted-foreground mb-1 mt-3"),
            el(
                "input",
                id="new-project-fade-out",
                type="range",
                min="0",
                max="3",
                step="0.1",
                value=_fmt_number(fade_out),
                class_="w-full accent-primary",
            ),
            el("input", id="new-project-layout-json", type="hidden", name="layout", value=""),
        ),
        "composer-placement-panel",
        open_default=False,
    )
