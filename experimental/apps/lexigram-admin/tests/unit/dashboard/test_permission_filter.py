from lexigram.admin.types import AdminUser
from lexigram.admin.dashboard.permission_filter import PermissionFilter


def test_widget_visible_when_user_has_required_perms() -> None:
    pf = PermissionFilter()
    items = [
        {"name": "secret", "perms": frozenset({"admin.view"})},
    ]
    user = AdminUser("1", "test", "test@ex.com", permissions=frozenset({"admin.view"}))
    result = pf.filter(
        items,
        user,
        get_required_permissions=lambda x: x["perms"],
    )
    assert len(result) == 1


def test_widget_hidden_when_user_lacks_any_required_perm() -> None:
    pf = PermissionFilter()
    items = [
        {"name": "super_secret", "perms": frozenset({"super.admin"})},
    ]
    user = AdminUser("1", "test", "test@ex.com", permissions=frozenset({"admin.view"}))
    result = pf.filter(
        items,
        user,
        get_required_permissions=lambda x: x["perms"],
    )
    assert len(result) == 0


def test_anonymous_user_sees_only_public_items() -> None:
    pf = PermissionFilter()
    items = [
        {"name": "public", "perms": frozenset()},
        {"name": "private", "perms": frozenset({"admin.view"})},
    ]
    result = pf.filter(
        items,
        None,
        get_required_permissions=lambda x: x["perms"],
    )
    assert [i["name"] for i in result] == ["public"]


def test_empty_items_returns_empty() -> None:
    pf = PermissionFilter()
    assert pf.filter([], None, get_required_permissions=lambda _: frozenset()) == []
