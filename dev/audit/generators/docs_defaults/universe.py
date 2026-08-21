"""Index of real config-field defaults used to verify doc claims."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from dataclasses import fields as dc_fields
from pathlib import Path
import typing
from typing import Any

from dev.audit.generators.docs_claims import (
    _build_direct_reads,
    _driver_segment,
    _field_names,
    _is_config_class,
    _mapping_value,
    _sequence_element,
    _try_import,
    _union_members,
    _verify_env_var,
)
from dev.core.package_inventory import discover_package_paths

_UNPARSEABLE_CELL = frozenset({"", "—", "-", "*", "n/a", "na"})

_KIND_MISSING = "missing"
_KIND_FACTORY = "factory"
_KIND_LITERAL = "literal"
_KIND_UNKNOWN = "unknown"


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
    annotations: dict[str, Any] = {}
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
    root = Path(__file__).resolve().parents[4]
    for rel in discover_package_paths(root):
        pkg_path = root / rel
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
