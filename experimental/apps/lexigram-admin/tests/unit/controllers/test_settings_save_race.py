"""The settings save path must survive an interleaved concurrent write.

The controller compares a revision token before writing. On its own that
leaves a time-of-check/time-of-use window: another session can commit
between the comparison and the write, and the second write would silently
discard it. These tests drive the real ``save_spec`` flow with a store that
mutates itself inside that exact window.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from lexigram.admin.controllers.settings import SettingsController
from lexigram.admin.settings.conflict import SettingsConflictError
from lexigram.admin.settings.panel.nodes import ConfigSpec, StringNode
from lexigram.admin.settings.panel.registry import ConfigRegistry, MemoryStore


class _RacingStore(MemoryStore):
    """Store whose value changes between the read and the conditional write.

    ``set_many_if_unchanged`` enforces the comparison the same way a real
    transactional backend does, so the controller sees a genuine late
    conflict rather than a mocked exception.
    """

    def __init__(self) -> None:
        super().__init__()
        self.writes: list[dict[str, Any]] = []
        self.intruder_value: str | None = None

    async def get(
        self, key: str, default: Any = None, tenant_id: str | None = None
    ) -> Any:
        value = await super().get(key, default, tenant_id=tenant_id)
        if self.intruder_value is not None and key.endswith(".title"):
            # Simulate another session committing right after this read.
            await super().set(key, self.intruder_value, tenant_id=tenant_id)
            self.intruder_value = None
        return value

    async def set_many_if_unchanged(
        self,
        items: dict[str, Any],
        expected: dict[str, Any],
        tenant_id: str | None = None,
    ) -> None:
        for key, want in expected.items():
            current = await super().get(key, None, tenant_id=tenant_id)
            if current is not None and str(current) != str(want):
                raise SettingsConflictError(f"changed: {key}")
        self.writes.append(dict(items))
        await super().set_many(items, tenant_id=tenant_id)

    async def supports_conditional_write(self) -> bool:
        return True


class _RaceSpec(ConfigSpec):
    namespace = "admin.race_test"
    label = "Race Test"
    icon = "bolt"
    description = ""
    title = StringNode(label="Title", default="original")


class _FakeUser:
    def __init__(self) -> None:
        self.permissions = frozenset({"admin.settings.edit"})
        self.roles: list[str] = []
        self.user_id = "user-1"
        self.username = "admin"


def _request(form_data: dict[str, str], hx: bool = False) -> MagicMock:
    req = MagicMock(spec=Request)
    req.method = "POST"
    req.headers = {"hx-request": "true"} if hx else {}
    req.query_params = {}
    req.path_params = {"namespace": _RaceSpec.namespace}

    async def _form() -> dict[str, str]:
        return form_data

    req.form = _form
    req.state = MagicMock(user=_FakeUser())
    req.scope = {}
    return req


def _build() -> tuple[SettingsController, _RacingStore, AsyncMock]:
    registry = ConfigRegistry()
    registry._specs[_RaceSpec.namespace] = _RaceSpec
    store = _RacingStore()
    registry.register_store("default", store)
    audit = AsyncMock()
    renderer = MagicMock()
    renderer.render_page = MagicMock(return_value=MagicMock(status_code=200))
    controller = SettingsController(
        renderer=renderer, audit_service=audit, registry=registry
    )
    return controller, store, audit


async def _revision(controller: SettingsController) -> str:
    values = await controller._registry.get_values(_RaceSpec.namespace)
    return controller._settings_revision(_RaceSpec, values)


class TestConcurrentSaveIsRejected:
    """A write landing inside the check/write window must not be lost."""

    @pytest.mark.asyncio
    async def test_uncontended_save_still_succeeds(self) -> None:
        controller, store, _ = _build()
        form = {"title": "mine", "settings_revision": await _revision(controller)}

        await controller.save_spec(_request(form))

        values = await controller._registry.get_values(_RaceSpec.namespace)
        assert values["title"] == "mine"
        assert len(store.writes) == 1

    @pytest.mark.asyncio
    async def test_interleaved_write_is_not_overwritten(self) -> None:
        controller, store, _ = _build()
        revision = await _revision(controller)
        # Another session commits after our revision check reads the values.
        store.intruder_value = "theirs"

        await controller.save_spec(
            _request({"title": "mine", "settings_revision": revision})
        )

        values = await controller._registry.get_values(_RaceSpec.namespace)
        assert values["title"] == "theirs"
        assert store.writes == []

    @pytest.mark.asyncio
    async def test_conflict_returns_409_for_a_plain_post(self) -> None:
        controller, store, _ = _build()
        revision = await _revision(controller)
        store.intruder_value = "theirs"

        response = await controller.save_spec(
            _request({"title": "mine", "settings_revision": revision})
        )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_conflict_is_audited_as_a_failed_save(self) -> None:
        controller, store, audit = _build()
        revision = await _revision(controller)
        store.intruder_value = "theirs"

        await controller.save_spec(
            _request({"title": "mine", "settings_revision": revision})
        )

        reasons = [
            call.kwargs["metadata"].get("reason")
            for call in audit.log_event.call_args_list
            if "metadata" in call.kwargs
        ]
        assert "concurrent_update_at_write" in reasons

    @pytest.mark.asyncio
    async def test_htmx_conflict_swaps_a_form_with_a_fresh_revision(self) -> None:
        """The user must be able to retry without reloading the page."""
        controller, store, _ = _build()
        revision = await _revision(controller)
        store.intruder_value = "theirs"

        response = await controller.save_spec(
            _request({"title": "mine", "settings_revision": revision}, hx=True)
        )
        body = bytes(response.body).decode()

        assert response.status_code == 200
        assert "changed in another session" in body
        # The re-rendered form must carry the post-conflict revision, not the
        # stale one, or the retry would conflict again forever.
        current = await controller._registry.get_values(_RaceSpec.namespace)
        assert controller._settings_revision(_RaceSpec, current) in body

    @pytest.mark.asyncio
    async def test_conflict_form_shows_the_other_session_value(self) -> None:
        controller, store, _ = _build()
        revision = await _revision(controller)
        store.intruder_value = "theirs"

        response = await controller.save_spec(
            _request({"title": "mine", "settings_revision": revision}, hx=True)
        )

        assert "theirs" in bytes(response.body).decode()
