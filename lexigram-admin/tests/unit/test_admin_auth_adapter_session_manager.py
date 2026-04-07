from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from lexigram.admin.auth.adapter import AdminAuthAdapter
from lexigram.auth import AuthenticationProvider
from lexigram.contracts.auth import AuthProviderProtocol


@pytest.mark.asyncio
async def test_adapter_attaches_session_manager():
    class C:
        """Test container that tracks registrations."""
        
        def __init__(self):
            self._singletons = {}
            self._registered_keys = []  # Track what's been registered

        async def resolve(self, name):
            # Simulate missing AuthProvider so adapter will create and register one
            if name in self._singletons:
                return self._singletons[name]()
            raise Exception(f"Not found: {name}")

        def singleton(self, k, v):
            self._singletons[k] = v
            self._registered_keys.append(k)
        
        def has(self, key) -> bool:
            """Public API to check registration."""
            return key in self._registered_keys


    container = C()
    
    from lexigram.contracts.data import DatabaseProviderProtocol
    db_provider = MagicMock()
    container.singleton(DatabaseProviderProtocol, lambda: db_provider)

    from lexigram.admin.auth.store import DirectSQLAdminUserStore
    class MockAdminStore(DirectSQLAdminUserStore):
        def __init__(self, db):
            self.db_provider = db
    
    admin_store = MockAdminStore(db_provider)
    container.singleton("lexigram.admin.auth.AbstractAdminUserStore", lambda: admin_store)

    from lexigram.auth.config import AuthConfig, JWTConfig
    _key = "test-session-manager-key-32bytes!!"
    auth_provider = AuthenticationProvider(config=AuthConfig(secret_key=_key, token=JWTConfig(secret_key=_key)))
    container.singleton(AuthenticationProvider, lambda: auth_provider)
    container.singleton(AuthProviderProtocol, lambda: auth_provider)
    container.singleton("AdminAuthProvider", lambda: auth_provider)
    adapter = AdminAuthAdapter(SimpleNamespace(), MagicMock())

    await adapter.sync(container)

    # Use public API instead of accessing internal _singletons
    assert container.has("AdminAuthProvider")
    registered = container._singletons.get("AdminAuthProvider")
    assert registered is not None
    created_auth_provider = registered()
    assert getattr(created_auth_provider, "session_manager", None) is not None
