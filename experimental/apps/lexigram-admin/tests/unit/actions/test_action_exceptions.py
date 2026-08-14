"""Tests for action exceptions — ActionError, PermissionDenied."""

from __future__ import annotations

import pytest

from lexigram.admin.exceptions import AdminError
from lexigram.admin.actions.exceptions import ActionError, PermissionDenied


class TestActionError:
    """Tests for ActionError exception."""

    def test_is_subclass_of_admin_error(self) -> None:
        assert issubclass(ActionError, AdminError)

    def test_can_be_raised_and_caught(self) -> None:
        with pytest.raises(ActionError):
            raise ActionError("action failed")

    def test_caught_as_admin_error(self) -> None:
        with pytest.raises(AdminError):
            raise ActionError("action failed")


class TestPermissionDenied:
    """Tests for PermissionDenied exception."""

    def test_is_subclass_of_action_error(self) -> None:
        assert issubclass(PermissionDenied, ActionError)

    def test_can_be_raised_and_caught(self) -> None:
        with pytest.raises(PermissionDenied):
            raise PermissionDenied("permission denied")

    def test_is_not_unrelated_exception(self) -> None:
        exc = PermissionDenied("denied")
        assert not isinstance(exc, ValueError)
        assert not isinstance(exc, RuntimeError)
        assert not isinstance(exc, TypeError)
