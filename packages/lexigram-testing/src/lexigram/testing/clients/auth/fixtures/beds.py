"""Auth test bed and client fixtures."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

from lexigram.testing.clients.auth.bed import AuthTestBed
from lexigram.testing.clients.auth.client import AuthTestClient
from lexigram.testing.clients.auth.fixtures._async import async_fixture


# Test bed fixtures
@async_fixture
async def auth_test_bed() -> AsyncGenerator[AuthTestBed, None]:
    """Provide an auth test bed for testing.

    Yields:
        AuthTestBed: Configured test bed with auth providers
    """
    async with AuthTestBed() as bed:
        yield bed


@pytest.fixture
def auth_test_client(auth_test_bed: AuthTestBed) -> AuthTestClient:
    """Provide an auth test client.

    Args:
        auth_test_bed: The auth test bed

    Returns:
        AuthTestClient: Configured test client
    """
    return AuthTestClient(auth_test_bed)
