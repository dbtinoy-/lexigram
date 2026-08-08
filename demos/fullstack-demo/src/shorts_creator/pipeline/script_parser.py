"""Parses LLM output produced from prompts.SCRIPTWRITING_PROMPT and
prompts.IDEA_GENERATION_PROMPT into structured data."""

import re
from dataclasses import dataclass, field


@dataclass
class ParsedScript:
    title: str
    duration_seconds: float
    word_count: int
    pacing_wps: float
    hook: str
    hook_seconds: float
    message_lines: list[str]
    message_seconds: float
    metaphor: str
    metaphor_seconds: float
    conclusion: str
    conclusion_seconds: float
    emotional_arc: list[str]
    parallel_structure: str
    hook_score: str
    top_items: list[str] = field(default_factory=list)
    top_items_seconds: float = 0.0
    fact_count: int = 0
    claim: str = ""
    twist: str = ""
    emphasis: list[str] = field(default_factory=list)
    section_names: list[str] = field(default_factory=list)


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


def _section(text: str, name: str) -> tuple[float | None, str]:
    """Extract (seconds, first_quoted_line) for a single-line section.

    Seconds is None when the LLM left the "Ns" placeholder unfilled, signaling
    the caller should backfill a non-zero duration rather than produce a
    0-frame timeline clip.
    """
    match = re.search(rf'\[{name}\s*(?:[-–—]\s*)?([\d.]+)s\]\s*\n"([^"]+)"', text)
    if match:
        return float(match.group(1)), match.group(2)
    match = re.search(rf'\[{name}\s*(?:[-–—]\s*)?N?s?\]\s*\n"([^"]+)"', text)
    if match:
        return None, match.group(1)
    raise ValueError(f"Could not find {name} section in script output")


def _section_optional(text: str, name: str) -> tuple[float | None, str]:
    """Like _section but returns (None, "") when the section is absent, for
    sections that only some script structures emit."""
    try:
        return _section(text, name)
    except ValueError:
        return None, ""


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


def _backfill_missing_seconds(
    sections: dict[str, float | None], target_total: float
) -> dict[str, float]:
    """Split whatever duration remains after known sections evenly across
    sections whose timing the LLM left unfilled, with a 1s floor so no
    section (and therefore no timeline clip) ends up at 0 or negative length.
    """
    missing = [k for k, v in sections.items() if v is None]
    if not missing:
        return {k: v for k, v in sections.items() if v is not None}
    known_total = sum(v for v in sections.values() if v is not None)
    remaining = max(target_total - known_total, len(missing))
    share = remaining / len(missing)
    return {k: (v if v is not None else share) for k, v in sections.items()}


def apply_profile_overrides(saved: dict, snapshot: dict | None) -> ParsedScript:
    """Apply resolved profile content knobs (hook_text, section_texts) on top
    of a saved idea script before pipeline conversion. Copy stays
    author-controlled; only explicitly resolved knobs win."""
    merged = dict(saved)
    if snapshot:
        hook_text = snapshot.get("hook_text")
        if hook_text and hook_text.strip():
            merged["hook"] = hook_text.strip()
            for sec in merged.get("sections") or []:
                if sec.get("name") == "hook":
                    sec["text"] = hook_text
        section_texts = snapshot.get("section_texts") or {}
        if section_texts and merged.get("sections"):
            for sec in merged["sections"]:
                name = sec.get("name")
                if section_texts.get(name):
                    sec["text"] = section_texts[name]
        emphasis_words = snapshot.get("emphasis_words")
        if emphasis_words:
            merged["emphasis"] = [
                w.strip() for w in re.split(r"[,\n]", str(emphasis_words)) if w.strip()
            ]
    return to_pipeline_script(merged)


def to_pipeline_script(saved: dict) -> ParsedScript:
    """Convert a saved idea script dict (new sections format or legacy
    top-level keys) into the pipeline's fixed-section ParsedScript.

    Sections are matched by name; any section that is not hook, metaphor,
    conclusion, or top_items is folded into the narration message_lines so
    scripts from skills with different structures still render fully.
    """
    sections = saved.get("sections") or []
    known_names = {"hook", "metaphor", "conclusion", "top_items"}

    def _section_text(name: str) -> str:
        for sec in sections:
            if sec.get("name") == name:
                return sec.get("text", "")
        return saved.get(name, "")

    def _section_seconds(name: str) -> float:
        for sec in sections:
            if sec.get("name") == name:
                return sec.get("duration_seconds", 0) or 0
        return saved.get(f"{name}_seconds", 0) or 0

    if sections:
        message_lines = []
        message_seconds = 0.0
        top_items = []
        top_items_seconds = 0.0
        fact_count = 0
        claim = ""
        twist = ""
        top_item_labels = []
        message_labels = []
        for sec in sections:
            name = sec.get("name", "")
            text = sec.get("text", "")
            seconds = sec.get("duration_seconds", 0) or 0
            if name == "top_items":
                if text:
                    top_items.append(text)
                    top_item_labels.append("top_items")
                top_items_seconds += seconds
                continue
            if name == "claim":
                claim = text
            elif name == "fact":
                fact_count += 1
            elif name == "twist":
                twist = text
            if name in known_names:
                continue
            if text:
                message_lines.append(text)
                message_labels.append("message")
            message_seconds += seconds
        section_names = ["hook"] + top_item_labels + message_labels + ["metaphor", "conclusion"]
        duration = (
            saved.get("total_duration")
            or saved.get("duration_seconds")
            or sum(sec.get("duration_seconds", 0) or 0 for sec in sections)
            or 0
        )
    else:
        message_lines = saved.get("message_lines", []) or []
        message_seconds = _section_seconds("message")
        top_items = saved.get("top_items", []) or []
        top_items_seconds = saved.get("top_items_seconds", 0) or 0
        duration = saved.get("duration_seconds", 0) or 0
        fact_count = 0
        claim = ""
        twist = ""
        inferred = []
        if len(message_lines) == 1:
            inferred = ["hook"]
        elif len(message_lines) >= 2:
            inferred = ["hook"] + ["message"] * (len(message_lines) - 2) + ["conclusion"]
        section_names = (
            ["hook"] + ["top_items"] * len(top_items) + inferred + ["metaphor", "conclusion"]
        )

    emphasis = saved.get("emphasis") or []
    if isinstance(emphasis, str):
        emphasis = re.split(r"[,\n]", emphasis)
    emphasis = [w.strip() for w in emphasis if isinstance(w, str) and w.strip()]

    return ParsedScript(
        title=saved.get("title", ""),
        duration_seconds=float(duration),
        word_count=saved.get("word_count", 0),
        pacing_wps=saved.get("pacing_wps", 0),
        hook=_section_text("hook"),
        hook_seconds=_section_seconds("hook"),
        message_lines=message_lines,
        message_seconds=message_seconds,
        metaphor=_section_text("metaphor"),
        metaphor_seconds=_section_seconds("metaphor"),
        conclusion=_section_text("conclusion"),
        conclusion_seconds=_section_seconds("conclusion"),
        emotional_arc=saved.get("emotional_arc", []),
        parallel_structure=saved.get("parallel_structure", ""),
        hook_score=saved.get("hook_score", ""),
        top_items=top_items,
        top_items_seconds=top_items_seconds,
        fact_count=fact_count,
        claim=claim,
        twist=twist,
        emphasis=emphasis,
        section_names=section_names,
    )


def parse_script(text: str) -> ParsedScript:
    title_match = re.search(r"TITLE:\s*(.+)", text)
    title = title_match.group(1).strip() if title_match else "Untitled"
    wc_match = re.search(r"WORD COUNT:\s*(\d+)", text)
    word_count = int(wc_match.group(1)) if wc_match else 0
    pacing_match = re.search(r"PACING:\s*([\d.]+)", text)
    pacing_wps = float(pacing_match.group(1)) if pacing_match else 0.0

    duration_match = re.search(r"DURATION:\s*([\d.]+)", text)

    hook_seconds, hook = _section(text, "HOOK")
    metaphor_seconds, metaphor = _section(text, "METAPHOR")
    conclusion_seconds, conclusion = _section(text, "CONCLUSION")

    message_match = re.search(
        r'\[MESSAGE\s*[-—]\s*([\d.]+)s\]\s*\n((?:"[^"]+"\s*\n?)+)',
        text,
    )
    if not message_match:
        # Fallback: handle "Ns" placeholder
        message_match = re.search(
            r'\[MESSAGE\s*[-—]\s*N?s?\]\s*\n((?:"[^"]+"\s*\n?)+)',
            text,
        )
        message_seconds = None
    else:
        message_seconds = float(message_match.group(1))
    message_lines = re.findall(r'"([^"]+)"', message_match.group(0) if message_match else "")

    claim_seconds, claim = _section_optional(text, "CLAIM")
    twist_seconds, twist = _section_optional(text, "TWIST")
    fact_sections = _fact_sections(text)
    fact_count = len(re.findall(r"\[FACT", text))
    if claim or twist or fact_sections:
        myth_lines = [claim] if claim else []
        myth_lines += [line for _, line in fact_sections]
        if twist:
            myth_lines.append(twist)
        message_lines = myth_lines

    top_items_match = re.search(
        r'\[TOP_ITEMS\s*(?:[-–—]\s*)?([\d.]+)?[Nn]?s?\]\s*\n((?:"[^"]+"\s*\n?)+)',
        text,
    )
    if top_items_match:
        top_items_seconds = float(top_items_match.group(1)) if top_items_match.group(1) else None
        top_items = [l for l in re.findall(r'"([^"]+)"', top_items_match.group(2)) if l]
    else:
        top_items_seconds = None
        top_items = []

    target_total = float(duration_match.group(1)) if duration_match else word_count / pacing_wps
    section_timings = {
        "hook": hook_seconds,
        "message": message_seconds,
        "metaphor": metaphor_seconds,
        "conclusion": conclusion_seconds,
        "top_items": top_items_seconds,
    }
    if claim or twist or fact_sections:
        if claim:
            section_timings["claim"] = claim_seconds
        for idx, (fact_seconds, _line) in enumerate(fact_sections):
            section_timings[f"fact_{idx}"] = fact_seconds
        if twist:
            section_timings["twist"] = twist_seconds
    sections = _backfill_missing_seconds(section_timings, target_total)
    hook_seconds = sections["hook"]
    message_seconds = sections["message"]
    metaphor_seconds = sections["metaphor"]
    conclusion_seconds = sections["conclusion"]
    top_items_seconds = sections["top_items"]

    duration_seconds = (
        float(duration_match.group(1))
        if duration_match
        else hook_seconds
        + message_seconds
        + metaphor_seconds
        + conclusion_seconds
        + top_items_seconds
    )

    arc_match = re.search(r"EMOTIONAL ARC MAP:\s*\n(.+)", text)
    emotional_arc = (
        [stage.strip() for stage in re.split(r"->|→", arc_match.group(1))] if arc_match else []
    )

    parallel_match = re.search(r"PARALLEL STRUCTURE USED:\s*(.+)", text)
    hook_score_match = re.search(r"HOOK SCORE:\s*(.+)", text)

    return ParsedScript(
        title=title,
        duration_seconds=duration_seconds,
        word_count=word_count,
        pacing_wps=pacing_wps,
        hook=hook,
        hook_seconds=hook_seconds,
        message_lines=message_lines,
        message_seconds=message_seconds,
        metaphor=metaphor,
        metaphor_seconds=metaphor_seconds,
        conclusion=conclusion,
        conclusion_seconds=conclusion_seconds,
        emotional_arc=emotional_arc,
        parallel_structure=parallel_match.group(1).strip() if parallel_match else "",
        hook_score=hook_score_match.group(1).strip() if hook_score_match else "",
        top_items=top_items,
        top_items_seconds=top_items_seconds,
        fact_count=fact_count,
        claim=claim,
        twist=twist,
    )


def parse_ideas(text: str) -> list[Idea]:
    blocks = re.split(r"\n\*{0,2}IDEA #\d+:\s*\*{0,2}\s*", "\n" + text)[1:]
    ideas = []
    for block in blocks:
        title_line, _, rest = block.partition("\n")
        title = re.sub(r"\*+", "", title_line).strip()
        fields = {
            k: re.sub(r"\*+", "", v).strip() for k, v in re.findall(r"[•*]\s*([^:]+):\s*(.+)", rest)
        }
        score_text = fields.get("Quotability Score", "0")
        score_match = re.search(r"[\d.]+", score_text)
        ideas.append(
            Idea(
                title=title,
                core_message=fields.get("Core Message", "").strip(),
                hook_line=fields.get("Hook Line", "").strip(),
                identity_signal=fields.get("Identity Signal", "").strip(),
                permission_given=fields.get("Permission Given", "").strip(),
                emotional_arc=fields.get("Emotional Arc", "").strip(),
                target_audience=fields.get("Target Audience", "").strip(),
                quotability_score=float(score_match.group()) if score_match else 0.0,
                share_trigger=fields.get("Share Trigger", "").strip(),
            )
        )
    return ideas
