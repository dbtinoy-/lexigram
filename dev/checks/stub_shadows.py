"""Fail when a class attribute resolves to a NotImplementedError stub that
shadows a real implementation later in its MRO.

The auth-controller split (commit 7bfb54c3) introduced typing stubs such as

    def generate_breadcrumbs(self, *crumbs, current=None):
        raise NotImplementedError

inside endpoint mixins. Because the mixins sat earlier in the MRO than
``AdminController`` (which owns the real implementations), every call raised
at runtime. This gate re-detects that shape anywhere in the workspace.

Usage:
    python check_stub_shadows.py [--root PATH]

Exit codes: 0 = clean, 1 = at least one shadow found.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import inspect
import logging
import pkgutil
import sys
import textwrap

ROOT_PACKAGES = ("lexigram",)


def _body_statements(tree: ast.Module) -> list[ast.stmt]:
    """Statements of the first function in *tree*, minus docstrings/``...``."""
    fn = next(
        (
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ),
        None,
    )
    if fn is None:
        return []
    return [
        statement
        for statement in fn.body
        if not (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
        )
    ]


def _is_stub(func: object) -> bool:
    """True when the body is exactly ``raise NotImplementedError``."""
    try:
        # getsource preserves the definition's original indentation; dedent
        # before parsing or module-level parse fails on class-body indent.
        source = textwrap.dedent(inspect.getsource(func))  # type: ignore[arg-type]
        tree = ast.parse(source)
    except (OSError, TypeError, SyntaxError):
        return False
    body = _body_statements(tree)
    return (
        len(body) == 1
        and isinstance(body[0], ast.Raise)
        and "NotImplementedError" in ast.dump(body[0])
    )


def _is_declaration(func: object) -> bool:
    """True for Protocol/ABC bodies: only ``...`` or a docstring."""
    try:
        source = textwrap.dedent(inspect.getsource(func))  # type: ignore[arg-type]
        tree = ast.parse(source)
    except (OSError, TypeError, SyntaxError):
        return False
    return not _body_statements(tree)


def _unwrap(attr: object) -> object:
    """Expose the callable behind properties and staticmethods."""
    return getattr(attr, "fget", getattr(attr, "__func__", attr))


def _import_workspace_packages() -> None:
    logging.disable(logging.CRITICAL)
    # Module import side effects (structlog lines) write to stdout; keep the
    # gate's report clean by swallowing everything emitted during discovery.
    # stderr is redirected too: scaffold templates shipped under
    # lexigram.cli.templates contain Jinja2 syntax and raise SyntaxError on
    # import — pkgutil.walk_packages would otherwise re-raise it and crash
    # the gate (see the onerror handler below).
    import contextlib
    import io

    def _ignore(name: str) -> None:
        # Unimportable modules are not shadows; template scaffolds (Jinja2
        # ``{{ }}`` syntax in .py files) and optional-dep modules land here.
        return None

    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
        io.StringIO()
    ):
        for name in ROOT_PACKAGES:
            try:
                package = importlib.import_module(name)
            except ImportError:
                continue
            for module in pkgutil.walk_packages(
                package.__path__, prefix=name + ".", onerror=_ignore
            ):
                try:
                    importlib.import_module(module.name)
                except Exception:  # noqa: BLE001 — unimportable modules are not shadows
                    continue


def _workspace_classes() -> set[type]:
    # Only classes *defined* in lexigram modules — re-exported stdlib/3rd-party
    # classes (e.g. ``from collections import Counter``) are out of scope.
    return {
        value
        for module in list(sys.modules.values())
        if getattr(module, "__name__", "").startswith("lexigram")
        for value in vars(module).values()
        if inspect.isclass(value)
        and getattr(value, "__module__", "").startswith("lexigram")
    }


def find_shadows() -> list[str]:
    """Return one report line per stub-shadow finding.

    A finding means the effective MRO resolution is a
    ``raise NotImplementedError`` stub while a later base carries a *real*
    implementation. Protocol/ABC declarations (``...`` bodies, abstracts) do
    not count as real — stubbing over them is ordinary abstract design.
    """

    _import_workspace_packages()
    findings: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for cls in _workspace_classes():
        try:
            mro = cls.__mro__
        except AttributeError:
            continue
        for name in dir(cls):
            if name.startswith("__"):
                continue
            owners = [candidate for candidate in mro if name in vars(candidate)]
            if len(owners) < 2:
                continue
            key = (cls.__module__, cls.__qualname__, name)
            if key in seen:
                continue
            seen.add(key)
            first_fn = _unwrap(vars(owners[0])[name])
            if not _is_stub(first_fn):
                continue
            real_owner = next(
                (
                    candidate
                    for candidate in owners[1:]
                    if not (
                        _is_stub(_unwrap(vars(candidate)[name]))
                        or _is_declaration(_unwrap(vars(candidate)[name]))
                    )
                ),
                None,
            )
            if real_owner is not None:
                findings.append(
                    f"{cls.__qualname__}.{name} -> stub in {owners[0].__name__} "
                    f"shadows real in {real_owner.__name__}"
                )
    return sorted(findings)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repo root (informational)")
    args = parser.parse_args()
    del args  # parity with sibling tools; scanning uses imported packages

    findings = find_shadows()
    for line in findings:
        print(line)
    print(f"{len(findings)} shadow finding(s)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
