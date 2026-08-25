"""Guard against new unbounded third-party pins in workspace member manifests.

A specifier like ``starlette>=0.28.0`` declares only a lower bound and lets
the dependency float to any future major version. This check fails CI when a
member adds an unbounded pin that is not already covered by the committed
baseline (``scripts/dep_pins_baseline.json``), keeping the existing debt
visible while preventing it from growing.

Regenerate the baseline deliberately after review:

    uv run python scripts/check_dep_pins.py --write-baseline

Note:
    Third-party is defined as any distribution outside the ``lexigram`` /
    ``lexigram-*`` workspace members.
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))

import argparse
import json  # noqa: TID251 — standalone CI guard; runs before workspace serialization
from pathlib import Path
import sys
import tomllib

from packaging.requirements import Requirement


from dev.core.package_inventory import discover_package_paths

BOUNDED_OPERATORS = frozenset(("<", "<=", "==", "===", "~="))


def load_pyproject(path: Path) -> dict[str, object]:
    """Load a pyproject.toml file as a dictionary."""

    with path.open("rb") as handle:
        return tomllib.load(handle)


def iter_member_pyprojects(
    root: Path,
) -> tuple[tuple[str, Path, dict[str, object]], ...]:
    """Return ``(name, pyproject_path, data)`` for every workspace member."""

    found: list[tuple[str, Path, dict[str, object]]] = []
    for rel in discover_package_paths(root):
        pyproject_path = root / rel / "pyproject.toml"
        data = load_pyproject(pyproject_path)
        found.append((rel.name, pyproject_path, data))

    return tuple(found)


def _is_third_party(name: str) -> bool:
    """Return True for distributions outside the lexigram workspace."""

    return name != "lexigram" and not name.startswith("lexigram-")


def _unbounded_specs(specs: list[str]) -> list[tuple[str, str]]:
    """Extract unbounded third-party specs from a dependency requirement list."""

    unbounded: list[tuple[str, str]] = []
    for entry in specs:
        try:
            requirement = Requirement(entry)
        except ValueError:
            continue
        if not _is_third_party(requirement.name):
            continue
        if not requirement.specifier:
            continue
        operators = {specifier.operator for specifier in requirement.specifier}
        if not operators.intersection(BOUNDED_OPERATORS):
            unbounded.append((requirement.name, str(requirement.specifier)))
    return sorted(unbounded)


def scan_unbounded_pins(
    root: Path,
) -> tuple[dict[str, list[tuple[str, str]]], list[Path]]:
    """Scan member manifests for unbounded third-party pins.

    Args:
        root: Workspace root directory.

    Returns:
        Mapping of package name to its unbounded ``(dependency, specifier)``
        pairs, and the list of member pyproject files that were scanned.
    """

    pinned: dict[str, list[tuple[str, str]]] = {}
    scanned: list[Path] = []
    for name, pyproject_path, data in iter_member_pyprojects(root):
        scanned.append(pyproject_path)
        project = data.get("project")
        if not isinstance(project, dict):
            continue
        dependency_lists: list[tuple[str, list[str]]] = []
        direct = project.get("dependencies")
        if isinstance(direct, list):
            dependency_lists.append(("dependencies", direct))
        optional = project.get("optional-dependencies")
        if isinstance(optional, dict):
            for key, specs in optional.items():
                if isinstance(specs, list):
                    dependency_lists.append((f"optional[{key}]", specs))
        for _section, specs in dependency_lists:
            unbounded = _unbounded_specs(specs)
            if unbounded:
                pinned.setdefault(name, []).extend(unbounded)
    return pinned, scanned


def load_baseline(path: Path) -> set[tuple[str, str]]:
    """Load the baseline set of accepted ``(package, dependency)`` keys."""

    if not path.exists():
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    baseline: set[tuple[str, str]] = set()
    for package, entries in payload.items():
        for entry in entries:
            baseline.add((package, entry[0]))
    return baseline


def write_baseline(path: Path, pins: dict[str, list[tuple[str, str]]]) -> None:
    """Write the current unbounded pins as the committed baseline."""

    payload = {
        package: [list(pair) for pair in pairs] for package, pairs in pins.items()
    }
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    """Run the dependency pin guard."""

    parser = argparse.ArgumentParser(prog="check_dep_pins")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Workspace root containing lexigram-* member directories",
    )
    baseline_default = Path(__file__).resolve().with_name("dep_pins_baseline.json")
    parser.add_argument(
        "--baseline",
        type=Path,
        default=baseline_default,
        help=f"Baseline file (default: {baseline_default.name})",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Overwrite the baseline with the current state and exit 0",
    )
    args = parser.parse_args(argv)

    pins, scanned = scan_unbounded_pins(args.root)
    total = sum(len(pairs) for pairs in pins.values())

    if args.write_baseline:
        write_baseline(args.baseline, pins)
        print(f"wrote baseline with {total} unbounded pins to {args.baseline}")
        return 0

    baseline = load_baseline(args.baseline)
    violations: list[tuple[str, str, str]] = []
    for package, pairs in pins.items():
        for dependency, specifier in pairs:
            if (package, dependency) not in baseline:
                violations.append((package, dependency, specifier))

    for package, dependency, specifier in sorted(violations):
        print(f"unbounded pin: {package} -> {dependency}{specifier}")
    print(
        f"scanned {len(scanned)} member manifests, "
        f"{total} unbounded pins (baseline-covered: {total - len(violations)})"
    )
    if violations:
        print(
            "run 'python scripts/check_dep_pins.py --write-baseline' after reviewing",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
