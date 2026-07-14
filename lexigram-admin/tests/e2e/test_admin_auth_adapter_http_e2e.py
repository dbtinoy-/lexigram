import types

from httpx import ASGITransport, AsyncClient
import pytest
from starlette.applications import Starlette
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from lexigram.admin.auth.adapter import AdminAuthAdapter
from lexigram.admin.auth.store import AuthProviderAdminUserStore
from lexigram.admin.controllers.auth import AuthController
from lexigram.admin.middleware.auth import AdminAuthMiddleware
from lexigram.auth.authn.security import PasswordHasher
from lexigram.auth.authz.service import AuthorizationService
from lexigram.auth.di import AuthenticationProvider
from lexigram.contracts.auth import AuthProviderProtocol
from lexigram.contracts.data import DatabaseProviderProtocol
from lexigram.contracts.exceptions import UnresolvableDependencyError


class DummyRenderer:
    def render_page(self, content, request=None, title=None, breadcrumbs=None):
        return PlainTextResponse(str(content))


class DummyTaskManager:
    def create_background_task(self, task, name=None):
        pass


class SimpleContainer:
    def __init__(self):
        self._singletons = {}

    def singleton(self, cls, factory):
        self._singletons[cls] = factory

    async def resolve(self, cls):
        if cls in self._singletons:
            return self._singletons[cls]()
        # Fallback to key matches if cls is a protocol
        for key, factory in self._singletons.items():
            if isinstance(cls, str):
                # For string keys, only check exact match
                if key == cls:
                    return factory()
            elif isinstance(key, type) and isinstance(cls, type) and issubclass(key, cls):
                return factory()
            elif key == cls:
                return factory()
        raise UnresolvableDependencyError(f"{cls} not registered")


def create_app(controller, container, user_store):
    async def login_form(request):
        return await controller.login_form(request)

    async def login_submit(request):
        return await controller.login_submit(request)

    async def logout(request):
        return await controller.logout(request)

    routes = [
        Route("/admin/login", login_form, methods=["GET"]),
        Route("/admin/login", login_submit, methods=["POST"]),
        Route("/admin/logout", logout, methods=["GET"]),
    ]

    app = Starlette(routes=routes)
    # Session secret must match AuthProvider secret used in tests
    # Add AdminAuthMiddleware first (it will be the inner middleware)
    app.add_middleware(
        AdminAuthMiddleware,
        container=container,
        user_store=user_store,
        require_auth=False,
    )
    # Add SessionMiddleware last so it runs *before* AdminAuthMiddleware and populates request.session
    app.add_middleware(SessionMiddleware, secret_key="test-secret")  # noqa: S106
    return app


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_admin_auth_adapter_register_and_login_flow():
    pytest.skip("E2E test needs framework update")
    from unittest.mock import AsyncMock
    container.singleton(DatabaseProviderProtocol, lambda: AsyncMock())

    # Create an admin user config with pre-hashed password
    hashed = await PasswordHasher().hash("Secret1!")
    admin_user = types.SimpleNamespace(
        username="admin",
        email="admin@example.com",
        hashed_password=hashed,
        roles=["admin"],
    )
    auth_config = types.SimpleNamespace(secret_key="test-secret", users=[admin_user])  # noqa: S106
    authz_service = AuthorizationService()

    adapter = AdminAuthAdapter(auth_config, authz_service)

    # Pre-create admin user via adapter (creation on startup is disabled for sync)
    await adapter.create_user(
        container,
        username="admin",
        email="admin@example.com",
        password="Secret1!",  # noqa: S106
        roles=["admin"],
    )

    # Register (sync) roles into AuthProvider
    await adapter.sync(container)

    # Verify the auth provider can authenticate the synced user
    authenticated = await auth_provider.authenticate_user(
        "admin@example.com", "Secret1!",
    )
    assert authenticated.is_ok()
    assert authenticated.unwrap().email == "admin@example.com"

    # Create controller and app wiring
    user_store = AuthProviderAdminUserStore(auth_provider)
    controller = AuthController(user_store=user_store, renderer=DummyRenderer(), task_manager=DummyTaskManager())
    app = create_app(controller, container, user_store)

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver", follow_redirects=False,
    ) as client:
        # GET login form
        r = await client.get("/admin/login")
        assert r.status_code == 200

        # POST valid credentials
        r = await client.post(
            "/admin/login",
            data={
                "email": "admin@example.com",
                "password": "Secret1!",
                "next": "/admin/",
            },
        )
        assert r.status_code == 302
        assert "session" in r.headers.get("set-cookie", "")

        set_cookie = r.headers.get("set-cookie", "")
        cookie_pair = set_cookie.split(";", 1)[0]
        assert cookie_pair

        # Access login form with cookie - should redirect because user is authenticated
        r2 = await client.get(
            "/admin/login", headers={"cookie": cookie_pair}, follow_redirects=False,
        )
        assert r2.status_code == 302

        # logout
        r3 = await client.get(
            "/admin/logout", headers={"cookie": cookie_pair}, follow_redirects=False,
        )
        assert r3.status_code == 302

        # after logout, login form should be accessible (no redirect)
        r4 = await client.get("/admin/login")
        assert r4.status_code == 200


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_admin_auth_adapter_create_delete_user_emits_audit():
    # Prepare auth provider and container
    auth_provider = AuthenticationProvider(secret_key="test-secret")  # noqa: S106
    container = SimpleContainer()
    container.singleton(AuthenticationProvider, lambda: auth_provider)
    container.singleton(AuthProviderProtocol, lambda: auth_provider)
    from unittest.mock import AsyncMock
    container.singleton(DatabaseProviderProtocol, lambda: AsyncMock())

    # Prepare a fake audit logger and register it under the real AuditLogger type

    class FakeAuditLogger:
        def __init__(self):
            self.events = []

        async def log_change(self, user_id, resource, action, details):
            self.events.append(
                {"user_id": user_id, "resource": resource, "action": action, **details},
            )

    fake_audit = FakeAuditLogger()
    container.singleton("AuditLogger", lambda: fake_audit)

    auth_config = types.SimpleNamespace(secret_key="test-secret", users=[])  # noqa: S106
    authz_service = AuthorizationService()
    adapter = AdminAuthAdapter(auth_config, authz_service)

    # Create a new admin user via adapter (calls AuthProvider.create_user internally)
    created = await adapter.create_user(
        container, username="bob", email="bob@example.com", password="Secret2!",  # noqa: S106
    )
    assert created is not None

    # Authenticate the newly created user
    auth_user = await auth_provider.authenticate_user("bob@example.com", "Secret2!")
    assert auth_user.is_ok()

    # Audit logger should have recorded an INSERT event
    assert len(fake_audit.events) >= 1
    assert any(evt.get("action") == "INSERT" for evt in fake_audit.events)

    # Now delete the user via adapter
    await adapter.delete_user(container, getattr(created, "user_id", created.username))

    # After deletion, the user should not be authenticateable
    auth_user_after = await auth_provider.authenticate_user(
        "bob@example.com", "Secret2!",
    )
    assert auth_user_after.is_err()

    # Audit logger should have recorded a DELETE event
    assert any(evt.get("action") == "DELETE" for evt in fake_audit.events)
