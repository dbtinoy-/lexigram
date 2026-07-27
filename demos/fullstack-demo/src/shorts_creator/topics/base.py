from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from shorts_creator.contracts.matcher import TopicSide


@dataclass
class ScriptSection:
    name: str
    text: str
    duration_seconds: float


@dataclass
class ParsedScript:
    title: str
    sections: list[ScriptSection]
    total_duration: float
    word_count: int
    pacing_wps: float
    emotional_arc: list[str] | None = None
    metadata: dict | None = None


@dataclass
class Idea:
    title: str
    core_message: str
    hook_line: str
    identity_signal: str
    permission_given: str
    emotional_arc: str
    target_audience: str
    quotability_score: float
    share_trigger: str
    topic: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> Idea:
        known = set(cls.__dataclass_fields__.keys())
        return cls(**{k: v for k, v in d.items() if k in known})


@runtime_checkable
class Topic(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def label(self) -> str: ...

    @property
    def description(self) -> str: ...

    @property
    def structure_sections(self) -> list[str]: ...

    @property
    def topic_categories(self) -> list[str]: ...

    @property
    def banned_phrases(self) -> list[str]: ...

    @property
    def background_queries(self) -> list[str]: ...

    @property
    def default_format(self) -> str | None: ...

    def build_idea_prompt(
        self,
        count: int,
        focus: str,
        seo_context: str = "",
        voice: dict | None = None,
    ) -> str: ...

    def parse_ideas(self, text: str) -> list[Idea]: ...

    def build_script_prompt(
        self,
        idea: Idea,
        angle_context: str = "",
        format_name: str = "",
        pacing_wps: float | None = None,
        voice: dict | None = None,
    ) -> str: ...

    def parse_script(self, text: str) -> ParsedScript: ...

    def to_contract_side(self) -> TopicSide: ...

    def mock_ideas(self, count: int = 10) -> str: ...

    def mock_script(self) -> str: ...

    def mock_seo(self) -> str: ...


def _backfill_seconds(sections: dict[str, float | None], target: float) -> dict[str, float]:
    missing = [k for k, v in sections.items() if v is None]
    if not missing:
        return {k: v for k, v in sections.items() if v is not None}
    known = sum(v for v in sections.values() if v is not None)
    remaining = max(target - known, len(missing))
    share = remaining / len(missing)
    return {k: (v if v is not None else share) for k, v in sections.items()}


def _extract_section(text: str, name: str) -> tuple[float | None, str]:
    m = re.search(rf'\[{name}\s*(?:[-–—]\s*)?([\d.]+)s\]\s*\n"([^"]+)"', text)
    if m:
        return float(m.group(1)), m.group(2)
    m = re.search(rf'\[{name}\s*(?:[-–—]\s*)?N?s?\]\s*\n"([^"]+)"', text)
    if m:
        return None, m.group(1)
    raise ValueError(f"Could not find {name} section in script output")


def _extract_items_section(text: str, fallback_seconds: float) -> list[ScriptSection]:
    """Extract the [TOP_ITEMS - Ns] block: header + exactly 5 quoted numbered
    lines, as one ScriptSection per item. Each item gets duration
    block_seconds / 5 (header seconds, or ``fallback_seconds`` when the
    header carries no number)."""
    m = re.search(
        r'\[TOP_ITEMS\s*(?:[-–—]\s*)?([\d.]+)?[Nn]?s?\]\s*\n((?:"[^"]+"\s*\n?)+)',
        text,
    )
    if not m:
        raise ValueError("Could not find TOP_ITEMS section in script output")
    block_seconds = float(m.group(1)) if m.group(1) else fallback_seconds
    lines = re.findall(r'"([^"]+)"', m.group(2))
    if len(lines) != 5:
        raise ValueError(f"TOP_ITEMS section must contain exactly 5 items, got {len(lines)}")
    share = block_seconds / 5
    return [ScriptSection(name="top_items", text=line, duration_seconds=share) for line in lines]


def _parse_topn_script(text: str) -> ParsedScript:
    """Shared parser for ranked-list scripts: hook + exactly 5 top_items +
    conclusion. Used by every topic's parse_script when the text carries a
    [TOP_ITEMS] block."""
    title_match = re.search(r"TITLE:\s*(.+)", text)
    title = title_match.group(1).strip() if title_match else "Untitled"
    wc_match = re.search(r"WORD COUNT:\s*(\d+)", text)
    word_count = int(wc_match.group(1)) if wc_match else 0
    pacing_match = re.search(r"PACING:\s*([\d.]+)", text)
    pacing_wps = float(pacing_match.group(1)) if pacing_match else 0.0
    duration_match = re.search(r"DURATION:\s*([\d.]+)", text)

    hook_sec, hook = _extract_section(text, "HOOK")
    conc_sec, conclusion = _extract_section(text, "CONCLUSION")
    base_target = (
        float(duration_match.group(1)) if duration_match else word_count / max(pacing_wps, 0.1)
    )
    items = _extract_items_section(
        text,
        fallback_seconds=max(base_target - (hook_sec or 0) - (conc_sec or 0), 0.0),
    )
    items_sec = sum(s.duration_seconds for s in items)
    if hook_sec is None or conc_sec is None:
        filled = _backfill_seconds(
            {"hook": hook_sec, "conclusion": conc_sec}, base_target - items_sec
        )
        hook_sec = filled["hook"]
        conc_sec = filled["conclusion"]
    total_dur = (
        float(duration_match.group(1)) if duration_match else hook_sec + items_sec + conc_sec
    )

    arc_match = re.search(r"EMOTIONAL ARC MAP:\s*\n(.+)", text)
    arcs = [s.strip() for s in re.split(r"->|→", arc_match.group(1))] if arc_match else []

    sections = [
        ScriptSection("hook", hook, hook_sec),
        *items,
        ScriptSection("conclusion", conclusion, conc_sec),
    ]
    return ParsedScript(
        title=title,
        sections=sections,
        total_duration=total_dur,
        word_count=word_count,
        pacing_wps=pacing_wps,
        emotional_arc=arcs,
    )


def _fact_sections(text: str) -> list[tuple[float | None, str]]:
    """All [FACT] blocks in order as (seconds, line); seconds is None when
    the "Ns" placeholder was left unfilled."""
    found = []
    for seconds, line in re.findall(
        r'\[FACT\s*(?:[-–—]\s*)?([\d.]*)\s*N?s?\]\s*\n"([^"]+)"',
        text,
    ):
        found.append((float(seconds) if seconds else None, line))
    return found


def _parse_myth_script(text: str) -> ParsedScript:
    """Shared parser for myth-vs-fact scripts: hook + one claim + correcting
    facts + twist + conclusion. Used by every topic's parse_script when the
    text carries a [CLAIM] block."""
    title_match = re.search(r"TITLE:\s*(.+)", text)
    title = title_match.group(1).strip() if title_match else "Untitled"
    wc_match = re.search(r"WORD COUNT:\s*(\d+)", text)
    word_count = int(wc_match.group(1)) if wc_match else 0
    pacing_match = re.search(r"PACING:\s*([\d.]+)", text)
    pacing_wps = float(pacing_match.group(1)) if pacing_match else 0.0
    duration_match = re.search(r"DURATION:\s*([\d.]+)", text)

    hook_sec, hook = _extract_section(text, "HOOK")
    claim_sec, claim = _extract_section(text, "CLAIM")
    twist_sec, twist = _extract_section(text, "TWIST")
    conc_sec, conclusion = _extract_section(text, "CONCLUSION")
    fact_sections = _fact_sections(text)

    base_target = (
        float(duration_match.group(1)) if duration_match else word_count / max(pacing_wps, 0.1)
    )
    fill = {"hook": hook_sec, "claim": claim_sec, "twist": twist_sec, "conclusion": conc_sec}
    for idx, (sec, _line) in enumerate(fact_sections):
        fill[f"fact_{idx}"] = sec
    filled = _backfill_seconds(fill, base_target)
    hook_sec = filled["hook"]
    claim_sec = filled["claim"]
    twist_sec = filled["twist"]
    conc_sec = filled["conclusion"]
    fact_secs = [filled[f"fact_{idx}"] for idx in range(len(fact_sections))]

    total_dur = (
        float(duration_match.group(1))
        if duration_match
        else hook_sec + claim_sec + sum(fact_secs) + twist_sec + conc_sec
    )

    arc_match = re.search(r"EMOTIONAL ARC MAP:\s*\n(.+)", text)
    arcs = [s.strip() for s in re.split(r"->|→", arc_match.group(1))] if arc_match else []

    sections = [
        ScriptSection("hook", hook, hook_sec),
        ScriptSection("claim", claim, claim_sec),
        *[
            ScriptSection("fact", line, sec)
            for sec, line in zip(fact_secs, (line for _sec, line in fact_sections))
        ],
        ScriptSection("twist", twist, twist_sec),
        ScriptSection("conclusion", conclusion, conc_sec),
    ]
    return ParsedScript(
        title=title,
        sections=sections,
        total_duration=total_dur,
        word_count=word_count,
        pacing_wps=pacing_wps,
        emotional_arc=arcs,
    )


def _parse_common_ideas(text: str) -> list[dict]:
    blocks = re.split(r"\n(?:#{1,6}\s+|\*{0,2})IDEA #?\d+:\s*\*{0,2}\s*", "\n" + text)[1:]
    results = []
    for block in blocks:
        title_line, _, rest = block.partition("\n")
        title = re.sub(r"\*+", "", title_line).strip()
        fields = {
            re.sub(r"\*+", "", k).strip(): re.sub(r"\*+", "", v).strip()
            for k, v in re.findall(r"[•*]\s*([^:]+):\s*(.+)", rest)
        }
        results.append({"title": title, "fields": fields})
    return results
