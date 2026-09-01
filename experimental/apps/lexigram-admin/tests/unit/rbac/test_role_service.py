"""Unit tests for AdminRoleService with fake store/authorizer/audit."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.rbac.errors import (
    RoleDuplicateError,
    RoleNotFoundError,
    SystemRoleError,
)
from lexigram.admin.rbac.role_service import AdminRoleService
from lexigram.contracts.auth import RoleDefinition


class FakeRoleStore:
    """In-memory AdminRoleStoreProtocol."""

    def __init__(self, roles: list[RoleDefinition] | None = None) -> None:
        self.roles = {r.name: r for r in (roles or [])}
        self.schema_initialized = False

    async def ensure_schema(self) -> None:
        self.schema_initialized = True

    async def list_roles(self) -> list[RoleDefinition]:
        return sorted(self.roles.values(), key=lambda r: r.name)

    async def get_role(self, name: str) -> RoleDefinition | None:
        return self.roles.get(name)

    async def create_role(self, role: RoleDefinition) -> None:
        self.roles[role.name] = role

    async def update_role(self, role: RoleDefinition) -> None:
        self.roles[role.name] = role

    async def delete_role(self, name: str) -> bool:
        return self.roles.pop(name, None) is not None


class FakeAuthorizer:
    """AuthorizerProtocol double with register_role/remove_role."""

    def __init__(self) -> None:
        self.roles: dict[str, MagicMock] = {}
        self.removed: list[str] = []

    def register_role(self, name: str, role: object) -> None:
        self.roles[name] = role  # type: ignore[assignment]

    def remove_role(self, name: str) -> None:
        self.roles.pop(name, None)
        self.removed.append(name)


def _make_service(
    roles: list[RoleDefinition] | None = None,
    authorizer: FakeAuthorizer | None = None,
    audit: MagicMock | None = None,
) -> tuple[AdminRoleService, FakeRoleStore, FakeAuthorizer, MagicMock]:
    store = FakeRoleStore(roles)
    authz = authorizer or FakeAuthorizer()
    audit_svc = audit or MagicMock()
    if audit is None:
        audit_svc.log_event = AsyncMock(return_value=None)
    svc = AdminRoleService(
        role_store=store,
        authorization_service=authz,
        audit_service=audit_svc,
    )
    return svc, store, authz, audit_svc


@pytest.mark.asyncio
async def test_list_roles_returns_sorted_roles() -> None:
    svc, _, _, _ = _make_service(
        [RoleDefinition("viewer", "Viewers"), RoleDefinition("admin", "Admins")]
    )

    roles = await svc.list_roles()

    assert [r.name for r in roles] == ["admin", "viewer"]


@pytest.mark.asyncio
async def test_create_role_persists_mirrors_and_audits() -> None:
    svc, store, authz, audit = _make_service()

    result = await svc.create_role("editor", "Editors", ["posts.edit"], ["viewer"])

    assert result.is_ok()
    role = result.unwrap()
    assert role.name == "editor"
    assert store.roles["editor"].permissions == ["posts.edit"]
    assert authz.roles["editor"] is not None
    audit.log_event.assert_awaited_once()
    assert (
        audit.log_event.await_args.kwargs["event_type"]
        == AdminSecurityEventType.ROLE_CREATED
    )


@pytest.mark.asyncio
async def test_create_role_duplicate_returns_err() -> None:
    svc, _, authz, audit = _make_service([RoleDefinition("editor", "Existing")])

    result = await svc.create_role("editor", "Again", [], [])

    assert result.is_err()
    assert isinstance(result.unwrap_err(), RoleDuplicateError)
    assert "editor" not in authz.roles
    audit.log_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_role_mirrors_and_audits() -> None:
    svc, store, authz, audit = _make_service([RoleDefinition("editor", "Old")])

    result = await svc.update_role("editor", "New", ["posts.view"], [])

    assert result.is_ok()
    assert store.roles["editor"].description == "New"
    assert authz.roles["editor"] is not None
    assert (
        audit.log_event.await_args.kwargs["event_type"]
        == AdminSecurityEventType.ROLE_UPDATED
    )


@pytest.mark.asyncio
async def test_update_role_missing_returns_not_found() -> None:
    svc, _, _, audit = _make_service()

    result = await svc.update_role("ghost", "X", [], [])

    assert result.is_err()
    assert isinstance(result.unwrap_err(), RoleNotFoundError)
    audit.log_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_role_preserves_stored_name() -> None:
    svc, store, _, _ = _make_service([RoleDefinition("admin", "Admin", [], [], True)])

    result = await svc.update_role("admin", "Super Admin", ["*"], [])

    assert result.is_ok()
    assert store.roles["admin"].name == "admin"


@pytest.mark.asyncio
async def test_system_role_permissions_can_be_updated() -> None:
    svc, store, authz, _ = _make_service([RoleDefinition("admin", "Admin", [], [], True)])

    result = await svc.update_role("admin", "Admin", ["*"], [])

    assert result.is_ok()
    assert store.roles["admin"].permissions == ["*"]
    assert authz.roles["admin"] is not None


@pytest.mark.asyncio
async def test_delete_role_removes_and_audits() -> None:
    svc, store, authz, audit = _make_service([RoleDefinition("editor", "Editors")])

    result = await svc.delete_role("editor")

    assert result.is_ok()
    assert "editor" not in store.roles
    assert authz.removed == ["editor"]
    assert (
        audit.log_event.await_args.kwargs["event_type"]
        == AdminSecurityEventType.ROLE_DELETED
    )


@pytest.mark.asyncio
async def test_delete_role_missing_returns_not_found() -> None:
    svc, _, authz, audit = _make_service()

    result = await svc.delete_role("ghost")

    assert result.is_err()
    assert isinstance(result.unwrap_err(), RoleNotFoundError)
    assert authz.removed == []
    audit.log_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_delete_system_role_returns_system_error() -> None:
    svc, _, authz, audit = _make_service([RoleDefinition("admin", "Admin", [], [], True)])

    result = await svc.delete_role("admin")

    assert result.is_err()
    assert isinstance(result.unwrap_err(), SystemRoleError)
    assert authz.removed == []
    audit.log_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_authorizer_or_audit_skips_gracefully() -> None:
    store = FakeRoleStore()
    svc = AdminRoleService(
        role_store=store,
        authorization_service=None,
        audit_service=None,
    )

    result = await svc.create_role("editor", "Editors", [], [])

    assert result.is_ok()
    assert store.roles["editor"].name == "editor"


def test_role_service_types_authorizer_via_protocol() -> None:
    import inspect

    from lexigram.admin.rbac.role_service import AdminRoleService
    from lexigram.contracts.auth import AuthorizerProtocol

    sig = inspect.signature(AdminRoleService.__init__)
    annotation = sig.parameters["authorization_service"].annotation
    assert "AuthorizationService" not in str(annotation)
    assert AuthorizerProtocol.__name__ in str(annotation)


def test_role_service_uses_contracts_role_definition() -> None:
    import inspect

    from lexigram.admin.rbac.role_service import AdminRoleService

    for method in ("create_role", "update_role"):
        sig = inspect.signature(getattr(AdminRoleService, method))
        assert "RoleDefinition" in str(sig.return_annotation)


@pytest.mark.asyncio
async def test_audit_attributes_actor_when_provided() -> None:
    """R10: controller-passed actor_id lands on the audit row."""
    svc, _store, _authz, audit = _make_service()

    await svc.create_role("editor", "Editors", [], [], actor_id="admin-9")
    kwargs = audit.log_event.await_args.kwargs
    assert kwargs["admin_user_id"] == "admin-9"

    await svc.update_role("editor", "Editors", ["users.list"], [], actor_id="admin-9")
    assert audit.log_event.await_args.kwargs["admin_user_id"] == "admin-9"

    await svc.delete_role("editor", actor_id="admin-9")
    assert audit.log_event.await_args.kwargs["admin_user_id"] == "admin-9"


@pytest.mark.asyncio
async def test_audit_actor_defaults_to_none() -> None:
    """Callers without request context stay backwards compatible."""
    svc, _store, _authz, audit = _make_service()
    await svc.create_role("editor", "Editors", [], [])
    assert audit.log_event.await_args.kwargs["admin_user_id"] is None
