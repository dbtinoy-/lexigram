"""Claim extraction and env-var verification."""

from __future__ import annotations

from dev.audit.generators.docs_claims._constants import (
    _DYNAMIC_PREFIXES,
    _ENV_TOKEN_RE,
    _ERROR_CODE_PREFIX,
    _PREFIX_TOKEN_SUFFIX,
    _PRIORITY_RE,
)
from dev.audit.generators.docs_claims.introspect import _iter_python_blocks


def _collect_env_claims(md_text: str) -> tuple[str, ...]:
    """Return every distinct non-error-code ``LEX_*`` token in a doc."""
    seen: set[str] = set()
    for block in _iter_python_blocks(md_text):
        seen.update(_ENV_TOKEN_RE.findall(block))
    for match in _ENV_TOKEN_RE.finditer(md_text):
        seen.add(match.group(0))
    return tuple(sorted(t for t in seen if not t.startswith(_ERROR_CODE_PREFIX)))


def _collect_priority_claims(md_text: str) -> tuple[str, ...]:
    seen: set[str] = set()
    for match in _PRIORITY_RE.finditer(md_text):
        seen.add(match.group(1))
    return tuple(sorted(seen))


def _parts_match(valid_key: str, token: str) -> bool:
    """Part-wise match where ``*`` segments in the validity key match any token part."""
    token_parts = token.split("__")
    valid_parts = valid_key.split("__")
    if len(token_parts) != len(valid_parts):
        return False
    for valid_part, token_part in zip(valid_parts, token_parts, strict=True):
        if valid_part not in ("*", token_part):
            return False
    return True


def _prefix_parts_match(valid_key: str, token_prefix: str) -> bool:
    """True when a token prefix matches a validity key part-wise (wildcard-aware)."""
    token_parts = token_prefix.split("__")
    key_parts = valid_key.split("__")
    if len(key_parts) < len(token_parts):
        return False
    for token_part, key_part in zip(token_parts, key_parts):
        if key_part != "*" and key_part != token_part:
            return False
    return True


def _verify_env_var(
    token: str,
    validity: dict[str, str],
    direct_reads: set[str],
    declared_prefixes: set[str] | frozenset[str] = frozenset(),
) -> tuple[bool, str]:
    """Return (ok, explanation) for an env var claim."""
    normalized = token.upper()
    if normalized in direct_reads:
        return True, ""
    for prefix in _DYNAMIC_PREFIXES:
        if normalized.startswith(prefix):
            return True, f"dynamic {prefix}namespace"
    for prefix in declared_prefixes:
        if normalized.startswith(prefix):
            return True, f"declared env prefix `{prefix}`"
    if normalized.endswith(_PREFIX_TOKEN_SUFFIX):
        prefix = normalized[: -len(_PREFIX_TOKEN_SUFFIX)]
        matches = [var for var in validity if var.startswith(f"{prefix}__")]
        wildcard_matches = [
            var
            for var in validity
            if "*" in var and _prefix_parts_match(var, prefix)
        ]
        if matches or wildcard_matches:
            count = len(matches) + len(wildcard_matches)
            return True, f"prefix `{prefix}__` maps {count} variables"
        return False, f"no variable starts with prefix `{prefix}__`"
    if "__" not in normalized:
        return False, (
            "not a section/key mapping (`LEX_<SECTION>__<KEY>`), nor read directly"
        )
    section = normalized[4:].split("__", 1)[0]
    if not section:
        return False, "missing section"
    desc = validity.get(normalized)
    if desc is None:
        for valid_key, valid_desc in validity.items():
            if "*" in valid_key and _parts_match(valid_key, normalized):
                desc = f"{valid_desc} (wildcard)"
                break
    if desc is None:
        return False, "no config section/key path matches this variable"
    return True, desc
