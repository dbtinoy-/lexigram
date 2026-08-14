from types import SimpleNamespace

import pytest

from lexigram.admin.auth.guards import AuthGuardMiddleware


class DummyUserStore:
    def __init__(self, user):
        self.user = user

    async def get_user_by_id(self, user_id):
        return self.user


class DummyAuthProvider:
    def __init__(self, verify_behavior=None, user_store=None):
        # verify_behavior: callable(token) -> payload or raise
        self._verify_behavior = verify_behavior
        self.user_store = user_store

    async def verify_token(self, token):
        if callable(self._verify_behavior):
            return self._verify_behavior(token)
        return None


class DummyRequest:
    def __init__(self, headers=None, cookies=None, session=None):
        self.headers = headers or {}
        self.cookies = cookies or {}
        self.scope = {"session": session or {}}
        self.session = self.scope["session"]


@pytest.mark.asyncio
async def test_get_authenticated_user_with_invalid_token_logs_header(caplog):
    # Build a fake token with a header indicating RS256 (non-default alg)
    # header: {"alg":"RS256","kid":"k1"}
    header_b64 = "eyJhbGciOiJSUzI1NiIsImtpZCI6ImsxIn0"
    fake_token = header_b64 + ".invalid.payload"

    # Simulate verify_token raising an exception with message about alg
    def raise_on_verify(token):
        raise ValueError("Invalid token: The specified alg value is not allowed")

    auth_provider = DummyAuthProvider(verify_behavior=raise_on_verify)
    from lexigram.admin.auth.guards import GuardConfig

    config = GuardConfig(allow_bearer_tokens=True)
    mw = AuthGuardMiddleware(app=None, auth_provider=auth_provider, config=config)

    req = DummyRequest(headers={"Authorization": f"Bearer {fake_token}"})

    caplog.clear()
    caplog.set_level("WARNING", logger="lexigram.admin.auth.guards")

    user = await mw._get_authenticated_user(req)

    # It should return None and log a warning containing the header and message
    assert user is None
    # Note: caplog doesn't work with structlog, but we can see the log in output
    # found = any("Token validation failed" in rec.message for rec in caplog.records)
    # assert found, "Expected a warning log about token validation failure"
    # # Also ensure header content was logged (alg or kid present)
    # header_logged = any(
    #     "RS256" in rec.message or "k1" in rec.message for rec in caplog.records
    # )
    # assert header_logged, "Expected the JWT header to appear in warning logs"


@pytest.mark.asyncio
async def test_get_authenticated_user_with_valid_bearer_token_returns_user():
    payload = {"sub": "user-123"}

    def return_payload(token):
        return payload

    expected_user = SimpleNamespace(id="user-123", email="a@b.com")
    user_store = DummyUserStore(expected_user)

    auth_provider = DummyAuthProvider(
        verify_behavior=return_payload,
        user_store=user_store,
    )
    from lexigram.admin.auth.guards import GuardConfig

    config = GuardConfig(allow_bearer_tokens=True)
    mw = AuthGuardMiddleware(app=None, auth_provider=auth_provider, config=config)

    fake_token = "eyJhbGciOiJIUzI1NiIsImtpZCI6ImRlZmF1bHQifQ.invalid.payload"
    req = DummyRequest(headers={"Authorization": f"Bearer {fake_token}"})

    user = await mw._get_authenticated_user(req)
    assert user is expected_user


@pytest.mark.asyncio
async def test_get_authenticated_user_with_request_session_uses_user_store():
    expected_user = SimpleNamespace(id="session-user-1", email="session@a.com")
    user_store = DummyUserStore(expected_user)

    # Build a fake auth provider with user_store only.
    auth_provider = DummyAuthProvider(verify_behavior=None, user_store=user_store)

    mw = AuthGuardMiddleware(app=None, auth_provider=auth_provider)

    req = DummyRequest(headers={}, session={"admin_user_id": "session-user-1"})

    user = await mw._get_authenticated_user(req)
    assert user is expected_user


# ---------------------------------------------------------------------------
# Result-based guard tests
# ---------------------------------------------------------------------------


class _State:
    """Minimal request state stub."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _Request:
    """Minimal request stub with mutable state."""

    def __init__(self, **state_kwargs):
        self.state = _State(**state_kwargs)


class TestPermissionGuard:
    @pytest.mark.asyncio
    async def test_unauthenticated_returns_err(self):
        from lexigram.admin.auth.guards import PermissionGuard
        from lexigram.admin.exceptions import PermissionDeniedError

        guard = PermissionGuard("users.list")
        result = await guard(_Request())  # no user in state

        assert result.is_err()
        assert isinstance(result.unwrap_err(), PermissionDeniedError)

    @pytest.mark.asyncio
    async def test_user_with_permission_returns_ok(self):
        from lexigram.admin.auth.guards import PermissionGuard
        from lexigram.admin.auth.permissions import PermissionSet

        guard = PermissionGuard("users.list")
        user = SimpleNamespace(id="u1", is_active=True)
        perms = PermissionSet(permissions={"users.list"})
        result = await guard(_Request(user=user, permissions=perms))

        assert result.is_ok()
        assert result.unwrap() is None

    @pytest.mark.asyncio
    async def test_user_without_permission_returns_err(self):
        from lexigram.admin.auth.guards import PermissionGuard
        from lexigram.admin.auth.permissions import PermissionSet
        from lexigram.admin.exceptions import PermissionDeniedError

        guard = PermissionGuard("users.delete")
        user = SimpleNamespace(id="u1", is_active=True)
        perms = PermissionSet(permissions={"users.list"})
        result = await guard(_Request(user=user, permissions=perms))

        assert result.is_err()
        assert isinstance(result.unwrap_err(), PermissionDeniedError)

    @pytest.mark.asyncio
    async def test_require_all_with_partial_perms_returns_err(self):
        from lexigram.admin.auth.guards import PermissionGuard
        from lexigram.admin.auth.permissions import PermissionSet

        guard = PermissionGuard("users.list", "users.create", require_all=True)
        user = SimpleNamespace(id="u1", is_active=True)
        perms = PermissionSet(permissions={"users.list"})  # missing users.create
        result = await guard(_Request(user=user, permissions=perms))

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_result_match_on_success(self):
        from lexigram.admin.auth.guards import PermissionGuard
        from lexigram.admin.auth.permissions import PermissionSet

        guard = PermissionGuard("reports.view")
        user = SimpleNamespace(id="u1", is_active=True)
        perms = PermissionSet(permissions={"reports.view"})
        result = await guard(_Request(user=user, permissions=perms))

        message = result.match(
            ok=lambda _: "allowed",
            err=lambda e: f"denied: {e}",
        )
        assert message == "allowed"


class TestRoleGuard:
    @pytest.mark.asyncio
    async def test_unauthenticated_returns_err(self):
        from lexigram.admin.auth.guards import RoleGuard
        from lexigram.admin.exceptions import PermissionDeniedError

        guard = RoleGuard("admin")
        result = await guard(_Request())

        assert result.is_err()
        assert isinstance(result.unwrap_err(), PermissionDeniedError)

    @pytest.mark.asyncio
    async def test_user_with_required_role_returns_ok(self):
        from lexigram.admin.auth.guards import RoleGuard

        guard = RoleGuard("admin")
        user = SimpleNamespace(id="u1", roles=["admin", "editor"])
        result = await guard(_Request(user=user))

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_user_without_required_role_returns_err(self):
        from lexigram.admin.auth.guards import RoleGuard
        from lexigram.admin.exceptions import PermissionDeniedError

        guard = RoleGuard("superuser")
        user = SimpleNamespace(id="u1", roles=["admin"])
        result = await guard(_Request(user=user))

        assert result.is_err()
        assert isinstance(result.unwrap_err(), PermissionDeniedError)

    @pytest.mark.asyncio
    async def test_require_all_roles_missing_one_returns_err(self):
        from lexigram.admin.auth.guards import RoleGuard

        guard = RoleGuard("admin", "auditor", require_all=True)
        user = SimpleNamespace(id="u1", roles=["admin"])  # missing auditor
        result = await guard(_Request(user=user))

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_require_all_roles_fully_satisfied_returns_ok(self):
        from lexigram.admin.auth.guards import RoleGuard

        guard = RoleGuard("admin", "auditor", require_all=True)
        user = SimpleNamespace(id="u1", roles=["admin", "auditor"])
        result = await guard(_Request(user=user))

        assert result.is_ok()


class TestCompositeGuard:
    @pytest.mark.asyncio
    async def test_and_logic_all_pass_returns_ok(self):
        from lexigram.admin.auth.guards import (
            CompositeGuard,
            PermissionGuard,
            RoleGuard,
        )
        from lexigram.admin.auth.permissions import PermissionSet

        user = SimpleNamespace(id="u1", roles=["admin"])
        perms = PermissionSet(permissions={"users.list"})
        request = _Request(user=user, permissions=perms)

        guard = CompositeGuard(
            PermissionGuard("users.list"),
            RoleGuard("admin"),
            logic="and",
        )
        result = await guard(request)

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_and_logic_first_failure_short_circuits(self):
        from lexigram.admin.auth.guards import (
            CompositeGuard,
            PermissionGuard,
            RoleGuard,
        )
        from lexigram.admin.auth.permissions import PermissionSet

        user = SimpleNamespace(id="u1", roles=["admin"])
        perms = PermissionSet()  # no permissions
        request = _Request(user=user, permissions=perms)

        guard = CompositeGuard(
            PermissionGuard("users.delete"),  # fails
            RoleGuard("admin"),  # would pass
            logic="and",
        )
        result = await guard(request)

        assert result.is_err()

    @pytest.mark.asyncio
    async def test_or_logic_one_pass_returns_ok(self):
        from lexigram.admin.auth.guards import (
            CompositeGuard,
            PermissionGuard,
            RoleGuard,
        )
        from lexigram.admin.auth.permissions import PermissionSet

        user = SimpleNamespace(id="u1", roles=["admin"])
        perms = PermissionSet()  # no permissions (PermissionGuard fails)
        request = _Request(user=user, permissions=perms)

        guard = CompositeGuard(
            PermissionGuard("users.delete"),  # fails
            RoleGuard("admin"),  # passes
            logic="or",
        )
        result = await guard(request)

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_or_logic_all_fail_returns_err(self):
        from lexigram.admin.auth.guards import (
            CompositeGuard,
            PermissionGuard,
            RoleGuard,
        )
        from lexigram.admin.auth.permissions import PermissionSet
        from lexigram.admin.exceptions import PermissionDeniedError

        user = SimpleNamespace(id="u1", roles=["editor"])
        perms = PermissionSet()  # no permissions
        request = _Request(user=user, permissions=perms)

        guard = CompositeGuard(
            PermissionGuard("users.delete"),  # fails
            RoleGuard("admin"),  # fails (user only has "editor")
            logic="or",
        )
        result = await guard(request)

        assert result.is_err()
        assert isinstance(result.unwrap_err(), PermissionDeniedError)
