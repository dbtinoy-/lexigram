from __future__ import annotations

from dataclasses import dataclass, field

from shorts_creator.contracts.matcher import FormatSide, format_side_from_frontmatter

_COLOUR_DEFAULT_KEYS = ("caption_highlight_colour", "pill_bg_colour")


def _normalise_colour_value(value: object) -> object:
    if isinstance(value, int) and not isinstance(value, bool):
        return f"0x{value:08X}"
    return value


def _normalise_defaults(defaults: dict) -> dict:
    normalised = {k: v for k, v in defaults.items()}
    for key in _COLOUR_DEFAULT_KEYS:
        if key in normalised:
            normalised[key] = _normalise_colour_value(normalised[key])
    accents = normalised.get("stage_accents")
    if isinstance(accents, dict):
        normalised["stage_accents"] = {k: _normalise_colour_value(v) for k, v in accents.items()}
    return normalised


@dataclass(frozen=True)
class FormatDefinition:
    """A presentation format for rendered shorts.

    The format decides how script content is shown on screen, including
    the reel's duration and pacing budget. A format declares the caption
    styles it supports; the pipeline consumes one of them at render time.
    Data lives in data/formats/<name>/FORMAT.md.
    """

    name: str
    label: str
    description: str
    caption_styles: list[str]
    default_caption_style: str
    duration_range: tuple[int, int] = (30, 60)
    pacing_wps_range: tuple[float, float] = (2.0, 3.0)
    requires: dict[str, list[str]] = field(default_factory=dict)
    objectives: list[str] = field(default_factory=list)
    assets: list[str] = field(default_factory=list)
    layout: dict = field(default_factory=dict)
    palette: dict = field(default_factory=dict)
    defaults: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, d: dict) -> FormatDefinition:
        if "caption_styles" in d:
            styles = [str(s) for s in (d["caption_styles"] or [])]
        else:
            styles = ["highlight"]
        duration = d.get("duration_range") or [30, 60]
        pacing = d.get("pacing_wps_range") or [2.0, 3.0]
        return cls(
            name=str(d.get("name", "")),
            label=str(d.get("label", "")),
            description=str(d.get("description", "")),
            caption_styles=styles,
            default_caption_style=str(
                d.get("default_caption_style") or (styles[0] if styles else "")
            ),
            duration_range=(int(duration[0]), int(duration[1])),
            pacing_wps_range=(float(pacing[0]), float(pacing[1])),
            requires=dict(d.get("requires") or {}),
            objectives=[str(o) for o in (d.get("objectives") or [])],
            assets=[str(a) for a in (d.get("assets") or [])],
            layout=dict(d.get("layout") or {}),
            palette={
                str(k): (v if not isinstance(v, int) or isinstance(v, bool) else f"0x{v:08X}")
                for k, v in (d.get("palette") or {}).items()
            },
            defaults=_normalise_defaults(d.get("defaults") or {}),
        )

    def to_contract_side(self) -> FormatSide:
        """Contractual view of what this format requires (validated at load)."""
        requires = dict(self.requires)
        if self.assets and not requires.get("assets"):
            requires["assets"] = list(self.assets)
        return format_side_from_frontmatter(self.name, requires, self.objectives)
