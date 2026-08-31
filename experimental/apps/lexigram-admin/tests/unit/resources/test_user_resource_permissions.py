"""Permission checks on the built-in UserResource.

These previously read ``user.is_admin or user.role in [...]``. Neither
attribute exists: ``AdminUserRecord`` has ``roles: list[str]`` and
``has_role()`` but no ``is_admin``, and no user type in the admin app has a
singular ``role``. Every call raised AttributeError.

The failure was invisible from the outside. The caller in
``resources/handler.py`` wraps the check in ``except Exception`` and fails
closed, so authenticated admins simply got 403 on /admin/users while the
cause stayed in the ``admin.resource_permission_check_failed`` log.

The tests cover both user types that reach this resource, since they expose
different APIs and only ``has_role()`` is common to both.
"""

from __future__ import annotations

import pytest

from lexigram.admin.auth.integration import AdminUser
from lexigram.admin.auth.user import AdminUserRecord
from lexigram.admin.resources.users import UserResource

PERMISSION_METHODS = (
    "has_view_permission",
    "has_add_permission",
    "has_change_permission",
    "has_delete_permission",
)


@pytest.fixture
def resource() -> UserResource:
    return UserResource()


def _record(*roles: str) -> AdminUserRecord:
    return AdminUserRecord(user_id="1", email="u@example.test", roles=list(roles))


class TestAdminUserRecord:
    """The type that lacks is_admin -- the one that broke."""

    def test_admin_has_every_permission(self, resource: UserResource) -> None:
        user = _record("admin")

        assert all(getattr(resource, name)(user) for name in PERMISSION_METHODS)

    def test_moderator_can_view_and_change(self, resource: UserResource) -> None:
        user = _record("moderator")

        assert resource.has_view_permission(user)
        assert resource.has_change_permission(user)

    def test_moderator_cannot_add_or_delete(self, resource: UserResource) -> None:
        """Moderation is not user administration."""
        user = _record("moderator")

        assert not resource.has_add_permission(user)
        assert not resource.has_delete_permission(user)

    def test_unprivileged_role_is_refused(self, resource: UserResource) -> None:
        user = _record("viewer")

        assert not any(getattr(resource, name)(user) for name in PERMISSION_METHODS)

    def test_user_without_roles_is_refused(self, resource: UserResource) -> None:
        user = _record()

        assert not any(getattr(resource, name)(user) for name in PERMISSION_METHODS)

    def test_extra_roles_do_not_mask_a_grant(self, resource: UserResource) -> None:
        user = _record("viewer", "admin")

        assert resource.has_delete_permission(user)


class TestAdminUser:
    """The integration type, which does expose is_admin."""

    def test_admin_role_is_granted(self, resource: UserResource) -> None:
        user = AdminUser(id=1, email="a@example.test", name="A", roles=["admin"])

        assert all(getattr(resource, name)(user) for name in PERMISSION_METHODS)

    def test_superuser_is_granted(self, resource: UserResource) -> None:
        """AdminUser.has_role() returns True for a superuser regardless of
        the roles list."""
        user = AdminUser(id=2, email="s@example.test", name="S", is_superuser=True)

        assert all(getattr(resource, name)(user) for name in PERMISSION_METHODS)

    def test_plain_user_is_refused(self, resource: UserResource) -> None:
        user = AdminUser(id=3, email="p@example.test", name="P", roles=["viewer"])

        assert not any(getattr(resource, name)(user) for name in PERMISSION_METHODS)


class TestAnonymous:
    @pytest.mark.parametrize("name", PERMISSION_METHODS)
    def test_none_user_is_refused_without_raising(
        self, resource: UserResource, name: str
    ) -> None:
        assert getattr(resource, name)(None) is False

    @pytest.mark.parametrize("name", PERMISSION_METHODS)
    def test_result_is_a_real_bool(self, resource: UserResource, name: str) -> None:
        """The caller does `if not allowed`, and the old code returned the
        user object or None rather than a bool."""
        assert isinstance(getattr(resource, name)(_record("admin")), bool)


class TestNoAttributeErrors:
    """The regression itself: these must never raise."""

    @pytest.mark.parametrize("name", PERMISSION_METHODS)
    @pytest.mark.parametrize(
        "user",
        [
            None,
            _record("admin"),
            _record(),
            AdminUser(id=1, email="a@example.test", name="A"),
            object(),  # a type with neither has_role() nor roles
        ],
    )
    def test_check_never_raises(
        self, resource: UserResource, name: str, user: object
    ) -> None:
        getattr(resource, name)(user)
