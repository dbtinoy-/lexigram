#!/usr/bin/env python3
"""
Generate REF_ENV_VARS.md — authoritative environment variable registry.

Scans all config.py files to build the nested config class hierarchy,
then derives env var names from the field path (not class names).
"""

from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dev.core.package_inventory import discover_package_paths

REPO_ROOT = Path.cwd()

EXCLUDED_DIRS = {"__pycache__", ".egg-info", ".git", "node_modules", ".mypy_cache", ".ruff_cache", ".pytest_cache", "templates"}

# Regex for direct env var access
DIRECT_ENV_RE = re.compile(
    r'(?:os\.environ\.get|os\.getenv|environ\.get|getenv)\s*\(\s*["\'](LEX_[A-Z0-9_]+)["\']'
)

# ENV_PREFIX or env_prefix constant
ENV_PREFIX_RE = re.compile(r'(?:ENV_PREFIX|env_prefix)\s*[=:]\s*["\'](LEX_[A-Z0-9_]+)["\']')

# Classes considered "config roots" — base classes for config models
CONFIG_BASE_CLASSES = {"BaseConfig", "BaseDomainConfig"}


def _md(val: str) -> str:
    """Escape pipe characters that would break markdown table columns."""
    return val.replace("|", "\\|")


class ConfigField:
    def __init__(
        self,
        name: str,
        type_str: str,
        default: str = "—",
        is_config: bool = False,
        config_class: str | None = None,
        description: str = "",
    ):
        self.name = name
        self.type_str = type_str
        self.default = default
        self.is_config = is_config
        self.config_class = config_class
        self.description = description


class ConfigClass:
    def __init__(self, name: str, file_path: Path, bases: list[str], fields: list[ConfigField]):
        self.name = name
        self.file_path = file_path
        self.bases = bases
        self.fields = fields


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
        if "config" not in str(pyfile).lower() and pyfile.stem != "constants":
            continue

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

            pkg_classes[name] = ConfigClass(name=name, file_path=pyfile, bases=bases, fields=fields)

    return pkg_classes


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate REF_ENV_VARS.md")
    parser.add_argument("--all", action="store_true", help="Write generated docs to repo root (publish mode)")
    args = parser.parse_args()

    all_pkg_srcs = discover_packages(include_all=args.all)
    total_pkg_classes = 0

    env_prefixes = find_env_prefixes()
    print(f"Env prefixes: {len(env_prefixes)}")
    for p, pf in sorted(env_prefixes.items()):
        print(f"  {p}: {pf}")

    pkg_entries: dict[str, list[dict]] = defaultdict(list)

    # Process each package independently to avoid cross-package name collisions
    for pkg_src in all_pkg_srcs:
        pkg_name = pkg_src.parent.name

        # Scan config classes in this package only
        pkg_classes = scan_config_classes_in_package(pkg_src)
        total_pkg_classes += len(pkg_classes)

        if not pkg_classes:
            continue

        # Build within-package child reference map
        within_child: dict[str, bool] = {}
        for name in pkg_classes:
            is_child = False
            for other_name, other_cls in pkg_classes.items():
                if other_name == name:
                    continue
                for f in other_cls.fields:
                    if name in f.type_str.replace('"', "").replace("'", ""):
                        is_child = True
                        break
                if is_child:
                    break
            within_child[name] = is_child

        # Find all files that actually contain Config classes in this package
        config_files = {cls.file_path for cls in pkg_classes.values()}
        for cfg_file in sorted(config_files):
            try:
                text = cfg_file.read_text(encoding="utf-8")
                tree = ast.parse(text, filename=str(cfg_file))
            except (SyntaxError, Exception):
                continue

            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                if not node.name.endswith("Config"):
                    continue
                if node.name not in pkg_classes:
                    continue

                cls = pkg_classes[node.name]
                used_as_child = within_child.get(node.name, False)
                has_base_config = any(b in CONFIG_BASE_CLASSES for b in cls.bases)

                # BaseConfig subclasses are ALWAYS roots, even if referenced as children
                if used_as_child and not has_base_config:
                    continue

                # Root config must: have BaseConfig base, have empty bases, or have config children
                has_empty_bases = len(cls.bases) == 0
                has_config_children = any(
                    resolve_config_class(f.type_str, pkg_classes) for f in cls.fields
                )

                if not (has_base_config or has_empty_bases or has_config_children):
                    continue

                prefix = env_prefixes.get(pkg_name, f"LEX_{pkg_name.replace('lexigram-', '').upper().replace('-', '_')}__")
                field_paths = build_field_paths(cls, pkg_classes)

                for type_str, field, file_path, dotted in field_paths:
                    upper_path = dotted.upper().replace(".", "__")
                    env_var = f"{prefix}{upper_path}"
                    source = f"{Path(file_path).relative_to(REPO_ROOT)}:{node.name}.{dotted}"
                    if len(source) > 100:
                        source = source[:55] + "..." + source[-40:]

                    pkg_entries[pkg_name].append({
                        "env_var": env_var,
                        "type": type_str,
                        "default": field.default,
                        "description": field.description,
                        "source": source,
                    })

    direct_entries = scan_direct_env_vars()
    for e in direct_entries:
        pkg_entries[e["package"]].append(e)

    print(f"\nTotal config classes across all packages: {total_pkg_classes}")

    # Deduplicate within each package
    deduped: dict[str, list[dict]] = {}
    for pkg, entries in pkg_entries.items():
        seen: set[str] = set()
        unique: list[dict] = []
        for e in sorted(entries, key=lambda x: x["env_var"]):
            if e["env_var"] not in seen:
                seen.add(e["env_var"])
                unique.append(e)
        deduped[pkg] = unique

    total_unique = sum(len(e) for e in deduped.values())
    print(f"\nTotal unique env vars: {total_unique}")

    # Check for packages not covered
    all_src_pkgs = {s.parent.name for s in discover_packages()}
    covered_pkgs = set(deduped.keys())
    missing = all_src_pkgs - covered_pkgs
    if missing:
        print(f"  Packages with NO env vars: {', '.join(sorted(missing))}")

    # --- Generate markdown ---
    lines: list[str] = []
    lines.append("# REF_ENV_VARS.md — Lexigram Framework Environment Variables")
    lines.append("")
    lines.append(f"**Date:** {datetime.now(UTC).strftime('%Y-%m-%d')}")
    lines.append(f"**Total entries:** {total_unique}")
    lines.append(f"**Packages:** {len(deduped)}")
    lines.append("")
    lines.append("> Generated by scanning config class fields and tracing nested config hierarchies.")
    lines.append("")
    lines.append("---")

    # Duplicate analysis
    all_vars: dict[str, list[str]] = defaultdict(list)
    for pkg, entries in deduped.items():
        for e in entries:
            all_vars[e["env_var"]].append(pkg)

    dupes = {v: pkgs for v, pkgs in all_vars.items() if len(pkgs) > 1}
    if dupes:
        lines.append("")
        lines.append("## Duplicate Analysis")
        lines.append("")
        lines.append("| Env Var | Occurrences | Packages |")
        lines.append("|---------|-------------|----------|")
        for var in sorted(dupes.keys()):
            pkgs_str = ", ".join(sorted(dupes[var]))
            lines.append(f"| `{var}` | {len(dupes[var])} | {pkgs_str} |")
        lines.append("")
        lines.append("---")
        lines.append("")

    # --- Quality analysis ---
    total_direct = sum(1 for pkg_es in deduped.values() for e in pkg_es if e.get("note"))
    total_empty_desc = sum(1 for pkg_es in deduped.values() for e in pkg_es if not e.get("description"))
    total_complex = sum(1 for pkg_es in deduped.values() for e in pkg_es if "(complex)" in e.get("default", ""))
    if total_direct or total_empty_desc or total_complex or missing:
        lines.append("## Analysis")
        lines.append("")
        if total_direct:
            lines.append(f"- **Direct env access vars**: {total_direct} — accessed via `os.environ.get()` outside config classes")
        if total_empty_desc:
            lines.append(f"- **Missing descriptions**: {total_empty_desc} of {total_unique} ({total_empty_desc * 100 // total_unique}%)")
        if total_complex:
            lines.append(f"- **Complex defaults**: {total_complex} — default values that could not be statically resolved")
        if missing:
            lines.append(f"- **Packages with NO env vars**: {', '.join(sorted(missing))}")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## Package Registry")
    lines.append("")

    sorted_pkgs = sorted(deduped.keys(), key=package_sort_key)
    for pkg in sorted_pkgs:
        entries = deduped[pkg]
        lines.append(f"### `{pkg}` ({len(entries)} vars)")
        lines.append("")
        lines.append("| Env Var | Type | Default | Description | Source |")
        lines.append("|---------|------|---------|-------------|--------|")
        for e in entries:
            src = e.get("source", "")
            desc = e.get("description", "") or ""
            if len(desc) > 80:
                desc = desc[:77] + "..."
            desc = desc or "—"
            var_type = _md(e["type"])
            default = _md(e["default"])
            desc = _md(desc)
            src = _md(src)
            note = e.get("note", "")
            lines.append(f"| `{e['env_var']}` | {var_type} | {default} | {desc} | `{src}{note}` |")
        lines.append("")

    refs_dir = REPO_ROOT / "docs/lexigram-docs/reference" if not args.all else REPO_ROOT
    refs_dir.mkdir(parents=True, exist_ok=True)
    output_path = refs_dir / "REF_ENV_VARS.md"
    output_path.write_text("\n".join(lines) + "\n")
    print(f"\n✅ Generated {output_path}")


if __name__ == "__main__":
    main()
