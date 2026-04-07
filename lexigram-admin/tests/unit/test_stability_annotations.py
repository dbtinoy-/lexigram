"""Verify stability-tier docstring annotations on key public modules."""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path

import pytest

PACKAGE = "lexigram.admin"

# Map of importable path → expected marker in docstring
EXPECTED_MARKERS: dict[str, str] = {
    # Module-level docstring markers
    "lexigram.admin.resources.base": ".. stability:: stable",
    "lexigram.admin.actions.base": ".. stability:: stable",
    "lexigram.admin.pages.base": ".. experimental::",
    "lexigram.admin.clusters.base": ".. experimental::",
    "lexigram.admin.relations.manager_ext": ".. experimental::",
    # Class-level docstring markers
    "lexigram.admin.data.data_source.IDataSource": ".. stability:: stable",
    "lexigram.admin.schema.base.SchemaField": ".. stability:: stable",
}


def _resolve_source_file(import_path: str) -> Path | None:
    """Get the source file for a module or class."""
    parts = import_path.split(".")
    # Walk the package chain to find the module
    for importer, modname, ispkg in pkgutil.walk_packages(
        path=[str(Path(__file__).parents[3] / "src")],
        prefix="",
    ):
        if modname == ".".join(parts[:2]) or modname == ".".join(parts[:3]):
            spec = importer.find_spec(modname)
            if spec and spec.origin:
                return Path(spec.origin)
    return None


def _module_has_marker(import_path: str, marker: str) -> bool:
    """Check if a module's source contains the marker."""
    parts = import_path.split(".")
    if "." not in import_path:
        return False
    # Class-level markers: 5+ parts (e.g. "lexigram.admin.data.data_source.IDataSource")
    if len(parts) >= 5:
        module_path = ".".join(parts[:-1])
        class_name = parts[-1]
        try:
            mod = importlib.import_module(module_path)
        except (ImportError, ValueError):
            return False
        cls = getattr(mod, class_name, None)
        if cls is None:
            return False
        doc = cls.__doc__ or ""
        return marker in doc
    # For module-level markers (4 parts: lexigram.admin.actions.base)
    try:
        mod = importlib.import_module(import_path)
    except (ImportError, ValueError):
        return False
    doc = mod.__doc__ or ""
    return marker in doc


class TestStabilityAnnotations:
    """Verify that key public modules carry the expected stability markers."""

    @pytest.mark.parametrize(
        "import_path,marker",
        [(k, v) for k, v in EXPECTED_MARKERS.items()],
        ids=list(EXPECTED_MARKERS.keys()),
    )
    def test_marker_present(self, import_path: str, marker: str) -> None:
        """Each annotated target must contain the expected marker string."""
        assert _module_has_marker(import_path, marker), (
            f"Marker {marker!r} not found in {import_path}"
        )
