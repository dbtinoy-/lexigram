"""Dialect-branch regression tests for the admin-security SQL port.

Guards the Postgres/SQLite branches introduced by the SQLite portability
work: each store's ``ensure_schema`` must emit Postgres-only syntax only
for Postgres providers, and SQLite-compatible DDL for SQLite providers.
Also covers the ``sql_dialect`` helpers and spot-checks DML branches.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from lexigram.admin.auth.store.audit_log_sql import AdminAuditLogSqlStore
from lexigram.admin.auth.store.direct_sql import DirectSQLAdminUserStore
from lexigram.admin.auth.store.email_otp_sql import AdminEmailOtpSqlStore
from lexigram.admin.auth.store.email_verification_sql import (
    AdminEmailVerificationSqlStore,
)
from lexigram.admin.auth.store.lockout_sql import AdminAccountLockoutSqlStore
from lexigram.admin.auth.store.login_attempt_sql import AdminLoginAttemptSqlStore
from lexigram.admin.auth.store.mfa_sql import AdminMfaSqlStore
from lexigram.admin.auth.store.password_reset_token_sql import (
    AdminPasswordResetTokenSqlStore,
)
from lexigram.admin.rbac.roles_sql import AdminRoleSqlStore
from lexigram.admin.services.settings_service import AdminSettingsDbProvider
from lexigram.admin.sql_dialect import is_postgres, now_expr, since_expr

POSTGRES_MARKERS = ("gen_random_uuid", "TIMESTAMPTZ", "NOW()")


class FakeDb:
    """Recording provider that accepts any query."""

    def __init__(self, database_type: str) -> None:
        self.database_type = database_type
        self.sqls: list[str] = []
        self.params: list[object] = []

    async def execute(self, sql: str, params: object = None) -> object:
        self.sqls.append(str(sql))
        self.params.append(params)
        return SimpleNamespace(rows=[], row_count=0, success=True)

    async def execute_query(self, sql: str, params: object = None) -> object:
        return await self.execute(sql, params)

    async def execute_insert(self, table: str, data: dict[str, object]) -> object:
        return SimpleNamespace(rows=[], row_count=1, success=True)

    async def execute_update(
        self, table: str, data: dict[str, object], where: str, where_params: object
    ) -> object:
        return 1


@pytest.mark.asyncio
async def test_is_postgres_accepts_postgres_alias() -> None:
    assert is_postgres(FakeDb("postgres")) is True
    assert is_postgres(FakeDb("postgresql")) is True
    assert is_postgres(FakeDb("sqlite")) is False
    assert is_postgres(FakeDb("mysql")) is False


def test_now_expr_matches_dialect() -> None:
    assert now_expr(FakeDb("postgres")) == "NOW()"
    assert now_expr(FakeDb("sqlite")) == "CURRENT_TIMESTAMP"


def test_since_expr_matches_dialect() -> None:
    assert (
        since_expr(FakeDb("postgres"), 900)
        == "NOW() - INTERVAL '900 seconds'"
    )
    assert (
        since_expr(FakeDb("sqlite"), 900)
        == "datetime('now', '-900 seconds')"
    )


@pytest.mark.asyncio
async def test_ddl_uses_postgres_syntax_only_on_postgres() -> None:
    cases = [
        (AdminLoginAttemptSqlStore, ()),
        (AdminAccountLockoutSqlStore, ()),
        (AdminAuditLogSqlStore, ()),
        (AdminEmailOtpSqlStore, ()),
        (AdminEmailVerificationSqlStore, ()),
        (AdminMfaSqlStore, ()),
        (AdminPasswordResetTokenSqlStore, ()),
        (AdminRoleSqlStore, ()),
    ]
    for store_cls, args in cases:
        pg = FakeDb("postgres")
        await store_cls(pg, *args).ensure_schema()
        joined = " ".join(pg.sqls)
        assert any(m in joined for m in POSTGRES_MARKERS), (
            f"{store_cls.__name__} emits no Postgres-only syntax on Postgres"
        )

        sq = FakeDb("sqlite")
        await store_cls(sq, *args).ensure_schema()
        joined = " ".join(sq.sqls)
        assert "CURRENT_TIMESTAMP" in joined, (
            f"{store_cls.__name__} emits no SQLite timestamp default"
        )
        assert all(m not in joined for m in POSTGRES_MARKERS), (
            f"{store_cls.__name__} leaks Postgres-only syntax into SQLite DDL"
        )


@pytest.mark.asyncio
async def test_settings_ensure_table_selects_dialect() -> None:
    pg = FakeDb("postgres")
    await AdminSettingsDbProvider(pg).get_config("t", "k")
    assert "TIMESTAMPTZ" in pg.sqls[0]

    sq = FakeDb("sqlite")
    await AdminSettingsDbProvider(sq).get_config("t", "k")
    assert "CURRENT_TIMESTAMP" in sq.sqls[0]
    assert "TIMESTAMPTZ" not in sq.sqls[0]


@pytest.mark.asyncio
async def test_otp_consume_dml_uses_dialect_now() -> None:

    pg = FakeDb("postgres")
    otp = AdminEmailOtpSqlStore(pg)
    await otp.consume("user-1", "hash")
    assert any("NOW()" in s and "expires_at >" in s for s in pg.sqls)

    sq = FakeDb("sqlite")
    otp = AdminEmailOtpSqlStore(sq)
    await otp.consume("user-1", "hash")
    assert any("CURRENT_TIMESTAMP" in s and "expires_at >" in s for s in sq.sqls)


@pytest.mark.asyncio
async def test_login_attempts_since_window_uses_dialect() -> None:
    pg = FakeDb("postgres")
    attempts = AdminLoginAttemptSqlStore(pg)
    await attempts.count_recent_failures("a@b.c", 900)
    assert any("INTERVAL '900 seconds'" in s for s in pg.sqls)

    sq = FakeDb("sqlite")
    attempts = AdminLoginAttemptSqlStore(sq)
    await attempts.count_recent_failures("a@b.c", 900)
    assert any("datetime('now', '-900 seconds')" in s for s in sq.sqls)


@pytest.mark.asyncio
async def test_direct_sql_insert_does_not_serialize_lists_on_postgres() -> None:
    pg = FakeDb("postgres")
    store = DirectSQLAdminUserStore(pg)
    await store.create_user("Admin", "a@b.c", "hash", roles=["super_admin"])
    assert any(
        isinstance(p, list) and ["super_admin"] in p for p in pg.params
    ), "Postgres branch must pass roles as a list, not JSON text"
