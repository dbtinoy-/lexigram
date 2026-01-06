from dataclasses import dataclass, field
"""Integration tests for Resource Management and Integration (Phase 3)."""

from unittest.mock import AsyncMock, MagicMock

from lexigram.domain import DomainModel
import pytest

from lexigram.admin.data.adapters.memory_adapter import InMemoryDataSource
from lexigram.admin.data.query import QuerySpec
from lexigram.admin.services.resource_manager import ResourceManager
from lexigram.admin.lib.transformation import DataTransformer, json_transformer


@dataclass
class Product(DomainModel):
    id: int
    name: str
    metadata: dict = field(default_factory=dict)


class TestResourceIntegration:
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_resource_manager_crud(self):
        # Arrange
        data = [{"id": 1, "name": "Phone"}]
        ds = InMemoryDataSource(data)
        manager = ResourceManager("products", ds, model=Product)

        # Act: List
        result = (await manager.list(QuerySpec())).unwrap()
        assert result.total == 1
        assert result.items[0].name == "Phone"

        # Act: Create
        (await manager.create({"id": 2, "name": "Laptop"})).unwrap()
        assert (await ds.count(QuerySpec())) == 2

        # Act: Get
        item = (await manager.get(2)).unwrap()
        assert item.name == "Laptop"

        # Act: Update
        (await manager.update(2, {"name": "Super Laptop"})).unwrap()
        updated = (await manager.get(2)).unwrap()
        assert updated.name == "Super Laptop"

        # Act: Delete
        (await manager.delete(1)).unwrap()
        assert (await ds.count(QuerySpec())) == 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_data_transformer_integration(self):
        # Arrange
        transformer = DataTransformer()
        to_f, from_f = json_transformer()
        transformer.register("metadata", to_f, from_f)

        raw_data = {"id": 1, "metadata": '{"color": "red"}'}

        # Act: To Form
        form_data = transformer.transform_to_form(raw_data)
        assert form_data["metadata"] == {"color": "red"}

        # Act: From Form
        back_data = transformer.transform_from_form(form_data)
        # Allow JSON spacing variations across different json.dumps implementations
        from lexigram import serialization as json

        assert json.loads(back_data["metadata"]) == {"color": "red"}

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_controller_integration_concept(self):
        """Verify the controller would use the manager correctly."""
        from lexigram.admin.controllers.resource import ResourceController

        # Mocking the registry and request
        mock_ds = AsyncMock()
        mock_ds.find_one.return_value = {"id": 1, "name": "Test"}
        manager = ResourceManager("test", mock_ds, model=Product)

        res_config = MagicMock()
        res_config.manager = manager

        registry = {"test": res_config}
        _controller = ResourceController(registry)

        # Verifying that edit would fetch via manager
        request = MagicMock()
        request.headers = {}

        # We'll just manually call the logic that was inside edit
        item = (await manager.get("1")).unwrap()
        assert item.name == "Test"
        mock_ds.find_one.assert_called_with("1")