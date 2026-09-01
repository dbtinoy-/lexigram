"""Reconcile framework-generated Pydantic models with the graph's field types.

The SQL ``model`` generator
(``lexigram.sql.cli.generators.entity_model:EntityModelGenerator``) renders
``<Name>`` / ``<Name>Create`` / ``<Name>Update`` Pydantic models, but its
internal type map only understands a handful of types
(``str/int/float/bool/datetime``); every other builder field type
(``decimal``, ``date``, ``time``, ``uuid``, ``json``, ``bytes``, ``email``…)
falls back to ``str``, and ``datetime`` is *coerced to ``str``* on the
Create/Update payloads.

Once the builder wires strict request validation into the controllers
(see :mod:`controller_postprocess`), those wrong annotations reject valid
input (e.g. a numeric ``decimal`` is refused because the field says ``str``).

The framework generator stays the single source of the file's shape
(reserved columns, class layout). We post-process its emitted source:
rewrite the annotation of each known field line to the correct Pydantic
type derived from the graph, and ensure supporting imports are present.
Best-effort and idempotent — fields we cannot match are left untouched.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dc_field
import re

from lexigram.builder.graph.models import EntityConfig, FieldConfig
from lexigram.logging import get_logger

_logger = get_logger(__name__)

#: Builder field type → base Pydantic annotation (optionality appended later).
_FIELD_ANNOTATIONS: dict[str, str] = {
    "str": "str",
    "text": "str",
    "filename": "str",
    "filepath": "str",
    "phone": "str",
    "enum": "str",
    "ipv4": "str",
    "ipv6": "str",
    "url": "HttpUrl",
    "email": "EmailStr",
    "int": "int",
    "float": "float",
    "bool": "bool",
    # Decimal is not bindable by the SQLite driver used by the generic
    # repository (LEX_ERR_SQL_005); float is the portable numeric type and
    # still validates numeric JSON. A postgres/NUMERIC path can emit Decimal
    # later once the data layer binds it explicitly.
    "decimal": "float",
    "datetime": "datetime",
    "date": "date",
    "time": "time",
    "uuid": "UUID",
    "json": "dict[str, Any]",
    "bytes": "bytes",
}

#: Annotation token → (kind, statement) needed to import it.
#: ``kind`` groups stdlib ``datetime`` members into one combined import.
_IMPORT_SPECS: dict[str, tuple[str, str]] = {
    "datetime": ("datetime", "datetime"),
    "date": ("datetime", "date"),
    "time": ("datetime", "time"),
    "UUID": ("std", "from uuid import UUID"),
    "HttpUrl": ("pydantic", "from pydantic import HttpUrl"),
    "EmailStr": ("pydantic", "from pydantic import EmailStr"),
    "dict[str, Any]": ("typing", "from typing import Any"),
}

# A model field line, e.g. `    price: str` or `    email: str | None = None`.
_FIELD_LINE = re.compile(
    r"^(?P<indent>\s+)(?P<name>[a-z_][a-z0-9_]*):\s*(?P<rest>.+?)\s*$",
    re.MULTILINE,
)


@dataclass(frozen=True, slots=True)
class ModelRewrite:
    """Result of reconciling one generated model file.

    Attributes:
        text: The (possibly rewritten) model source.
        fixed: Mapping of field name → new annotation for every change made.
        added_imports: Import statements inserted into the source.
    """

    text: str
    fixed: dict[str, str] = dc_field(default_factory=dict)
    added_imports: tuple[str, ...] = ()

    @property
    def changed(self) -> bool:
        return bool(self.fixed)


def _annotation_for(fc: FieldConfig) -> str:
    base = _FIELD_ANNOTATIONS.get(fc.type, "str")
    if fc.nullable:
        return f"{base} | None"
    return base


def reconcile_model(text: str, entity: EntityConfig) -> ModelRewrite:
    """Rewrite field annotations in generated model source for *entity*.

    Args:
        text: Raw source of the ``<name>.py`` model file from the framework.
        entity: The graph entity describing the correct field types.

    Returns:
        A :class:`ModelRewrite` with the corrected source.
    """
    by_name: dict[str, FieldConfig] = {f.name: f for f in entity.fields}
    fixed: dict[str, str] = {}
    needed_tokens: set[str] = set()

    def _replace(match: re.Match[str]) -> str:
        name = match.group("name")
        indent = match.group("indent")
        rest = match.group("rest")
        fc = by_name.get(name)
        if fc is None:
            return match.group(0)
        desired = _annotation_for(fc)
        current_ann = rest.split("=", 1)[0].strip()
        raw_default = rest.split("=", 1)[1].strip() if "=" in rest else ""
        # The framework renders Update payloads as `<ann> = None` even when
        # the annotation is non-optional (e.g. `name: str = None`), which
        # pydantic rejects. Normalize to `<ann> | None = None`.
        is_none_default = raw_default == "None"
        # Compare whitespace-insensitively so `str | None` matches
        # the framework's space-less `str|None`.
        norm = lambda s: s.replace(" ", "")  # noqa: E731
        # The framework renders Update payloads as `<ann> = None` (a partial
        # patch), so every field is optional there — make the *graph-derived*
        # annotation optional regardless of the entity's nullability.
        if is_none_default:
            desired = desired.replace(" | None", "") + " | None"
        default = f" = {raw_default}" if raw_default else ""
        if norm(current_ann) == norm(desired):
            return match.group(0)
        fixed[name] = desired
        base_token = desired.replace(" | None", "")
        if base_token in _IMPORT_SPECS:
            needed_tokens.add(base_token)
        return f"{indent}{name}: {desired}{default}"

    new_text = _FIELD_LINE.sub(_replace, text)

    statements = _build_imports(needed_tokens, new_text)
    for stmt in statements:
        new_text = _insert_import(new_text, stmt)

    if fixed:
        _logger.debug("model_reconciled", entity=entity.name, fields=sorted(fixed))

    return ModelRewrite(text=new_text, fixed=fixed, added_imports=tuple(statements))


def _build_imports(tokens: set[str], source: str) -> list[str]:
    """Deterministically build the import statements still missing from *source*."""
    statements: list[str] = []

    # Combine datetime/date/time into one `from datetime import ...` line,
    # merging with a pre-existing single-member import (the model already
    # does `from datetime import datetime, timezone`).
    dt_members = {
        spec
        for tok, (kind, spec) in _IMPORT_SPECS.items()
        if kind == "datetime" and tok in tokens
    }
    if dt_members:
        existing = re.search(r"^from datetime import (.+)$", source, re.MULTILINE)
        if existing:
            have = {m.strip() for m in existing.group(1).split(",")}
            merged = sorted(have | dt_members)
            merged_line = f"from datetime import {', '.join(merged)}"
            if merged_line not in source:
                statements.append(merged_line)
        else:
            statements.append(
                f"from datetime import {', '.join(sorted(dt_members))}"
            )

    for tok in sorted(tokens):
        kind, stmt = _IMPORT_SPECS[tok]
        if kind == "datetime":
            continue  # handled by the combined import above
        if stmt not in source:
            statements.append(stmt)

    return statements


def _insert_import(source: str, statement: str) -> str:
    """Insert *statement* after the module docstring/import header block."""
    if statement in source:
        return source
    # Upgrade an existing single-member datetime import to the merged form.
    if statement.startswith("from datetime import ") and "from datetime import " in source:
        return re.sub(
            r"^from datetime import .+$", statement, source, count=1, flags=re.MULTILINE
        )
    lines = source.splitlines(keepends=True)
    insert_at = 0
    in_docstring = False
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if idx == 0 and stripped.startswith(('"""', "'''")):
            if stripped.count('"""') >= 2 or stripped.count("'''") >= 2:
                insert_at = idx + 1
                continue
            in_docstring = True
            continue
        if in_docstring:
            if '"""' in stripped or "'''" in stripped:
                in_docstring = False
                insert_at = idx + 1
            continue
        if stripped.startswith(("from ", "import ")):
            insert_at = idx + 1
        elif stripped == "":
            continue
        else:
            break
    lines.insert(insert_at, statement + "\n")
    return "".join(lines)


__all__ = ["ModelRewrite", "reconcile_model"]
