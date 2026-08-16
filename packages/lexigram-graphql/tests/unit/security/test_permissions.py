"""Tests for GraphQL permission classes."""

from unittest.mock import Mock

import pytest

from lexigram.graphql.core import Info
from lexigram.graphql.security.permissions import (
    AllowAny,
    AbstractPermission,
    DenyAll,
    IsAdmin,
    IsAuthenticated,
    IsOwner,
    IsOwnerOrAdmin,
    allow_any,
    deny_all,
    is_admin,
    is_authenticated,
    is_owner,
    is_owner_or_admin,
)


class TestBasePermission:
    """Test base permission class."""

    def test_abstract_method(self):
        """AbstractPermission should be abstract."""
        with pytest.raises(TypeError):
            AbstractPermission()


class TestIsAuthenticated:
    """Test IsAuthenticated permission."""

    @pytest.mark.asyncio
    async def test_authenticated_user(self):
        """Should allow authenticated users."""
        permission = IsAuthenticated()
        info = Mock(spec=Info)
        info.context.user = Mock()

        result = await permission.has_permission(None, info)
        assert result is True

    @pytest.mark.asyncio
    async def test_unauthenticated_user(self):
        """Should deny unauthenticated users."""
        permission = IsAuthenticated()
        info = Mock(spec=Info)
        info.context.user = None

        result = await permission.has_permission(None, info)
        assert result is False


class TestIsAdmin:
    """Test IsAdmin permission."""

    @pytest.mark.asyncio
    async def test_admin_user(self):
        """Should allow admin users."""
        permission = IsAdmin()
        info = Mock(spec=Info)
        info.context.user = Mock()
        info.context.user.roles = ["admin"]

        result = await permission.has_permission(None, info)
        assert result is True

    @pytest.mark.asyncio
    async def test_superuser(self):
        """Should allow superuser."""
        permission = IsAdmin()
        info = Mock(spec=Info)
        info.context.user = Mock()
        info.context.user.roles = ["superuser"]

        result = await permission.has_permission(None, info)
        assert result is True

    @pytest.mark.asyncio
    async def test_non_admin_user(self):
        """Should deny non-admin users."""
        permission = IsAdmin()
        info = Mock(spec=Info)
        info.context.user = Mock()
        info.context.user.roles = ["user"]

        result = await permission.has_permission(None, info)
        assert result is False

    @pytest.mark.asyncio
    async def test_unauthenticated_user(self):
        """Should deny unauthenticated users."""
        permission = IsAdmin()
        info = Mock(spec=Info)
        info.context.user = None

        result = await permission.has_permission(None, info)
        assert result is False


class TestIsOwner:
    """Test IsOwner permission."""

    @pytest.mark.asyncio
    async def test_owner(self):
        """Should allow resource owner."""
        permission = IsOwner()
        info = Mock(spec=Info)
        info.context.user = Mock()
        info.context.user.user_id = "user123"

        source = Mock()
        source.user_id = "user123"

        result = await permission.has_permission(source, info)
        assert result is True

    @pytest.mark.asyncio
    async def test_owner_with_id_field(self):
        """Should allow resource owner using id field."""
        permission = IsOwner()
        info = Mock(spec=Info)
        info.context.user = Mock()
        info.context.user.id = "user123"

        source = Mock()
        source.user_id = "user123"

        result = await permission.has_permission(source, info)
        assert result is True

    @pytest.mark.asyncio
    async def test_owner_with_owner_id(self):
        """Should allow resource owner using owner_id field."""
        permission = IsOwner()
        info = Mock(spec=Info)
        info.context.user = Mock()
        info.context.user.user_id = "user123"

        source = Mock()
        source.owner_id = "user123"

        result = await permission.has_permission(source, info)
        assert result is True

    @pytest.mark.asyncio
    async def test_not_owner(self):
        """Should deny non-owner."""
        permission = IsOwner()
        info = Mock(spec=Info)
        info.context.user = Mock()
        info.context.user.user_id = "user123"

        source = Mock()
        source.user_id = "user456"

        result = await permission.has_permission(source, info)
        assert result is False

    @pytest.mark.asyncio
    async def test_no_user_id_on_source(self):
        """Should deny if source has no user_id or owner_id."""
        permission = IsOwner()
        info = Mock(spec=Info)
        info.context.user = Mock()
        info.context.user.user_id = "user123"

        source = Mock()
        # No user_id or owner_id

        result = await permission.has_permission(source, info)
        assert result is False

    @pytest.mark.asyncio
    async def test_unauthenticated_user(self):
        """Should deny unauthenticated users."""
        permission = IsOwner()
        info = Mock(spec=Info)
        info.context.user = None

        source = Mock()
        source.user_id = "user123"

        result = await permission.has_permission(source, info)
        assert result is False


class TestIsOwnerOrAdmin:
    """Test IsOwnerOrAdmin permission."""

    @pytest.mark.asyncio
    async def test_owner(self):
        """Should allow resource owner."""
        permission = IsOwnerOrAdmin()
        info = Mock(spec=Info)
        info.context.user = Mock()
        info.context.user.user_id = "user123"

        source = Mock()
        source.user_id = "user123"

        result = await permission.has_permission(source, info)
        assert result is True

    @pytest.mark.asyncio
    async def test_admin(self):
        """Should allow admin users."""
        permission = IsOwnerOrAdmin()
        info = Mock(spec=Info)
        info.context.user = Mock()
        info.context.user.roles = ["admin"]

        source = Mock()
        source.user_id = "user456"  # Different user

        result = await permission.has_permission(source, info)
        assert result is True

    @pytest.mark.asyncio
    async def test_neither_owner_nor_admin(self):
        """Should deny users who are neither owner nor admin."""
        permission = IsOwnerOrAdmin()
        info = Mock(spec=Info)
        info.context.user = Mock()
        info.context.user.user_id = "user123"
        info.context.user.roles = ["user"]

        source = Mock()
        source.user_id = "user456"

        result = await permission.has_permission(source, info)
        assert result is False


class TestAllowAny:
    """Test AllowAny permission."""

    @pytest.mark.asyncio
    async def test_always_allows(self):
        """Should always allow access."""
        permission = AllowAny()
        info = Mock(spec=Info)

        result = await permission.has_permission(None, info)
        assert result is True


class TestDenyAll:
    """Test DenyAll permission."""

    @pytest.mark.asyncio
    async def test_always_denies(self):
        """Should always deny access."""
        permission = DenyAll()
        info = Mock(spec=Info)

        result = await permission.has_permission(None, info)
        assert result is False


class TestConvenienceInstances:
    """Test convenience permission instances."""

    @pytest.mark.asyncio
    async def test_instances_are_correct_type(self):
        """Convenience instances should be correct types."""
        assert isinstance(is_authenticated, IsAuthenticated)
        assert isinstance(is_admin, IsAdmin)
        assert isinstance(is_owner, IsOwner)
        assert isinstance(is_owner_or_admin, IsOwnerOrAdmin)
        assert isinstance(allow_any, AllowAny)
        assert isinstance(deny_all, DenyAll)

    @pytest.mark.asyncio
    async def test_is_authenticated_instance(self):
        """Test is_authenticated convenience instance."""
        info = Mock(spec=Info)
        info.context.user = Mock()

        result = await is_authenticated.has_permission(None, info)
        assert result is True

    @pytest.mark.asyncio
    async def test_allow_any_instance(self):
        """Test allow_any convenience instance."""
        result = await allow_any.has_permission(None, None)
        assert result is True

    @pytest.mark.asyncio
    async def test_deny_all_instance(self):
        """Test deny_all convenience instance."""
        result = await deny_all.has_permission(None, None)
        assert result is False
