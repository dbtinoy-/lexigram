from __future__ import annotations

import importlib.util
import re
import types
from pathlib import Path

import yaml

from shorts_creator.contracts.matcher import TopicSide, topic_side_from_provides
from shorts_creator.formats import registry as _formats
from shorts_creator.topics.base import Idea, ParsedScript

SKILL_MD_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)", re.DOTALL)
PROMPT_HEADER = re.compile(
    r"^##\s*(IDEA_PROMPT|SCRIPT_PROMPT|SCRIPT_PROMPT_TOPN|SCRIPT_PROMPT_MYTH)\s*$", re.MULTILINE
)


def _append_voice(prompt: str, voice: dict | None) -> str:
    if not voice:
        return prompt
    base = prompt + "\n\nVOICE PROFILE:"
    persona = voice.get("audience_persona")
    if persona:
        base += f"\n- Audience persona: {persona}"
    tone_rules = voice.get("tone_rules") or []
    if tone_rules:
        base += "\n- Tone rules: " + "; ".join(tone_rules)
    banned = voice.get("banned_topics") or []
    if banned:
        base += "\n- Never mention: " + ", ".join(banned)
    return base + "\nFollow this voice profile throughout."


def _import_script_module(skill_dir: Path) -> types.ModuleType:
    script_path = skill_dir / "scripts" / "main.py"
    if not script_path.exists():
        raise FileNotFoundError(f"scripts/main.py not found in {skill_dir}")
    spec = importlib.util.spec_from_file_location(
        f"_{skill_dir.name}_script",
        script_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load scripts/main.py from {skill_dir}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _parse_skill_md(md_path: Path) -> dict:
    content = md_path.read_text(encoding="utf-8")
    match = SKILL_MD_PATTERN.match(content)
    if not match:
        raise ValueError(f"Missing YAML frontmatter in {md_path}")
    frontmatter = yaml.safe_load(match.group(1)) or {}
    body = match.group(2).strip()
    prompts: dict[str, str] = {}
    current_key = None
    current_lines: list[str] = []
    for line in body.split("\n"):
        h = PROMPT_HEADER.match(line)
        if h:
            if current_key:
                prompts[current_key] = "\n".join(current_lines).strip()
            current_key = h.group(1)
            current_lines = []
        elif current_key:
            current_lines.append(line)
    if current_key:
        prompts[current_key] = "\n".join(current_lines).strip()
    return {
        "name": frontmatter["name"],
        "label": frontmatter["label"],
        "description": frontmatter.get("description", ""),
        "structure_sections": frontmatter.get("structure_sections", []),
        "topic_categories": frontmatter.get("topic_categories", []),
        "banned_phrases": frontmatter.get("banned_phrases", []),
        "background_queries": frontmatter.get("background_queries", []),
        "idea_prompt": prompts.get("IDEA_PROMPT", ""),
        "script_prompt": prompts.get("SCRIPT_PROMPT", ""),
        "script_prompt_topn": prompts.get("SCRIPT_PROMPT_TOPN", ""),
        "script_prompt_myth": prompts.get("SCRIPT_PROMPT_MYTH", ""),
        "provides": frontmatter.get("provides", {}),
        "objectives": frontmatter.get("objectives", []),
        "default_format": frontmatter.get("default_format"),
    }


class SkillTopic:
    """Topic loaded from a Lexigram SKILL.md skill directory."""

    def __init__(self, skill_dir: str | Path):
        self._skill_dir = Path(skill_dir)
        self._md = _parse_skill_md(self._skill_dir / "SKILL.md")
        self._side = self._build_side()
        self._mod = _import_script_module(self._skill_dir)

    def _build_side(self) -> TopicSide:
        """Contractual view of what this topic provides: capabilities come
        from ``provides`` (closed vocabulary), objectives from the top-level
        ``objectives`` key (open set, normalized only)."""
        base = topic_side_from_provides(self._md["provides"])
        objectives = frozenset(str(item).strip() for item in self._md["objectives"])
        return TopicSide(script=base.script, voice=base.voice, objectives=objectives)

    @property
    def name(self) -> str:
        return self._md["name"]

    @property
    def label(self) -> str:
        return self._md["label"]

    @property
    def description(self) -> str:
        return self._md["description"]

    @property
    def structure_sections(self) -> list[str]:
        return self._md["structure_sections"]

    @property
    def topic_categories(self) -> list[str]:
        return self._md["topic_categories"]

    @property
    def idea_prompt(self) -> str:
        return self._md["idea_prompt"]

    @property
    def script_prompt(self) -> str:
        return self._md["script_prompt"]

    def build_idea_prompt(
        self,
        count: int,
        focus: str,
        seo_context: str = "",
        voice: dict | None = None,
    ) -> str:
        banned = ", ".join(self._md["banned_phrases"])
        categories = "\n".join(f"{c}," for c in self.topic_categories)
        base = self._md["idea_prompt"].format(
            count=count,
            focus=focus,
            category_list=categories,
            banned_list=banned,
        )
        if seo_context:
            base += f"\n\nEXTERNAL TREND DATA TO CONSIDER:\n{seo_context}\n\n"
            base += "Incorporate these real search trends when choosing angles — they indicate proven demand."
        return _append_voice(base, voice)

    def parse_ideas(self, text: str) -> list[Idea]:
        return self._mod.parse_ideas(text)

    def build_script_prompt(
        self,
        idea: Idea,
        angle_context: str = "",
        format_name: str = "",
        pacing_wps: float | None = None,
        voice: dict | None = None,
    ) -> str:
        fmt = _formats.get(format_name or "narrated")
        min_dur, max_dur = fmt.duration_range if fmt is not None else (30, 60)
        sweet = (min_dur + max_dur) // 2
        min_wps, max_wps = fmt.pacing_wps_range if fmt is not None else (2.0, 3.0)
        min_words = int(min_dur * min_wps)
        max_words = int(max_dur * max_wps)
        if pacing_wps is not None:
            lo, hi = fmt.pacing_wps_range if fmt is not None else (2.0, 3.0)
            pacing_wps = max(lo, min(hi, pacing_wps))
            min_words = max_words = int(sweet * pacing_wps)
        wants_top_items = "top_items" in (
            (fmt.requires if fmt is not None else {}).get("script") or []
        )
        wants_myth = "claim" in ((fmt.requires if fmt is not None else {}).get("script") or [])
        body = self._md["script_prompt"]
        if wants_myth:
            body = self._md["script_prompt_myth"] or self._md["script_prompt"]
        elif wants_top_items:
            body = self._md["script_prompt_topn"] or self._md["script_prompt"]
        base = body.format(
            title=idea.title,
            core_message=idea.core_message,
            target_emotion=idea.emotional_arc,
            target_audience=idea.target_audience,
            min_dur=min_dur,
            max_dur=max_dur,
            sweet_spot=sweet,
            min_wps=min_wps,
            max_wps=max_wps,
            min_words=min_words,
            max_words=max_words,
        )
        if angle_context:
            base += f"\n\nCONTENT ANGLE RESEARCH TO INCORPORATE:\n{angle_context}\n\n"
            base += "Use these insights to strengthen the script's hook, structure, and emotional resonance."
        if pacing_wps is not None:
            base += (
                f"\n\nTARGET PACING: {pacing_wps:.1f} words per second — "
                "keep the script's spoken pace at this speed."
            )
        return _append_voice(base, voice)

    def parse_script(self, text: str) -> ParsedScript:
        return self._mod.parse_script(text)

    def mock_ideas(self, count: int = 10) -> str:
        return self._mod.mock_ideas(count=count)

    def mock_script(self) -> str:
        return self._mod.mock_script()

    @property
    def banned_phrases(self) -> list[str]:
        return self._md["banned_phrases"]

    @property
    def background_queries(self) -> list[str]:
        return list(self._md["background_queries"])

    @property
    def provides_script(self) -> list[str]:
        return list((self._md["provides"] or {}).get("script", []))

    @property
    def provides_voice(self) -> list[str]:
        return list((self._md["provides"] or {}).get("voice", []))

    @property
    def objectives(self) -> list[str]:
        return list(self._md["objectives"])

    @property
    def default_format(self) -> str | None:
        return self._md["default_format"]

    def to_contract_side(self) -> TopicSide:
        """Contractual view of what this topic provides (validated at load)."""
        return self._side

    def mock_seo(self) -> str:
        return self._mod.mock_seo()
