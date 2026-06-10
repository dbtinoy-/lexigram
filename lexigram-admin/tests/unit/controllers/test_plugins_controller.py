"""Tests for the PluginsController (list + toggle plugin state)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request

from lexigram.admin.controllers.plugins import PluginsController
from lexigram.contracts.plugins import PluginDescriptor


def _descriptor(name: str, entry: str, display: str | None = None) -> PluginDescriptor:
    return PluginDescriptor(
        name=name,
        display_name=display or name.title(),
        description=f"{name} description.",
        icon="box",
        provider_entry_point=entry,
    )


def _mock_request(
    method: str = "GET",
    form_data: dict[str, str] | None = None,
    user: object | None = None,
    session: dict[str, str] | None = None,
) -> MagicMock:
    req = MagicMock(spec=Request)
    req.method = method
    req.headers = {}
    req.query_params = {}
    req.path_params = {}
    req.session = session or {}

    async def _form() -> dict[str, str]:
        return form_data or {}

    req.form = _form
    req.state = MagicMock(user=user)
    req.scope = {}
    return req


class _FakeUser:
    """AdminUser stand-in with permissions."""

    def __init__(
        self,
        permissions: frozenset[str] | None = None,
        roles: list[str] | None = None,
    ) -> None:
        self.permissions = permissions or frozenset({"admin.settings.edit"})
        self.roles = roles or []
        self.user_id = "user-1"
        self.username = "admin"


class _FakeCsrf:
    """AdminCsrfServiceProtocol stand-in."""

    def __init__(self, valid: bool = True) -> None:
        self._valid = valid

    def generate_token(self, session_id: str) -> str:
        return "test-csrf-token"

    def validate_token(self, session_id: str, token: str) -> bool:
        return self._valid and token == "test-csrf-token"


class TestPluginsController:
    """Tests for PluginsController."""

    @pytest.fixture
    def renderer(self) -> MagicMock:
        renderer = MagicMock()
        renderer.render_page = MagicMock(return_value=MagicMock(status_code=200))
        return renderer

    @pytest.fixture
    def controller(self, renderer: MagicMock) -> PluginsController:
        return PluginsController(
            renderer=renderer,
            csrf_service=_FakeCsrf(),
            audit_service=AsyncMock(),
        )

    @pytest.fixture
    def descriptors(self) -> list[PluginDescriptor]:
        return [
            _descriptor("relay-gateway", "relay-gateway"),
            _descriptor("rag", "rag"),  # noqa: SIM117 — intentional distinct entries
        ]

    @pytest.mark.asyncio
    async def test_index_renders_rows_with_state(
        self,
        controller: PluginsController,
        renderer: MagicMock,
        descriptors: list[PluginDescriptor],
    ) -> None:
        with (
            patch(
                "lexigram.plugins.discovery.discover_plugins",
                return_value=descriptors,
            ),
            patch("lexigram.plugins.state.load_disabled", return_value={"rag"}),
        ):
            resp = await controller.index(
                _mock_request(user=_FakeUser(), session={"csrf_session_id": "s1"})
            )
        assert resp.status_code == 200
        renderer.render_page.assert_called_once()
        args, kwargs = renderer.render_page.call_args
        assert kwargs["title"] == "Plugins"
        body = str(args[0])
        assert "relay-gateway" in body
        assert "rag" in body
        assert "Disabled" in body

    @pytest.mark.asyncio
    async def test_index_renders_empty_state_without_plugins_package(
        self, controller: PluginsController, renderer: MagicMock
    ) -> None:
        with patch(
            "lexigram.admin.controllers.plugins._load_toolbox",
            return_value=None,
        ):
            resp = await controller.index(
                _mock_request(user=_FakeUser(), session={"csrf_session_id": "s1"})
            )
        assert resp.status_code == 200
        renderer.render_page.assert_called_once()
        args, _ = renderer.render_page.call_args
        assert "not installed" in str(args[0]).lower()

    @pytest.mark.asyncio
    async def test_toggle_disables_plugin(
        self,
        controller: PluginsController,
        descriptors: list[PluginDescriptor],
    ) -> None:
        with (
            patch(
                "lexigram.plugins.discovery.discover_plugins",
                return_value=descriptors,
            ),
            patch("lexigram.plugins.state.load_disabled", return_value=set()),
            patch("lexigram.plugins.state.save_disabled") as save,
        ):
            resp = await controller.toggle(
                _mock_request(
                    method="POST",
                    form_data={"plugin": "rag", "csrf_token": "test-csrf-token"},
                    user=_FakeUser(),
                    session={"csrf_session_id": "s1"},
                )
            )
        assert resp.status_code == 302
        assert resp.headers["location"].startswith("/admin/plugins")
        save.assert_called_once()
        assert save.call_args is not None
        assert save.call_args.args[0] == {"rag"}

    @pytest.mark.asyncio
    async def test_toggle_enables_plugin(
        self,
        controller: PluginsController,
        descriptors: list[PluginDescriptor],
    ) -> None:
        with (
            patch(
                "lexigram.plugins.discovery.discover_plugins",
                return_value=descriptors,
            ),
            patch("lexigram.plugins.state.load_disabled", return_value={"rag"}),
            patch("lexigram.plugins.state.save_disabled") as save,
        ):
            resp = await controller.toggle(
                _mock_request(
                    method="POST",
                    form_data={"plugin": "rag", "csrf_token": "test-csrf-token"},
                    user=_FakeUser(),
                    session={"csrf_session_id": "s1"},
                )
            )
        assert resp.status_code == 302
        save.assert_called_once()
        assert save.call_args is not None
        assert save.call_args.args[0] == set()

    @pytest.mark.asyncio
    async def test_toggle_rejects_bad_csrf(
        self, renderer: MagicMock, descriptors: list[PluginDescriptor]
    ) -> None:
        controller = PluginsController(
            renderer=renderer,
            csrf_service=_FakeCsrf(valid=False),
            audit_service=AsyncMock(),
        )
        with (
            patch(
                "lexigram.plugins.discovery.discover_plugins",
                return_value=descriptors,
            ),
            patch("lexigram.plugins.state.load_disabled", return_value=set()),
            patch("lexigram.plugins.state.save_disabled") as save,
        ):
            resp = await controller.toggle(
                _mock_request(
                    method="POST",
                    form_data={"plugin": "rag", "csrf_token": "wrong-token"},
                    user=_FakeUser(),
                    session={"csrf_session_id": "s1"},
                )
            )
        assert resp.status_code == 302
        assert "error" in resp.headers["location"]
        save.assert_not_called()

    @pytest.mark.asyncio
    async def test_toggle_rejects_without_permission(
        self, renderer: MagicMock, descriptors: list[PluginDescriptor]
    ) -> None:
        controller = PluginsController(renderer=renderer, csrf_service=_FakeCsrf())
        with (
            patch(
                "lexigram.plugins.discovery.discover_plugins",
                return_value=descriptors,
            ),
            patch("lexigram.plugins.state.load_disabled", return_value=set()),
            patch("lexigram.plugins.state.save_disabled") as save,
        ):
            resp = await controller.toggle(
                _mock_request(
                    method="POST",
                    form_data={"plugin": "rag", "csrf_token": "test-csrf-token"},
                    user=_FakeUser(permissions=frozenset({"admin.other"})),
                    session={"csrf_session_id": "s1"},
                )
            )
        assert resp.status_code == 302
        assert "error" in resp.headers["location"]
        save.assert_not_called()

    @pytest.mark.asyncio
    async def test_toggle_superadmin_bypasses_permission_gate(
        self, renderer: MagicMock, descriptors: list[PluginDescriptor]
    ) -> None:
        controller = PluginsController(renderer=renderer, csrf_service=_FakeCsrf())
        with (
            patch(
                "lexigram.plugins.discovery.discover_plugins",
                return_value=descriptors,
            ),
            patch("lexigram.plugins.state.load_disabled", return_value=set()),
            patch("lexigram.plugins.state.save_disabled") as save,
        ):
            resp = await controller.toggle(
                _mock_request(
                    method="POST",
                    form_data={
                        "plugin": "relay-gateway",
                        "csrf_token": "test-csrf-token",
                    },
                    user=_FakeUser(permissions=frozenset(), roles=["superadmin"]),
                    session={"csrf_session_id": "s1"},
                )
            )
        assert resp.status_code == 302
        save.assert_called_once()

    @pytest.mark.asyncio
    async def test_toggle_ignores_unknown_plugin(
        self,
        controller: PluginsController,
        descriptors: list[PluginDescriptor],
    ) -> None:
        with (
            patch(
                "lexigram.plugins.discovery.discover_plugins",
                return_value=descriptors,
            ),
            patch("lexigram.plugins.state.load_disabled", return_value=set()),
            patch("lexigram.plugins.state.save_disabled") as save,
        ):
            resp = await controller.toggle(
                _mock_request(
                    method="POST",
                    form_data={"plugin": "ghost", "csrf_token": "test-csrf-token"},
                    user=_FakeUser(),
                    session={"csrf_session_id": "s1"},
                )
            )
        assert resp.status_code == 302
        assert "error" in resp.headers["location"]
        save.assert_not_called()

    @pytest.mark.asyncio
    async def test_toggle_logs_audit(
        self, renderer: MagicMock, descriptors: list[PluginDescriptor]
    ) -> None:
        audit = AsyncMock()
        controller = PluginsController(
            renderer=renderer,
            csrf_service=_FakeCsrf(),
            audit_service=audit,
        )
        with (
            patch(
                "lexigram.plugins.discovery.discover_plugins",
                return_value=descriptors,
            ),
            patch("lexigram.plugins.state.load_disabled", return_value=set()),
            patch("lexigram.plugins.state.save_disabled"),
        ):
            await controller.toggle(
                _mock_request(
                    method="POST",
                    form_data={"plugin": "rag", "csrf_token": "test-csrf-token"},
                    user=_FakeUser(),
                    session={"csrf_session_id": "s1"},
                )
            )
        audit.log_event.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_prefix_is_plugins(self) -> None:
        assert PluginsController.prefix == "/plugins"
