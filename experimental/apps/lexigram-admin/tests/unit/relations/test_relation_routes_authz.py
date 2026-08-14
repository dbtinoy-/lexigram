"""Route-level authorization tests for relation endpoints (D1/D2/D3)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from lexigram.admin.auth.types import AdminSecurityEventType
from lexigram.admin.exceptions import PermissionDeniedError
from lexigram.admin.relations import RelationManager, register_relation_routes
from lexigram.result import Err, Ok, Result


class _Record:
    def __init__(self, record_id: str = "7") -> None:
        self.id = record_id


class _FakeParentDataSource:
    def __init__(self, parent: Any = None) -> None:
        self._parent = parent

    async def find_one(self, parent_id: Any) -> Any:
        return self._parent


class _AuditService:
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def log_event(self, **kwargs: Any) -> None:
        self.events.append(kwargs)


class _RaisingAuditService(_AuditService):
    async def log_event(self, **kwargs: Any) -> None:
        raise RuntimeError("audit store down")


def _make_request(path_params: dict[str, str], user: Any = object()) -> SimpleNamespace:
    """Build a minimal authenticated request stub."""
    return SimpleNamespace(
        path_params=path_params,
        state=SimpleNamespace(user=user),
        client=SimpleNamespace(host="127.0.0.1"),
        headers={},
    )


class _SpyRelationManager(RelationManager):
    """Manager recording predicate calls and renders on the class."""

    relationship_name = "pets"

    calls: list[str] = []
    renders: list[Any] = []
    view_parent_result: Result[None, PermissionDeniedError] | None = None
    create_result: Result[None, PermissionDeniedError] | None = None
    edit_result: Result[None, PermissionDeniedError] | None = None
    delete_result: Result[None, PermissionDeniedError] | None = None

    @classmethod
    def reset(cls) -> None:
        cls.calls = []
        cls.renders = []
        cls.view_parent_result = None
        cls.create_result = None
        cls.edit_result = None
        cls.delete_result = None

    @classmethod
    def table(cls, table_config: Any = None) -> list[Any]:
        return []

    async def get_query(self) -> list[Any]:
        return [_Record()]

    def create_form(self) -> str | None:
        return "<form>create</form>"

    def edit_form(self, record: Any) -> str | None:
        return "<form>edit</form>"

    async def render(self, request: Any, resource_name: str = "") -> str:
        self.__class__.renders.append(self.parent)
        return "<div>panel</div>"

    def can_view_parent(
        self, parent: Any, user: Any | None = None
    ) -> Result[None, PermissionDeniedError]:
        self.__class__.calls.append("can_view_parent")
        return (
            self.__class__.view_parent_result
            if self.__class__.view_parent_result is not None
            else Ok(None)
        )

    def can_create(
        self, user: Any | None = None
    ) -> Result[None, PermissionDeniedError]:
        self.__class__.calls.append("can_create")
        return (
            self.__class__.create_result
            if self.__class__.create_result is not None
            else Ok(None)
        )

    def can_edit(
        self, record: Any, user: Any | None = None
    ) -> Result[None, PermissionDeniedError]:
        self.__class__.calls.append("can_edit")
        return (
            self.__class__.edit_result
            if self.__class__.edit_result is not None
            else Ok(None)
        )

    def can_delete(
        self, record: Any, user: Any | None = None
    ) -> Result[None, PermissionDeniedError]:
        self.__class__.calls.append("can_delete")
        return (
            self.__class__.delete_result
            if self.__class__.delete_result is not None
            else Ok(None)
        )


class _BenignRelationManager(RelationManager):
    """Default-predicate manager rendering static panel HTML."""

    relationship_name = "pets"

    @classmethod
    def table(cls, table_config: Any = None) -> list[Any]:
        return []

    async def get_query(self) -> list[Any]:
        return [_Record()]

    def create_form(self) -> str | None:
        return "<form>create</form>"

    def edit_form(self, record: Any) -> str | None:
        return "<form>edit</form>"

    async def render(self, request: Any, resource_name: str = "") -> str:
        return "<div>panel</div>"


class _EmptyRelationManager(RelationManager):
    relationship_name = "pets"

    @classmethod
    def table(cls, table_config: Any = None) -> list[Any]:
        return []

    async def get_query(self) -> list[Any]:
        return []

    async def render(self, request: Any, resource_name: str = "") -> str:
        return "<div>empty panel</div>"


class TestFailClosed:
    """(a) route-level requests without a user are denied 403."""

    @pytest.mark.parametrize("index", [0, 1, 2, 3, 4, 5])
    @pytest.mark.asyncio
    async def test_each_handler_denies_without_user(self, index: int) -> None:
        _SpyRelationManager.reset()
        routes = register_relation_routes("users", _SpyRelationManager)
        request = SimpleNamespace(
            path_params={"parent_id": "1", "record_id": "7"},
            state=SimpleNamespace(user=None),
        )
        response = await routes[index].endpoint(request)
        assert response.status_code == 403
        assert "Permission denied" in response.body.decode()

    @pytest.mark.asyncio
    async def test_list_denies_on_missing_state_attribute(self) -> None:
        _SpyRelationManager.reset()
        routes = register_relation_routes("users", _SpyRelationManager)
        request = SimpleNamespace(path_params={"parent_id": "1"})
        response = await routes[0].endpoint(request)
        assert response.status_code == 403
        assert _SpyRelationManager.calls == []


class TestDefaultPreservation:
    """(b) default predicates with no data source preserve behavior."""

    @pytest.mark.asyncio
    async def test_list_renders_panel(self) -> None:
        routes = register_relation_routes("users", _BenignRelationManager)
        request = _make_request({"parent_id": "1"})
        response = await routes[0].endpoint(request)
        assert response.status_code == 200
        assert "<div>panel</div>" in response.body.decode()

    @pytest.mark.asyncio
    async def test_create_form_returns_manager_form(self) -> None:
        routes = register_relation_routes("users", _BenignRelationManager)
        request = _make_request({"parent_id": "1"})
        response = await routes[1].endpoint(request)
        assert "<form>create</form>" in response.body.decode()

    @pytest.mark.asyncio
    async def test_edit_form_fallback_on_missing_record(self) -> None:
        routes = register_relation_routes("users", _EmptyRelationManager)
        request = _make_request({"parent_id": "1", "record_id": "123"})
        response = await routes[3].endpoint(request)
        assert "Edit form for 123" in response.body.decode()

    @pytest.mark.asyncio
    async def test_create_rerenders_list(self) -> None:
        routes = register_relation_routes("users", _BenignRelationManager)
        request = _make_request({"parent_id": "1"})
        response = await routes[2].endpoint(request)
        assert "<div>panel</div>" in response.body.decode()

    @pytest.mark.asyncio
    async def test_update_rerenders_list(self) -> None:
        routes = register_relation_routes("users", _BenignRelationManager)
        request = _make_request({"parent_id": "1", "record_id": "7"})
        response = await routes[4].endpoint(request)
        assert "<div>panel</div>" in response.body.decode()

    @pytest.mark.asyncio
    async def test_delete_returns_empty_html(self) -> None:
        routes = register_relation_routes("users", _BenignRelationManager)
        request = _make_request({"parent_id": "1", "record_id": "7"})
        response = await routes[5].endpoint(request)
        assert response.body == b""


class TestDenyManager:
    """(c) deny-override managers 403 before any render, with audit."""

    @pytest.mark.asyncio
    async def test_update_denied_403_no_render_with_audit(self) -> None:
        _SpyRelationManager.reset()
        _SpyRelationManager.edit_result = Err(PermissionDeniedError("denied"))
        audit = _AuditService()
        routes = register_relation_routes(
            "users", _SpyRelationManager, audit_service=audit
        )
        request = _make_request({"parent_id": "1", "record_id": "7"})
        response = await routes[4].endpoint(request)
        assert response.status_code == 403
        assert "Permission denied" in response.body.decode()
        assert _SpyRelationManager.renders == []
        assert len(audit.events) == 1
        event = audit.events[0]
        assert event["event_type"] == AdminSecurityEventType.PERMISSION_DENIED
        assert event["success"] is False
        assert event["metadata"]["action"] == "relation.can_edit"
        assert event["metadata"]["parent_id"] == "1"

    @pytest.mark.asyncio
    async def test_edit_form_denied_returns_403(self) -> None:
        _SpyRelationManager.reset()
        _SpyRelationManager.edit_result = Err(PermissionDeniedError("denied"))
        audit = _AuditService()
        routes = register_relation_routes(
            "users", _SpyRelationManager, audit_service=audit
        )
        request = _make_request({"parent_id": "1", "record_id": "7"})
        response = await routes[3].endpoint(request)
        assert response.status_code == 403
        assert _SpyRelationManager.renders == []
        assert audit.events[0]["metadata"]["action"] == "relation.can_edit"

    @pytest.mark.asyncio
    async def test_create_denied_403_no_render_with_audit(self) -> None:
        _SpyRelationManager.reset()
        _SpyRelationManager.create_result = Err(PermissionDeniedError("denied"))
        audit = _AuditService()
        routes = register_relation_routes(
            "users", _SpyRelationManager, audit_service=audit
        )
        request = _make_request({"parent_id": "1"})
        response = await routes[2].endpoint(request)
        assert response.status_code == 403
        assert _SpyRelationManager.renders == []
        assert len(audit.events) == 1
        assert audit.events[0]["metadata"]["action"] == "relation.can_create"

    @pytest.mark.asyncio
    async def test_delete_denied_403_no_render_with_audit(self) -> None:
        _SpyRelationManager.reset()
        _SpyRelationManager.delete_result = Err(PermissionDeniedError("denied"))
        audit = _AuditService()
        routes = register_relation_routes(
            "users", _SpyRelationManager, audit_service=audit
        )
        request = _make_request({"parent_id": "1", "record_id": "7"})
        response = await routes[5].endpoint(request)
        assert response.status_code == 403
        assert _SpyRelationManager.renders == []
        assert len(audit.events) == 1
        assert audit.events[0]["metadata"]["action"] == "relation.can_delete"

    @pytest.mark.asyncio
    async def test_audit_failure_does_not_break_denial(self) -> None:
        _SpyRelationManager.reset()
        _SpyRelationManager.edit_result = Err(PermissionDeniedError("denied"))
        routes = register_relation_routes(
            "users", _SpyRelationManager, audit_service=_RaisingAuditService()
        )
        request = _make_request({"parent_id": "1", "record_id": "7"})
        response = await routes[4].endpoint(request)
        assert response.status_code == 403


class TestHostileParent:
    """(d) parent-IDOR gate: 403 on deny, 404 on missing parent, no data."""

    @pytest.mark.asyncio
    async def test_list_denied_403_no_data(self) -> None:
        _SpyRelationManager.reset()
        _SpyRelationManager.view_parent_result = Err(PermissionDeniedError("denied"))
        routes = register_relation_routes(
            "users",
            _SpyRelationManager,
            parent_data_source=_FakeParentDataSource(object()),
        )
        request = _make_request({"parent_id": "999"})
        response = await routes[0].endpoint(request)
        assert response.status_code == 403
        assert "panel" not in response.body.decode()
        assert _SpyRelationManager.renders == []

    @pytest.mark.asyncio
    async def test_list_missing_parent_404_no_render(self) -> None:
        _SpyRelationManager.reset()
        routes = register_relation_routes(
            "users",
            _SpyRelationManager,
            parent_data_source=_FakeParentDataSource(None),
        )
        request = _make_request({"parent_id": "999"})
        response = await routes[0].endpoint(request)
        assert response.status_code == 404
        assert "Parent not found" in response.body.decode()
        assert _SpyRelationManager.renders == []

    @pytest.mark.asyncio
    async def test_default_mount_renders_benign_parent(self) -> None:
        routes = register_relation_routes("users", _BenignRelationManager)
        request = _make_request({"parent_id": "1"})
        response = await routes[0].endpoint(request)
        assert response.status_code == 200
        assert "<div>panel</div>" in response.body.decode()

    @pytest.mark.asyncio
    async def test_resolved_parent_attached_to_manager_before_render(self) -> None:
        _SpyRelationManager.reset()
        parent = SimpleNamespace(id=1)
        routes = register_relation_routes(
            "users",
            _SpyRelationManager,
            parent_data_source=_FakeParentDataSource(parent),
        )
        request = _make_request({"parent_id": "1"})
        response = await routes[0].endpoint(request)
        assert response.status_code == 200
        assert _SpyRelationManager.renders == [parent]


class TestRecordMissing:
    """(d2) update/delete on a bogus record_id 404 without predicates."""

    @pytest.mark.asyncio
    async def test_update_missing_record_404(self) -> None:
        _SpyRelationManager.reset()
        routes = register_relation_routes("users", _SpyRelationManager)
        request = _make_request({"parent_id": "1", "record_id": "nope"})
        response = await routes[4].endpoint(request)
        assert response.status_code == 404
        assert "Not found" in response.body.decode()
        assert "can_edit" not in _SpyRelationManager.calls

    @pytest.mark.asyncio
    async def test_delete_missing_record_404(self) -> None:
        _SpyRelationManager.reset()
        routes = register_relation_routes("users", _SpyRelationManager)
        request = _make_request({"parent_id": "1", "record_id": "nope"})
        response = await routes[5].endpoint(request)
        assert response.status_code == 404
        assert "can_delete" not in _SpyRelationManager.calls

    @pytest.mark.asyncio
    async def test_delete_resolvable_record_keeps_empty_html(self) -> None:
        _SpyRelationManager.reset()
        routes = register_relation_routes("users", _SpyRelationManager)
        request = _make_request({"parent_id": "1", "record_id": "7"})
        response = await routes[5].endpoint(request)
        assert response.status_code == 200
        assert response.body == b""


class TestPredicateWiring:
    """(e) every registered handler consults at least one predicate."""

    @pytest.mark.asyncio
    async def test_all_six_handlers_consult_predicates(self) -> None:
        _SpyRelationManager.reset()
        parent = SimpleNamespace(id=1)
        routes = register_relation_routes(
            "users",
            _SpyRelationManager,
            parent_data_source=_FakeParentDataSource(parent),
        )

        list_resp = await routes[0].endpoint(_make_request({"parent_id": "1"}))
        assert list_resp.status_code == 200
        assert _SpyRelationManager.calls == ["can_view_parent"]
        _SpyRelationManager.reset()

        form_resp = await routes[1].endpoint(_make_request({"parent_id": "1"}))
        assert form_resp.status_code == 200
        assert _SpyRelationManager.calls == ["can_view_parent"]
        _SpyRelationManager.reset()

        create_resp = await routes[2].endpoint(_make_request({"parent_id": "1"}))
        assert create_resp.status_code == 200
        assert _SpyRelationManager.calls == ["can_create"]
        _SpyRelationManager.reset()

        edit_resp = await routes[3].endpoint(
            _make_request({"parent_id": "1", "record_id": "7"})
        )
        assert edit_resp.status_code == 200
        assert _SpyRelationManager.calls == ["can_view_parent", "can_edit"]
        _SpyRelationManager.reset()

        update_resp = await routes[4].endpoint(
            _make_request({"parent_id": "1", "record_id": "7"})
        )
        assert update_resp.status_code == 200
        assert _SpyRelationManager.calls == ["can_edit"]
        _SpyRelationManager.reset()

        delete_resp = await routes[5].endpoint(
            _make_request({"parent_id": "1", "record_id": "7"})
        )
        assert delete_resp.status_code == 200
        assert _SpyRelationManager.calls == ["can_delete"]
