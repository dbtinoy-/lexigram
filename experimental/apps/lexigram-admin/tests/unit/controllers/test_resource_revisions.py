"""Revision history, diff, and revert must be reachable and safe.

``RevisionService`` recorded a snapshot after every create and update, but
no route ever read them back, so ``revert_data()`` was unreachable dead
code. These tests drive the endpoints that expose it.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.controllers.resource import ResourceController, ResourceMeta
from lexigram.admin.services.revisions import RevisionService


class _Store:
    """Minimal in-memory data source for the controller under test."""

    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {
            "1": {"id": "1", "name": "current", "email": "now@test.com"}
        }
        self.updates: list[tuple[str, dict[str, Any]]] = []

    def find_one(self, item_id: Any) -> dict[str, Any] | None:
        return self.records.get(str(item_id))

    def update(self, item_id: Any, data: dict[str, Any]) -> dict[str, Any]:
        self.updates.append((str(item_id), dict(data)))
        self.records[str(item_id)].update(data)
        return self.records[str(item_id)]


class _RevisionController(ResourceController[dict]):
    meta = ResourceMeta(name="item", label="Item", label_plural="Items", prefix="")

    def __init__(self, data_source: _Store) -> None:
        super().__init__(data_source=data_source)
        self._store = data_source

    def get_data_source(self) -> _Store:
        return self._store

    def validate_update(self, item_id: Any, data: dict[str, Any]) -> dict[str, Any]:
        return dict(data)


def _request(
    method: str = "GET",
    path_params: dict[str, str] | None = None,
    query: dict[str, str] | None = None,
    hx: bool = False,
) -> MagicMock:
    req = MagicMock(spec=Request)
    req.method = method
    req.headers = {"hx-request": "true"} if hx else {}
    req.query_params = query or {}
    req.path_params = path_params or {}
    req.state = MagicMock(user=MagicMock(id="actor-1"))
    req.scope = {}
    req.app = MagicMock(state=MagicMock(admin_prefix=""))
    return req


async def _seeded() -> tuple[_RevisionController, _Store, RevisionService, list[str]]:
    """Controller with two recorded revisions, oldest first."""
    store = _Store()
    controller = _RevisionController(store)
    service = RevisionService()
    controller.set_revision_service(service)

    first = await service.record(
        "item", "1", {"id": "1", "name": "original", "email": "old@test.com"}
    )
    second = await service.record(
        "item", "1", {"id": "1", "name": "current", "email": "now@test.com"}
    )
    return controller, store, service, [first.revision_id, second.revision_id]


class TestRevisionHistory:
    """History lists snapshots and offers restore only where meaningful."""

    @pytest.mark.asyncio
    async def test_lists_recorded_revisions(self) -> None:
        controller, _, _, ids = await _seeded()

        response = await controller.revision_history(_request(path_params={"id": "1"}))
        body = bytes(response.body).decode()

        assert response.status_code == 200
        for revision_id in ids:
            assert revision_id in body

    @pytest.mark.asyncio
    async def test_current_revision_offers_no_restore(self) -> None:
        """Reverting to the newest snapshot is a no-op, so it is not offered."""
        controller, _, _, ids = await _seeded()

        body = bytes(
            (await controller.revision_history(_request(path_params={"id": "1"}))).body
        ).decode()

        assert f'value="{ids[0]}"' in body
        assert f'value="{ids[1]}"' not in body

    @pytest.mark.asyncio
    async def test_empty_history_is_not_an_error(self) -> None:
        controller, _, _, _ = await _seeded()

        response = await controller.revision_history(
            _request(path_params={"id": "does-not-exist"})
        )

        assert response.status_code == 200
        assert "No revisions" in bytes(response.body).decode()

    @pytest.mark.asyncio
    async def test_disabled_without_a_service(self) -> None:
        controller = _RevisionController(_Store())

        response = await controller.revision_history(_request(path_params={"id": "1"}))

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_comment_is_escaped(self) -> None:
        """Snapshot metadata is attacker-influenced and must not be raw HTML."""
        controller, _, service, _ = await _seeded()
        await service.record(
            "item", "1", {"name": "x"}, comment="<script>alert(1)</script>"
        )

        body = bytes(
            (await controller.revision_history(_request(path_params={"id": "1"}))).body
        ).decode()

        assert "<script>" not in body
        assert "&lt;script&gt;" in body


class TestRevisionDiff:
    """Diff compares two snapshots field by field."""

    @pytest.mark.asyncio
    async def test_reports_changed_fields(self) -> None:
        controller, _, _, ids = await _seeded()

        response = await controller.revision_diff(
            _request(path_params={"id": "1"}, query={"from": ids[0], "to": ids[1]})
        )
        body = bytes(response.body).decode()

        assert "original" in body
        assert "current" in body

    @pytest.mark.asyncio
    async def test_missing_parameters_are_rejected(self) -> None:
        controller, _, _, ids = await _seeded()

        response = await controller.revision_diff(
            _request(path_params={"id": "1"}, query={"from": ids[0]})
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_unknown_revision_is_not_found(self) -> None:
        controller, _, _, ids = await _seeded()

        response = await controller.revision_diff(
            _request(path_params={"id": "1"}, query={"from": ids[0], "to": "nope"})
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_identical_revisions_report_no_changes(self) -> None:
        controller, _, _, ids = await _seeded()

        response = await controller.revision_diff(
            _request(path_params={"id": "1"}, query={"from": ids[0], "to": ids[0]})
        )

        assert "identical" in bytes(response.body).decode()

    @pytest.mark.asyncio
    async def test_values_are_escaped(self) -> None:
        controller, _, service, _ = await _seeded()
        a = await service.record("item", "2", {"bio": "safe"})
        b = await service.record("item", "2", {"bio": "<img src=x onerror=1>"})

        body = bytes(
            (
                await controller.revision_diff(
                    _request(path_params={"id": "2"}, query={"from": a.revision_id, "to": b.revision_id})
                )
            ).body
        ).decode()

        assert "<img" not in body
        assert "&lt;img" in body


class TestRevisionRevert:
    """Revert applies a snapshot through the normal update path."""

    @pytest.mark.asyncio
    async def test_restores_prior_values(self) -> None:
        controller, store, _, ids = await _seeded()

        response = await controller.revision_revert(
            _request("POST", {"id": "1", "revision_id": ids[0]})
        )

        assert response.status_code == 303
        assert store.records["1"]["name"] == "original"

    @pytest.mark.asyncio
    async def test_identity_columns_are_not_replayed(self) -> None:
        """Restoring content must not rewrite identity or audit columns."""
        controller, store, service, _ = await _seeded()
        stale = await service.record(
            "item",
            "1",
            {"id": "999", "created_at": "2001-01-01", "name": "old"},
        )

        await controller.revision_revert(
            _request("POST", {"id": "1", "revision_id": stale.revision_id})
        )

        # The live record's own id survives (it comes from the current row),
        # but the snapshot's stale identity and audit values must not be
        # replayed over it.
        _, written = store.updates[-1]
        assert written["id"] == "1"
        assert written.get("created_at") != "2001-01-01"
        assert written["name"] == "old"

    @pytest.mark.asyncio
    async def test_revert_is_itself_snapshotted(self) -> None:
        """A revert must be reversible like any other forward change."""
        controller, _, service, ids = await _seeded()
        before = len(await service.list_revisions("item", "1"))

        await controller.revision_revert(
            _request("POST", {"id": "1", "revision_id": ids[0]})
        )

        after = await service.list_revisions("item", "1")
        assert len(after) == before + 1
        assert "revert to" in after[0].comment

    @pytest.mark.asyncio
    async def test_unknown_revision_is_not_found(self) -> None:
        controller, store, _, _ = await _seeded()

        response = await controller.revision_revert(
            _request("POST", {"id": "1", "revision_id": "missing"})
        )

        assert response.status_code == 404
        assert store.updates == []

    @pytest.mark.asyncio
    async def test_missing_record_is_not_found(self) -> None:
        controller, _, _, ids = await _seeded()

        response = await controller.revision_revert(
            _request("POST", {"id": "nope", "revision_id": ids[0]})
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_permission_is_enforced_against_the_live_record(self) -> None:
        """Revert must not be a way around normal update authorization."""
        controller, store, _, ids = await _seeded()
        controller.can_update = lambda item: False  # type: ignore[assignment]

        response = await controller.revision_revert(
            _request("POST", {"id": "1", "revision_id": ids[0]})
        )

        assert response.status_code == 403
        assert store.updates == []

    @pytest.mark.asyncio
    async def test_htmx_revert_redirects_via_header(self) -> None:
        controller, _, _, ids = await _seeded()

        response = await controller.revision_revert(
            _request("POST", {"id": "1", "revision_id": ids[0]}, hx=True)
        )

        assert response.status_code == 200
        assert response.headers["HX-Redirect"].endswith("/item/1")

    @pytest.mark.asyncio
    async def test_revert_is_audited(self) -> None:
        controller, _, _, ids = await _seeded()
        audit = AsyncMock()
        controller.set_audit_logger(audit)

        await controller.revision_revert(
            _request("POST", {"id": "1", "revision_id": ids[0]})
        )

        assert audit.log.await_count == 1

    @pytest.mark.asyncio
    async def test_snapshot_invalid_for_current_schema_is_rejected(self) -> None:
        """An old snapshot may no longer validate; that is a 422, not a 500."""
        controller, store, _, ids = await _seeded()

        def _reject(item_id: Any, data: dict[str, Any]) -> dict[str, Any]:
            raise ValueError("schema changed")

        controller.validate_update = _reject  # type: ignore[assignment]

        response = await controller.revision_revert(
            _request("POST", {"id": "1", "revision_id": ids[0]})
        )

        assert response.status_code == 422
        assert store.updates == []

    @pytest.mark.asyncio
    async def test_disabled_without_a_service(self) -> None:
        controller = _RevisionController(_Store())

        response = await controller.revision_revert(
            _request("POST", {"id": "1", "revision_id": "x"})
        )

        assert response.status_code == 404


class TestRoutesAreRegistered:
    """The endpoints must actually be mounted, not merely defined."""

    def test_revision_routes_exist(self) -> None:
        controller = _RevisionController(_Store())
        paths = {(r.path, tuple(sorted(r.methods))) for r in controller.get_routes()}

        assert ("/item/{id}/revisions", ("GET", "HEAD")) in paths
        assert ("/item/{id}/revisions/diff", ("GET", "HEAD")) in paths
        assert ("/item/{id}/revisions/{revision_id}/revert", ("POST",)) in paths
