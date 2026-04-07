"""Integration tests for worker pool lifecycles."""

import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from lexigram.ai.workers.config import WorkersConfig
from lexigram.ai.workers.di.provider import WorkersProvider


@pytest.fixture
def mock_container():
    """Mock DI container for testing registration."""
    class MockContainer:
        def __init__(self):
            self.singletons = {}
            self.registrations = []

        def singleton(self, cls, instance):
            self.singletons[cls] = instance

        def register(self, cls):
            self.registrations.append(cls)

    return MockContainer()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workers_provider_lifecycle_enabled(mock_container):
    """Test the complete provider lifecycle when workers are enabled."""
    config = WorkersConfig(enabled=True)
    provider = WorkersProvider(config=config)

    # Test Registration
    await provider.register(mock_container)
    
    assert WorkersConfig in mock_container.singletons
    assert mock_container.singletons[WorkersConfig] is config
    
    # Verify workers are registered
    assert len(mock_container.registrations) == 4
    
    # The list of workers registered
    from lexigram.ai.workers.dlq import DeadLetterQueueWorker
    from lexigram.ai.workers.batch_embedding.worker import BatchEmbeddingWorker
    from lexigram.ai.workers.document_ingestion.worker import DocumentIngestionWorker
    from lexigram.ai.workers.maintenance import MaintenanceWorker
    
    assert DeadLetterQueueWorker in mock_container.registrations
    assert BatchEmbeddingWorker in mock_container.registrations
    assert DocumentIngestionWorker in mock_container.registrations
    assert MaintenanceWorker in mock_container.registrations

    # Test Boot and Shutdown (Should not raise anything)
    await provider.boot(mock_container)
    await provider.shutdown()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_workers_provider_lifecycle_disabled(mock_container):
    """Test the complete provider lifecycle when workers are disabled."""
    config = WorkersConfig(enabled=False)
    provider = WorkersProvider(config=config)

    # Test Registration
    await provider.register(mock_container)
    
    # Config is still registered
    assert WorkersConfig in mock_container.singletons
    
    # But workers are skipped!
    assert len(mock_container.registrations) == 0

    # Test Boot and Shutdown
    await provider.boot(mock_container)
    await provider.shutdown()


@pytest.mark.integration
def test_workers_config_creation():
    """Test WorkersConfig can be created."""
    config = WorkersConfig()
    assert config is not None


@pytest.mark.integration
def test_workers_config_model_dump():
    """Test WorkersConfig model can be serialized."""
    config = WorkersConfig()
    config_dict = config.model_dump()
    assert isinstance(config_dict, dict)


@pytest.mark.integration
def test_workers_config_has_enabled():
    """Test WorkersConfig has enabled field."""
    config = WorkersConfig(enabled=True)
    assert config.enabled is True


@pytest.mark.integration
def test_workers_provider_name():
    """Test WorkersProvider has correct name."""
    provider = WorkersProvider()
    assert provider.name == "workers"


@pytest.mark.integration
def test_workers_module_import():
    """Test WorkersModule can be imported."""
    from lexigram.ai.workers.module import WorkersModule
    assert WorkersModule is not None
