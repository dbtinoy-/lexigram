#!/usr/bin/env python3
"""Empirically verify that every documented ``LEX_*`` variable actually binds.

Reads ``.env.example`` and runs each ``LEX_*`` entry through
``dev._lib.env_binding.check_var``, which loads the owning config family
through its real ``from_yaml()`` path and checks whether the variable
reaches a declared field.  Exits non-zero when any documented variable is
provably dead, so CI can gate documentation accuracy against runtime truth.

Variables outside the known root-config families report as ``unknown``
rather than failing; ``--strict`` turns those into failures too.

Usage:
    python dev/checks/env_binding.py [--example PATH] [--strict]
"""

from __future__ import annotations

import argparse
import importlib
import os
from pathlib import Path
import re
import sys
import tempfile
import typing
from typing import cast

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dev._lib.bootstrap import REPO_ROOT as ROOT  # noqa: E402 — needs bootstrap first

EXAMPLE = ROOT / ".env.example"

_ENV_NAME = r"[A-Z][A-Z0-9_]{1,}"


def documented_vars(path: Path) -> list[str]:
    """Return every variable name declared in a dotenv example file."""
    names: list[str] = []
    seen: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(" + _ENV_NAME + r")=", line)
        if match and match.group(1) not in seen:
            seen.add(match.group(1))
            names.append(match.group(1))
    return names


def run_check(
    names: list[str],
    *,
    strict: bool = False,
    probe=None,
) -> int:
    """Probe each name and print a verdict summary; return an exit code.

    ``probe`` defaults to ``dev._lib.env_binding.check_var`` and is
    injectable so tests can supply canned verdicts.
    """
    if probe is None:
        probe = check_var  # defined below: the inlined empirical engine

    live: list[str] = []
    dead: list[str] = []
    unknown: list[str] = []
    skipped = 0
    for name in names:
        if not name.startswith("LEX_"):
            skipped += 1
            continue
        verdict = probe(name)
        if verdict is True:
            live.append(name)
        elif verdict is False:
            dead.append(name)
            print(f"DEAD: {name}")
        else:
            unknown.append(name)

    summary = (
        f"env binding OK: {len(live)} live, {len(unknown)} unknown"
        f", {skipped} non-LEX skipped"
        if not dead
        else (
            f"env binding FAILED: {len(dead)} dead of "
            f"{len(live) + len(dead) + len(unknown)} probed"
        )
    )
    print(summary)
    if unknown:
        shown = ", ".join(unknown[:20])
        more = "" if len(unknown) <= 20 else f" … (+{len(unknown) - 20} more)"
        print(f"  unknown (no family/probe error): {shown}{more}")
    if dead:
        return 1
    if strict and unknown:
        return 1
    return 0


def main() -> int:
    """Run the check and return a process exit code."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--example", default=EXAMPLE, type=Path, help=".env.example to validate"
    )
    ap.add_argument(
        "--strict",
        action="store_true",
        help="also fail on variables outside known config families",
    )
    args = ap.parse_args()

    if not args.example.is_file():
        print(f"ERROR: {args.example} does not exist")
        return 1
    names = documented_vars(args.example)
    if not names:
        print(f"ERROR: no variables found in {args.example}")
        return 1
    print(f"probing {len(names)} documented variable(s) from {args.example} …")
    return run_check(names, strict=args.strict)


# -- empirical binding engine (verbatim from dev/_lib/env_binding.py) --

REPO_ROOT = Path(__file__).resolve().parents[2]

MARKER = "LEXBINDCHECK"

# Root config class per documented prefix family, resolved lazily at probe time.
# The key is the exact prefix between "LEX_" and the first "__" — i.e. the
# YAML/config_section namespace the variables are written against.
FAMILY_ROOTS: dict[str, tuple[str, str | None]] = {
    # prefix segment -> (module, root Config class)
    "LEXIGRAM": ("lexigram.config.main", "LexigramConfig"),
    "SECURITY": ("lexigram.security.config", "SecurityConfig"),
    "WEB": ("lexigram.web.config", "WebConfig"),
    "AUTH": ("lexigram.auth.config", "AuthConfig"),
    "SEARCH": ("lexigram.search.config", "SearchConfig"),
    "CACHE": ("lexigram.cache.config", "CacheConfig"),
    "EVENTS": ("lexigram.events.config", "EventsConfig"),
    "MONITOR": ("lexigram.monitor.config", "MonitorConfig"),
    "SQL": ("lexigram.sql.config", "DatabaseConfig"),
    "STORAGE": ("lexigram.storage.config", "StorageConfig"),
    "TASKS": ("lexigram.tasks.config", None),
    "GRAPHQL": ("lexigram.graphql.config", None),
    "MULTIMEDIA": ("lexigram.multimedia.config", "MultimediaConfig"),
    "VECTOR": ("lexigram.vector.config", None),
    "AI": ("lexigram.ai.config", "AIConfig"),
    "ADMIN": ("lexigram.admin.config", "AdminConfig"),
    "UI": ("lexigram.ui.config", "UIConfig"),
    "NOSQL": ("lexigram.nosql.config", None),
    "GRAPH": ("lexigram.graph.config", None),
    "TENANCY": ("lexigram.tenancy.config", "TenancyConfig"),
    "NOTIFICATION": ("lexigram.notification.config", "NotificationConfig"),
    "AUDIT": ("lexigram.audit.config", "AuditConfig"),
    "FEATURES": ("lexigram.features.config", "FeatureFlagsConfig"),
    "RESILIENCE": ("lexigram.resilience.config", "ResilienceConfig"),
    "HTTP": ("lexigram.http.config", None),
    "QUEUE": ("lexigram.queue.config", None),
    "SECRETS": ("lexigram.secrets.config", None),
    "WORKFLOW": ("lexigram.workflow.config", None),
    # AI extension families (section names use underscores, prefixes don't)
    "AI_AGENTS": ("lexigram.ai.agents.config", "AgentConfig"),
    "AI_EVALUATION": ("lexigram.ai.evaluation.config", "EvaluationConfig"),
    "AI_FEEDBACK": ("lexigram.ai.feedback.config", "FeedbackConfig"),
    "AI_GOVERNANCE": ("lexigram.ai.governance.config", "GovernanceConfig"),
    "AI_GUARD": ("lexigram.ai.guard.config", "GuardConfig"),
    "AI_LLM": ("lexigram.ai.llm.config", "ClientConfig"),
    "AI_MCP": ("lexigram.ai.mcp.config", "MCPConfig"),
    "AI_MEMORY": ("lexigram.ai.memory.config", "MemoryConfig"),
    "AI_OBSERVABILITY": ("lexigram.ai.observability.config", "ObservabilityConfig"),
    "AI_PROMPT": ("lexigram.ai.prompt.config", "PromptConfig"),
    "AI_RAG": ("lexigram.ai.rag.config", "RAGConfig"),
    "AI_SESSION": ("lexigram.ai.session.config", "SessionConfig"),
    "AI_SKILLS": ("lexigram.ai.skills.config", "SkillsConfig"),
    "AI_WORKERS": ("lexigram.ai.workers.config", "WorkersConfig"),
    "WEBHOOK": ("lexigram.webhook.config", "WebhookConfig"),
}

# Minimal YAML bodies that satisfy required fields so from_yaml() succeeds.
FAMILY_BASE_YAML: dict[str, str] = {
    "AUTH": (
        "auth:\n"
        "  secret_key: base-secret-key-base-secret-key-32\n"
        "  token:\n"
        "    secret_key: jwt-secret-key-jwt-secret-key-32\n"
    ),
}


def _resolve_class(module_path: str, class_name: str | None) -> type:
    """Import the module and return the root config class."""
    mod = importlib.import_module(module_path)
    if class_name is not None:
        return getattr(mod, class_name)
    # Fall back to the single BaseConfig subclass carrying a config_section
    candidates = [
        obj
        for name in dir(mod)
        if (obj := getattr(mod, name)) is not None
        and isinstance(obj, type)
        and name.endswith("Config")
        and not name.startswith("Base")
        and getattr(obj, "config_section", None)
        and obj.__module__ == module_path
    ]
    if not candidates:
        raise ImportError(f"no root Config with config_section in {module_path}")
    return candidates[0]


def _dump_fields(obj: object) -> object:
    """Recursively dump declared fields of a DomainModel/dataclass instance.

    Uses ``__annotations__`` because DomainModel subclasses register their
    dataclass fields lazily on first instantiation; ``dataclasses.fields()``
    under-reports for such classes.  Each dumped level carries ``__type__``
    naming the live source class so raw dicts stay distinguishable from
    typed child models.
    """
    if isinstance(obj, (str, int, float, bool, bytes)) or obj is None:
        return obj
    # SecretStr reprs as "**********" — unwrap so markers stay visible.
    if hasattr(obj, "get_secret_value") and callable(obj.get_secret_value):
        return obj.get_secret_value()
    if isinstance(obj, (list, tuple)):
        return [_dump_fields(v) for v in obj]
    if isinstance(obj, dict):
        return {"__type__": "dict", **{k: _dump_fields(v) for k, v in obj.items()}}
    cls = type(obj)
    try:
        hints = typing.get_type_hints(cls)
    except Exception:
        hints = getattr(cls, "__annotations__", {})
    out: dict[str, object] = {"__type__": cls.__name__}
    for name in hints:
        if name.startswith("_") or name.isupper():
            continue
        if "ClassVar" in str(hints.get(name, "")):
            continue
        if hasattr(obj, name):
            out[name] = _dump_fields(getattr(obj, name))
    return out


def _probe(cls: type, var: str, yaml_body: str) -> bool | None:
    """Set ``var`` to the marker, load via from_yaml, report binding.

    Returns True (bound), False (loaded but not bound), or None when the load
    failed even before binding could be judged (caller should re-probe with a
    valid-typed value or skip).  A marker sitting inside a raw dict that
    replaced a typed child model does NOT count — that is the coercion
    engine's unknown-key fallback, not a declared field.
    """

    def _load_once(env_value: str | None) -> tuple[str | None, dict[str, str] | None]:
        """One from_yaml pass; ``env_value=None`` means variable unset."""
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(yaml_body)
            path = f.name
        old = os.environ.pop(var, None)
        if env_value is not None:
            os.environ[var] = env_value
        try:
            cfg = cls.from_yaml(path)  # type: ignore[attr-defined]
            dumped = cast("dict", _dump_fields(cfg))
            return repr(dumped), _kind_tree(dumped)
        except Exception:
            return None, None
        finally:
            os.environ.pop(var, None)
            if old is not None and env_value is None:
                os.environ[var] = old
            Path(path).unlink(missing_ok=True)

    baseline_repr, baseline_kinds = _load_once(None)
    sentinel = f"{MARKER}{var}"
    marked_repr, marked_kinds = _load_once(sentinel)

    if marked_repr is None:
        # The load crashed WITH the variable set.  Distinguish "config is
        # broken regardless" (baseline also crashes -> unknown) from "this
        # value broke a declared field's coercion" — the latter means the
        # variable was read; report it live.
        if baseline_repr is None:
            return None
        return True
    if MARKER not in marked_repr:
        return False

    # Marker present.  Reject when the leaf's parent flipped model -> raw dict
    # (unknown key swallowed into the coercion fallback).
    segs = [s.lower() for s in var[4:].split("__")[1:]]
    parent = ".".join(segs[:-1])
    return not _model_to_dict_swap(baseline_kinds, marked_kinds, parent)


def check_var(var: str) -> bool | None:
    """Empirically test one ``LEX_*`` variable against its family root config.

    Returns True/False for a verdict, or None when the variable belongs to no
    known family (or every probe errored).
    """
    if not var.startswith("LEX_"):
        return None
    segment = var[4:].split("__", 1)[0]
    entry = FAMILY_ROOTS.get(segment)
    if entry is None:
        return None
    module_path, class_name = entry
    try:
        cls = _resolve_class(module_path, class_name)
    except ImportError:
        return None
    yaml_body = FAMILY_BASE_YAML.get(segment, "{}\n")
    result = _probe(cls, var, yaml_body)
    if result is True:
        return True
    # Marker absent or load failed.  A clean load without landing is NOT proof
    # of death: validators normalize unknown values (e.g. log levels reset to
    # INFO).  Retry with type-valid candidates; keep the earlier verdict only
    # if none of them land either.
    return _probe_typed(cls, var, yaml_body, fallback=result)


def _kind_tree(dumped: dict) -> dict[str, str]:
    """Flatten a ``_dump_fields`` dump into ``{path: value_type}`` entries.

    Paths are lowercase dot-joined field paths; the mapped type is the
    field VALUE's own type name ("dict" for raw dicts, model class name
    for typed children, primitives otherwise).  ``__type__`` keys skipped.
    """
    kinds: dict[str, str] = {}

    def walk(node: dict, prefix: str) -> None:
        for k, v in node.items():
            if k == "__type__":
                continue
            path = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                kinds[path] = str(v.get("__type__", "dict"))
                walk(v, path)
            elif isinstance(v, list):
                kinds[path] = "list"
            else:
                kinds[path] = type(v).__name__

    walk(dumped, "")
    return kinds


_PRIMITIVE_TYPES = {"dict", "list", "str", "int", "float", "bool", "NoneType"}


def _model_to_dict_swap(
    base_kinds: dict[str, str] | None,
    cand_kinds: dict[str, str] | None,
    parent: str,
) -> bool:
    """True when the leaf's parent flipped from a typed model to a raw dict.

    That pattern means the candidate value was swallowed by the coercion
    engine's unknown-key fallback (the whole child became a plain dict) —
    it never reached a declared field.
    """
    if not parent or base_kinds is None or cand_kinds is None:
        return False
    c_type = cand_kinds.get(parent)
    b_type = base_kinds.get(parent)
    return c_type == "dict" and b_type is not None and b_type not in _PRIMITIVE_TYPES


def _probe_typed(
    cls: type, var: str, yaml_body: str, fallback: bool | None
) -> bool | None:
    """Second-chance probe: bind type-valid values and diff the whole config.

    Substring searches are unsound (candidate strings can collide with field
    names/defaults), so compare a full dump with the variable set against one
    without it.  Any difference means the variable reached a field — unless it
    merely swapped a typed child model for a raw dict (the coercion engine's
    silent bail-out on unknown keys), which reaches no declared field.
    """
    segment = var[4:].split("__", 1)[0] if var.startswith("LEX_") else ""
    body = FAMILY_BASE_YAML.get(segment, yaml_body)

    def _load() -> tuple[str | None, dict[str, str] | None]:
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(body)
            path = f.name
        try:
            cfg = cls.from_yaml(path)  # type: ignore[attr-defined]
            dumped = cast("dict", _dump_fields(cfg))
            return repr(dumped), _kind_tree(dumped)
        except Exception:
            return None, None
        finally:
            Path(path).unlink(missing_ok=True)

    old = os.environ.pop(var, None)
    try:
        baseline, base_kinds = _load()
        saw_load = baseline is not None
        # Path below the family segment, e.g. INTEGRATION__ENABLED ->
        # ["integration", "enabled"]; parent path drops the leaf.
        segs = [s.lower() for s in var[4:].split("__")[1:]]
        parent = ".".join(segs[:-1])
        # "false" matters: bool fields defaulting True coerce every truthy
        # string back to True (no diff) but flip on "false".  The int/float
        # spread clears common Field(ge=..., le=...) windows (e.g. timeouts
        # ge=1000, csrf_token_lifetime ge=60, sidebar widths 48..100 and
        # 200..400, sample rates 0..1) that reject out-of-range values and
        # would otherwise look unbound.
        for candidate in (
            "true",
            "false",
            "42",
            "300",
            "80",
            "999",
            "5000",
            "123456",
            "0.75",
            "gzip",
            "postgres",
            "DEBUG",
        ):
            os.environ[var] = candidate
            dumped, cand_kinds = _load()
            if dumped is None:
                continue
            saw_load = True
            if dumped == baseline:
                continue
            # Structural bail-out check: if the diff is a typed child model
            # swapping to a raw dict along the var's parent path, the value
            # was swallowed by the coercion engine's unknown-key fallback —
            # it never reached a declared field.  The leaf path itself is
            # exempt: a declared ``dict`` field being REPLACED by a scalar is
            # a legitimate binding (e.g. CSP directives), not a swallow.
            if _model_to_dict_swap(
                base_kinds, cand_kinds, parent
            ) or _model_to_dict_swap(base_kinds, cand_kinds, ".".join(segs)):
                continue
            return True
        if not saw_load:
            return None
        return fallback
    finally:
        os.environ.pop(var, None)
        if old is not None:
            os.environ[var] = old


def _probe_value(cls: type, var: str, value: str) -> bool | None:
    """Probe with a specific value; True only if the value landed verbatim."""
    segment = None
    yaml_body = "{}\n"
    if var.startswith("LEX_") and "__" in var[4:]:
        segment = var[4:].split("__", 1)[0]
        yaml_body = FAMILY_BASE_YAML.get(segment, "{}\n")
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        f.write(yaml_body)
        path = f.name
    old = os.environ.pop(var, None)
    os.environ[var] = value
    try:
        cfg = cls.from_yaml(path)  # type: ignore[attr-defined]
    except Exception:
        return None
    finally:
        os.environ.pop(var, None)
        if old is not None:
            os.environ[var] = old
        Path(path).unlink(missing_ok=True)
    return value in repr(_dump_fields(cfg))


__all__ = ["FAMILY_ROOTS", "check_var"]

if __name__ == "__main__":
    sys.exit(main())
