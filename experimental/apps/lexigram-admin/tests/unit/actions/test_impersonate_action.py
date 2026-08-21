"""Unit tests for ImpersonateAction."""

from __future__ import annotations

from types import SimpleNamespace

from lexigram.admin.actions.standard import ImpersonateAction
from lexigram.admin.actions.types import ActionContext


class TestImpersonateActionVisibility:
    def test_hidden_for_own_record(self) -> None:
        action = ImpersonateAction()
        record = {"id": "admin1", "name": "Admin One"}
        user = SimpleNamespace(id="admin1")
        assert action.visible_for(record, user) is False

    def test_visible_for_other_records(self) -> None:
        action = ImpersonateAction()
        record = {"id": "user-123", "name": "Other User"}
        user = SimpleNamespace(id="admin1")
        assert action.visible_for(record, user) is True

    def test_visible_when_user_is_none(self) -> None:
        action = ImpersonateAction()
        record = {"id": "user-123", "name": "Other User"}
        assert action.visible_for(record, None) is True


class TestImpersonateActionUrl:
    def test_get_url_shape(self) -> None:
        action = ImpersonateAction()
        record = {"id": "user-123", "name": "Other User"}
        ctx = ActionContext(resource_name="users", resource_prefix="/admin/users")
        assert action._get_url(record, ctx) == "/admin/impersonate/user-123"

    def test_get_url_none_when_no_record_id(self) -> None:
        action = ImpersonateAction()
        ctx = ActionContext(resource_name="users", resource_prefix="/admin/users")
        assert action._get_url({}, ctx) is None


class TestImpersonateActionHtmxAttrs:
    def test_htmx_attrs_use_post_and_confirm(self) -> None:
        action = ImpersonateAction()
        record = {"id": "user-123", "name": "Other User"}
        ctx = ActionContext(resource_name="users", resource_prefix="/admin/users")
        url = action._get_url(record, ctx)
        attrs = action._get_htmx_attrs(url, record, ctx)
        assert attrs["hx-post"] == "/admin/impersonate/user-123"
        assert attrs["hx-target"] == "body"
        assert attrs["hx-swap"] == "none"
        assert "hx-confirm" in attrs
