from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import re

from scripts.audit.generators.base import MarkdownAuditGenerator
from scripts.audit.generators.non_config_env_sources import NON_CONFIG_ENV_SOURCES
from scripts.core.package_inventory import discover_package_paths


@dataclass(frozen=True, slots=True)
class FieldDef:
    """Parsed field definition from a config class."""

    name: str
    type_annotation: str
    default_value: str
    description: str
    nested_target: str | None


@dataclass(frozen=True, slots=True)
class ConfigClassDef:
    """Parsed config class metadata."""

    name: str
    env_prefix: str | None
    env_nested_delimiter: str | None
    has_env_prefix_key: bool
    fields: tuple[FieldDef, ...]


@dataclass(frozen=True, slots=True)
class EnvVarDef:
    """A fully expanded environment-variable row."""

    package: str
    env_var: str
    type_annotation: str
    default_value: str
    description: str
    source_file: str
    source_class: str
    source_field_path: str


class EnvVarsAuditGenerator(MarkdownAuditGenerator):
    """Generate a markdown inventory of environment variables."""

    name = "env_vars"
    description = "Generate AUDIT_ENV_VARS.md from config models and known non-config reads."
    output_file = "AUDIT_ENV_VARS.md"
    env_vars = tuple(source.env_var for source in NON_CONFIG_ENV_SOURCES)

    def render_markdown(self, *, root: Path) -> str:
        """Render the environment-variable audit markdown."""

        all_mode = getattr(self, "_all_mode", False)
        packages = None if all_mode else tuple(
            str(p.relative_to(root)) for p in self.iter_package_roots(root=root)
        )
        return generate_markdown(scan_all_configs(root, packages=packages))


def get_package_prefix(package_path: Path) -> str | None:
    """Resolve a package ENV_PREFIX constant when one is defined."""

    package_name = package_path.name
    module_path = package_name.removeprefix("lexigram-").replace("-", "/")
    possible_paths = (
        package_path / "src" / "lexigram" / module_path / "constants.py",
        package_path / "src" / "lexigram" / module_path / "core" / "constants.py",
        package_path / "constants.py",
        package_path / "src" / "lexigram" / "constants.py",
        package_path / "src" / "lexigram" / "config" / "constants.py",
    )

    for constants_path in possible_paths:
        if not constants_path.is_file():
            continue
        content = constants_path.read_text(encoding="utf-8")
        match = re.search(r'ENV_PREFIX:\s*str\s*=\s*["\'](.+?)["\']', content)
        if match:
            return match.group(1)
    return None


def _resolve_string_expr(node: ast.AST | None, constants: dict[str, str]) -> str | None:
    """Resolve a string-like AST expression for config constants."""

    if node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return constants.get(node.id)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _resolve_string_expr(node.left, constants)
        right = _resolve_string_expr(node.right, constants)
        if left is not None and right is not None:
            return left + right
    return None


def _type_to_string(node: ast.AST | None) -> str:
    """Convert an annotation AST node into a readable type string."""

    if node is None:
        return "Any"
    try:
        return ast.unparse(node)
    except (AttributeError, ValueError):
        if isinstance(node, ast.Name):
            return node.id
        return "Any"


def _extract_default(node: ast.AST | None) -> str:
    """Extract a human-readable default value from AST."""

    if node is None:
        return "(required)"
    if isinstance(node, ast.Constant):
        if isinstance(node.value, str):
            return f'"{node.value}"'
        return str(node.value)
    if isinstance(node, ast.List):
        return "[]" if not node.elts else "[...]"
    if isinstance(node, ast.Dict):
        return "{}" if not node.keys else "{...}"
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Call):
        func_name = _type_to_string(node.func)
        if func_name.endswith("Field") or func_name == "Field":
            for keyword in node.keywords:
                if keyword.arg == "default":
                    return _extract_default(keyword.value)
            if node.args:
                return _extract_default(node.args[0])
            return "(required)"
        return f"{func_name}(...)"
    return "(complex)"


def _extract_description(field_call: ast.Call) -> str:
    """Extract Field(description=...) text when present."""

    for keyword in field_call.keywords:
        if keyword.arg != "description":
            continue
        if isinstance(keyword.value, ast.Constant) and isinstance(keyword.value.value, str):
            return keyword.value.value
    return ""


def _extract_model_config(
    node: ast.AST | None,
    constants: dict[str, str],
) -> tuple[str | None, str | None, bool]:
    """Extract env metadata from a model_config assignment."""

    if node is None:
        return None, None, False

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "cast":
        if len(node.args) >= 2 and isinstance(node.args[1], ast.Dict):
            env_prefix: str | None = None
            env_delimiter: str | None = None
            has_env_prefix_key = False
            for key, value in zip(node.args[1].keys, node.args[1].values, strict=False):
                if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                    continue
                if key.value == "env_prefix":
                    env_prefix = _resolve_string_expr(value, constants)
                    has_env_prefix_key = True
                if key.value == "env_nested_delimiter":
                    env_delimiter = _resolve_string_expr(value, constants)
            return env_prefix, env_delimiter, has_env_prefix_key
        return None, None, False

    if not isinstance(node, ast.Call):
        return None, None, False

    env_prefix = None
    env_delimiter = None
    has_env_prefix_key = False
    for keyword in node.keywords:
        if keyword.arg == "env_prefix":
            env_prefix = _resolve_string_expr(keyword.value, constants)
            has_env_prefix_key = True
        if keyword.arg == "env_nested_delimiter":
            env_delimiter = _resolve_string_expr(keyword.value, constants)
    return env_prefix, env_delimiter, has_env_prefix_key


def _nested_target(annotation: ast.AST | None, local_class_names: set[str]) -> str | None:
    """Return a nested config class target if the annotation references one."""

    if annotation is None:
        return None
    if isinstance(annotation, ast.Name):
        return annotation.id if annotation.id in local_class_names else None
    if isinstance(annotation, ast.Attribute):
        return annotation.attr if annotation.attr in local_class_names else None
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        return _nested_target(annotation.left, local_class_names) or _nested_target(
            annotation.right,
            local_class_names,
        )
    return None


def _parse_config_file(
    config_file: Path,
    package_fallback_prefix: str | None,
    workspace_root: Path,
) -> tuple[dict[str, ConfigClassDef], list[EnvVarDef]]:
    """Parse a config file and expand its environment-variable definitions."""

    content = config_file.read_text(encoding="utf-8")
    tree = ast.parse(content)

    constants: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                value = _resolve_string_expr(node.value, constants)
                if value is not None:
                    constants[target.id] = value
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            value = _resolve_string_expr(node.value, constants)
            if value is not None:
                constants[node.target.id] = value

    class_nodes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    local_class_names = {node.name for node in class_nodes}
    classes: dict[str, ConfigClassDef] = {}

    for class_node in class_nodes:
        env_prefix: str | None = None
        env_nested_delimiter: str | None = None
        has_env_prefix_key = False
        fields: list[FieldDef] = []

        for statement in class_node.body:
            if isinstance(statement, ast.AnnAssign) and isinstance(statement.target, ast.Name):
                field_name = statement.target.id
                if field_name in {"model_config", "__pydantic_extra__", "config_section"}:
                    if field_name == "model_config":
                        env_prefix, env_nested_delimiter, has_env_prefix_key = _extract_model_config(
                            statement.value,
                            constants,
                        )
                    continue
                if field_name.startswith("_") or field_name.isupper():
                    continue

                type_annotation = _type_to_string(statement.annotation)
                if "ClassVar[" in type_annotation:
                    continue
                description = ""
                if isinstance(statement.value, ast.Call):
                    func_name = _type_to_string(statement.value.func)
                    if func_name.endswith("Field") or func_name == "Field":
                        description = _extract_description(statement.value)
                fields.append(
                    FieldDef(
                        name=field_name,
                        type_annotation=type_annotation,
                        default_value=_extract_default(statement.value),
                        description=description,
                        nested_target=_nested_target(statement.annotation, local_class_names),
                    )
                )

            if isinstance(statement, ast.Assign):
                for target in statement.targets:
                    if isinstance(target, ast.Name) and target.id == "model_config":
                        env_prefix, env_nested_delimiter, has_env_prefix_key = _extract_model_config(
                            statement.value,
                            constants,
                        )

        classes[class_node.name] = ConfigClassDef(
            name=class_node.name,
            env_prefix=env_prefix,
            env_nested_delimiter=env_nested_delimiter,
            has_env_prefix_key=has_env_prefix_key,
            fields=tuple(fields),
        )

    package_name = next(
        (part for part in config_file.parts if part.startswith("lexigram-")),
        "lexigram",
    )

    def expand_from_root(root_class: ConfigClassDef) -> list[EnvVarDef]:
        prefix = root_class.env_prefix or package_fallback_prefix
        if not prefix:
            return []

        delimiter = root_class.env_nested_delimiter or "__"
        rows: list[EnvVarDef] = []

        def walk(
            class_name: str,
            path: tuple[str, ...],
            visited: set[tuple[str, tuple[str, ...]]],
        ) -> None:
            state = (class_name, path)
            if state in visited:
                return
            visited.add(state)

            class_def = classes.get(class_name)
            if class_def is None:
                return

            for field in class_def.fields:
                field_path = (*path, field.name)
                scoped_key = delimiter.join(part.upper() for part in field_path)
                if field.nested_target and field.nested_target in classes:
                    walk(field.nested_target, field_path, visited)
                    continue

                rows.append(
                    EnvVarDef(
                        package=package_name,
                        env_var=f"{prefix}{scoped_key}",
                        type_annotation=field.type_annotation,
                        default_value=field.default_value,
                        description=field.description,
                        source_file=str(config_file.relative_to(workspace_root)),
                        source_class=class_name,
                        source_field_path=".".join(field_path),
                    )
                )

        walk(root_class.name, (), set())
        return rows

    env_vars: list[EnvVarDef] = []
    for class_def in classes.values():
        if class_def.has_env_prefix_key:
            env_vars.extend(expand_from_root(class_def))

    return classes, env_vars


def scan_all_configs(root: Path, packages: tuple[str, ...] | None = None) -> dict[str, list[EnvVarDef]]:
    """Scan package config.py files and group environment variables by package."""

    grouped: dict[str, list[EnvVarDef]] = {}
    for rel in discover_package_paths(root):
        package_path = root / rel
        if packages is not None and str(rel) not in packages:
            continue

        package_prefix = get_package_prefix(package_path)
        config_files = [
            path
            for path in package_path.glob("**/config.py")
            if "__pycache__" not in path.parts and "examples" not in path.parts
        ]
        for config_file in config_files:
            _, rows = _parse_config_file(config_file, package_prefix, root)
            for row in rows:
                grouped.setdefault(row.package, []).append(row)

    for package, rows in grouped.items():
        grouped[package] = sorted(
            rows,
            key=lambda row: (row.env_var, row.source_class, row.source_field_path),
        )
    return grouped


def _escape_markdown(text: str, *, max_length: int = 120) -> str:
    """Escape markdown table content and cap length."""

    return text.replace("\n", " ").replace("|", " \\|")[:max_length]


def generate_markdown(packages: dict[str, list[EnvVarDef]]) -> str:
    """Generate AUDIT_ENV_VARS.md content."""

    all_rows = [row for rows in packages.values() for row in rows]
    env_var_counts: dict[str, int] = {}
    for row in all_rows:
        env_var_counts[row.env_var] = env_var_counts.get(row.env_var, 0) + 1

    duplicate_items = sorted(
        (item for item in env_var_counts.items() if item[1] > 1),
        key=lambda item: (item[0], item[1]),
    )

    markdown = """# AUDIT_ENV_VARS.md — Lexigram Framework Environment Variables

> **Source**: Extracted from `config.py` root settings classes and known non-config env reads.

---

## Summary

"""
    markdown += f"- Packages scanned: {len(packages)}\n"
    markdown += f"- Documented env var entries: {len(all_rows)}\n"
    markdown += f"- Unique env var names: {len(env_var_counts)}\n"
    markdown += f"- Duplicate env var names: {len(duplicate_items)}\n"
    markdown += f"- Intentional non-config env sources: {len(NON_CONFIG_ENV_SOURCES)}\n\n"

    if duplicate_items:
        markdown += "## Duplicate Analysis\n\n"
        markdown += "| Env Var | Occurrences |\n"
        markdown += "|---------|-------------|\n"
        for env_var, count in duplicate_items:
            markdown += f"| `{env_var}` | {count} |\n"
        markdown += "\n"

    markdown += "## Package Registry\n\n"
    for package in sorted(packages):
        markdown += f"### `{package}`\n\n"
        markdown += "| Env Var | Type | Default | Description | Source |\n"
        markdown += "|---------|------|---------|-------------|--------|\n"
        for row in packages[package]:
            source = f"{row.source_file}:{row.source_class}.{row.source_field_path}"
            markdown += (
                f"| `{row.env_var}` | {_escape_markdown(row.type_annotation, max_length=80)} "
                f"| {_escape_markdown(row.default_value, max_length=60)} "
                f"| {_escape_markdown(row.description)} "
                f"| `{_escape_markdown(source, max_length=100)}` |\n"
            )
        markdown += "\n"

    markdown += "## Non-Config ENV Sources\n\n"
    markdown += "| Env Var | Source | Rationale |\n"
    markdown += "|---------|--------|-----------|\n"
    for source in NON_CONFIG_ENV_SOURCES:
        markdown += (
            f"| `{source.env_var}` | `{_escape_markdown(source.source_file)}` "
            f"| {_escape_markdown(source.rationale, max_length=160)} |\n"
        )
    markdown += "\n---\n\n"
    markdown += "*This document is auto-generated. Do not edit manually.*\n"
    return markdown
