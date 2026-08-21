"""Report config fields that no code in their own package reads.

Config classes are contracts; fields nothing consumes erode that contract
(first known case: EvaluationConfig.default_seed /
LEX_AI_EVALUATION__DEFAULT_SEED parses but has zero readers).

Coverage: every ``lexigram.*`` member the workspace env can import — the
merged namespace exposes core, packages, and experimental subtrees alike
(members extend ``lexigram.__path__`` via pkgutil.extend_path). Each class's
scan root is derived from its module ``__file__`` up to the enclosing ``src/``
directory, so ``.venv`` trees are never traversed.

ADVISORY: always exits 0 today. Promote to failing only after triaging the
known inventory.

Usage:
    python check_config_fields.py [--root PATH]
"""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import redirect_stdout
import inspect
import io
import logging
from pathlib import Path
import re
import sys

_SKIP_FIELDS = {"config_section"}


def _declared_fields(cls: type) -> list[str]:
    """Public instance field names of a dataclass-style config class."""
    fields: list[str] = []
    for name, annotation in getattr(cls, "__annotations__", {}).items():
        if name.startswith("_") or name in _SKIP_FIELDS:
            continue
        if isinstance(annotation, str) and annotation.startswith("ClassVar"):
            continue
        fields.append(name)
    return fields


def _package_src_of(module_file: str) -> str | None:
    """Return the enclosing ``.../src`` directory of a module file."""
    path = Path(module_file).resolve()
    for parent in path.parents:
        if parent.name == "src":
            return str(parent)
    return None


def _config_classes() -> list[tuple[object, str]]:
    """Collect ``(cls, package_src_dir)`` for *Config classes workspace-wide."""
    logging.disable(logging.CRITICAL)
    import importlib
    import pkgutil

    try:
        package = importlib.import_module("lexigram")
    except ImportError:
        return []
    # Import side effects (structlog lines) write to stdout; keep the report clean.
    with redirect_stdout(io.StringIO()):
        for module_info in pkgutil.walk_packages(package.__path__, prefix="lexigram."):
            if module_info.name.startswith("lexigram.testing"):
                continue  # test-support modules reference everything; pure noise
            try:
                importlib.import_module(module_info.name)
            except Exception:  # noqa: BLE001 — unimportable members carry no configs
                continue

    found: list[tuple[object, str]] = []
    seen: set[str] = set()
    src_roots: set[str] = set()
    for module in list(sys.modules.values()):
        name = getattr(module, "__name__", "")
        if not name.startswith("lexigram") or name.startswith(
            ("lexigram.testing", "lexigram.contracts")
        ):
            continue
        module_file = getattr(module, "__file__", None)
        if not module_file:
            continue
        pkg_src = _package_src_of(module_file)
        if pkg_src is None:
            continue
        for value in vars(module).values():
            if not (
                inspect.isclass(value)
                and value.__name__.endswith("Config")
                and getattr(value, "__module__", "").startswith("lexigram")
                and getattr(value, "__annotations__", None)
            ):
                continue
            qualname = f"{value.__module__}.{value.__qualname__}"
            if qualname in seen:
                continue
            seen.add(qualname)
            found.append((value, pkg_src))
            src_roots.add(pkg_src)
    return found, src_roots


_ATTR_REF = re.compile(r"\.(\w+)\b")
# getattr(cfg, "field"), cfg.get("field"), model_extra lookups by name
_STR_LOOKUP = re.compile(r"(?:getattr\s*\([^,)]+,|\.get\s*\()\s*[\'\"](\w+)[\'\"]")


def _build_usage_index(src_roots: set[str]) -> Counter[str]:
    """Count field references across every src tree once.

    Two reference shapes count as usage: direct attribute access (``.field``)
    and dynamic lookup by name (``getattr(cfg, "field")`` / ``cfg.get("field")``),
    which is how generic config plumbing consumes fields.
    """
    index: Counter[str] = Counter()
    for root in src_roots:
        for path in Path(root).rglob("*.py"):
            parts = path.parts
            if any(part == ".venv" for part in parts):
                continue
            text = path.read_text(errors="ignore")
            index.update(_ATTR_REF.findall(text))
            index.update(_STR_LOOKUP.findall(text))
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repo root")
    args = parser.parse_args()
    del args

    classes, src_roots = _config_classes()
    index = _build_usage_index(src_roots)
    unused: list[str] = []
    reported: set[tuple[str, str]] = set()
    for cls, _pkg_src in classes:
        for field in _declared_fields(cls):
            key = (f"{cls.__module__}.{cls.__name__}", field)
            if key in reported:
                continue
            reported.add(key)
            if index[field] == 0:
                unused.append(f"UNUSED {cls.__module__}.{cls.__name__}.{field}")

    for line in unused:
        print(line)
    print(f"{len(unused)} unread config field(s) — advisory only, always exits 0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
