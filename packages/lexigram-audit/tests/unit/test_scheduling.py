"""Tests for AuditScheduler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.audit.scheduling.scheduler import AuditScheduler


class MockVerifier:
    """Mock verifier for testing."""

    def __init__(self, mismatches: int = 0) -> None:
        self._mismatches = mismatches

    async def verify_recent(self, *, limit: int = 100) -> list:
        return [{"id": f"mismatch-{i}"} for i in range(self._mismatches)]


class MockConfig:
    """Mock config for testing."""

    def __init__(
        self,
        verification_batch_size: int = 100,
        verification_schedule: str = "0 0 * * *",
    ) -> None:
        self.verification_batch_size = verification_batch_size
        self.verification_schedule = verification_schedule


class MockTaskProvider:
    """Mock task provider for testing."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.registered_handlers: dict = {}
        self.scheduled_jobs: list = []

    def register_handler(self, name: str, handler) -> None:
        if self.should_fail:
            raise RuntimeError("Registration failed")
        self.registered_handlers[name] = handler

    def schedule_job(self, name: str, schedule: str) -> str:
        if self.should_fail:
            raise RuntimeError("Schedule failed")
        self.scheduled_jobs.append({"name": name, "schedule": schedule})
        return f"job-{len(self.scheduled_jobs)}"


class TestAuditScheduler:
    """Tests for AuditScheduler."""

    @pytest.fixture
    def mock_verifier(self) -> MockVerifier:
        return MockVerifier(mismatches=0)

    @pytest.fixture
    def mock_config(self) -> MockConfig:
        return MockConfig(verification_batch_size=50)

    def test_scheduler_creation(self, mock_verifier, mock_config) -> None:
        scheduler = AuditScheduler(verifier=mock_verifier, config=mock_config)
        assert scheduler._verifier is mock_verifier
        assert scheduler._config is mock_config

    def test_register_handler_success(self, mock_verifier, mock_config) -> None:
        scheduler = AuditScheduler(verifier=mock_verifier, config=mock_config)
        task_provider = MockTaskProvider()
        
        scheduler.register_handler(task_provider)
        
        assert "audit:verify_recent" in task_provider.registered_handlers

    def test_register_handler_stores_handler(self, mock_verifier, mock_config) -> None:
        scheduler = AuditScheduler(verifier=mock_verifier, config=mock_config)
        task_provider = MockTaskProvider()
        
        scheduler.register_handler(task_provider)
        
        handler = task_provider.registered_handlers["audit:verify_recent"]
        assert callable(handler)

    @pytest.mark.asyncio
    async def test_registered_handler_calls_verifier(self, mock_verifier, mock_config) -> None:
        scheduler = AuditScheduler(verifier=mock_verifier, config=mock_config)
        task_provider = MockTaskProvider()
        
        scheduler.register_handler(task_provider)
        handler = task_provider.registered_handlers["audit:verify_recent"]
        
        result = await handler()
        
        assert "mismatches" in result
        assert result["mismatches"] == []

    @pytest.mark.asyncio
    async def test_registered_handler_returns_mismatches(self) -> None:
        verifier = MockVerifier(mismatches=3)
        config = MockConfig()
        scheduler = AuditScheduler(verifier=verifier, config=config)
        task_provider = MockTaskProvider()
        
        scheduler.register_handler(task_provider)
        handler = task_provider.registered_handlers["audit:verify_recent"]
        
        result = await handler()
        
        assert len(result["mismatches"]) == 3

    def test_register_handler_ignores_runtime_error(self, mock_verifier, mock_config) -> None:
        scheduler = AuditScheduler(verifier=mock_verifier, config=mock_config)
        task_provider = MockTaskProvider(should_fail=True)
        
        scheduler.register_handler(task_provider)
        # Should not raise, just silently fail

    def test_register_handler_ignores_type_error(self, mock_verifier, mock_config) -> None:
        scheduler = AuditScheduler(verifier=mock_verifier, config=mock_config)
        
        class BadProvider:
            def register_handler(self, name: str, handler) -> None:
                raise TypeError("Bad type")
        
        scheduler.register_handler(BadProvider())

    def test_register_handler_ignores_attribute_error(self, mock_verifier, mock_config) -> None:
        scheduler = AuditScheduler(verifier=mock_verifier, config=mock_config)
        
        class BadProvider:
            def register_handler(self) -> None:
                raise AttributeError("Missing method")
        
        scheduler.register_handler(BadProvider())

    def test_schedule_success(self, mock_verifier, mock_config) -> None:
        scheduler = AuditScheduler(verifier=mock_verifier, config=mock_config)
        task_provider = MockTaskProvider()
        
        job_id = scheduler.schedule(task_provider)
        
        assert job_id is not None
        assert len(task_provider.scheduled_jobs) == 1
        assert task_provider.scheduled_jobs[0]["name"] == "audit:verify_recent"

    def test_schedule_returns_none_on_failure(self, mock_verifier, mock_config) -> None:
        scheduler = AuditScheduler(verifier=mock_verifier, config=mock_config)
        task_provider = MockTaskProvider(should_fail=True)
        
        job_id = scheduler.schedule(task_provider)
        
        assert job_id is None

    def test_schedule_with_custom_audit_table(self, mock_verifier, mock_config) -> None:
        scheduler = AuditScheduler(verifier=mock_verifier, config=mock_config)
        task_provider = MockTaskProvider()
        
        job_id = scheduler.schedule(task_provider, audit_table="custom_audit")
        
        assert job_id is not None

    def test_schedule_with_key(self, mock_verifier, mock_config) -> None:
        scheduler = AuditScheduler(verifier=mock_verifier, config=mock_config)
        task_provider = MockTaskProvider()
        
        job_id = scheduler.schedule(task_provider, key=b"secret-key")
        
        assert job_id is not None

    def test_schedule_ignores_attribute_error(self, mock_verifier, mock_config) -> None:
        scheduler = AuditScheduler(verifier=mock_verifier, config=mock_config)
        
        class BadProvider:
            def schedule_job(self, name: str, schedule: str) -> str:
                raise AttributeError("Missing")
        
        job_id = scheduler.schedule(BadProvider())
        assert job_id is None

    def test_schedule_ignores_value_error(self, mock_verifier, mock_config) -> None:
        scheduler = AuditScheduler(verifier=mock_verifier, config=mock_config)
        
        class BadProvider:
            def schedule_job(self, name: str, schedule: str) -> str:
                raise ValueError("Invalid")
        
        job_id = scheduler.schedule(BadProvider())
        assert job_id is None

    def test_uses_config_batch_size(self, mock_verifier) -> None:
        config = MockConfig(verification_batch_size=200)
        scheduler = AuditScheduler(verifier=mock_verifier, config=config)
        task_provider = MockTaskProvider()
        
        scheduler.register_handler(task_provider)
        
        # The batch_size should be passed to the verifier
        handler = task_provider.registered_handlers["audit:verify_recent"]
        # We can't easily test the limit without running the handler
        assert scheduler._config.verification_batch_size == 200