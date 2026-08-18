from __future__ import annotations

import ast
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import re


class RuleSeverity(str, Enum):
    """Severity level for a Lexigram architectural rule finding."""

    CRITICAL = "critical"
    IMPORTANT = "important"
    MINOR = "minor"


SEVERITY_ORDER = {
    RuleSeverity.CRITICAL: 0,
    RuleSeverity.IMPORTANT: 1,
    RuleSeverity.MINOR: 2,
}

ALLOWED_CROSS_EXTENSION_IMPORTS: dict[str, frozenset[str]] = {
    "lexigram-admin": frozenset(
        {
            "lexigram-auth",
            "lexigram-cache",
            "lexigram-features",
            "lexigram-resilience",
            "lexigram-ui",
        }
    ),
    "lexigram-web": frozenset({"lexigram-ui"}),
    "lexigram-events": frozenset({"lexigram-resilience"}),
    "lexigram-tasks": frozenset({"lexigram-resilience"}),
    "lexigram-monitor": frozenset({"lexigram-tasks"}),
    "lexigram-multimedia": frozenset(
        {
            "lexigram-multimedia-beat",
            "lexigram-multimedia-image",
            "lexigram-multimedia-interpolate",
            "lexigram-multimedia-music",
            "lexigram-multimedia-tts",
            "lexigram-multimedia-upscale",
            "lexigram-multimedia-video",
            "lexigram-tasks",
        }
    ),
    "lexigram-ai-governance": frozenset({"lexigram-tasks"}),
    "lexigram-ai": frozenset(
        {
            "lexigram-vector",
            "lexigram-ai-agents",
            "lexigram-ai-feedback",
            "lexigram-ai-governance",
            "lexigram-ai-guard",
            "lexigram-ai-llm",
            "lexigram-ai-mcp",
            "lexigram-ai-memory",
            "lexigram-ai-observability",
            "lexigram-ai-prompt",
            "lexigram-ai-rag",
            "lexigram-ai-session",
            "lexigram-ai-skills",
            "lexigram-ai-workers",
        }
    ),
}


@dataclass(frozen=True, slots=True)
class RuleFinding:
    """Single rule violation captured from static Lexigram analysis."""

    rule_id: str
    severity: RuleSeverity
    owner: str
    rationale: str
    package_name: str
    path: Path
    line: int
    message: str


@dataclass(frozen=True, slots=True)
class RuleSourceFile:
    """Python source file prepared for rule evaluation."""

    package_name: str
    package_root: Path
    path: Path
    relative_path: Path
    module_name: str
    tree: ast.Module


@dataclass(frozen=True, slots=True)
class RuleCatalogContext:
    """Shared lookup context available to every rule detector."""

    root: Path
    module_owners: Mapping[str, frozenset[str]]

    def resolve_import_owner(self, module_name: str) -> str | None:
        """Resolve the owning package for a Python import path."""

        best_match: tuple[str, frozenset[str]] | None = None
        for prefix, owners in self.module_owners.items():
            if module_name != prefix and not module_name.startswith(f"{prefix}."):
                continue
            if best_match is None or len(prefix) > len(best_match[0]):
                best_match = (prefix, owners)
        if best_match is None:
            return None
        if len(best_match[1]) != 1:
            return None
        return next(iter(best_match[1]))


@dataclass(frozen=True, slots=True)
class RuleDefinition:
    """Metadata and detector callback for one Lexigram rule."""

    rule_id: str
    severity: RuleSeverity
    owner: str
    rationale: str
    detector: Callable[[RuleSourceFile, RuleCatalogContext], tuple[RuleFinding, ...]]


def build_rules_catalog() -> tuple[RuleDefinition, ...]:
    """Return the static catalog of Lexigram architectural rules."""

    return (
        RuleDefinition(
            rule_id="init-no-logic",
            severity=RuleSeverity.IMPORTANT,
            owner="framework",
            rationale="__init__.py files should contain exports only so package entry points stay declarative.",
            detector=_detect_init_no_logic,
        ),
        RuleDefinition(
            rule_id="import-absolute-only",
            severity=RuleSeverity.IMPORTANT,
            owner="framework",
            rationale="Relative imports obscure package boundaries and are disallowed across the framework.",
            detector=_detect_relative_imports,
        ),
        RuleDefinition(
            rule_id="no-cross-extension-import",
            severity=RuleSeverity.CRITICAL,
            owner="architecture",
            rationale="Core and extension packages must respect the declared dependency hierarchy instead of importing across forbidden boundaries.",
            detector=_detect_cross_extension_imports,
        ),
        RuleDefinition(
            rule_id="enum-must-use-enum",
            severity=RuleSeverity.MINOR,
            owner="framework",
            rationale="Enumeration-like classes must inherit from enum.Enum for type safety and consistency.",
            detector=_detect_pseudo_enum,
        ),
        RuleDefinition(
            rule_id="sec-tls-verify-disabled",
            severity=RuleSeverity.IMPORTANT,
            owner="security",
            rationale="TLS certificate verification must stay enabled for every outbound client; verify=False or an unverified context defeats transport encryption.",
            detector=_detect_tls_verify_disabled,
        ),
        RuleDefinition(
            rule_id="sec-hardcoded-secret",
            severity=RuleSeverity.IMPORTANT,
            owner="security",
            rationale="Long literal secrets assigned to secret-named variables must come from configuration, not source code.",
            detector=_detect_hardcoded_secret,
        ),
        RuleDefinition(
            rule_id="sec-cors-wildcard-credentials",
            severity=RuleSeverity.IMPORTANT,
            owner="security",
            rationale="A wildcard CORS origin combined with allow_credentials exposes authenticated endpoints to any origin.",
            detector=_detect_cors_wildcard_credentials,
        ),
        RuleDefinition(
            rule_id="sec-jwt-verification-disabled",
            severity=RuleSeverity.CRITICAL,
            owner="security",
            rationale="Signing JWT verification must never be disabled or pinned to the 'none' algorithm.",
            detector=_detect_jwt_verification_disabled,
        ),
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
        marker = (node.lineno, owner)
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
                line=node.lineno,
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


def _finding(
    source_file: RuleSourceFile,
    *,
    rule_id: str,
    severity: RuleSeverity,
    owner: str,
    rationale: str,
    line: int,
    message: str,
) -> RuleFinding:
    """Create a normalized rule finding for one source location."""

    return RuleFinding(
        rule_id=rule_id,
        severity=severity,
        owner=owner,
        rationale=rationale,
        package_name=source_file.package_name,
        path=source_file.relative_path,
        line=line,
        message=message,
    )


def make_rule_finding(
    *,
    rule_id: str,
    severity: RuleSeverity,
    owner: str,
    rationale: str,
    package_name: str,
    path: Path,
    line: int,
    message: str,
) -> RuleFinding:
    """Build a rule finding outside the AST-backed detector flow."""

    return RuleFinding(
        rule_id=rule_id,
        severity=severity,
        owner=owner,
        rationale=rationale,
        package_name=package_name,
        path=path,
        line=line,
        message=message,
    )


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


_SECRET_NAME_RE = re.compile(
    r"(?i)(password|passwd|secret|api_key|apikey|private_key|auth_token)"
)
_PLACEHOLDER_RE = re.compile(
    r"(?i)(change|example|your-|xxx|placeholder|lorem|dummy|test|fixture)"
)


def _detect_tls_verify_disabled(
    source_file: RuleSourceFile,
    _context: RuleCatalogContext,
) -> tuple[RuleFinding, ...]:
    """Flag calls that disable TLS certificate verification."""

    findings: list[RuleFinding] = []
    for node in ast.walk(source_file.tree):
        if not isinstance(node, ast.Call):
            continue
        if _call_name(node) == "_create_unverified_context":
            findings.append(
                _finding(
                    source_file,
                    rule_id="sec-tls-verify-disabled",
                    severity=RuleSeverity.IMPORTANT,
                    owner="security",
                    rationale="TLS certificate verification must stay enabled for every outbound client; verify=False or an unverified context defeats transport encryption.",
                    line=node.lineno,
                    message=f"{source_file.relative_path.as_posix()} disables TLS verification via ssl._create_unverified_context.",
                )
            )
        for keyword in node.keywords:
            if keyword.arg != "verify" or not isinstance(keyword.value, ast.Constant):
                continue
            if keyword.value.value is False or keyword.value.value == 0:
                findings.append(
                    _finding(
                        source_file,
                        rule_id="sec-tls-verify-disabled",
                        severity=RuleSeverity.IMPORTANT,
                        owner="security",
                        rationale="TLS certificate verification must stay enabled for every outbound client; verify=False or an unverified context defeats transport encryption.",
                        line=node.lineno,
                        message=f"{source_file.relative_path.as_posix()} disables TLS verification with verify={keyword.value.value!r}.",
                    )
                )
    return tuple(findings)


def _detect_hardcoded_secret(
    source_file: RuleSourceFile,
    _context: RuleCatalogContext,
) -> tuple[RuleFinding, ...]:
    """Flag long literal strings assigned to secret-named module/class variables.

    Test files, prose/error-message values, dummy placeholders, and `*_name`
    references (config keys holding a secret's name, not its value) are
    skipped to keep the signal high where ruff S105/S106 are noisy.
    """

    if "tests" in source_file.path.parts or source_file.path.name.startswith("test_"):
        return ()
    findings: list[RuleFinding] = []
    for node in ast.walk(source_file.tree):
        if isinstance(node, ast.AnnAssign):
            targets = (node.target,)
            value = node.value
        elif isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        else:
            continue
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        secret = value.value
        if len(secret) < 16 or _PLACEHOLDER_RE.search(secret) or " " in secret:
            continue
        for target in targets:
            if not isinstance(target, ast.Name) or not _SECRET_NAME_RE.search(target.id):
                continue
            if target.id.upper().endswith("_NAME") or "DUMMY" in target.id.upper():
                continue
            if secret == target.id.lower():
                continue
            findings.append(
                _finding(
                    source_file,
                    rule_id="sec-hardcoded-secret",
                    severity=RuleSeverity.IMPORTANT,
                    owner="security",
                    rationale="Long literal secrets assigned to secret-named variables must come from configuration, not source code.",
                    line=node.lineno,
                    message=f"{source_file.relative_path.as_posix()} assigns a {len(secret)}-character literal to '{target.id}'; move it to configuration.",
                )
            )
    return tuple(findings)


def _detect_cors_wildcard_credentials(
    source_file: RuleSourceFile,
    _context: RuleCatalogContext,
) -> tuple[RuleFinding, ...]:
    """Flag CORS configuration combining a '*' origin list with credentials."""

    findings: list[RuleFinding] = []
    for node in ast.walk(source_file.tree):
        if not isinstance(node, ast.Call):
            continue
        origins: ast.expr | None = None
        credentials: ast.expr | None = None
        for keyword in node.keywords:
            if keyword.arg == "allow_origins":
                origins = keyword.value
            elif keyword.arg == "allow_credentials":
                credentials = keyword.value
        if origins is None or credentials is None:
            continue
        if not _is_wildcard_origin_list(origins) or not _is_true_constant(credentials):
            continue
        findings.append(
            _finding(
                source_file,
                rule_id="sec-cors-wildcard-credentials",
                severity=RuleSeverity.IMPORTANT,
                owner="security",
                rationale="A wildcard CORS origin combined with allow_credentials exposes authenticated endpoints to any origin.",
                line=node.lineno,
                message=f"{source_file.relative_path.as_posix()} sets allow_origins=['*'] with allow_credentials=True.",
            )
        )
    return tuple(findings)


def _detect_jwt_verification_disabled(
    source_file: RuleSourceFile,
    _context: RuleCatalogContext,
) -> tuple[RuleFinding, ...]:
    """Flag JWT verification disabled via algorithms=['none'] or verify_signature=False.

    The ``options={"verify_signature": False}`` decode pattern is only
    flagged when it could feed an authentication decision.  Decoding a
    token without verification to extract metadata (expiry TTL, subject
    for audit hooks, revocation targeting after the signature was already
    verified upstream) is a standard PyJWT idiom and is not flagged.
    Explicitly gated dev-only opt-in paths are reported as IMPORTANT
    instead of CRITICAL.
    """

    findings: list[RuleFinding] = []
    for node in ast.walk(source_file.tree):
        if not isinstance(node, ast.Call):
            continue
        if _call_name(node).lower() not in ("decode", "verify_token"):
            continue
        if _list_contains_none(_keyword_value(node, "algorithms")):
            findings.append(
                _finding(
                    source_file,
                    rule_id="sec-jwt-verification-disabled",
                    severity=RuleSeverity.CRITICAL,
                    owner="security",
                    rationale="Signing JWT verification must never be disabled or pinned to the 'none' algorithm.",
                    line=node.lineno,
                    message=f"{source_file.relative_path.as_posix()} accepts the unsigned 'none' JWT algorithm.",
                )
            )
            continue
        if not _dict_disables_verification(_keyword_value(node, "options")):
            continue
        if _is_benign_unverified_decode(source_file.tree, node):
            continue
        severity = (
            RuleSeverity.IMPORTANT
            if _is_gated_dev_opt_in(source_file.tree, node)
            else RuleSeverity.CRITICAL
        )
        findings.append(
            _finding(
                source_file,
                rule_id="sec-jwt-verification-disabled",
                severity=severity,
                owner="security",
                rationale="Signing JWT verification must never be disabled or pinned to the 'none' algorithm.",
                line=node.lineno,
                message=(
                    f"{source_file.relative_path.as_posix()} disables JWT signature "
                    f"verification via options{_dev_gate_note(source_file.tree, node)}."
                ),
            )
        )
    return tuple(findings)


def _keyword_value(node: ast.Call, name: str) -> ast.expr | None:
    """Return the value of the named keyword argument, or ``None``."""

    for keyword in node.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


def _nodes_containing(tree: ast.Module, node: ast.AST) -> list[ast.AST]:
    """Return all ancestors (and the node itself) that enclose *node*."""

    return [
        candidate
        for candidate in ast.walk(tree)
        if getattr(candidate, "lineno", -1) >= 0
        and getattr(candidate, "end_lineno", -1) >= 0
        and candidate.lineno <= node.lineno <= candidate.end_lineno
    ]


def _is_benign_unverified_decode(tree: ast.Module, node: ast.Call) -> bool:
    """Return whether the decode result is used for metadata extraction only.

    Two signals mark the standard safe idiom: the result is bound to a
    variable whose name contains "unverified", or the decode sits inside a
    revoke/logout/blacklist/refresh routine where the signature has either
    already been verified or is irrelevant to the operation.
    """

    for enclosing in _nodes_containing(tree, node):
        if isinstance(enclosing, ast.Assign):
            for target in enclosing.targets:
                if isinstance(target, ast.Name) and "unverified" in target.id.lower():
                    return True
        if isinstance(enclosing, (ast.FunctionDef, ast.AsyncFunctionDef)):
            name = enclosing.name.lower()
            if any(marker in name for marker in ("revoke", "logout", "blacklist", "refresh")):
                return True
    return False


def _is_gated_dev_opt_in(tree: ast.Module, node: ast.Call) -> bool:
    """Return whether the decode is gated behind an explicit dev-only flag."""

    for enclosing in _nodes_containing(tree, node):
        if not isinstance(enclosing, ast.If):
            continue
        for child in ast.walk(enclosing.test):
            if not isinstance(child, ast.Attribute):
                continue
            attr = child.attr.lower()
            if "unverified" in attr and "dev" in attr:
                return True
    return False


def _dev_gate_note(tree: ast.Module, node: ast.Call) -> str:
    """Return a suffix noting an explicit dev-opt-in gate when present."""

    if _is_gated_dev_opt_in(tree, node):
        return " (explicit dev-only opt-in gate)"
    return ""


def _call_name(node: ast.Call) -> str:
    """Return the dotted function name for a call node."""

    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _is_wildcard_origin_list(node: ast.expr) -> bool:
    """Return whether an expression is a literal list/set/tuple containing '*'."""

    if not isinstance(node, (ast.List, ast.Set, ast.Tuple)):
        return False
    for element in node.elts:
        if isinstance(element, ast.Constant) and element.value == "*":
            return True
    return False


def _is_true_constant(node: ast.expr) -> bool:
    """Return whether an expression is the constant True."""

    return isinstance(node, ast.Constant) and node.value is True


def _list_contains_none(node: ast.expr) -> bool:
    """Return whether an expression is a literal list containing 'none'."""

    if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return False
    return any(
        isinstance(element, ast.Constant) and element.value == "none"
        for element in node.elts
    )


def _dict_disables_verification(node: ast.expr) -> bool:
    """Return whether a literal dict sets verify_signature to False."""

    if not isinstance(node, ast.Dict):
        return False
    for key, value in zip(node.keys, node.values, strict=True):
        if not isinstance(key, ast.Constant) or key.value != "verify_signature":
            continue
        if isinstance(value, ast.Constant) and value.value is False:
            return True
    return False
