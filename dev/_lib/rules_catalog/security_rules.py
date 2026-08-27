"""Security rules for the Lexigram rule catalog."""

from __future__ import annotations

import ast
import re

from dev._lib.rules_catalog.types import (
    _finding,
    RuleCatalogContext,
    RuleFinding,
    RuleSeverity,
    RuleSourceFile,
)

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
            targets: tuple[ast.expr, ...] | list[ast.expr] = (node.target,)
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


def _nodes_containing(tree: ast.Module, node: ast.Call) -> list[ast.AST]:
    """Return all ancestors (and the node itself) that enclose *node*."""

    node_line = node.lineno
    return [
        candidate
        for candidate in ast.walk(tree)
        if getattr(candidate, "lineno", -1) >= 0
        and getattr(candidate, "end_lineno", -1) >= 0
        and getattr(candidate, "lineno", 0) <= node_line <= getattr(candidate, "end_lineno", 0)
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


def _list_contains_none(node: ast.expr | None) -> bool:
    """Return whether an expression is a literal list containing 'none'."""

    if not isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return False
    return any(
        isinstance(element, ast.Constant) and element.value == "none"
        for element in node.elts
    )


def _dict_disables_verification(node: ast.expr | None) -> bool:
    """Return whether a literal dict sets verify_signature to False."""

    if not isinstance(node, ast.Dict):
        return False
    for key, value in zip(node.keys, node.values, strict=True):
        if not isinstance(key, ast.Constant) or key.value != "verify_signature":
            continue
        if isinstance(value, ast.Constant) and value.value is False:
            return True
    return False
