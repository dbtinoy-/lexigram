"""Env-prefix discovery, field-path expansion, and direct-access scanning."""

from __future__ import annotations

import ast

from dev.catalogs.env_vars_catalog._model import (
    DIRECT_ENV_RE,
    ENV_PREFIX_RE,
    EXCLUDED_DIRS,
    ConfigClass,
    ConfigField,
    REPO_ROOT,
)
from dev.catalogs.env_vars_catalog.scan import (
    discover_packages,
    resolve_config_class,
)


def find_env_prefixes() -> dict[str, str]:
    """Find ENV_PREFIX defined in each package's constants.py."""
    prefixes: dict[str, str] = {}
    for pkg_src in discover_packages():
        pkg_name = pkg_src.parent.name
        constants_file = pkg_src / pkg_name / "constants.py"
        if constants_file.exists():
            try:
                tree = ast.parse(constants_file.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and target.id == "ENV_PREFIX":
                                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                                    prefixes[pkg_name] = node.value.value
            except (SyntaxError, Exception):
                pass

        if pkg_name not in prefixes:
            config_file = pkg_src / pkg_name / "config.py"
            if config_file.exists():
                try:
                    text = config_file.read_text(encoding="utf-8")
                    for m in ENV_PREFIX_RE.finditer(text):
                        prefixes[pkg_name] = m.group(1)
                except (OSError, Exception):
                    pass

        if pkg_name not in prefixes:
            prefixes[pkg_name] = f"LEX_{pkg_name.replace('lexigram-', '').upper().replace('-', '_')}__"

    return prefixes


def build_field_paths(
    root_class: ConfigClass,
    classes: dict[str, ConfigClass],
    prefix: str = "",
    depth: int = 0,
    visited: set[str] | None = None,
) -> list[tuple[str, ConfigField, str, str]]:
    """
    Build (type_str, field, file_path, dotted_path) tuples for all terminal fields.

    Only recurses into DIRECT child config references (not wrapped in collections).
    Tracks visited classes to prevent circular references.
    """
    if depth > 8:
        return []
    if visited is None:
        visited = set()

    results: list[tuple[str, ConfigField, str, str]] = []

    for field in root_class.fields:
        dotted = f"{prefix}.{field.name}" if prefix else field.name
        raw_type = field.type_str.strip().replace('"', "").replace("'", "")

        # Only recurse into DIRECT child config references (not wrapped in list/dict/set)
        is_collection = any(raw_type.startswith(c) for c in ("list[", "List[", "dict[", "Dict[", "set[", "Set["))
        if is_collection:
            results.append((field.type_str, field, str(root_class.file_path), dotted))
            continue

        child_class = resolve_config_class(raw_type, classes)

        if child_class and child_class in classes and child_class not in visited:
            visited.add(child_class)
            child_results = build_field_paths(
                classes[child_class], classes, prefix=dotted, depth=depth + 1, visited=visited
            )
            results.extend(child_results)
        else:
            results.append((field.type_str, field, str(root_class.file_path), dotted))

    return results


def scan_direct_env_vars() -> list[dict]:
    """Scan for direct os.environ.get('LEX_*') calls."""
    entries: list[dict] = []
    seen: set[str] = set()

    for pkg_src in discover_packages():
        pkg_name = pkg_src.parent.name
        for pyfile in pkg_src.rglob("*.py"):
            if any(p in EXCLUDED_DIRS for p in pyfile.parts):
                continue
            try:
                text = pyfile.read_text(encoding="utf-8")
                rel = pyfile.relative_to(REPO_ROOT)
                for m in DIRECT_ENV_RE.finditer(text):
                    var = m.group(1)
                    if var.startswith("LEX_ERR_"):
                        continue
                    if var not in seen:
                        seen.add(var)
                        entries.append({
                            "env_var": var,
                            "type": "str",
                            "default": "—",
                            "description": "",
                            "source": f"{rel}",
                            "package": pkg_name,
                            "note": " *(direct env access; not config-derived)*",
                        })
            except (OSError, UnicodeDecodeError):
                pass

    return entries


def package_sort_key(pkg: str) -> tuple:
    if pkg == "lexigram-contracts":
        return (0, "")
    if pkg == "lexigram":
        return (1, "")
    return (2, pkg)
