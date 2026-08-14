"""Tests for action types — ActionColor, ActionContext, ConfirmationConfig."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from lexigram.admin.actions.types import (
    ActionColor,
    ActionContext,
    ConfirmationConfig,
)


class TestActionColor:
    """Tests for ActionColor enum."""

    def test_has_expected_values(self) -> None:
        values = {c.value for c in ActionColor}
        assert values == {"gray", "primary", "secondary", "success", "warning", "danger", "info"}

    def test_values_match_strings(self) -> None:
        assert ActionColor.GRAY.value == "gray"
        assert ActionColor.PRIMARY.value == "primary"
        assert ActionColor.SUCCESS.value == "success"
        assert ActionColor.WARNING.value == "warning"
        assert ActionColor.DANGER.value == "danger"
        assert ActionColor.INFO.value == "info"

    def test_is_str_enum(self) -> None:
        assert isinstance(ActionColor.GRAY, str)


class TestActionContext:
    """Tests for ActionContext dataclass."""

    def test_default_construction(self) -> None:
        ctx = ActionContext()
        assert ctx.request is None
        assert ctx.user is None
        assert ctx.resource_name == ""

    def test_all_args_construction(self) -> None:
        request = object()
        user = object()
        ctx = ActionContext(request=request, user=user, resource_name="users")
        assert ctx.request is request
        assert ctx.user is user
        assert ctx.resource_name == "users"

    def test_fields_are_accessible(self) -> None:
        ctx = ActionContext(request="req", user="admin", resource_name="projects")
        assert ctx.request == "req"
        assert ctx.user == "admin"
        assert ctx.resource_name == "projects"

    def test_metadata_defaults_to_empty_dict(self) -> None:
        ctx = ActionContext()
        assert ctx.metadata == {}

    def test_metadata_is_independent_per_instance(self) -> None:
        ctx1 = ActionContext()
        ctx2 = ActionContext()
        ctx1.metadata["key"] = "val"
        assert "key" not in ctx2.metadata

    def test_record_id_defaults_to_none(self) -> None:
        ctx = ActionContext()
        assert ctx.record_id is None

    def test_record_id_accepts_string(self) -> None:
        ctx = ActionContext(record_id="user-42")
        assert ctx.record_id == "user-42"

    def test_metadata_accepts_arbitrary_values(self) -> None:
        ctx = ActionContext(metadata={"reason": "test", "count": 3})
        assert ctx.metadata["reason"] == "test"
        assert ctx.metadata["count"] == 3


class TestConfirmationConfig:
    """Tests for ConfirmationConfig frozen dataclass."""

    def test_requires_title(self) -> None:
        config = ConfirmationConfig(title="Delete user?")
        assert config.title == "Delete user?"

    def test_style_defaults_to_warning(self) -> None:
        config = ConfirmationConfig(title="Confirm")
        assert config.style == ActionColor.WARNING

    def test_message_defaults_to_none(self) -> None:
        config = ConfirmationConfig(title="Confirm")
        assert config.message is None

    def test_is_frozen(self) -> None:
        config = ConfirmationConfig(title="Frozen")
        with pytest.raises(FrozenInstanceError):
            config.title = "Mutated"  # type: ignore[misc]
