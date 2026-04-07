"""Tests for core/distributed_lock.py — LockError, LockConfig, AdminLockManager, ResourceLock."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.core.distributed_lock import (
    AdminLockContext,
    AdminLockManager,
    BulkOperationLock,
    LockAcquisitionError,
    LockConfig,
    LockError,
    LockTimeoutError,
    ResourceLock,
    distributed_lock,
)


# ---------------------------------------------------------------------------
# Error classes
# ---------------------------------------------------------------------------


class TestLockErrors:
    """Tests for lock error hierarchy."""

    def test_lock_error_default_message(self) -> None:
        err = LockError()
        assert "Lock error" in str(err)

    def test_lock_error_custom_message(self) -> None:
        err = LockError("Custom lock error")
        assert "Custom lock error" in str(err)

    def test_lock_acquisition_error_default_message(self) -> None:
        err = LockAcquisitionError()
        assert "Could not acquire lock" in str(err)

    def test_lock_acquisition_error_custom(self) -> None:
        err = LockAcquisitionError("Already locked by another process")
        assert "Already locked" in str(err)

    def test_lock_timeout_error_default_message(self) -> None:
        err = LockTimeoutError()
        assert "timed out" in str(err).lower()

    def test_error_hierarchy(self) -> None:
        assert issubclass(LockAcquisitionError, LockError)
        assert issubclass(LockTimeoutError, LockError)

    def test_lock_code(self) -> None:
        assert LockError._code == "LEX_ERR_ADMIN_023"
        assert LockAcquisitionError._code == "LEX_ERR_ADMIN_024"
        assert LockTimeoutError._code == "LEX_ERR_ADMIN_025"


# ---------------------------------------------------------------------------
# LockConfig
# ---------------------------------------------------------------------------


class TestLockConfig:
    """Tests for LockConfig dataclass."""

    def test_defaults(self) -> None:
        config = LockConfig()
        assert config.default_ttl == 30
        assert config.acquisition_timeout == 30.0
        assert config.key_prefix == "admin:lock:"

    def test_custom_values(self) -> None:
        config = LockConfig(
            default_ttl=60,
            acquisition_timeout=10.0,
            key_prefix="my:prefix:",
        )
        assert config.default_ttl == 60
        assert config.acquisition_timeout == 10.0
        assert config.key_prefix == "my:prefix:"


# ---------------------------------------------------------------------------
# AdminLockManager
# ---------------------------------------------------------------------------


class TestAdminLockManager:
    """Tests for AdminLockManager."""

    def test_full_key_with_default_prefix(self) -> None:
        mock_store = MagicMock()
        manager = AdminLockManager(lock_store=mock_store)
        assert manager._full_key("users:123") == "admin:lock:users:123"

    def test_full_key_with_custom_prefix(self) -> None:
        mock_store = MagicMock()
        config = LockConfig(key_prefix="test:")
        manager = AdminLockManager(lock_store=mock_store, config=config)
        assert manager._full_key("mykey") == "test:mykey"

    def test_acquire_returns_lock_context(self) -> None:
        mock_store = MagicMock()
        manager = AdminLockManager(lock_store=mock_store)
        ctx = manager.acquire("my-lock")
        assert isinstance(ctx, AdminLockContext)

    def test_acquire_uses_default_ttl(self) -> None:
        mock_store = MagicMock()
        config = LockConfig(default_ttl=45)
        manager = AdminLockManager(lock_store=mock_store, config=config)
        ctx = manager.acquire("my-lock")
        assert ctx.ttl == 45

    def test_acquire_uses_custom_ttl(self) -> None:
        mock_store = MagicMock()
        manager = AdminLockManager(lock_store=mock_store)
        ctx = manager.acquire("my-lock", ttl=120)
        assert ctx.ttl == 120

    def test_acquire_uses_default_timeout(self) -> None:
        mock_store = MagicMock()
        config = LockConfig(acquisition_timeout=15.0)
        manager = AdminLockManager(lock_store=mock_store, config=config)
        ctx = manager.acquire("my-lock")
        assert ctx.timeout == 15.0

    def test_acquire_uses_custom_timeout(self) -> None:
        mock_store = MagicMock()
        manager = AdminLockManager(lock_store=mock_store)
        ctx = manager.acquire("my-lock", timeout=5.0)
        assert ctx.timeout == 5.0

    def test_acquire_prefixes_key(self) -> None:
        mock_store = MagicMock()
        manager = AdminLockManager(lock_store=mock_store)
        ctx = manager.acquire("resource:123")
        assert ctx.key == "admin:lock:resource:123"

    def test_default_config_if_none(self) -> None:
        mock_store = MagicMock()
        manager = AdminLockManager(lock_store=mock_store)
        assert isinstance(manager.config, LockConfig)


# ---------------------------------------------------------------------------
# AdminLockContext
# ---------------------------------------------------------------------------


class TestAdminLockContext:
    """Tests for AdminLockContext."""

    @pytest.mark.asyncio
    async def test_acquires_lock_on_enter(self) -> None:
        mock_store = AsyncMock()
        mock_store.acquire = AsyncMock(return_value=True)
        mock_store.release = AsyncMock()

        ctx = AdminLockContext(
            lock_store=mock_store,
            key="test-key",
            ttl=30,
            timeout=5.0,
        )
        async with ctx:
            assert ctx.acquired is True
        mock_store.acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_releases_lock_on_exit(self) -> None:
        mock_store = AsyncMock()
        mock_store.acquire = AsyncMock(return_value=True)
        mock_store.release = AsyncMock()

        ctx = AdminLockContext(
            lock_store=mock_store,
            key="test-key",
            ttl=30,
            timeout=5.0,
        )
        async with ctx:
            pass
        mock_store.release.assert_called_once_with("test-key", ctx.owner)

    @pytest.mark.asyncio
    async def test_timeout_raises_lock_timeout_error(self) -> None:
        mock_store = AsyncMock()
        mock_store.acquire = AsyncMock(return_value=False)  # Never acquired

        ctx = AdminLockContext(
            lock_store=mock_store,
            key="busy-key",
            ttl=30,
            timeout=0.05,  # Very short timeout
        )
        with pytest.raises(LockTimeoutError):
            async with ctx:
                pass

    @pytest.mark.asyncio
    async def test_acquired_false_initially(self) -> None:
        mock_store = MagicMock()
        ctx = AdminLockContext(
            lock_store=mock_store,
            key="k",
            ttl=10,
            timeout=1.0,
        )
        assert ctx.acquired is False


# ---------------------------------------------------------------------------
# ResourceLock
# ---------------------------------------------------------------------------


class TestResourceLock:
    """Tests for ResourceLock."""

    def test_key_format(self) -> None:
        mock_store = MagicMock()
        manager = AdminLockManager(lock_store=mock_store)
        lock = ResourceLock("users", "user-42", lock_manager=manager)
        assert lock.key == "users:user-42:edit"

    def test_key_format_custom_operation(self) -> None:
        mock_store = MagicMock()
        manager = AdminLockManager(lock_store=mock_store)
        lock = ResourceLock("posts", "post-1", lock_manager=manager, operation="delete")
        assert lock.key == "posts:post-1:delete"

    @pytest.mark.asyncio
    async def test_acquires_lock(self) -> None:
        mock_store = AsyncMock()
        mock_store.acquire = AsyncMock(return_value=True)
        mock_store.release = AsyncMock()

        manager = AdminLockManager(lock_store=mock_store)
        async with ResourceLock("users", "u1", lock_manager=manager, ttl=30):
            pass
        mock_store.acquire.assert_called_once()


# ---------------------------------------------------------------------------
# BulkOperationLock
# ---------------------------------------------------------------------------


class TestBulkOperationLock:
    """Tests for BulkOperationLock."""

    def test_key_format(self) -> None:
        mock_store = MagicMock()
        manager = AdminLockManager(lock_store=mock_store)
        lock = BulkOperationLock("users", "delete", lock_manager=manager)
        assert lock.key == "bulk:users:delete"

    def test_default_ttl(self) -> None:
        mock_store = MagicMock()
        manager = AdminLockManager(lock_store=mock_store)
        lock = BulkOperationLock("users", "export", lock_manager=manager)
        assert lock.ttl == 300

    @pytest.mark.asyncio
    async def test_acquires_lock(self) -> None:
        mock_store = AsyncMock()
        mock_store.acquire = AsyncMock(return_value=True)
        mock_store.release = AsyncMock()

        manager = AdminLockManager(lock_store=mock_store)
        async with BulkOperationLock("posts", "import", lock_manager=manager):
            pass
        mock_store.acquire.assert_called_once()


# ---------------------------------------------------------------------------
# distributed_lock decorator
# ---------------------------------------------------------------------------


class TestDistributedLockDecorator:
    """Tests for distributed_lock decorator."""

    @pytest.mark.asyncio
    async def test_static_key_acquires_lock(self) -> None:
        mock_store = AsyncMock()
        mock_store.acquire = AsyncMock(return_value=True)
        mock_store.release = AsyncMock()

        manager = AdminLockManager(lock_store=mock_store)

        @distributed_lock("my-operation", lock_manager=manager)
        async def do_work() -> str:
            return "done"

        result = await do_work()
        assert result == "done"
        mock_store.acquire.assert_called_once()

    @pytest.mark.asyncio
    async def test_callable_key(self) -> None:
        mock_store = AsyncMock()
        mock_store.acquire = AsyncMock(return_value=True)
        mock_store.release = AsyncMock()

        manager = AdminLockManager(lock_store=mock_store)

        @distributed_lock(
            lambda resource_id: f"resource:{resource_id}",
            lock_manager=manager,
        )
        async def process(resource_id: str) -> str:
            return f"processed:{resource_id}"

        result = await process("user-123")
        assert result == "processed:user-123"

    @pytest.mark.asyncio
    async def test_on_locked_callback_invoked_on_timeout(self) -> None:
        mock_store = AsyncMock()
        mock_store.acquire = AsyncMock(return_value=False)  # Never acquires

        manager = AdminLockManager(lock_store=mock_store)

        @distributed_lock(
            "busy-lock",
            lock_manager=manager,
            timeout=0.05,
            on_locked=lambda: "fallback",
        )
        async def do_work() -> str:
            return "done"

        result = await do_work()
        assert result == "fallback"

    @pytest.mark.asyncio
    async def test_no_callback_raises_on_timeout(self) -> None:
        mock_store = AsyncMock()
        mock_store.acquire = AsyncMock(return_value=False)

        manager = AdminLockManager(lock_store=mock_store)

        @distributed_lock("busy-lock", lock_manager=manager, timeout=0.05)
        async def do_work() -> str:
            return "done"

        with pytest.raises(LockTimeoutError):
            await do_work()

    def test_preserves_function_metadata(self) -> None:
        mock_store = MagicMock()
        manager = AdminLockManager(lock_store=mock_store)

        @distributed_lock("key", lock_manager=manager)
        async def my_operation() -> None:
            """My operation docstring."""

        assert my_operation.__name__ == "my_operation"
