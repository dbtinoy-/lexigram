from unittest.mock import AsyncMock

import pytest


class DummyAuthProvider:
    def __init__(self):
        self.create_user = AsyncMock()
        self.authenticate_user = AsyncMock()
        self.get_user = AsyncMock()
        self.get_user_by_email = AsyncMock()
        self.delete_user = AsyncMock()


class DummyContainer:
    def __init__(self, auth_provider=None, db_present=True):
        self._singletons = {}
        self._auth_provider = auth_provider
        self._db_present = db_present

    def resolve(self, cls):
        if cls in self._singletons:
            return self._singletons[cls]
        name = getattr(cls, "__name__", str(cls))
        if name == "AuthProvider":
            return self._auth_provider
        if name == "DatabaseProviderProtocol":
            return True if self._db_present else None
        if name in self._singletons:
            return self._singletons[name]
        raise LookupError(f"Unrecognized dependency: {cls}")

    def singleton(self, key, value=None):
        if value is None:
            self._singletons[key] = True
        else:
            self._singletons[key] = value


pytest.skip(reason="LocalAuthService not implemented", allow_module_level=True)
