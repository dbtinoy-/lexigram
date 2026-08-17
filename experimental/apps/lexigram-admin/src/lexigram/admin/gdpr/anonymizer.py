"""Anonymization helpers — strategy application and record anonymization."""

from __future__ import annotations

import hashlib
from typing import Any

from lexigram.admin.gdpr.models import AnonymizationRule, AnonymizationStrategy


def _apply_strategy(value: Any, strategy: str | AnonymizationStrategy) -> Any:
    """Apply a single anonymization strategy to a value.

    Args:
        value: Original field value.
        strategy: Strategy to apply.

    Returns:
        Anonymized value.
    """
    s = AnonymizationStrategy(strategy) if isinstance(strategy, str) else strategy
    match s:
        case AnonymizationStrategy.HASH:
            return hashlib.sha256(str(value).encode()).hexdigest()
        case AnonymizationStrategy.CLEAR:
            return ""
        case AnonymizationStrategy.REDACT:
            return "[REDACTED]"
        case AnonymizationStrategy.ZERO:
            return 0
        case AnonymizationStrategy.NULLIFY:
            return None
        case AnonymizationStrategy.FAKE_EMAIL:
            return "anonymized@example.com"
        case _:
            return value


def anonymize_record(
    record: dict[str, Any],
    rule: AnonymizationRule,
) -> dict[str, Any]:
    """Return a copy of *record* with PII fields anonymized per *rule*.

    Fields not listed in the rule are passed through unchanged.

    Args:
        record: Original record dict.
        rule: Anonymization rule defining per-field strategies.

    Returns:
        New dict with anonymized values.
    """
    result = dict(record)
    for fname, strategy in rule.fields.items():
        if fname in result:
            if rule.preserve_id and fname == "id":
                continue
            result[fname] = _apply_strategy(result[fname], strategy)
    return result


__all__ = [
    "anonymize_record",
]
