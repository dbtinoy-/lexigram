"""Focused tests for DataTable Action base classes."""

from __future__ import annotations

from typing import Any

from lexigram.ui.actions.base import Action, ActionTarget, BulkAction


class TestActionTarget:
    def test_members(self) -> None:
        assert ActionTarget.DATA.value == "data"
        assert ActionTarget.MODAL.value == "modal"
        assert ActionTarget.SLIDE_OVER.value == "slide_over"
        assert ActionTarget.ROW.value == "row"
        assert ActionTarget.FULL_TABLE.value == "full_table"
        assert ActionTarget.EXTERNAL.value == "external"

    def test_all_members_are_string_enum(self) -> None:
        assert all(isinstance(m, str) for m in ActionTarget)


class TestActionConstruction:
    def test_defaults(self) -> None:
        action = Action("approve")
        assert action.name == "approve"
        assert action.label == "Approve"
        assert action._icon is None
        assert action._icon_position == "left"
        assert action._color == "primary"
        assert action._url is None
        assert action._visible is True
        assert action._disabled is False
        assert action._requires_confirmation is False
        assert action._confirmation_title == "Are you sure?"
        assert action._hx_swap == "outerHTML"
        assert action._target == "_self"

    def test_label_title_case(self) -> None:
        assert Action("approve_item").label == "Approve Item"

    def test_explicit_label(self) -> None:
        assert Action("approve", label="Custom").label == "Custom"

    def test_chainability(self) -> None:
        action = Action("a").icon("check").color("danger").url("/x")
        assert isinstance(action, Action)
        assert action._icon == "check"
        assert action._color == "danger"
        assert action._url == "/x"


class TestFluentSetters:
    def test_icon_position(self) -> None:
        action = Action("a").icon("trash", position="right")
        assert action._icon == "trash"
        assert action._icon_position == "right"

    def test_colors(self) -> None:
        a = Action("a")
        assert a.danger()._color == "danger"
        assert a.success()._color == "success"
        assert a.warning()._color == "warning"
        assert a.info()._color == "info"
        assert a.gray()._color == "gray"
        assert a.color("purple")._color == "purple"

    def test_url_with_target(self) -> None:
        action = Action("a").url("/x", target="_blank")
        assert action._url == "/x"
        assert action._target == "_blank"

    def test_url_callable(self) -> None:
        action = Action("a").url(lambda record: f"/users/{record['id']}")
        assert callable(action._url)

    def test_action_callback(self) -> None:
        cb = lambda record: None  # noqa: E731
        action = Action("a").action(cb)
        assert action._action is cb

    def test_open_modal(self) -> None:
        action = Action("a").open_modal()
        assert action._open_modal is True
        assert action._modal_component is None
        assert action._hx_push_url == "false"

    def test_open_modal_with_component(self) -> None:
        action = Action("a").open_modal("UserForm")
        assert action._modal_component == "UserForm"

    def test_slide_over(self) -> None:
        action = Action("a").slide_over()
        assert action._open_slide_over is True
        assert action._hx_target == "#slide-over-container"
        assert action._hx_swap == "innerHTML"

    def test_requires_confirmation_defaults(self) -> None:
        action = Action("a").requires_confirmation()
        assert action._requires_confirmation is True
        assert action._confirmation_title == "Are you sure?"
        assert action._confirmation_message is None

    def test_requires_confirmation_custom(self) -> None:
        action = Action("a").requires_confirmation(
            title="Delete permanently?", message="This cannot be undone."
        )
        assert action._confirmation_title == "Delete permanently?"
        assert action._confirmation_message == "This cannot be undone."

    def test_visible_bool(self) -> None:
        assert Action("a").visible(False)._visible is False

    def test_visible_callable(self) -> None:
        cb = lambda record: False  # noqa: E731
        action = Action("a").visible(cb)
        assert action._visible_callback is cb

    def test_disabled_bool(self) -> None:
        assert Action("a").disabled(True)._disabled is True

    def test_disabled_callable(self) -> None:
        cb = lambda record: True  # noqa: E731
        action = Action("a").disabled(cb)
        assert action._disabled_callback is cb


class TestHx:
    def test_hx_all_params(self) -> None:
        action = Action("a").hx(
            get="/g", post="/p", delete="/d", target="#z", swap="innerHTML", push_url="/u"
        )
        assert action._hx_get == "/g"
        assert action._hx_post == "/p"
        assert action._hx_delete == "/d"
        assert action._hx_target == "#z"
        assert action._hx_swap == "innerHTML"
        assert action._hx_push_url == "/u"

    def test_hx_partial(self) -> None:
        action = Action("a").hx(get="/g", target="#t")
        assert action._hx_get == "/g"
        assert action._hx_post is None
        assert action._hx_target == "#t"
        assert action._hx_swap == "outerHTML"

    def test_getters(self) -> None:
        action = Action("a").hx(get="/g", post="/p", delete="/d")
        assert action.get_hx_get() == "/g"
        assert action.get_hx_post() == "/p"
        assert action.get_hx_delete() == "/d"


class TestVisibilityAndState:
    def test_is_visible_default(self) -> None:
        assert Action("a").is_visible() is True

    def test_is_visible_bool_false(self) -> None:
        assert Action("a").visible(False).is_visible() is False

    def test_is_visible_callback(self) -> None:
        action = Action("a").visible(lambda record: record.get("active") is True)
        assert action.is_visible(record={"active": True}) is True
        assert action.is_visible(record={"active": False}) is False

    def test_is_visible_callback_none_record(self) -> None:
        seen: list[Any] = []

        def cb(record: dict) -> bool:
            seen.append(record)
            return True

        action = Action("a").visible(cb)
        assert action.is_visible() is True
        assert seen == [{}]

    def test_permission_service_denies(self) -> None:
        class Perm:
            def can_perform_action(self, user: Any, resource: str, name: str) -> bool:
                return False

        class User:
            user_id = "u1"

        action = Action("delete")
        assert (
            action.is_visible(
                user=User(), resource_name="users", permission_service=Perm()
            )
            is False
        )

    def test_permission_service_allows(self) -> None:
        class Perm:
            def can_perform_action(self, user: Any, resource: str, name: str) -> bool:
                return True

        class User:
            user_id = "u1"

        action = Action("delete")
        assert (
            action.is_visible(
                user=User(), resource_name="users", permission_service=Perm()
            )
            is True
        )

    def test_permission_service_ignored_without_user_attrs(self) -> None:
        seen: list[tuple[Any, str, str]] = []

        class Perm:
            def can_perform_action(self, user: Any, resource: str, name: str) -> bool:
                seen.append((user, resource, name))
                return False

        action = Action("delete")
        assert (
            action.is_visible(user=object(), resource_name="users", permission_service=Perm())
            is True
        )
        assert seen == []

    def test_is_disabled_default(self) -> None:
        assert Action("a").is_disabled() is False

    def test_is_disabled_callback(self) -> None:
        action = Action("a").disabled(lambda record: record["total"] > 5)
        assert action.is_disabled({"total": 10}) is True
        assert action.is_disabled({"total": 1}) is False

    def test_get_url_plain(self) -> None:
        assert Action("a").url("/plain").get_url() == "/plain"

    def test_get_url_callable(self) -> None:
        action = Action("a").url(lambda record: f"/x/{record.get('id')}")
        assert action.get_url({"id": 3}) == "/x/3"
        assert action.get_url() == "/x/None"


class TestRender:
    def test_render_hidden_when_not_visible(self) -> None:
        assert Action("a").visible(False).render(record={}) == ""

    def test_render_simple(self) -> None:
        el = Action("approve").render(record={})
        assert el.tag == "button"
        assert el.children == ["Approve"]
        assert "text-primary-600" in el.attrs["class_"]

    def test_render_with_color(self) -> None:
        el = Action("delete").danger().render(record={})
        assert "text-red-600" in el.attrs["class_"]

    def test_render_hx_substitution_with_dict(self) -> None:
        action = Action("edit").hx(get="/users/{id}/edit")
        el = action.render(record={"id": "42"})
        assert el.attrs["hx_get"] == "/users/42/edit"

    def test_render_plain_url_not_substituted(self) -> None:
        action = Action("edit").url("/users/{id}/edit")
        el = action.render(record={"id": "42"})
        assert el.attrs["href"] == "/users/{id}/edit"

    def test_render_hx_substitution_with_object_fallback(self) -> None:
        class Rec:
            user_id = "u-9"

        action = Action("edit").hx(get="/users/{id}/edit")
        el = action.render(record=Rec())
        assert el.attrs["hx_get"] == "/users/u-9/edit"

    def test_render_hx_substitution_object_with_pk(self) -> None:
        class Rec:
            pk = 7

        action = Action("edit").hx(get="/users/{id}/edit")
        el = action.render(record=Rec())
        assert el.attrs["hx_get"] == "/users/7/edit"

    def test_render_hx_substitution_missing_key_keeps_placeholder(self) -> None:
        action = Action("edit").hx(get="/users/{missing}/edit")
        el = action.render(record={"id": "42"})
        assert el.attrs["hx_get"] == "/users/{missing}/edit"

    def test_render_hx_substitution_invalid_keeps_value(self) -> None:
        action = Action("edit").hx(get="/users/{bad")
        el = action.render(record={"bad": 1})
        assert el.attrs["hx_get"] == "/users/{bad"

    def test_render_hx_get_post_delete_substitution(self) -> None:
        action = Action("a").hx(
            get="/g/{id}", post="/p/{id}", delete="/d/{id}"
        )
        el = action.render(record={"id": 5})
        assert el.attrs["hx_get"] == "/g/5"
        assert el.attrs["hx_post"] == "/p/5"
        assert el.attrs["hx_delete"] == "/d/5"

    def test_render_confirmation_default(self) -> None:
        el = Action("a").requires_confirmation().render(record={})
        assert el.attrs["hx_confirm"] == "Are you sure?"

    def test_render_confirmation_custom(self) -> None:
        el = Action("a").requires_confirmation(
            title="Delete?", message="Really delete this record?"
        ).render(record={})
        assert el.attrs["hx_confirm"] == "Really delete this record?"

    def test_render_no_confirmation(self) -> None:
        el = Action("a").render(record={})
        assert el.attrs["hx_confirm"] is None

    def test_render_unknown_color_passthrough(self) -> None:
        el = Action("a").color("purple").render(record={})
        assert "text-purple-600" in el.attrs["class_"]


class TestBulkAction:
    def test_deselect_after_default(self) -> None:
        assert BulkAction("bulk_delete")._deselect_after is True

    def test_deselect_after_setter(self) -> None:
        action = BulkAction("bulk_delete").deselect_after(False)
        assert isinstance(action, BulkAction)
        assert action._deselect_after is False

    def test_inherits_action_behavior(self) -> None:
        action = BulkAction("bulk_delete").danger()
        assert action._color == "danger"
        assert action.label == "Bulk Delete"