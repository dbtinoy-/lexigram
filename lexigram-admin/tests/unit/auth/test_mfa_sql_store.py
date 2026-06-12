"""Unit tests for AdminMfaSqlStore with a fake DB provider."""

from __future__ import annotations

import pytest

from lexigram.admin.auth.store.mfa_sql import AdminMfaSqlStore
from lexigram.security.encryption import EncryptionService

ENCRYPTION_KEY = EncryptionService(secret_key="test-mfa-encryption-key-32b")


class FakeProvider:
    """Records calls; returns configurable rows."""

    def __init__(self, rows: list[dict] | None = None) -> None:
        self.database_type = "sqlite"
        self.executed: list[tuple[str, list]] = []
        self.queries: list[tuple[str, list]] = []
        self._rows = rows or []

    async def execute(self, sql: str, params: list | None = None) -> None:
        self.executed.append((sql, params or []))

    async def execute_query(self, sql: str, params: list | None = None) -> list[dict]:
        self.queries.append((sql, params or []))
        return self._rows


@pytest.mark.asyncio
async def test_ensure_schema_creates_table() -> None:
    provider = FakeProvider()
    store = AdminMfaSqlStore(provider)

    await store.ensure_schema()

    assert any("CREATE TABLE IF NOT EXISTS" in sql for sql, _ in provider.executed)
    assert any("admin_mfa_totp" in sql for sql, _ in provider.executed)


@pytest.mark.asyncio
async def test_is_enabled_false_when_no_row() -> None:
    store = AdminMfaSqlStore(FakeProvider())

    assert await store.is_enabled("user-001") is False


@pytest.mark.asyncio
async def test_is_enabled_true_when_row_present() -> None:
    provider = FakeProvider(rows=[{"secret": "SECRET"}])
    store = AdminMfaSqlStore(provider)

    assert await store.is_enabled("user-001") is True

    sql, params = provider.queries[0]
    assert "user_id = ?" in sql
    assert params == ["user-001"]


@pytest.mark.asyncio
async def test_save_secret_upserts_row() -> None:
    provider = FakeProvider()
    store = AdminMfaSqlStore(provider)

    await store.save_secret("user-001", "SECRET")

    sql, params = provider.executed[0]
    assert "INSERT INTO" in sql
    assert "ON CONFLICT" in sql
    assert params == ["user-001", "SECRET"]


@pytest.mark.asyncio
async def test_get_secret_returns_stored_value() -> None:
    provider = FakeProvider(rows=[{"secret": "SECRET"}])
    store = AdminMfaSqlStore(provider)

    secret = await store.get_secret("user-001")

    assert secret == "SECRET"
    sql, params = provider.queries[0]
    assert "admin_mfa_totp" in sql
    assert params == ["user-001"]


@pytest.mark.asyncio
async def test_get_secret_returns_none_when_missing() -> None:
    store = AdminMfaSqlStore(FakeProvider())

    assert await store.get_secret("user-001") is None


@pytest.mark.asyncio
async def test_disable_deletes_row() -> None:
    provider = FakeProvider()
    store = AdminMfaSqlStore(provider)

    await store.disable("user-001")

    sql, params = provider.executed[0]
    assert "DELETE" in sql
    assert params == ["user-001"]


@pytest.mark.asyncio
async def test_resave_after_disable_re_enables() -> None:
    provider = FakeProvider()
    store = AdminMfaSqlStore(provider)

    await store.save_secret("user-001", "SECRET")
    await store.disable("user-001")
    await store.save_secret("user-001", "SECRET2")

    assert len(provider.executed) == 3
    assert "DELETE" in provider.executed[1][0]


@pytest.mark.asyncio
async def test_save_secret_writes_ciphertext_at_rest_with_encryption() -> None:
    provider = FakeProvider()
    store = AdminMfaSqlStore(provider, encryption_service=ENCRYPTION_KEY)

    await store.save_secret("user-001", "SECRET")

    _, params = provider.executed[0]
    stored = params[1]
    assert stored != "SECRET"
    assert len(stored) > 60  # nonce 12 + tag 16 + data bytes, hex-encoded
    assert all(c in "0123456789abcdef" for c in stored)


@pytest.mark.asyncio
async def test_get_secret_round_trips_encrypted_value() -> None:
    provider = FakeProvider()
    store = AdminMfaSqlStore(provider, encryption_service=ENCRYPTION_KEY)
    await store.save_secret("user-001", "SECRET")
    stored = provider.executed[0][1][1]
    provider._rows = [{"secret": stored}]

    secret = await store.get_secret("user-001")

    assert secret == "SECRET"


@pytest.mark.asyncio
async def test_get_secret_falls_back_to_legacy_raw_value() -> None:
    provider = FakeProvider(rows=[{"secret": "LEGACYBASE32"}])
    store = AdminMfaSqlStore(provider, encryption_service=ENCRYPTION_KEY)

    secret = await store.get_secret("user-001")

    assert secret == "LEGACYBASE32"


@pytest.mark.asyncio
async def test_ensure_schema_widens_secret_column() -> None:
    provider = FakeProvider()
    store = AdminMfaSqlStore(provider)

    await store.ensure_schema()

    sql = provider.executed[0][0]
    assert "VARCHAR(512)" in sql


@pytest.mark.asyncio
async def test_ensure_schema_issues_idempotent_postgres_alter() -> None:
    provider = FakeProvider()
    provider.database_type = "postgres"
    store = AdminMfaSqlStore(provider)

    await store.ensure_schema()

    alters = [sql for sql, _ in provider.executed if "ALTER TABLE" in sql]
    assert len(alters) == 1
    assert "admin_mfa_totp" in alters[0]
    assert "VARCHAR(512)" in alters[0]
