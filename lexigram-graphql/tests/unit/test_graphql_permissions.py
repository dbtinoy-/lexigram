"""Unit tests for GraphQL permissions."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from lexigram.graphql.core.context import GraphQLContext

try:
    from lexigram.graphql.security.permissions import (
        IsAuthenticated,
        IsAdmin,
        IsOwner,
        AllowAny,
        DenyAll,
        AbstractPermission
    )
except ImportError:
    # Handle if types aren't available during test collection
    pass

class TestPermissions:
    """Test permission classes."""

    @pytest.fixture
    def context(self):
        context = MagicMock(spec=GraphQLContext)
        context.user = None
        return context

    @pytest.fixture
    def info(self, context):
        info = MagicMock()
        info.context = context
        return info

    @pytest.mark.asyncio
    async def test_is_authenticated_true(self, info):
        """Test IsAuthenticated with user."""
        info.context.user = MagicMock(id="123")
        perm = IsAuthenticated()
        assert await perm.has_permission(None, info)

    @pytest.mark.asyncio
    async def test_is_authenticated_false(self, info):
        """Test IsAuthenticated without user."""
        info.context.user = None
        perm = IsAuthenticated()
        assert not await perm.has_permission(None, info)

    @pytest.mark.asyncio
    async def test_is_admin_true(self, info):
        """Test IsAdmin with admin role."""
        info.context.user = MagicMock(roles=["admin"])
        perm = IsAdmin()
        assert await perm.has_permission(None, info)

    @pytest.mark.asyncio
    async def test_is_admin_false(self, info):
        """Test IsAdmin without admin role."""
        info.context.user = MagicMock(roles=["user"])
        perm = IsAdmin()
        assert not await perm.has_permission(None, info)

    @pytest.mark.asyncio
    async def test_is_owner_true(self, info):
        """Test IsOwner when IDs match."""
        info.context.user = MagicMock(user_id="123", id="123")
        source = MagicMock(user_id="123")
        
        perm = IsOwner()
        assert await perm.has_permission(source, info)

    @pytest.mark.asyncio
    async def test_is_owner_false(self, info):
        """Test IsOwner when IDs mismatch."""
        info.context.user = MagicMock(user_id="123")
        source = MagicMock(user_id="456")
        
        perm = IsOwner()
        assert not await perm.has_permission(source, info)

    @pytest.mark.asyncio
    async def test_allow_any(self, info):
        """Test AllowAny."""
        perm = AllowAny()
        assert await perm.has_permission(None, info)

    @pytest.mark.asyncio
    async def test_deny_all(self, info):
        """Test DenyAll."""
        perm = DenyAll()
        assert not await perm.has_permission(None, info)
