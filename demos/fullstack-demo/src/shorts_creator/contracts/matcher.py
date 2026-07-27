from __future__ import annotations

from dataclasses import dataclass

from shorts_creator.contracts.capabilities import parse_capabilities
from shorts_creator.contracts.issues import ContractIssue, Severity
from shorts_creator.contracts.pipeline import PIPELINE_CAPABILITIES


@dataclass(frozen=True)
class TopicSide:
    """What a topic contractually provides (built from a SkillTopic)."""

    script: frozenset[str]
    voice: frozenset[str]
    objectives: frozenset[str]


@dataclass(frozen=True)
class FormatSide:
    """What a format contractually requires (built from a FormatDefinition)."""

    name: str
    requires_script: frozenset[str]
    requires_voice: frozenset[str]
    requires_pipeline: frozenset[str]
    requires_assets: frozenset[str]
    objectives: frozenset[str]


def validate_pair(topic: TopicSide, fmt: FormatSide) -> list[ContractIssue]:
    """Return every contract violation between a topic and a format.

    ERROR severities block creation/load/render; WARN severities only flag.
    Pure function — no registry or app dependencies.
    """
    issues: list[ContractIssue] = []

    missing_script = fmt.requires_script - topic.script
    if missing_script:
        issues.append(
            ContractIssue(
                Severity.ERROR,
                "REQ_SCRIPT",
                f"format '{fmt.name}' requires script capability(-ies) the topic does not provide: "
                f"{sorted(missing_script)}",
            )
        )

    missing_voice = fmt.requires_voice - topic.voice
    if missing_voice:
        issues.append(
            ContractIssue(
                Severity.ERROR,
                "REQ_VOICE",
                f"format '{fmt.name}' requires voice capability(-ies) the topic does not provide: "
                f"{sorted(missing_voice)}",
            )
        )

    missing_pipeline = fmt.requires_pipeline - frozenset(PIPELINE_CAPABILITIES)
    if missing_pipeline:
        issues.append(
            ContractIssue(
                Severity.ERROR,
                "REQ_PIPELINE",
                f"format '{fmt.name}' requires pipeline stage(s) the pipeline does not implement: "
                f"{sorted(missing_pipeline)}",
            )
        )

    obj_missing = fmt.objectives - topic.objectives
    if obj_missing:
        issues.append(
            ContractIssue(
                Severity.WARN,
                "OBJ_NOT_SUPPORTED",
                f"format '{fmt.name}' objective(s) not producible by this topic: {sorted(obj_missing)}",
            )
        )

    return issues


def is_valid_pair(topic: TopicSide, fmt: FormatSide) -> bool:
    """True when no ERROR-severity issue exists (WARNs do not block)."""
    return not any(i.severity is Severity.ERROR for i in validate_pair(topic, fmt))


def incompatible_reasons(topic: TopicSide, fmt: FormatSide) -> list[str]:
    """Human-readable messages for every blocking (ERROR) reason."""
    return [
        issue.message for issue in validate_pair(topic, fmt) if issue.severity is Severity.ERROR
    ]


def topic_side_from_provides(provides: dict) -> TopicSide:
    """Build a TopicSide from raw parsed SKILL.md frontmatter values.

    Capabilities (script/voice) are validated against the closed vocabulary;
    objectives are an open set (normalized only).
    """
    provides = provides or {}
    script = frozenset(parse_capabilities(provides.get("script"), "script"))
    voice = frozenset(parse_capabilities(provides.get("voice"), "voice"))
    objectives = frozenset(str(item).strip() for item in provides.get("objectives") or [])
    return TopicSide(script=script, voice=voice, objectives=objectives)


def format_side_from_frontmatter(name: str, requires: dict, objectives: list) -> FormatSide:
    """Build a FormatSide from raw parsed FORMAT.md frontmatter values."""
    requires = requires or {}
    return FormatSide(
        name=name,
        requires_script=frozenset(parse_capabilities(requires.get("script"), "script")),
        requires_voice=frozenset(parse_capabilities(requires.get("voice"), "voice")),
        requires_pipeline=frozenset(parse_capabilities(requires.get("pipeline"), "pipeline")),
        requires_assets=frozenset(parse_capabilities(requires.get("assets"), "assets")),
        objectives=frozenset(str(item).strip() for item in objectives or []),
    )
