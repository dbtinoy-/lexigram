"""Config-class discovery and env-validity registry construction."""

from __future__ import annotations

import importlib
from pathlib import Path
import re
import typing

from dev.audit.generators.docs_claims._constants import _SECTION_CONFIG_SUFFIX
from dev.audit.generators.docs_claims.introspect import (
    _driver_segment,
    _field_names,
    _is_config_class,
    _mapping_value,
    _sequence_element,
    _union_members,
)
from dev.audit.generators.docs_claims._constants import _DIRECT_READ_ENV_VARS
from dev._lib.package_inventory import discover_package_paths


def _nested_keypaths(config_cls: type, max_depth: int = 4) -> tuple[str, ...]:
    """All dotted key paths (depth 1..max_depth) reachable from a config class.

    ``*`` segments denote list/dict positions: ``drivers.*.bucket`` or
    ``extra.*`` for scalar-valued mappings (arbitrary keys).
    """

    seen_types: set[int] = set()
    paths: list[str] = []

    def walk(cls: type, prefix: str, depth: int) -> None:
        if depth > max_depth or id(cls) in seen_types:
            return
        seen_types.add(id(cls))
        names = _field_names(cls)
        annotations: dict[str, object] = {}
        try:
            annotations = typing.get_type_hints(cls)
        except Exception:  # noqa: BLE001 - unresolvable hints degrade gracefully
            pass
        for name in names:
            path = f"{prefix}.{name}" if prefix else name
            paths.append(path)
            ftype = annotations.get(name)
            if ftype is None or typing.get_origin(ftype) is typing.ClassVar:
                continue
            for member in _union_members(ftype):
                element = _sequence_element(member)
                if element is not None and _is_config_class(element):
                    walk(typing.cast('type', element), f"{path}.*", depth + 1)
                    continue
                mapped = _mapping_value(member)
                if mapped is not None:
                    value_members = [
                        m for m in _union_members(mapped) if _is_config_class(m)
                    ]
                    if value_members:
                        for value_member in value_members:
                            value_cls = typing.cast('type', value_member)
                            walk(value_cls, f"{path}.*", depth + 1)
                            segment = _driver_segment(value_cls)
                            if segment:
                                walk(value_cls, f"{path}.{segment}", depth + 1)
                    else:
                        paths.append(f"{path}.*")
                    continue
                if _is_config_class(member):
                    walk(typing.cast('type', member), path, depth + 1)

    walk(config_cls, "", 1)
    return tuple(paths)


def _config_classes(target: object | None) -> tuple[type, ...]:
    """Every config class (dataclass or pydantic) exposed by a module."""
    if target is None:
        return ()
    found: list[type] = []
    for attr_name in dir(target):
        if attr_name.endswith(_SECTION_CONFIG_SUFFIX):
            try:
                attr = getattr(target, attr_name)
            except Exception:  # noqa: BLE001 - lazy __getattr__ may raise
                continue
            if _is_config_class(attr):
                found.append(attr)
    return tuple(found)


def _config_modules(pkg_root: Path, pkg_mod_name: str) -> tuple[str, ...]:
    """Dotted module paths of a package's config-bearing modules.

    Any module whose path contains a ``config`` component or that ends in
    ``config.py`` (e.g. ``lexigram.logging.config``,
    ``lexigram.app.config.models``, ``lexigram.web.security.config``).
    """
    src_dir = pkg_root / "src"
    if not src_dir.is_dir():
        return ()
    modules: list[str] = []
    for py in sorted(src_dir.rglob("*.py")):
        parts = py.relative_to(src_dir).with_suffix("").parts
        if not parts or parts[0] != pkg_mod_name.split(".", 1)[0] or "." in parts[0]:
            continue
        if "config" not in parts:
            continue
        if parts[-1] == "__init__":
            modules.append(".".join(parts[:-1]))
        else:
            modules.append(".".join(parts))
    return tuple(modules)


def _try_import(mod_name: str) -> object | None:
    try:
        return importlib.import_module(mod_name)
    except Exception:  # noqa: BLE001 - optional modules may not import
        return None


def _build_declared_prefixes() -> set[str]:
    """Env prefixes declared as constants in framework source.

    Some packages declare an env prefix constant (``GRAPH_ENV_PREFIX =
    "LEX_WORKFLOW__GRAPH__"``) without wiring it into ``model_config``;
    tokens under a declared prefix are still legitimate claims.
    """
    root = Path(__file__).resolve().parents[4]
    declared: set[str] = set()
    prefix_re = re.compile(
        r'\w*PREFIX\w*\s*(?::\s*\w+\s*)?=\s*["\'](LEX_[A-Z0-9_]+__)["\']'
    )
    for rel in discover_package_paths(root):
        pkg = root / rel
        src_dir = pkg / "src"
        if not src_dir.is_dir():
            continue
        for py in src_dir.rglob("*.py"):
            try:
                text = py.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if "PREFIX" not in text:
                continue
            declared.update(prefix_re.findall(text))
    # Package-level headers (`LEX_SQL__`) declare a namespace, not specific
    # vars — only sub-section prefixes (`LEX_WORKFLOW__GRAPH__`) count as
    # declared variables.
    return {p for p in declared if p[p.index("LEX_") + 4 :].count("__") >= 2}


def _build_env_validity() -> dict[str, str]:
    """Map valid env vars to their ``section.key`` path.

    Two families cover the framework's env patterns:

    1. Core prefix ``LEX_`` + config-class section: ``LEX_LOGGING__JSON_FORMAT``
       (any package's ``*Config`` class, nested keys joined with ``__``).
    2. Package prefix ``LEX_<PACKAGE>`` + nested key path: extension packages
       register their own prefix (e.g. ``LEX_SQL``) with keys straight from the
       package's config classes (e.g. ``LEX_SQL__BACKEND__URL``).
    """
    validity: dict[str, str] = {}
    root = Path(__file__).resolve().parents[4]
    packages = sorted(root / p for p in discover_package_paths(root))
    for pkg in packages:
        pkg_mod_name = (
            "lexigram" if pkg.name == "lexigram" else pkg.name.replace("-", ".")
        )
        classes = list(_config_classes(_try_import(pkg_mod_name)))
        for mod_path in _config_modules(pkg, pkg_mod_name):
            classes += _config_classes(_try_import(mod_path))
        pkg_short = (
            None
            if pkg.name == "lexigram"
            else pkg.name[len("lexigram-") :].replace("-", "_")
        )
        for config_cls in classes:
            declared_section = getattr(config_cls, "config_section", None)
            section = (
                str(declared_section)
                if declared_section
                else config_cls.__name__[: -len(_SECTION_CONFIG_SUFFIX)].lower()
            )
            model_config = getattr(config_cls, "model_config", None)
            env_prefix = ""
            nested_delimiter = "__"
            if isinstance(model_config, dict):
                env_prefix = str(model_config.get("env_prefix", ""))
                nested_delimiter = str(
                    model_config.get("env_nested_delimiter", "__")
                )
            for keypath in _nested_keypaths(config_cls):
                parts = "__".join(keypath.upper().split("."))
                if env_prefix:
                    validity[f"{env_prefix.upper()}{parts.replace('__', nested_delimiter.upper())}"] = (
                        f"{env_prefix}{keypath}".lower()
                    )
                    continue
                validity[f"LEX_{section.upper()}__{parts}"] = (
                    f"{section}.{keypath}"
                )
                if pkg_short is not None:
                    validity[f"LEX_{pkg_short.upper()}__{parts}"] = (
                        f"{pkg_short}.{keypath}"
                    )
    return validity


def _build_direct_reads() -> set[str]:
    """Env vars read directly by framework source code."""
    root = Path(__file__).resolve().parents[4]
    found: set[str] = set(_DIRECT_READ_ENV_VARS)
    get_re = re.compile(r"os\.environ\.get\(\s*[\"'](LEX_[A-Z0-9_]+)[\"']")
    for rel in discover_package_paths(root):
        pkg = root / rel
        src_dir = pkg / "src"
        if not src_dir.is_dir():
            continue
        for py in src_dir.rglob("*.py"):
            try:
                text = py.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            found.update(get_re.findall(text))
    return found
