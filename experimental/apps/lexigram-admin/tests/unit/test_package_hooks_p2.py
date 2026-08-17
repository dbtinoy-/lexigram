"""P2 hook surface import verification for lexigram-admin."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass

import pytest


def test_admin_hooks_root_module_exists() -> None:
    import lexigram.admin
    from lexigram.admin.hooks import (
        AdminPanelStartedHook,
        AdminPanelStoppedHook,
        AdminResourceAccessedHook,
    )

    assert AdminPanelStartedHook.__name__ == "AdminPanelStartedHook"
    assert AdminPanelStoppedHook.__name__ == "AdminPanelStoppedHook"
    assert AdminResourceAccessedHook.__name__ == "AdminResourceAccessedHook"
    assert lexigram.admin.AdminPanelStartedHook is AdminPanelStartedHook
    assert lexigram.admin.AdminPanelStoppedHook is AdminPanelStoppedHook
    assert lexigram.admin.AdminResourceAccessedHook is AdminResourceAccessedHook
    assert "AdminPanelStartedHook" in lexigram.admin.__all__
    assert "AdminPanelStoppedHook" in lexigram.admin.__all__
    assert "AdminResourceAccessedHook" in lexigram.admin.__all__


def test_admin_hook_payloads_are_frozen_and_keyword_only() -> None:
    from lexigram.admin.hooks import AdminPanelStartedHook, AdminResourceAccessedHook

    started = AdminPanelStartedHook()
    accessed = AdminResourceAccessedHook(
        resource_name="User", action="list", user_id="u1"
    )

    assert is_dataclass(started)
    assert is_dataclass(accessed)

    with pytest.raises(TypeError):
        AdminResourceAccessedHook("User", "list", "u1")  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        accessed.resource_name = "Order"  # type: ignore[misc]
