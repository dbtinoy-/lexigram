"""Structural and import-boundary rules for the Lexigram rule catalog."""

from __future__ import annotations

import ast

from dev.core.rules_catalog.types import (
    ALLOWED_CROSS_EXTENSION_IMPORTS,
    _finding,
    RuleCatalogContext,
    RuleFinding,
    RuleSeverity,
    RuleSourceFile,
)


def _detect_init_no_logic(
    source_file: RuleSourceFile,
    _context: RuleCatalogContext,
) -> tuple[RuleFinding, ...]:
    """Flag class and function declarations inside __init__.py modules.

    Excludes magic methods (__all__, __getattr__, __dir__, etc.) which are
    legitimate in __init__.py for package-level customization.
    """

    if source_file.path.name != "__init__.py":
        return ()

    findings: list[RuleFinding] = []
    for node in source_file.tree.body:
        if not isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        # Exclude magic methods (dunder functions) — these are legitimate in __init__.py
        if node.name.startswith("__") and node.name.endswith("__"):
            continue
        findings.append(
            _finding(
                source_file,
                rule_id="init-no-logic",
                severity=RuleSeverity.IMPORTANT,
                owner="framework",
                rationale="__init__.py files should contain exports only so package entry points stay declarative.",
                line=node.lineno,
                message=f"{source_file.relative_path.as_posix()} declares {node.__class__.__name__} '{node.name}' in __init__.py.",
            )
        )
    return tuple(findings)


def _detect_relative_imports(
    source_file: RuleSourceFile,
    _context: RuleCatalogContext,
) -> tuple[RuleFinding, ...]:
    """Flag relative imports so modules stick to absolute import paths."""

    findings: list[RuleFinding] = []
    for node in ast.walk(source_file.tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level <= 0:
            continue
        findings.append(
            _finding(
                source_file,
                rule_id="import-absolute-only",
                severity=RuleSeverity.IMPORTANT,
                owner="framework",
                rationale="Relative imports obscure package boundaries and are disallowed across the framework.",
                line=node.lineno,
                message=f"{source_file.relative_path.as_posix()} uses a relative import; replace it with an absolute import.",
            )
        )
    return tuple(findings)


def _detect_cross_extension_imports(
    source_file: RuleSourceFile,
    context: RuleCatalogContext,
) -> tuple[RuleFinding, ...]:
    """Flag forbidden direct imports across Lexigram package boundaries."""

    if not (
        _is_extension_package(source_file.package_name)
        or source_file.package_name == "lexigram"
    ):
        return ()
    if source_file.package_name == "lexigram-testing":
        return ()

    findings: list[RuleFinding] = []
    seen_pairs: set[tuple[int, str]] = set()
    for node, imported_module in _iter_import_targets(source_file.tree):
        owner = context.resolve_import_owner(imported_module)
        if owner is None or owner == source_file.package_name:
            continue
        if owner == "lexigram-ui":
            # Shared UI primitive layer: every package's admin pages
            # compose lexigram-ui atoms (sanctioned for admin/web).
            continue
        if source_file.package_name == "lexigram":
            if not _is_extension_package(owner):
                continue
            import_description = f"core lexigram directly imports {owner}"
        else:
            if not _is_extension_package(owner):
                continue
            if owner in ALLOWED_CROSS_EXTENSION_IMPORTS.get(
                source_file.package_name, frozenset()
            ):
                continue
            import_description = f"{source_file.package_name} directly imports {owner}"
        marker = (getattr(node, "lineno", 0), owner)
        if marker in seen_pairs:
            continue
        seen_pairs.add(marker)
        findings.append(
            _finding(
                source_file,
                rule_id="no-cross-extension-import",
                severity=RuleSeverity.CRITICAL,
                owner="architecture",
                rationale="Core and extension packages must respect the declared dependency hierarchy instead of importing across forbidden boundaries.",
                line=getattr(node, "lineno", 0),
                message=(
                    f"{import_description} via {imported_module}; "
                    "route cross-package behavior through contracts, providers, or container bindings instead."
                ),
            )
        )
    return tuple(findings)


def _detect_pseudo_enum(
    source_file: RuleSourceFile,
    _context: RuleCatalogContext,
) -> tuple[RuleFinding, ...]:
    """Flag classes that behave like enums without inheriting from Enum."""

    findings: list[RuleFinding] = []
    for node in ast.walk(source_file.tree):
        if not isinstance(node, ast.ClassDef):
            continue
        if any(_is_enum_base(base) for base in node.bases):
            continue
        enum_members = _pseudo_enum_members(node)
        if len(enum_members) < 2:
            continue
        # Exclude classes that have methods (e.g., __init__, properties, async methods)
        # These are likely services or utility classes, not enums
        has_methods = any(
            isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef))
            for stmt in node.body
        )
        if has_methods:
            continue
        findings.append(
            _finding(
                source_file,
                rule_id="enum-must-use-enum",
                severity=RuleSeverity.MINOR,
                owner="framework",
                rationale="Enumeration-like classes must inherit from enum.Enum for type safety and consistency.",
                line=node.lineno,
                message=(
                    f"{source_file.relative_path.as_posix()} defines pseudo-enum class '{node.name}' with "
                    f"{len(enum_members)} constant members; inherit from Enum instead."
                ),
            )
        )
    return tuple(findings)


def _iter_import_targets(tree: ast.Module) -> tuple[tuple[ast.AST, str], ...]:
    """Yield import targets, skipping lazy and guarded imports.

    Imports inside function/class bodies, ``try`` blocks, or any ``if``
    guard (including ``TYPE_CHECKING``) are deferred/conditional loads
    and are not part of the package's static dependency surface.
    """

    targets: list[tuple[ast.AST, str]] = []

    def _walk(node: ast.AST, *, guarded: bool = False) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if guarded:
                continue
            if isinstance(child, ast.Import):
                for alias in child.names:
                    targets.append((child, alias.name))
                continue
            if isinstance(child, ast.ImportFrom) and child.level == 0 and child.module:
                targets.append((child, child.module))
                continue
            if isinstance(child, (ast.Try, ast.If)):
                _walk(child, guarded=True)
                continue
            _walk(child)

    _walk(tree)
    return tuple(targets)


def _is_extension_package(package_name: str) -> bool:
    """Return whether a top-level Lexigram package is an extension package."""

    return package_name.startswith("lexigram-") and package_name != "lexigram-contracts"


def _is_enum_base(base: ast.expr) -> bool:
    """Return whether a class base expression refers to Enum or any Enum subclass."""

    if isinstance(base, ast.Name):
        return base.id in ("Enum", "StrEnum", "IntEnum", "Flag", "IntFlag")
    if isinstance(base, ast.Attribute):
        return base.attr in ("Enum", "StrEnum", "IntEnum", "Flag", "IntFlag")
    if isinstance(base, ast.Subscript):
        return _is_enum_base(base.value)
    return False


def _pseudo_enum_members(node: ast.ClassDef) -> tuple[str, ...]:
    """Return uppercase constant member names from a pseudo-enum class body."""

    members: list[str] = []
    for statement in node.body:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name) and _is_constant_member_name(target.id):
                    members.append(target.id)
            continue
        if isinstance(statement, ast.AnnAssign) and isinstance(
            statement.target, ast.Name
        ):
            if _is_constant_member_name(statement.target.id):
                members.append(statement.target.id)
    return tuple(members)


def _is_constant_member_name(name: str) -> bool:
    """Return whether a class attribute name looks like an enum member."""

    return name.isupper() and any(character.isalpha() for character in name)
