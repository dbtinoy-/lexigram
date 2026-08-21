"""Snapshot-check the method surface of every runtime_checkable Protocol.

When a Protocol in lexigram-contracts gains or loses a member, every stub and
fake implementing it goes stale silently (isinstance flips at runtime — see
TaskProviderProtocol/build_idempotency_manager). This tool makes protocol
drift a deliberate, reviewed diff:

    python check_protocol_surface.py             # check against manifest
    python check_protocol_surface.py --update    # regenerate manifest

Usage:
    python check_protocol_surface.py [--root PATH] [--update]

Exit codes: 0 = manifest matches (or --update), 1 = drift or missing manifest.
"""

from __future__ import annotations

import argparse
import inspect
import json
import logging
from pathlib import Path
import sys

MANIFEST = Path(__file__).parent / "protocol_surface.json"
CONTRACTS_PKG = "lexigram.contracts"


def _runtime_protocols() -> dict[str, list[str]]:
    """Map ``qualname -> sorted member names`` for runtime_checkable Protocols."""
    logging.disable(logging.CRITICAL)
    import importlib
    import pkgutil

    package = importlib.import_module(CONTRACTS_PKG)
    for module_info in pkgutil.walk_packages(
        package.__path__, prefix=CONTRACTS_PKG + "."
    ):
        try:
            importlib.import_module(module_info.name)
        except Exception:  # noqa: BLE001 — unimportable modules carry no protocols
            continue

    surface: dict[str, list[str]] = {}
    for module in list(sys.modules.values()):
        name = getattr(module, "__name__", "")
        if not name.startswith(CONTRACTS_PKG):
            continue
        module_file = getattr(module, "__file__", None) or ""
        if "lexigram-contracts" not in module_file:
            continue  # imported-in protocols belong to their home package
        for value in vars(module).values():
            if (
                not inspect.isclass(value)
                or not getattr(value, "__module__", "").startswith(CONTRACTS_PKG)
                or not getattr(value, "_is_runtime_protocol", False)
            ):
                continue
            members: list[str] = []
            for member in vars(value):
                if member.startswith("_"):
                    continue
                static = inspect.getattr_static(value, member)
                if isinstance(static, (property, staticmethod, classmethod)) or callable(
                    static
                ):
                    members.append(member)
            surface[f"{value.__module__}.{value.__qualname__}"] = sorted(members)
    return surface


def _load_manifest() -> dict[str, list[str]]:
    if not MANIFEST.exists():
        return {}
    return json.loads(MANIFEST.read_text())


def _write_manifest(surface: dict[str, list[str]]) -> None:
    MANIFEST.write_text(json.dumps(surface, indent=2, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repo root (informational)")
    parser.add_argument(
        "--update", action="store_true", help="rewrite the manifest and exit 0"
    )
    args = parser.parse_args()

    surface = _runtime_protocols()
    if args.update:
        _write_manifest(surface)
        print(f"wrote {len(surface)} protocols to {MANIFEST.name}")
        return 0

    manifest = _load_manifest()
    if not manifest:
        print("manifest missing — run with --update to create it", file=sys.stderr)
        return 1

    drift = 0
    for qualname in sorted(set(manifest) | set(surface)):
        old = set(manifest.get(qualname, []))
        new = set(surface.get(qualname, []))
        for member in sorted(new - old):
            print(f"{qualname}.{member} ADDED")
            drift += 1
        for member in sorted(old - new):
            print(f"{qualname}.{member} REMOVED")
            drift += 1
        if qualname not in surface and qualname in manifest:
            print(f"{qualname} REMOVED PROTOCOL")
            drift += 1
    print(f"{drift} protocol surface change(s)")
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
