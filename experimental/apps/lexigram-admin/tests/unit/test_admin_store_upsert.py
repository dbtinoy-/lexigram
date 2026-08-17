import pytest

from lexigram.admin.auth.store import DirectSQLAdminUserStore


class FakeProviderUpsert:
    def __init__(self):
        self.database_type = "postgres"
        self.last_sql = None
        self.last_params = None

    async def execute(self, sql, params=None):
        self.last_sql = sql
        self.last_params = params
        # Simulate RETURNING row — column is `name` matching the admin_users schema
        return [{"id": "u1", "name": "admin", "email": "admin@example.com"}]

    async def execute_query(self, sql, params=None):
        return await self.execute(sql, params)


@pytest.mark.asyncio
async def test_create_user_upsert_on_postgres_returns_row():
    prov = FakeProviderUpsert()
    store = DirectSQLAdminUserStore(prov)

    user = await store.create_user(
        "admin", "admin@example.com", "$2b$hash", roles=["admin"], permissions=[],
    )

    assert getattr(user, "user_id") == "u1"
    assert getattr(user, "username") == "admin"


class FakeProviderDuplicate:
    def __init__(self):
        self.database_type = "sqlite"
        self.insert_called = False
        self.queries = []

    async def execute_insert(self, table, payload):
        self.insert_called = True
        raise Exception(
            'duplicate key value violates unique constraint "users_email_key"',
        )

    async def execute_query(self, sql, params=None):
        # Simulated select returning existing row
        self.queries.append((sql, params))
        return [{"id": "u2", "username": "admin2", "email": "admin2@example.com"}]

    async def execute_update(self, table, payload, where_clause, where_params):
        # pretend update succeeded
        return 1


@pytest.mark.asyncio
async def test_create_user_handles_duplicate_by_loading_existing():
    prov = FakeProviderDuplicate()
    store = DirectSQLAdminUserStore(prov)

    user = await store.create_user("admin2", "admin2@example.com", "$2b$hash")

    assert getattr(user, "user_id") == "u2" or getattr(user, "username") == "admin2"
    assert prov.insert_called is True
    # verify we attempted to query for existing
    assert prov.queries
