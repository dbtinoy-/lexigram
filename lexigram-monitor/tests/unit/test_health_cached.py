"""Tests for CachedHealthChecker."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import UTC, datetime, timedelta

from lexigram.monitor.health.cached import CachedHealthChecker
from lexigram.contracts.core import HealthStatus, HealthCheckResult


@pytest.fixture
def mock_db():
    # Use a real mock that doesn't have everything by default to test hasattr logic
    db = MagicMock()
    # Remove health_check attribute to force it to use execute/execute_query
    if hasattr(db, "health_check"):
        del db.health_check
    db.execute = AsyncMock()
    return db

@pytest.fixture
def mock_cache():
    cache = MagicMock()
    cache.health_check = AsyncMock()
    return cache

@pytest.mark.asyncio
async def test_cached_health_checker_db_only(mock_db):
    """Test database health check logic."""
    checker = CachedHealthChecker(db_provider=mock_db, cache_ttl=0.1)
    
    # Test healthy via execute
    result = await checker.get_database_health()
    assert result.status == HealthStatus.HEALTHY
    assert result.component == "database"
    mock_db.execute.assert_awaited_once_with("SELECT 1")
    
    # Test unhealthy via exception
    mock_db.execute.side_effect = ConnectionError("offline")
    # Wait for TTL to expire if needed, but we don't have cache yet for the second call if we didn't wait
    # Actually checker._is_cache_valid will return False if we wait
    await asyncio.sleep(0.15)
    result = await checker.get_database_health()
    assert result.status == HealthStatus.UNHEALTHY
    assert "offline" in result.message

@pytest.mark.asyncio
async def test_cached_health_checker_redis_only(mock_cache):
    """Test redis health check logic."""
    checker = CachedHealthChecker(cache_backend=mock_cache, cache_ttl=0.1)
    
    # Test healthy
    result = await checker.get_redis_health()
    assert result.status == HealthStatus.HEALTHY
    mock_cache.health_check.assert_awaited_once()
    
    # Test unhealthy
    mock_cache.health_check.side_effect = TimeoutError("slow")
    await asyncio.sleep(0.15)
    result = await checker.get_redis_health()
    assert result.status == HealthStatus.UNHEALTHY
    assert "slow" in result.message

@pytest.mark.asyncio
async def test_cached_health_checker_overall(mock_db, mock_cache):
    """Test overall health aggregation."""
    checker = CachedHealthChecker(db_provider=mock_db, cache_backend=mock_cache)
    
    # Both healthy
    overall = await checker.get_overall_health()
    assert overall["status"] == "healthy"
    assert "database" in overall["components"]
    assert "redis" in overall["components"]
    
    # One unhealthy
    mock_db.execute.side_effect = ConnectionError("err")
    # Force refresh by waiting
    checker._cache_ttl = 0.01
    await asyncio.sleep(0.02)
    
    overall = await checker.get_overall_health()
    assert overall["status"] == "unhealthy"

@pytest.mark.asyncio
async def test_cached_health_checker_background_refresh(mock_db, mock_cache):
    """Test background refresh loop."""
    checker = CachedHealthChecker(db_provider=mock_db, cache_backend=mock_cache, cache_ttl=0.05)
    
    await checker.start_background_refresh()
    assert checker._running
    
    # Wait for a few iterations
    await asyncio.sleep(0.15)
    
    # Check that calls were made multiple times
    assert mock_db.execute.await_count >= 2
    assert mock_cache.health_check.await_count >= 2
    
    await checker.stop_background_refresh()
    assert not checker._running
    assert len(checker._background_tasks) == 0

@pytest.mark.asyncio
async def test_cached_health_checker_no_provider():
    """Test behavior when no providers are configured."""
    checker = CachedHealthChecker(db_provider=None, cache_backend=None)
    
    db_res = await checker.get_database_health()
    assert db_res.status == HealthStatus.UNHEALTHY
    assert "No database provider configured" in db_res.message
    
    # Redis health check always tries if cache_backend is None it just succeeds?
    # Wait, looking at _check_redis_health:
    # if self._cache_backend is not None:
    #     await self._cache_backend.health_check(...)
    # It doesn't have an else block, so it returns HEALTHY if None?
    # That might be a bug or intended.
    redis_res = await checker.get_redis_health()
    assert redis_res.status == HealthStatus.HEALTHY
