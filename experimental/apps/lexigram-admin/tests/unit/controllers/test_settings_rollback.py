"""Settings rollback must round-trip through the normal save path.

A rollback re-submits stored values rather than writing them directly, so
validation, optimistic concurrency, permissions, and auditing all continue
to apply to it.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.controllers.settings import SettingsController
from lexigram.admin.settings.panel.nodes import ConfigSpec, SecretNode, StringNode
from lexigram.admin.settings.panel.registry import ConfigRegistry, MemoryStore
from lexigram.admin.settings.snapshots import SettingsSnapshotService


class _RollbackSpec(ConfigSpec):
    namespace = "admin.rollback_test"
    label = "Rollback Test"
    icon = "clock"
    description = ""
    title = StringNode(label="Title", default="original")
    api_key = SecretNode(label="API Key", default="")


class _FakeUser:
    def __init__(self) -> None:
        self.permissions = frozenset({"admin.settings.edit"})
        self.roles: list[str] = []
        self.user_id = "user-9"
        self.username = "admin"


def _request(form_data: dict[str, str]) -> MagicMock:
    req = MagicMock(spec=Request)
    req.method = "POST"
    req.headers = {}
    req.query_params = {}
    req.path_params = {"namespace": _RollbackSpec.namespace}

    async def _form() -> dict[str, str]:
        return form_data

    req.form = _form
    req.state = MagicMock(user=_FakeUser())
    req.scope = {}
    return req


def _build() -> tuple[SettingsController, SettingsSnapshotService, AsyncMock]:
    registry = ConfigRegistry()
    registry._specs[_RollbackSpec.namespace] = _RollbackSpec
    registry.register_store("default", MemoryStore())
    snapshots = SettingsSnapshotService()
    audit = AsyncMock()
    renderer = MagicMock()
    renderer.render_page = MagicMock(return_value=MagicMock(status_code=200))
    controller = SettingsController(
        renderer=renderer,
        audit_service=audit,
        registry=registry,
        snapshot_service=snapshots,
    )
    return controller, snapshots, audit


async def _revision(controller: SettingsController) -> str:
    values = await controller._registry.get_values(_RollbackSpec.namespace)
    return controller._settings_revision(_RollbackSpec, values)


async def _values(controller: SettingsController) -> dict[str, Any]:
    return await controller._registry.get_values(_RollbackSpec.namespace)


class TestSnapshotOnSave:
    """Every successful save records the state it replaced."""

    @pytest.mark.asyncio
    async def test_save_captures_previous_values(self) -> None:
        controller, snapshots, _ = _build()

        await controller.save_spec(
            _request(
                {"title": "changed", "settings_revision": await _revision(controller)}
            )
        )

        history = await snapshots.list_history(_RollbackSpec.namespace)
        assert len(history) == 1
        # The snapshot must hold the value being replaced, not the new one.
        assert history[0].values["title"] == "original"

    @pytest.mark.asyncio
    async def test_noop_save_does_not_create_history(self) -> None:
        controller, snapshots, _ = _build()

        await controller.save_spec(
            _request(
                {"title": "original", "settings_revision": await _revision(controller)}
            )
        )

        assert await snapshots.list_history(_RollbackSpec.namespace) == []

    @pytest.mark.asyncio
    async def test_secret_values_are_not_snapshotted(self) -> None:
        controller, snapshots, _ = _build()

        await controller.save_spec(
            _request(
                {
                    "title": "changed",
                    "api_key": "s3cret",
                    "settings_revision": await _revision(controller),
                }
            )
        )

        history = await snapshots.list_history(_RollbackSpec.namespace)
        assert "api_key" not in history[0].values

    @pytest.mark.asyncio
    async def test_rejected_save_records_no_snapshot(self) -> None:
        """A stale submission changes nothing, so there is nothing to record."""
        controller, snapshots, _ = _build()

        await controller.save_spec(
            _request({"title": "changed", "settings_revision": "stale"})
        )

        assert await snapshots.list_history(_RollbackSpec.namespace) == []


class TestRollback:
    """A rollback restores captured values through the save path."""

    @pytest.mark.asyncio
    async def test_restores_previous_values(self) -> None:
        controller, snapshots, _ = _build()
        await controller.save_spec(
            _request(
                {"title": "changed", "settings_revision": await _revision(controller)}
            )
        )
        assert (await _values(controller))["title"] == "changed"

        snapshot = (await snapshots.list_history(_RollbackSpec.namespace))[0]
        await controller.save_spec(
            _request(
                {
                    "rollback_to": snapshot.snapshot_id,
                    "settings_revision": await _revision(controller),
                }
            )
        )

        assert (await _values(controller))["title"] == "original"

    @pytest.mark.asyncio
    async def test_rollback_restores_explicit_ownership_when_value_equals_default(
        self,
    ) -> None:
        """A snapshot remembers explicit ownership, not only effective value."""
        controller, snapshots, _ = _build()
        store = controller._registry._stores["default"]
        await store.set(f"{_RollbackSpec.namespace}.title", "original")
        snapshot = await snapshots.capture(
            _RollbackSpec.namespace,
            {"title": "original"},
        )
        await store.delete(f"{_RollbackSpec.namespace}.title")

        await controller.save_spec(
            _request(
                {
                    "rollback_to": snapshot.snapshot_id,
                    "settings_revision": await _revision(controller),
                }
            )
        )

        assert await store.contains(f"{_RollbackSpec.namespace}.title") is True
        assert (await _values(controller))["title"] == "original"

    @pytest.mark.asyncio
    async def test_rollback_is_itself_snapshotted(self) -> None:
        """A rollback is a forward change and must be reversible in turn."""
        controller, snapshots, _ = _build()
        await controller.save_spec(
            _request(
                {"title": "changed", "settings_revision": await _revision(controller)}
            )
        )
        snapshot = (await snapshots.list_history(_RollbackSpec.namespace))[0]

        await controller.save_spec(
            _request(
                {
                    "rollback_to": snapshot.snapshot_id,
                    "settings_revision": await _revision(controller),
                }
            )
        )

        history = await snapshots.list_history(_RollbackSpec.namespace)
        assert len(history) == 2
        assert history[0].values["title"] == "changed"

    @pytest.mark.asyncio
    async def test_rollback_is_audited_as_such(self) -> None:
        controller, snapshots, audit = _build()
        await controller.save_spec(
            _request(
                {"title": "changed", "settings_revision": await _revision(controller)}
            )
        )
        snapshot = (await snapshots.list_history(_RollbackSpec.namespace))[0]

        await controller.save_spec(
            _request(
                {
                    "rollback_to": snapshot.snapshot_id,
                    "settings_revision": await _revision(controller),
                }
            )
        )

        flags = [
            call.kwargs["metadata"].get("rollback")
            for call in audit.log_event.call_args_list
            if "metadata" in call.kwargs
        ]
        assert True in flags

    @pytest.mark.asyncio
    async def test_stale_revision_blocks_rollback(self) -> None:
        """Rollback is not a bypass for optimistic concurrency."""
        controller, snapshots, _ = _build()
        await controller.save_spec(
            _request(
                {"title": "changed", "settings_revision": await _revision(controller)}
            )
        )
        snapshot = (await snapshots.list_history(_RollbackSpec.namespace))[0]

        response = await controller.save_spec(
            _request(
                {"rollback_to": snapshot.snapshot_id, "settings_revision": "stale"}
            )
        )

        assert response.status_code == 409
        assert (await _values(controller))["title"] == "changed"

    @pytest.mark.asyncio
    async def test_unknown_snapshot_falls_through_to_a_normal_save(self) -> None:
        """An unresolvable id must not silently wipe the namespace."""
        controller, _, _ = _build()

        await controller.save_spec(
            _request(
                {
                    "rollback_to": "does-not-exist",
                    "title": "typed-by-hand",
                    "settings_revision": await _revision(controller),
                }
            )
        )

        assert (await _values(controller))["title"] == "typed-by-hand"

    @pytest.mark.asyncio
    async def test_snapshot_from_another_namespace_is_refused(self) -> None:
        controller, snapshots, _ = _build()
        foreign = await snapshots.capture("admin.other", {"title": "foreign"})

        await controller.save_spec(
            _request(
                {
                    "rollback_to": foreign.snapshot_id,
                    "title": "mine",
                    "settings_revision": await _revision(controller),
                }
            )
        )

        assert (await _values(controller))["title"] == "mine"

    @pytest.mark.asyncio
    async def test_secrets_are_not_restored_by_rollback(self) -> None:
        """Secrets were never captured, so a rollback must leave them alone."""
        controller, snapshots, _ = _build()
        await controller.save_spec(
            _request(
                {
                    "title": "changed",
                    "api_key": "keep-me",
                    "settings_revision": await _revision(controller),
                }
            )
        )
        snapshot = (await snapshots.list_history(_RollbackSpec.namespace))[0]

        await controller.save_spec(
            _request(
                {
                    "rollback_to": snapshot.snapshot_id,
                    "settings_revision": await _revision(controller),
                }
            )
        )

        assert (await _values(controller))["api_key"] == "keep-me"
