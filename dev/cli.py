from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
import sys

from dev.audit.generators import build_audit_registry
from dev.audit.generators.base import AuditGeneratorProtocol, AuditRunResult
from dev.core.validation import (
    has_quality_evidence,
    has_tests_evidence,
    parse_rules_report_summary,
)

RULES_CRITICAL_THRESHOLD = 0


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level scripts CLI parser."""

    parser = argparse.ArgumentParser(prog="dev")
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit_parser = subparsers.add_parser("audit", help="Audit generator commands")
    audit_subparsers = audit_parser.add_subparsers(dest="audit_command", required=True)

    list_parser = audit_subparsers.add_parser("list", help="List available audits")
    list_parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Workspace root for path-sensitive generators",
    )

    run_parser = audit_subparsers.add_parser("run", help="Run an audit generator")
    run_parser.add_argument("name", help="Generator name or 'all'")
    run_parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Workspace root for path-sensitive generators",
    )
    run_parser.add_argument(
        "--all",
        action="store_true",
        help="Output to repo root instead of docs/audit",
    )

    validate_parser = audit_subparsers.add_parser(
        "validate",
        help="Validate registered audit generators",
    )
    validate_parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Directory containing the audit reports (defaults to docs/audit)",
    )
    validate_parser.add_argument(
        "--all",
        action="store_true",
        help="Validate reports at the workspace root instead of docs/audit",
    )

    return parser


def run_named_generator_cli(
    generator_name: str, argv: Sequence[str] | None = None
) -> int:
    """Run a named audit generator as a standalone adapter command."""

    parser = argparse.ArgumentParser(prog=f"scripts {generator_name}")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Workspace root for path-sensitive generators",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    generator = _get_registry().get(generator_name)
    if generator is None:
        print(f"unknown audit generator: {generator_name}", file=sys.stderr)
        return 1

    return _emit_run_result(generator.run(root=args.root))


def _get_registry():
    """Return a fresh registry of audit generators."""

    return build_audit_registry()


def _emit_run_result(result: AuditRunResult) -> int:
    """Print a generator run result and return an exit code."""

    stream = sys.stdout if result.success else sys.stderr
    print(f"{result.name}: {result.message}", file=stream)
    return 0 if result.success else 1


def _handle_audit_list(_root: Path | None) -> int:
    """List registered audit generators."""

    registry = _get_registry()
    print("name\tdescription")
    for name in registry.names():
        generator = registry.get(name)
        if generator is None:
            continue
        print(f"{generator.name}\t{generator.description}")
    return 0


def _run_single_generator(
    generator: AuditGeneratorProtocol,
    *,
    root: Path | None,
    all_mode: bool = False,
) -> int:
    """Run a single generator and emit its result."""

    return _emit_run_result(generator.run(root=root, all_mode=all_mode))


def _handle_audit_run(name: str, root: Path | None, all_mode: bool = False) -> int:
    """Run one or all registered audit generators."""

    registry = _get_registry()
    if name == "all":
        exit_code = 0
        for generator_name in registry.names():
            generator = registry.get(generator_name)
            if generator is None:
                continue
            exit_code |= _run_single_generator(generator, root=root, all_mode=all_mode)
        return exit_code

    generator = registry.get(name)
    if generator is None:
        print(f"unknown audit generator: {name}", file=sys.stderr)
        return 1
    return _run_single_generator(generator, root=root, all_mode=all_mode)


def _handle_audit_validate(root: Path | None, all_mode: bool = False) -> int:
    """Validate all registered generators through the registry."""

    registry = _get_registry()
    validated = 0
    exit_code = 0
    resolved_root = _resolve_root(root, all_mode=all_mode)
    for name in registry.names():
        generator = registry.get(name)
        if generator is None or not isinstance(generator, AuditGeneratorProtocol):
            print(f"invalid generator registration: {name}", file=sys.stderr)
            exit_code = 1
            continue
        if not generator.name or not generator.description or not generator.output_file:
            print(f"invalid generator metadata: {name}", file=sys.stderr)
            exit_code = 1
            continue

        result = generator.validate(root=root)
        if not result.success:
            print(f"{name}: {result.message}", file=sys.stderr)
            exit_code = 1
            continue

        report_path = resolved_root / generator.output_file
        if not report_path.is_file():
            print(f"missing required report: {generator.output_file}", file=sys.stderr)
            exit_code = 1
            continue

        report_text = report_path.read_text(encoding="utf-8")
        exit_code |= _validate_report_content(name=name, report_text=report_text)
        validated += 1

    if exit_code == 0:
        print(f"validated {validated} audit generator(s)")
    return exit_code


def _resolve_root(root: Path | None, *, all_mode: bool = False) -> Path:
    """Resolve the directory that holds the audit reports.

    Mirrors the generator output layout: reports are written under
    ``docs/audit/`` by default and at the workspace root in ``--all``
    mode. An explicit ``root`` always wins.

    Args:
        root: Explicit report directory from ``--root``, or ``None``.
        all_mode: Whether to resolve the workspace root instead of
            ``docs/audit``.

    Returns:
        The directory to validate reports against.
    """

    if root is not None:
        return root.resolve()
    repo_root = Path(__file__).resolve().parents[1]
    return repo_root if all_mode else repo_root / "docs/audit"


def _validate_report_content(*, name: str, report_text: str) -> int:
    """Validate strict report-content expectations for critical audit outputs."""

    exit_code = 0
    if name == "quality" and not has_quality_evidence(report_text):
        print("quality: missing required evidence", file=sys.stderr)
        exit_code = 1
    if name == "tests" and not has_tests_evidence(report_text):
        print("tests: missing required evidence", file=sys.stderr)
        exit_code = 1
    if name == "rules":
        rules_summary = parse_rules_report_summary(report_text)
        if rules_summary.coverage_status is False or rules_summary.missing_packages:
            print("rules: package coverage gaps detected", file=sys.stderr)
            exit_code = 1
        if rules_summary.critical > RULES_CRITICAL_THRESHOLD:
            print("rules: critical violations exceed threshold", file=sys.stderr)
            exit_code = 1
    return exit_code


def main(argv: Sequence[str] | None = None) -> int:
    """Run the scripts CLI and return an exit status code."""

    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "audit" and args.audit_command == "list":
        return _handle_audit_list(args.root)
    if args.command == "audit" and args.audit_command == "run":
        all_mode = getattr(args, "all", False)
        return _handle_audit_run(args.name, args.root, all_mode=all_mode)
    if args.command == "audit" and args.audit_command == "validate":
        return _handle_audit_validate(args.root, all_mode=getattr(args, "all", False))

    parser.error("unsupported command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
