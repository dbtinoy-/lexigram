"""AST-backed discovery of config classes and their fields."""

from __future__ import annotations

import ast
from pathlib import Path
import re

from dev.catalogs.env_vars_catalog._model import (
    CONFIG_BASE_CLASSES,
    EXCLUDED_DIRS,
    ConfigClass,
    ConfigField,
    REPO_ROOT,
)
from dev.core.package_inventory import discover_package_paths


def discover_packages(include_all: bool = False) -> list[Path]:
    """Discover src trees of all workspace member packages at repo root."""
    packages: list[Path] = []
    for rel in discover_package_paths(REPO_ROOT):
        src_dir = REPO_ROOT / rel / "src"
        if src_dir.exists():
            packages.append(src_dir)
    return packages


def extract_field_description(value: ast.expr | None) -> str:
    """Extract description keyword from a Field() call AST node."""
    if not isinstance(value, ast.Call):
        return ""
    fn = ast.unparse(value.func)
    if fn != "Field":
        return ""
    for kw in value.keywords:
        if kw.arg == "description":
            if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                return kw.value.value
    return ""


def extract_field_comments_from_source(
    source_lines: list[str],
    lineno: int,
    end_lineno: int,
) -> str:
    """
    Look for #: directive comments on the line before or same line as a field.
    Returns the first such comment found.
    """
    # Check same line (after the annotation, before any code)
    line = source_lines[lineno - 1] if lineno <= len(source_lines) else ""
    if "#:" in line:
        idx = line.index("#:")
        return line[idx + 2:].strip()
    # Check line before
    if lineno > 1 and lineno - 1 <= len(source_lines):
        prev = source_lines[lineno - 2]
        stripped = prev.strip()
        if stripped.startswith("#:"):
            return stripped[2:].strip()
    return ""


def extract_default(item: ast.AnnAssign | ast.Assign) -> str:
    """Extract default value from an AST node."""
    value = item.value if isinstance(item, ast.AnnAssign) else item.value
    if value is None:
        return "—"
    if isinstance(value, ast.Constant):
        v = value.value
        if v is Ellipsis:
            return "(required)"
        if isinstance(v, str):
            return f'"{v}"'
        if v is True:
            return "True"
        if v is False:
            return "False"
        if v is None:
            return "None"
        return str(v)
    if isinstance(value, ast.Call):
        fn = ast.unparse(value.func)
        if fn == "Field":
            for kw in value.keywords:
                if kw.arg == "default":
                    dv = ast.unparse(kw.value)
                    return dv if dv != "..." else "(required)"
            return "—"
        if "Field" in fn:
            return "—"
        return "(complex)"
    if isinstance(value, ast.Name):
        vn = value.id
        if vn == "Ellipsis":
            return "(required)"
        if vn in ("True", "False", "None"):
            return vn
        return vn
    if isinstance(value, ast.List):
        return ast.unparse(value)
    if isinstance(value, ast.Dict):
        return "(dict)"
    if isinstance(value, ast.Set):
        return ast.unparse(value)
    if isinstance(value, ast.Tuple):
        return ast.unparse(value)
    if isinstance(value, ast.Attribute):
        return ast.unparse(value).replace("'", "\\'")
    if isinstance(value, ast.UnaryOp):
        return ast.unparse(value)
    if isinstance(value, ast.BinOp):
        return ast.unparse(value)
    return "(complex)"


def resolve_config_class(type_str: str, classes: dict[str, ConfigClass]) -> str | None:
    """Resolve a type annotation string to a known config class name."""
    stripped = type_str.strip().replace('"', "").replace("'", "")
    if stripped in classes:
        return stripped

    for part in re.split(r"\s*\|\s*", stripped):
        part = part.strip()
        if part in classes:
            return part
        if part.endswith("Config") and part in classes:
            return part

    return None


def get_base_names(bases: list[ast.expr]) -> list[str]:
    """Get base class names from AST bases list."""
    result = []
    for base in bases:
        if isinstance(base, ast.Name):
            result.append(base.id)
        elif isinstance(base, ast.Attribute) or isinstance(base, ast.Subscript):
            result.append(ast.unparse(base))
    return result


def scan_config_classes_in_package(pkg_src: Path) -> dict[str, ConfigClass]:
    """Scan config files within a specific package and return Config classes keyed by name."""
    pkg_classes: dict[str, ConfigClass] = {}
    seen: set[tuple[Path, str]] = set()

    for pyfile in pkg_src.rglob("*.py"):
        if any(p in EXCLUDED_DIRS for p in pyfile.parts):
            continue
        # Scan every module: config classes live outside config.py too
        # (e.g. graphql's RateLimitConfig in security/rate_limit.py) — a
        # filename filter silently mis-resolves same-name cross-package refs.

        try:
            text = pyfile.read_text(encoding="utf-8")
            source_lines = text.splitlines()
            tree = ast.parse(text, filename=str(pyfile))
        except (SyntaxError, Exception):
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            name = node.name
            if not name.endswith("Config"):
                continue

            if (pyfile, name) in seen:
                continue
            seen.add((pyfile, name))

            bases = get_base_names(node.bases)
            fields: list[ConfigField] = []
            config_section: str | None = None

            for item in node.body:
                # config_section: ClassVar[str] = "<section>" marks a root
                if (
                    isinstance(item, ast.AnnAssign)
                    and isinstance(item.target, ast.Name)
                    and item.target.id == "config_section"
                    and isinstance(item.value, ast.Constant)
                    and isinstance(item.value.value, str)
                ):
                    config_section = item.value.value

            for item in node.body:
                if isinstance(item, ast.Expr):
                    continue
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    fname = item.target.id
                    if fname.startswith("_") or fname.startswith("model_"):
                        continue
                    if item.annotation:
                        ann_str = ast.dump(item.annotation)
                        if "ClassVar" in ann_str or "ConfigDict" in ann_str:
                            continue

                    type_str = ast.unparse(item.annotation) if item.annotation else "?"
                    if type_str == "?":
                        continue
                    default = extract_default(item)
                    desc = extract_field_description(item.value)
                    if not desc:
                        desc = extract_field_comments_from_source(
                            source_lines, item.lineno, item.end_lineno or item.lineno
                        )
                    fields.append(ConfigField(name=fname, type_str=type_str, default=default, description=desc))

                elif isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            fname = target.id
                            if fname.startswith("_") or fname.startswith("model_"):
                                continue
                            type_str = ast.unparse(item.value)[:40] if item.value else "?"
                            if type_str == "?" and fname == "model_config":
                                continue
                            default = extract_default(item)
                            desc = extract_field_description(item.value)
                            if not desc:
                                desc = extract_field_comments_from_source(
                                    source_lines, item.lineno, item.end_lineno or item.lineno
                                )
                            fields.append(ConfigField(name=fname, type_str=type_str, default=default, description=desc))

            pkg_classes[name] = ConfigClass(
                name=name, file_path=pyfile, bases=bases, fields=fields, config_section=config_section
            )

    return pkg_classes


__all__ = ["CONFIG_BASE_CLASSES"]
