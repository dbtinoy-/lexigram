"""Schema-version marker for admin SQL stores (roadmap R15).

Boot used to run every store's ``ensure_schema()`` sequentially —
~16 DDL statements per boot even when the schema was fully current.
``AdminSchemaMarker`` collapses the warm path to two statements: it
persists a fingerprint of the stores' DDL in ``admin_schema_markers``
and, when the stored fingerprint matches the build's
:data:`ADMIN_AUTH_SCHEMA_FINGERPRINT`, the boot loop skips the ensure
pass entirely and marks each store ready.

The fingerprint is a SHA-256 over every ``CREATE TABLE`` / ``CREATE
[UNIQUE] INDEX`` string literal in :data:`SCHEMA_SOURCE_MODULES`,
computed from source by :func:`compute_schema_fingerprint` (tests only —
never at boot). A staleness-guard test recomputes it so any DDL change
that forgets to update the constant fails CI with the new value, and an
updated constant automatically invalidates every deployment's stored
marker on upgrade.

Recovery: if the schema was mutated by hand (e.g. a table dropped) while
the marker says current, delete the marker row and restart::

    DELETE FROM admin_schema_markers WHERE component = 'admin.auth_stores';
"""

from __future__ import annotations

import ast
import hashlib
import importlib
import inspect
import re
from typing import TYPE_CHECKING

from lexigram.admin.sql_dialect import now_expr
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.data import DatabaseProviderProtocol

logger = get_logger(__name__)

__all__ = [
    "ADMIN_AUTH_SCHEMA_FINGERPRINT",
    "AUTH_STORES_COMPONENT",
    "SCHEMA_SOURCE_MODULES",
    "AdminSchemaMarker",
    "compute_schema_fingerprint",
]

#: Marker component key for the eight auth/RBAC stores ensured at boot.
AUTH_STORES_COMPONENT = "admin.auth_stores"

#: Modules whose DDL string literals define the auth-store schema.
SCHEMA_SOURCE_MODULES: tuple[str, ...] = (
    "lexigram.admin.auth.store.login_attempt_sql",
    "lexigram.admin.auth.store.lockout_sql",
    "lexigram.admin.auth.store.audit_log_sql",
    "lexigram.admin.auth.store.password_reset_token_sql",
    "lexigram.admin.auth.store.mfa_sql",
    "lexigram.admin.auth.store.email_verification_sql",
    "lexigram.admin.auth.store.email_otp_sql",
    "lexigram.admin.rbac.roles_sql",
)

#: SHA-256 of the normalized DDL literals in SCHEMA_SOURCE_MODULES.
#: When any store's DDL changes, the staleness-guard test
#: (tests/unit/test_schema_marker.py) fails and prints the new value —
#: update this constant, which invalidates existing markers on upgrade.
ADMIN_AUTH_SCHEMA_FINGERPRINT = (
    "600da05f5fc40d4556110fab98a22af370434a09602fc82a1991c3d596396b96"
)

_DDL_PATTERN = re.compile(
    r"CREATE\s+(?:TABLE|UNIQUE\s+INDEX|INDEX)\b", re.IGNORECASE
)

_TABLE = "admin_schema_markers"

_CREATE_MARKER_SQL = f"""
CREATE TABLE IF NOT EXISTS {_TABLE} (
    component   VARCHAR(64)  PRIMARY KEY,
    fingerprint VARCHAR(64)  NOT NULL,
    updated_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""


def _iter_string_literals(tree: ast.AST) -> list[str]:
    """Collect string constants, including f-string constant parts."""
    literals: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.append(node.value)
        elif isinstance(node, ast.JoinedStr):
            parts = [
                value.value
                for value in node.values
                if isinstance(value, ast.Constant) and isinstance(value.value, str)
            ]
            if parts:
                literals.append("".join(parts))
    return literals


def compute_schema_fingerprint(
    modules: tuple[str, ...] = SCHEMA_SOURCE_MODULES,
) -> str:
    """Compute the SHA-256 fingerprint of the stores' DDL literals.

    Parses each module's source with ``ast`` and hashes every string
    literal that contains a ``CREATE TABLE`` / ``CREATE [UNIQUE] INDEX``
    statement, with whitespace normalized so pure re-indentation does not
    change the fingerprint. Used by tests and upgrade tooling only —
    never called at boot.

    Args:
        modules: Dotted module names to scan.

    Returns:
        Hex-encoded SHA-256 digest of the sorted, normalized DDL.

    Raises:
        ValueError: If any module contributes no DDL literal (a scan that
            silently misses everything must never produce a "valid"
            fingerprint).
    """
    ddl: list[str] = []
    for module_name in modules:
        module = importlib.import_module(module_name)
        tree = ast.parse(inspect.getsource(module))
        found = [
            re.sub(r"\s+", " ", literal).strip()
            for literal in _iter_string_literals(tree)
            if _DDL_PATTERN.search(literal)
        ]
        if not found:
            msg = f"no DDL literals found in {module_name}"
            raise ValueError(msg)
        ddl.extend(found)
    payload = "\n".join(sorted(ddl))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AdminSchemaMarker:
    """Reads and writes per-component schema fingerprints.

    Both operations are single statements after the marker table exists;
    callers are expected to treat every failure as "marker unavailable"
    and fall back to the full ensure pass (fail-open on availability).
    """

    def __init__(self, db: DatabaseProviderProtocol) -> None:
        self._db = db
        self._table_ready = False

    async def _ensure_table(self) -> None:
        if self._table_ready:
            return
        await self._db.execute(_CREATE_MARKER_SQL, [])
        self._table_ready = True

    async def is_current(self, component: str, fingerprint: str) -> bool:
        """Return True when the stored fingerprint matches ``fingerprint``."""
        await self._ensure_table()
        result = await self._db.execute_query(
            f"SELECT fingerprint FROM {_TABLE} WHERE component = ?",  # noqa: S608 — table name is module constant "admin_schema_markers", never user input
            [component],
        )
        rows = getattr(result, "rows", None)
        if rows is None and isinstance(result, list):
            rows = result
        if not rows:
            return False
        stored = rows[0].get("fingerprint")
        return bool(stored) and str(stored) == fingerprint

    async def mark_current(self, component: str, fingerprint: str) -> None:
        """Upsert the fingerprint for ``component``."""
        await self._ensure_table()
        await self._db.execute(
            f"""INSERT INTO {_TABLE} (component, fingerprint)
               VALUES (?, ?)
               ON CONFLICT (component)
               DO UPDATE SET fingerprint = excluded.fingerprint,
                             updated_at = {now_expr(self._db)}""",  # noqa: S608 — table name is module constant, now_expr yields fixed NOW()/CURRENT_TIMESTAMP
            [component, fingerprint],
        )
