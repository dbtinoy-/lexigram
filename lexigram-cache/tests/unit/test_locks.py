"""Tests for cache locks."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestAutoRenewingLock:
    """Tests for AutoRenewingLock."""

    def test_creation(self) -> None:
        """Test creating an AutoRenewingLock."""
        from lexigram.cache.locks.auto_renewing import AutoRenewingLock

        mock_redis = MagicMock()
        lock = AutoRenewingLock(
            redis=mock_redis,
            key="test:lock",
            lock_id="lock-123",
            ttl=30,
        )
        
        assert lock._key == "test:lock"
        assert lock._lock_id == "lock-123"
        assert lock._ttl == 30
        assert lock._auto_renew is True
        assert lock._renew_interval == 10  # ttl // 3

    def test_creation_with_custom_renew_interval(self) -> None:
        """Test creating with custom renew interval."""
        from lexigram.cache.locks.auto_renewing import AutoRenewingLock

        mock_redis = MagicMock()
        lock = AutoRenewingLock(
            redis=mock_redis,
            key="test:lock",
            lock_id="lock-123",
            ttl=30,
            renew_interval=5,
        )
        
        assert lock._renew_interval == 5

    def test_creation_with_auto_renew_disabled(self) -> None:
        """Test creating with auto_renew disabled."""
        from lexigram.cache.locks.auto_renewing import AutoRenewingLock

        mock_redis = MagicMock()
        lock = AutoRenewingLock(
            redis=mock_redis,
            key="test:lock",
            lock_id="lock-123",
            ttl=30,
            auto_renew=False,
        )
        
        assert lock._auto_renew is False

    @pytest.mark.asyncio
    async def test_start_auto_renewal(self) -> None:
        """Test starting auto-renewal."""
        from lexigram.cache.locks.auto_renewing import AutoRenewingLock

        mock_redis = MagicMock()
        mock_redis.eval = AsyncMock(return_value=1)
        
        lock = AutoRenewingLock(
            redis=mock_redis,
            key="test:lock",
            lock_id="lock-123",
            ttl=30,
        )
        
        await lock.start_auto_renewal()
        
        assert lock._renew_task is not None
        assert lock._acquired_at is not None

    @pytest.mark.asyncio
    async def test_start_auto_renewal_when_disabled(self) -> None:
        """Test starting auto-renewal when disabled does nothing."""
        from lexigram.cache.locks.auto_renewing import AutoRenewingLock

        mock_redis = MagicMock()
        
        lock = AutoRenewingLock(
            redis=mock_redis,
            key="test:lock",
            lock_id="lock-123",
            ttl=30,
            auto_renew=False,
        )
        
        await lock.start_auto_renewal()
        
        assert lock._renew_task is None

    @pytest.mark.asyncio
    async def test_stop_auto_renewal(self) -> None:
        """Test stopping auto-renewal."""
        from lexigram.cache.locks.auto_renewing import AutoRenewingLock

        mock_redis = MagicMock()
        mock_redis.eval = AsyncMock(return_value=1)
        
        lock = AutoRenewingLock(
            redis=mock_redis,
            key="test:lock",
            lock_id="lock-123",
            ttl=30,
        )
        
        await lock.start_auto_renewal()
        await lock.stop_auto_renewal()
        
        assert lock._stop_renew is True

    @pytest.mark.asyncio
    async def test_release(self) -> None:
        """Test releasing lock."""
        from lexigram.cache.locks.auto_renewing import AutoRenewingLock

        mock_redis = MagicMock()
        mock_redis.eval = AsyncMock(return_value=1)
        
        lock = AutoRenewingLock(
            redis=mock_redis,
            key="test:lock",
            lock_id="lock-123",
            ttl=30,
        )
        
        await lock.start_auto_renewal()
        await lock.release()
        
        assert lock._stop_renew is True


class TestLockContextManager:
    """Tests for LockContextManager."""

    @pytest.mark.asyncio
    async def test_context_manager_acquires_lock(self) -> None:
        """Test context manager acquires lock successfully."""
        from lexigram.cache.locks.context import LockContextManager

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.eval = AsyncMock(return_value=1)
        
        async with LockContextManager(
            redis=mock_redis,
            key="test:lock",
            ttl=30,
            auto_renew=True,
        ) as lock:
            assert lock is not None

    @pytest.mark.asyncio
    async def test_context_manager_raises_on_failure(self) -> None:
        """Test context manager raises when lock cannot be acquired."""
        from lexigram.cache.locks.context import LockContextManager
        from lexigram.cache.exceptions import LockAcquisitionError

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock(return_value=False)
        
        with pytest.raises(LockAcquisitionError):
            async with LockContextManager(
                redis=mock_redis,
                key="test:lock",
                ttl=30,
                auto_renew=True,
            ):
                pass
