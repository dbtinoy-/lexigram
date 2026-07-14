"""Audit generator: verify prose default-value claims in package docs.

Covers the claim classes the env-var/priority audit cannot see — literal
defaults stated in docs:

1. **Config-table ``Default`` columns** — rows whose key (or ``Env Var`` cell)
   resolves to a config field are checked against the field's real default.
2. **Inline claims** — ``KEY (default: VALUE)`` / ``KEY (default=VALUE)``.
3. **Prose** — ``KEY defaults to VALUE`` / ``KEY default is VALUE``.

An identified key is verified ONLY when it resolves to a unique config field
with a comparable literal default; ambiguous keys, unparseable values, and
``default_factory``/required fields are counted as unverifiable and never
flagged as findings.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from dataclasses import fields as dc_fields
from enum import Enum
from pathlib import Path
import re
import typing

from scripts.audit.generators.base import AuditRunResult, MarkdownAuditGenerator
from scripts.audit.generators.docs_claims import (
    _build_direct_reads,
    _build_env_validity,
    _driver_segment,
    _field_names,
    _is_config_class,
    _mapping_value,
    _sequence_element,
    _try_import,
    _union_members,
    _verify_env_var,
)

_UNPARSEABLE_CELL = frozenset({"", "—", "-", "*", "n/a", "na"})

_KIND_MISSING = "missing"
_KIND_FACTORY = "factory"
_KIND_LITERAL = "literal"
_KIND_UNKNOWN = "unknown"

_NUMERIC = (int, float)


@dataclass(frozen=True, slots=True)
class DefaultEntry:
    """One config field with its declared default, indexed for claim lookup."""

    pkg: str
    section: str
    keypath: str
    class_name: str
    field: str
    kind: str
    default: object
    parents: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DefaultIssue:
    """A doc default claim that disagrees with the framework's actual default."""

    doc: str
    claim: str
    claimed: str
    expected: str


def _field_default(config_cls: type, name: str) -> tuple[str, object]:
    """Return (kind, default) for a field of a config class.

    Handles pydantic ``model_fields``, dataclasses fields, and raw
    ``dataclasses.Field`` class attributes (the framework's ``DomainModel``
    converts pydantic ``Field()`` descriptors at class-creation time, and
    ``@dataclass`` is applied lazily on first instantiation).
    """
    model_fields = getattr(config_cls, "model_fields", None)
    if model_fields:
        info = model_fields.get(name)
        if info is not None:
            if info.is_required():
                return _KIND_MISSING, dataclasses.MISSING
            if info.default_factory is not None:
                return _KIND_FACTORY, dataclasses.MISSING
            return _KIND_LITERAL, info.default

    own = vars(config_cls).get("__dataclass_fields__", {})
    info = own.get(name)
    if info is None:
        for cls_attr in vars(config_cls).values():
            if isinstance(cls_attr, dataclasses.Field) and cls_attr.name == name:
                info = cls_attr
                break
    if isinstance(info, dataclasses.Field):
        if info.default is not dataclasses.MISSING:
            return _KIND_LITERAL, info.default
        if info.default_factory is not dataclasses.MISSING:
            return _KIND_FACTORY, dataclasses.MISSING
        return _KIND_MISSING, dataclasses.MISSING

    try:
        for field in dc_fields(config_cls):
            if field.name == name:
                if field.default is not dataclasses.MISSING:
                    return _KIND_LITERAL, field.default
                if field.default_factory is not dataclasses.MISSING:
                    return _KIND_FACTORY, dataclasses.MISSING
                return _KIND_MISSING, dataclasses.MISSING
    except TypeError:
        pass
    try:
        return _KIND_LITERAL, getattr(config_cls, name)
    except Exception:  # noqa: BLE001 - descriptors may raise on access
        return _KIND_UNKNOWN, None


def _walk_config(
    config_cls: type,
    prefix: str,
    depth: int,
    *,
    pkg: str,
    section: str,
    out: list[DefaultEntry],
    seen: set[int],
    nested: bool = True,
    parents: tuple[str, ...] = (),
) -> None:
    """Collect every field of a config class (nested included) with its default."""
    if depth > 4 or id(config_cls) in seen:
        return
    seen.add(id(config_cls))
    annotations: dict[str, object] = {}
    try:
        annotations = typing.get_type_hints(config_cls)
    except Exception:  # noqa: BLE001 - unresolvable hints degrade gracefully
        pass
    for name in _field_names(config_cls):
        ftype = annotations.get(name)
        if ftype is not None and typing.get_origin(ftype) is typing.ClassVar:
            continue
        path = f"{prefix}.{name}" if prefix else name
        kind, default = _field_default(config_cls, name)
        out.append(
            DefaultEntry(
                pkg=pkg,
                section=section,
                keypath=path,
                class_name=config_cls.__name__,
                field=name,
                kind=kind,
                default=default,
                parents=parents,
            )
        )
        if name == "config_section" or not nested:
            continue
        if ftype is None or type(ftype).__name__ == "ClassVar":
            continue
        for member in _union_members(ftype):
            element = _sequence_element(member)
            if element is not None and _is_config_class(element):
                _walk_config(
                    element,
                    f"{path}.*",
                    depth + 1,
                    pkg=pkg,
                    section=section,
                    out=out,
                    seen=seen,
                    nested=nested,
                    parents=(*parents, config_cls.__name__),
                )
                continue
            mapped = _mapping_value(member)
            if mapped is not None:
                for value_member in _union_members(mapped):
                    if _is_config_class(value_member):
                        _walk_config(
                            value_member,
                            f"{path}.*",
                            depth + 1,
                            pkg=pkg,
                            section=section,
                            out=out,
                            seen=seen,
                            nested=nested,
                            parents=(*parents, config_cls.__name__),
                        )
                        segment = _driver_segment(value_member)
                        if segment:
                            _walk_config(
                                value_member,
                                f"{path}.{segment}",
                                depth + 1,
                                pkg=pkg,
                                section=section,
                                out=out,
                                seen=seen,
                                nested=nested,
                                parents=(*parents, config_cls.__name__),
                            )
                continue
            if _is_config_class(member):
                _walk_config(
                    member,
                    path,
                    depth + 1,
                    pkg=pkg,
                    section=section,
                    out=out,
                    seen=seen,
                    nested=nested,
                    parents=(*parents, config_cls.__name__),
                )


def _section_of(config_cls: type) -> str:
    """Section name for a config class (same rule as the claims audit)."""
    declared = getattr(config_cls, "config_section", None)
    if declared:
        return str(declared)
    name = config_cls.__name__
    if name.endswith("Config"):
        name = name[: -len("Config")]
    return name.lower()


def _module_classes(mod: object) -> list[type]:
    """Classes defined in a module (not merely imported)."""
    defined: list[type] = []
    module_name = getattr(mod, "__name__", None)
    for attr_name in dir(mod):
        if attr_name.startswith("_"):
            continue
        try:
            attr = getattr(mod, attr_name)
        except Exception:  # noqa: BLE001 - lazy __getattr__ may raise
            continue
        if not isinstance(attr, type):
            continue
        if getattr(attr, "__module__", None) != module_name:
            continue
        defined.append(attr)
    return defined


def _walkable_class(cls: type) -> bool:
    """True when a module class is worth indexing (has at least two own fields)."""
    import dataclasses as _dc

    if _dc.is_dataclass(cls):
        return True
    if getattr(cls, "model_fields", None):
        return True
    own = sum(1 for k in vars(cls).get("__annotations__", {}) if not k.startswith("_"))
    return own >= 2


def _build_universe() -> dict[str, list[DefaultEntry]]:
    """Index every documented field default by path, class name, and field name."""
    path_index: dict[str, list[DefaultEntry]] = {}
    class_index: dict[str, list[DefaultEntry]] = {}
    field_index: dict[str, list[DefaultEntry]] = {}
    root = Path(__file__).resolve().parents[3]
    for pkg_path in sorted(root.iterdir()):
        if not (
            pkg_path.is_dir()
            and (pkg_path.name == "lexigram" or pkg_path.name.startswith("lexigram-"))
        ):
            continue
        pkg_mod_name = (
            "lexigram"
            if pkg_path.name == "lexigram"
            else pkg_path.name.replace("-", ".")
        )
        src_dir = pkg_path / "src"
        if not src_dir.is_dir():
            continue
        module_names: set[str] = set()
        for py in sorted(src_dir.rglob("*.py")):
            if "__pycache__" in py.parts or any(
                "test" in part.lower() for part in py.parts
            ):
                continue
            rel = py.relative_to(src_dir).with_suffix("")
            parts = rel.parts
            if py.name == "__init__.py":
                module_names.add(".".join(parts[:-1]))
            elif not parts[-1].startswith("_"):
                module_names.add(".".join(parts))
        for mod_name in sorted(module_names):
            mod = _try_import(mod_name)
            if mod is None:
                continue
            for cls in _module_classes(mod):
                if not _walkable_class(cls):
                    continue
                config_like = cls.__name__.endswith("Config")
                section = _section_of(cls)
                entries: list[DefaultEntry] = []
                _walk_config(
                    cls,
                    "",
                    1,
                    pkg=pkg_path.name,
                    section=section,
                    out=entries,
                    seen=set(),
                    nested=config_like,
                )
                for entry in entries:
                    path_index.setdefault(f"{section}.{entry.keypath}", []).append(
                        entry
                    )
                    class_index.setdefault(entry.class_name, []).append(entry)
                    field_index.setdefault(entry.field, []).append(entry)
    return {"path": path_index, "class": class_index, "field": field_index}


def _segments(path: str) -> tuple[str, ...]:
    return tuple(part for part in path.split(".") if part)


def _path_matches(a: str, b: str) -> bool:
    """Segment-wise match where ``*`` on either side matches any single segment."""
    a_parts, b_parts = _segments(a), _segments(b)
    if len(a_parts) != len(b_parts):
        return False
    for x, y in zip(a_parts, b_parts, strict=True):
        wildcard = x == "*" or y == "*"
        if not wildcard and x != y:
            return False
    return True


def _desc_to_path(desc: str) -> str | None:
    """Extract a ``section.keypath`` from a claims-audit validity description."""
    candidate = desc
    if candidate.endswith(" (wildcard)"):
        candidate = candidate[: -len(" (wildcard)")]
    if "`" in candidate or " " in candidate or ":" in candidate:
        return None
    return candidate or None


class DefaultUniverse:
    """Resolve doc keys to config-field defaults with ambiguity tracking."""

    def __init__(
        self, validity: dict[str, str], universe: dict[str, list[DefaultEntry]]
    ) -> None:
        self.validity = validity
        self.universe = universe
        self.direct_reads = _build_direct_reads()

    def resolve(self, key: str) -> list[DefaultEntry]:
        """Return candidate default entries for a doc key (empty when unresolvable)."""
        entries: list[DefaultEntry] = []
        if key.startswith("LEX_") and "__" in key:
            ok, desc = _verify_env_var(key, self.validity, self.direct_reads)
            if ok:
                path = _desc_to_path(desc)
                if path:
                    for pkey, cands in self.universe["path"].items():
                        if _path_matches(pkey, path):
                            entries.extend(cands)
            return _dedupe(entries)
        if key.count(".") >= 1:
            head, tail = key.rsplit(".", 1)
            if head and head[0].isupper():
                for cand in self.universe["class"].get(head, []):
                    if cand.field == tail:
                        entries.append(cand)
                return _dedupe(entries)
            for pkey, cands in self.universe["path"].items():
                if _path_matches(pkey, key):
                    entries.extend(cands)
            return _dedupe(entries)
        return _dedupe(self.universe["field"].get(key, []))


def _dedupe(entries: list[DefaultEntry]) -> list[DefaultEntry]:
    seen: list[DefaultEntry] = []
    for entry in entries:
        if entry not in seen:
            seen.append(entry)
    return seen


def _parse_claim_value(raw: str) -> tuple[bool, object]:
    """Parse a doc-stated default into a comparable scalar (or not)."""
    value = raw.strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1].strip()
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        if len(value) >= 2:
            return True, value[1:-1]
        return False, None
    lower = value.lower()
    if lower in ("true", "false"):
        return True, lower == "true"
    if lower in ("none", "null"):
        return True, None
    try:
        return True, int(value)
    except ValueError:
        pass
    try:
        return True, float(value)
    except ValueError:
        pass
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_.\-]*", value):
        return True, value
    return False, None


def _defaults_equal(claimed: object, real: object) -> bool | None:
    """Compare a parsed claim with a real default; None when not comparable."""
    if isinstance(real, Enum):
        return None
    if isinstance(real, bool):
        return claimed == real if isinstance(claimed, bool) else None
    if isinstance(real, _NUMERIC):
        return claimed == real if isinstance(claimed, _NUMERIC) else None
    if isinstance(real, str):
        return claimed == real if isinstance(claimed, str) else None
    if real is None:
        return claimed is None
    return None


_HINT_RE = re.compile(
    r"\b[A-Z][A-Za-z0-9_]*(?:Config|Contributor|Resource|Options|Spec|Settings)\b"
)


def _doc_class_hints(md_text: str) -> frozenset[str]:
    """Class names a doc mentions (config/resource-style), used to disambiguate."""
    return frozenset(_HINT_RE.findall(md_text))


def _unique_comparable_default(
    entries: list[DefaultEntry],
    hints: frozenset[str] = frozenset(),
) -> tuple[bool, object | None, list[DefaultEntry]]:
    """Return (unambiguous, default, comparable entries) for candidates.

    When multiple distinct defaults exist, doc-mentioned class names (``hints``)
    narrow the candidate set; if that leaves one distinct default, the claim is
    verified against it.
    """
    comparable = [e for e in entries if e.kind == _KIND_LITERAL]
    if not comparable:
        return False, None, []
    defaults = {repr(e.default) for e in comparable}
    if len(defaults) == 1:
        return True, comparable[0].default, comparable
    hinted = [
        e
        for e in comparable
        if e.class_name in hints or any(p in hints for p in e.parents)
    ]
    if hinted:
        hinted_defaults = {repr(e.default) for e in hinted}
        if len(hinted_defaults) == 1:
            return True, hinted[0].default, hinted
    return False, None, comparable


_INLINE_WITH_KEY_RE = re.compile(
    r"(?<![\w.`])([A-Za-z_][\w.]*)\s*\(default[:=]\s*([^)]+)\)", re.I
)
_INLINE_BARE_RE = re.compile(r"\(default[:=]\s*([^)]+)\)", re.I)
_DEFAULTS_TO_RE = re.compile(
    r"(?<![\w.`])([A-Za-z_][\w.]*)\s+defaults?\s+(?:to|is)\s+([^,.;\n):]+)", re.I
)
_INLINE_KEY_RE = re.compile(r"[\w.]*$")


def _claim_text(raw: str) -> str:
    text = raw.strip()
    if text.startswith("`") and text.endswith("`"):
        text = text[1:-1]
    return text.strip()


def _iter_claims(md_text: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Extract (key, claimed-value) claims from tables and from prose.

    Returns (table_claims, prose_claims); prose claims exclude lines that
    belong to a parsed table to avoid double-counting inline annotations.
    """
    lines = md_text.splitlines()
    table_claims: list[tuple[str, str]] = []
    prose_claims: list[tuple[str, str]] = []
    in_table_lines: set[int] = set()

    i = 0
    while i < len(lines) - 1:
        header = lines[i]
        if not header.startswith("|") or not lines[i + 1].startswith("|"):
            i += 1
            continue
        if not re.fullmatch(r"\|[\s\-:|]+", lines[i + 1]):
            i += 1
            continue
        cells = [c.strip() for c in header.strip("|").split("|")]
        if not cells:
            i += 1
            continue
        default_col = next(
            (idx for idx, cell in enumerate(cells) if "default" in cell.lower()), None
        )
        env_col = next(
            (
                idx
                for idx, cell in enumerate(cells)
                if re.search(r"env\s*var", cell.lower())
            ),
            None,
        )
        row_start = i + 2
        while row_start < len(lines) and lines[row_start].startswith("|"):
            in_table_lines.add(row_start)
            row_cells = [c.strip() for c in lines[row_start].strip("|").split("|")]
            while len(row_cells) < len(cells):
                row_cells.append("")
            if default_col is not None and default_col < len(row_cells):
                key = _claim_text(row_cells[0]) if row_cells else ""
                claimed = _claim_text(row_cells[default_col])
                if not key or not claimed or claimed.lower() in _UNPARSEABLE_CELL:
                    row_start += 1
                    continue
                if env_col is not None and env_col < len(row_cells):
                    env_cell = _claim_text(row_cells[env_col])
                    if env_cell and env_cell.lower() not in _UNPARSEABLE_CELL:
                        table_claims.append((env_cell, claimed))
                        row_start += 1
                        continue
                table_claims.append((key, claimed))
            row_start += 1
        i = row_start

    for idx, line in enumerate(lines):
        if idx in in_table_lines or line.startswith("```"):
            continue
        if line in ("```",) or line.startswith("```"):
            continue
        for match in _INLINE_WITH_KEY_RE.finditer(line):
            prose_claims.append((match.group(1), match.group(2)))
        for match in _INLINE_BARE_RE.finditer(line):
            prefix = line[: match.start()]
            key_match = _INLINE_KEY_RE.search(prefix)
            if key_match and key_match.group(0):
                prose_claims.append((key_match.group(0), match.group(1)))
        for match in _DEFAULTS_TO_RE.finditer(line):
            prose_claims.append((match.group(1), match.group(2)))
    return table_claims, prose_claims


class DocsDefaultsAuditGenerator(MarkdownAuditGenerator):
    """Audit doc default-value claims (tables, inline, prose) against config classes."""

    name = "docs-defaults"
    description = (
        "Generate AUDIT_DOC_DEFAULTS.md verifying that every default-value claim "
        "(config-table Default columns, inline `(default: X)`, prose `defaults to`) "
        "in package docs matches the config class's actual default."
    )
    output_file = "AUDIT_DOC_DEFAULTS.md"

    def run(
        self,
        *,
        root: Path | None = None,
        all_mode: bool = False,
    ) -> AuditRunResult:
        """Execute the defaults audit and fail when any claim mismatches."""
        validation = self.validate(root=root)
        if not validation.success:
            return validation
        resolved_root = self.resolve_root(root)
        output_dir = (
            resolved_root if all_mode else resolved_root / "docs/lexigram-docs/audit"
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        markdown, issue_count = self._render(resolved_root)
        output_path = output_dir / self.output_file
        output_path.write_text(markdown, encoding="utf-8")
        status = (
            "PASS" if issue_count == 0 else f"{issue_count} mismatched default claim(s)"
        )
        return AuditRunResult(
            name=self.name,
            success=issue_count == 0,
            message=f"{status} -> wrote {output_path.name}",
            output_path=output_path,
        )

    def render_markdown(self, *, root: Path) -> str:
        """Render the defaults audit report (protocol compatibility)."""
        return self._render(root)[0]

    def _render(self, root: Path) -> tuple[str, int]:
        validity = _build_env_validity()
        universe = DefaultUniverse(validity, _build_universe())

        verified = 0
        unverifiable = 0
        issues: list[DefaultIssue] = []
        for package in self.iter_package_roots(root=root):
            docs_dir = package / "docs"
            if not docs_dir.is_dir():
                continue
            for md_file in sorted(docs_dir.glob("*.md")):
                try:
                    text = md_file.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                rel = md_file.relative_to(root).as_posix()
                table_claims, prose_claims = _iter_claims(text)
                hints = _doc_class_hints(text)
                for key, claimed in table_claims + prose_claims:
                    claimed_value: object
                    ok, parsed = _parse_claim_value(claimed)
                    if not ok:
                        unverifiable += 1
                        continue
                    claimed_value = parsed
                    candidates = universe.resolve(key)
                    if not candidates:
                        unverifiable += 1
                        continue
                    unambiguous, real_default, comparable = _unique_comparable_default(
                        candidates, hints
                    )
                    if not unambiguous:
                        unverifiable += 1
                        continue
                    equal = _defaults_equal(claimed_value, real_default)
                    if equal is None:
                        unverifiable += 1
                        continue
                    if equal:
                        verified += 1
                        continue
                    expected = f"{comparable[0].class_name}.{comparable[0].field}={real_default!r}"
                    issues.append(
                        DefaultIssue(
                            doc=rel,
                            claim=f"{key} -> {claimed}",
                            claimed=repr(claimed_value),
                            expected=expected,
                        )
                    )

        lines = [
            "# AUDIT_DOC_DEFAULTS.md — Lexigram Documentation Default Claims Audit",
            "",
            "> **Source**: Every default-value claim in every package `docs/*.md` file",
            "> (config-table `Default` columns, inline `(default: X)`, prose `defaults to`)",
            "> resolved against the framework's config classes. Claims whose key is",
            "> ambiguous, whose value is not a comparable literal, or whose field has",
            "> no static default are counted unverifiable — never flagged.",
            "",
            "## Summary",
            "",
            f"- Default claims verified: {verified}",
            f"- Unverifiable claims (skipped): {unverifiable}",
            f"- Mismatched claims: {len(issues)}",
            "",
        ]

        if issues:
            lines.append("## Mismatched Claims")
            lines.append("")
            lines.append("| Doc | Claim | Claimed | Expected (class.field=default) |")
            lines.append("|-----|-------|---------|-------------------------------|")
            for issue in sorted(issues, key=lambda i: (i.doc, i.claim)):
                lines.append(
                    f"| `{issue.doc}` | `{issue.claim}` | {issue.claimed} | `{issue.expected}` |"
                )
            lines.append("")
        else:
            lines.append("No mismatched default claims detected.")
            lines.append("")

        return "\n".join(lines), len(issues)


__all__ = ["DocsDefaultsAuditGenerator"]
