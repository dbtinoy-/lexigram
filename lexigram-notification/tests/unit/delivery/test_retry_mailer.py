"""Tests for RetryingMailer with exponential backoff delivery retry."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from lexigram.result import Ok, Err


class TestRetryingMailer:

    @pytest.fixture
    def mock_backend(self) -> MagicMock:
        backend = MagicMock()
        backend.send = AsyncMock()
        return backend

    @pytest.fixture
    def mock_store(self) -> MagicMock:
        store = MagicMock()
        store.create_pending = AsyncMock(return_value="delivery-id-1")
        store.mark_delivered = AsyncMock()
        store.mark_failed = AsyncMock()
        store.get_retry_count = AsyncMock(return_value=0)
        store.increment_retry = AsyncMock(return_value=1)
        store.schedule_retry = AsyncMock()
        return store

    @pytest.mark.asyncio
    async def test_successful_delivery_marks_delivered(
        self, mock_backend: MagicMock, mock_store: MagicMock,
    ) -> None:
        from lexigram.notification.delivery.retry import RetryingMailer
        mock_backend.send.return_value = Ok(MagicMock())
        mailer = RetryingMailer(backend=mock_backend, store=mock_store, max_retries=3)
        result = await mailer.send(MagicMock())
        assert result.is_ok()
        mock_store.mark_delivered.assert_awaited_once_with("delivery-id-1")

    @pytest.mark.asyncio
    async def test_transient_failure_schedules_retry(
        self, mock_backend: MagicMock, mock_store: MagicMock,
    ) -> None:
        from lexigram.notification.delivery.retry import RetryingMailer
        mock_backend.send.return_value = Err(Exception("Connection reset"))
        mock_store.increment_retry.return_value = 1
        mailer = RetryingMailer(backend=mock_backend, store=mock_store, max_retries=3)
        result = await mailer.send(MagicMock())
        assert result.is_ok()
        mock_store.schedule_retry.assert_awaited_once()
        mock_store.mark_delivered.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_max_retries_exceeded_marks_permanently_failed(
        self, mock_backend: MagicMock, mock_store: MagicMock,
    ) -> None:
        from lexigram.notification.delivery.retry import RetryingMailer
        from lexigram.notification.delivery.exceptions import PermanentDeliveryFailure
        mock_backend.send.return_value = Err(Exception("Connection reset"))
        mock_store.increment_retry.return_value = 3
        mailer = RetryingMailer(backend=mock_backend, store=mock_store, max_retries=3)
        result = await mailer.send(MagicMock())
        assert result.is_err()
        assert isinstance(result.unwrap_err(), PermanentDeliveryFailure)
        mock_store.mark_failed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_exponential_backoff_delay(
        self, mock_backend: MagicMock, mock_store: MagicMock,
    ) -> None:
        from lexigram.notification.delivery.retry import RetryingMailer
        mock_backend.send.return_value = Err(Exception("fail"))
        mock_store.increment_retry.return_value = 2  # second retry
        mailer = RetryingMailer(backend=mock_backend, store=mock_store, max_retries=3, base_delay=60.0)
        await mailer.send(MagicMock())
        # 2nd retry: delay = 60 * (2^(2-1)) = 120 seconds
        mock_store.schedule_retry.assert_awaited_once()
        call_args = mock_store.schedule_retry.call_args
        delay = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("delay_seconds")
        assert delay == 120.0

    @pytest.mark.asyncio
    async def test_successful_delivery_returns_delivery_id(
        self, mock_backend: MagicMock, mock_store: MagicMock,
    ) -> None:
        from lexigram.notification.delivery.retry import RetryingMailer
        mock_backend.send.return_value = Ok(MagicMock())
        mailer = RetryingMailer(backend=mock_backend, store=mock_store, max_retries=3)
        result = await mailer.send(MagicMock())
        assert result.is_ok()
        assert result.unwrap() == "delivery-id-1"

    @pytest.mark.asyncio
    async def test_retry_returns_delivery_id(
        self, mock_backend: MagicMock, mock_store: MagicMock,
    ) -> None:
        from lexigram.notification.delivery.retry import RetryingMailer
        mock_backend.send.return_value = Err(Exception("transient"))
        mock_store.increment_retry.return_value = 1
        mailer = RetryingMailer(backend=mock_backend, store=mock_store, max_retries=3)
        result = await mailer.send(MagicMock())
        assert result.is_ok()
        assert result.unwrap() == "delivery-id-1"

    @pytest.mark.asyncio
    async def test_permanent_failure_contains_delivery_id(
        self, mock_backend: MagicMock, mock_store: MagicMock,
    ) -> None:
        from lexigram.notification.delivery.retry import RetryingMailer
        from lexigram.notification.delivery.exceptions import PermanentDeliveryFailure
        mock_backend.send.return_value = Err(Exception("fail"))
        mock_store.increment_retry.return_value = 3
        mailer = RetryingMailer(backend=mock_backend, store=mock_store, max_retries=3)
        result = await mailer.send(MagicMock())
        assert result.is_err()
        err = result.unwrap_err()
        assert isinstance(err, PermanentDeliveryFailure)
        assert err.delivery_id == "delivery-id-1"

    @pytest.mark.asyncio
    async def test_first_retry_base_delay(
        self, mock_backend: MagicMock, mock_store: MagicMock,
    ) -> None:
        from lexigram.notification.delivery.retry import RetryingMailer
        mock_backend.send.return_value = Err(Exception("fail"))
        mock_store.increment_retry.return_value = 1  # first retry
        mailer = RetryingMailer(backend=mock_backend, store=mock_store, max_retries=3, base_delay=60.0)
        await mailer.send(MagicMock())
        # 1st retry: delay = 60 * (2^(1-1)) = 60 seconds
        call_args = mock_store.schedule_retry.call_args
        delay = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("delay_seconds")
        assert delay == 60.0
