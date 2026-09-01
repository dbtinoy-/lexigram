"""Post-processing for generated SQL seeder modules.

The framework lexigram-sql ``seeder`` generator emits timestamps with
``datetime.now(timezone.utc)`` (the deprecated spelling under modern
``datetime`` rules; ruff UP017 prefers the ``datetime.UTC`` alias) and an
import block that normalises differently across generator versions. We
rewrite both so the module is lint-clean deterministically, without relying
on ruff being available at generation time.

When the wired entity carries authored ``seed_data`` (JSON row strings from
the Seed Data screen), the generator's sample ``SEED_DATA`` list is replaced.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from lexigram.serialization import loads_str
from lexigram.serialization.backends.json import JSONDecodeError


@dataclass(frozen=True, slots=True)
class SeederReconcileResult:
    """Outcome of reconciling a generated seeder module."""

    text: str


def _py_literal(value: object) -> str:
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        return repr(value)
    if isinstance(value, list):
        inner = ", ".join(_py_literal(v) for v in value)
        return f"[{inner}]"
    if isinstance(value, dict):
        parts = [f"{str(k)!r}: {_py_literal(v)}" for k, v in value.items()]
        return "{" + ", ".join(parts) + "}"
    return repr(str(value))


def _render_seed_data(rows: tuple[str, ...]) -> str:
    dicts: list[str] = []
    for raw in rows:
        try:
            parsed = loads_str(raw)
        except JSONDecodeError:
            continue
        if not isinstance(parsed, dict):
            continue
        parsed.setdefault("created_at", "__NOW__")
        parsed.setdefault("updated_at", "__NOW__")
        body = (
            _py_literal(parsed)
            .replace("'__NOW__'", "datetime.now(UTC)")
            .replace('"__NOW__"', "datetime.now(UTC)")
        )
        dicts.append(f"    {body},")
    inner = "\n".join(dicts) if dicts else ""
    return f"SEED_DATA: list[dict[str, object]] = [\n{inner}\n]\n"


_SEED_BLOCK = re.compile(
    r"SEED_DATA: list\[dict\[str, object\]\] = \[.*?\]\n",
    re.DOTALL,
)


def reconcile_seeder(
    text: str,
    seed_data: tuple[str, ...] = (),
) -> SeederReconcileResult:
    """Normalise a generated seeder module to a lint-clean form.

    Args:
        text: The generated seeder module source.
        seed_data: JSON-encoded row dicts from :class:`EntityConfig`. Empty
            keeps the generator sample row.

    Returns:
        A :class:`SeederReconcileResult` with the reconciled source.
    """
    text = text.replace(
        "from datetime import datetime, timezone",
        "from datetime import UTC, datetime",
    )
    text = text.replace("datetime.now(timezone.utc)", "datetime.now(UTC)")
    text = text.replace(
        "from lexigram.sql import SimpleUnitOfWork\n\n\nSEED_DATA",
        "from lexigram.sql import SimpleUnitOfWork\n\nSEED_DATA",
    )
    if seed_data:
        rendered = _render_seed_data(seed_data)
        text, n = _SEED_BLOCK.subn(rendered, text, count=1)
        if n == 0:
            text = text + "\n" + rendered
    return SeederReconcileResult(text=text)
