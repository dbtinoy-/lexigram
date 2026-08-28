import pytest

from lexigram.sql.api import DatabaseError, QueryEngine


class DummyResult:
    def __init__(self, rows=None, scalar_value=None):
        self._rows = rows or []
        self._scalar = scalar_value

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows

    def scalar(self):
        return self._scalar


class DummyConn:
    def __init__(self, result: DummyResult):
        self._result = result

    async def execute(self, sql, params=None):
        return self._result


class DummyProvider:
    def __init__(self, result: DummyResult):
        self._result = result

    async def boot(self, app=None):
        pass

    async def shutdown(self, app=None):
        pass

    async def health_check(self):
        return {"status": "healthy"}

    async def get_scoped_connection(self):
        # Not used in these tests
        return DummyConn(self._result)

    def get_connection(self):
        # Provide an async context manager
        class Ctx:
            async def __aenter__(inner_self):
                return DummyConn(self._result)

            async def __aexit__(inner_self, exc_type, exc, tb):
                return False

        return Ctx()


@pytest.mark.asyncio
async def test_query_engine_fetchall_and_fetchone():
    result = DummyResult(rows=[{"id": 1, "name": "Alice"}])
    provider = DummyProvider(result)
    qe = QueryEngine(provider)

    rows = await qe.fetchall("SELECT * FROM users")
    assert isinstance(rows, list)
    assert rows[0]["name"] == "Alice"

    row = await qe.fetchone("SELECT * FROM users LIMIT 1")
    assert row["id"] == 1


@pytest.mark.asyncio
async def test_query_engine_scalar():
    result = DummyResult(scalar_value=42)
    provider = DummyProvider(result)
    qe = QueryEngine(provider)

    value = await qe.scalar("SELECT COUNT(*) FROM t")
    assert value == 42


def test_database_error_hierarchy():
    with pytest.raises(DatabaseError):
        raise DatabaseError("test")
