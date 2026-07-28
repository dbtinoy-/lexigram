from __future__ import annotations

from importlib.util import find_spec
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable


class MissingOptionalDependencyError(ImportError):
    _code: str = "LEX_ERR_RAG_017"


def ensure_packages(
    packages: Iterable[str],
    hint: str | None = None,
) -> dict[str, Any | None]:
    """Ensure the given packages are importable."""
    missing: list[str] = []
    found: dict[str, Any | None] = {}

    for pkg in packages:
        spec = find_spec(pkg)
        if spec is None:
            missing.append(pkg)
            found[pkg] = None
        else:
            found[pkg] = None

    if missing:
        names = ", ".join(missing)
        hint_msg = f" Install with: {hint}" if hint else ""
        raise MissingOptionalDependencyError(
            f"Missing optional dependencies: {names}.{hint_msg}",
        )

    return found
