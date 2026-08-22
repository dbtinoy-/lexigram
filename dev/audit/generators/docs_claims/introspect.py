"""Type-introspection helpers for config-class analysis."""

from __future__ import annotations

from dataclasses import fields as dc_fields
import re
import types
import typing


def _iter_python_blocks(md_text: str) -> tuple[str, ...]:
    return tuple(
        match.group(1)
        for match in re.finditer(r"```(?:python|py)\s*\n(.*?)```", md_text, re.DOTALL)
    )


def _annotation_names(config_cls: type) -> tuple[str, ...]:
    """Field names from type annotations, excluding ClassVar/private members."""
    try:
        hints = typing.get_type_hints(config_cls)
    except Exception:  # noqa: BLE001 - unresolvable hints degrade gracefully
        return ()
    return tuple(
        name
        for name, ftype in hints.items()
        if not name.startswith("_")
        and typing.get_origin(ftype) is not typing.ClassVar
    )


def _is_config_class(obj: object) -> bool:
    """True for dataclasses, pydantic models, and DomainModel-style configs."""
    if not isinstance(obj, type):
        return False
    try:
        if dc_fields(obj):
            return True
    except TypeError:
        pass
    if getattr(obj, "model_fields", None):
        return True
    return bool(_annotation_names(obj))


def _field_names(config_cls: type) -> tuple[str, ...]:
    """Declared field names for dataclass / pydantic / annotated config classes."""
    fields = getattr(config_cls, "model_fields", ())
    if fields:
        return tuple(fields)
    try:
        own = tuple(f.name for f in dc_fields(config_cls))
    except TypeError:
        return _annotation_names(config_cls)
    if own:
        return own
    return _annotation_names(config_cls)


def _driver_segment(config_cls: type) -> str:
    """Lowercased short name of a driver config class (``StorageS3Config`` -> ``s3``)."""
    name = config_cls.__name__
    if name.endswith("Config"):
        name = name[: -len("Config")]
    for prefix in ("Storage", "Cache", "Backend", "Driver"):
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break
    return name.lower()


def _union_members(ftype: object) -> tuple[object, ...]:
    """Union arguments excluding ``None``; a non-union type is returned as-is."""
    origin = typing.get_origin(ftype)
    if origin is typing.Union or origin is types.UnionType:
        return tuple(
            arg for arg in typing.get_args(ftype) if arg is not type(None)  # noqa: E721
        )
    return (ftype,)


def _sequence_element(ftype: object) -> object | None:
    """Element type of ``list[T]`` / ``tuple[T]`` / ``Sequence[T]``, else None."""
    if typing.get_origin(ftype) in (list, tuple, set, frozenset, typing.Sequence):
        args = typing.get_args(ftype)
        if args:
            return args[0]
    return None


def _mapping_value(ftype: object) -> object | None:
    """Value type of ``dict[str, V]`` / ``Mapping[str, V]``, else None."""
    if typing.get_origin(ftype) in (dict, typing.Mapping):
        args = typing.get_args(ftype)
        if len(args) == 2:
            return args[1]
    return None
