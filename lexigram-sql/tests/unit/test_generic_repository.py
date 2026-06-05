from dataclasses import dataclass
#!/usr/bin/env python3
"""Unit tests for GenericRepository"""

from typing import Any
from unittest.mock import AsyncMock, Mock

from lexigram.domain import DomainModel
import pytest

from lexigram.contracts.data import DatabaseProviderProtocol, QueryResult, UpdateResult
from lexigram.sql.exceptions import DatabaseError, RepositoryError
from lexigram.sql.repositories.generic_repository import GenericRepository
from lexigram.sql.row_level_security import RowLevelSecurityPolicy, ScopeColumn


@dataclass
class SampleEntity(DomainModel):
    """Test Pydantic entity"""

    id: int | None = None
    name: str = ""
    value: int = 0


class SampleEntityRegular:
    """Test regular class entity"""

    def __init__(self, id=None, name="", value=0):
        self.id = id
        self.name = name
        self.value = value


class TestGenericRepository:
    """Test GenericRepository functionality"""

    @pytest.fixture
    def mock_provider(self):
        """Mock database provider"""
        provider = Mock(spec=DatabaseProviderProtocol)
        provider.execute_query = AsyncMock()
        provider.execute_insert = AsyncMock()
        provider.execute_update = AsyncMock()
        provider.execute_delete = AsyncMock()
        return provider

    @pytest.fixture
    def pydantic_repository(self, mock_provider):
        """Create repository for Pydantic entities"""
        return GenericRepository[SampleEntity, int](
            provider=mock_provider,
            table_name="test_entities",
            entity_class=SampleEntity,
            key_field="id",
        )

    @pytest.fixture
    def regular_repository(self, mock_provider):
        """Create repository for regular class entities"""
        return GenericRepository[SampleEntityRegular, int](
            provider=mock_provider,
            table_name="test_entities",
            entity_class=SampleEntityRegular,
            key_field="id",
        )

    @pytest.fixture
    def dict_repository(self, mock_provider):
        """Create repository for dict entities"""
        return GenericRepository[dict[str, Any], str](
            provider=mock_provider,
            table_name="test_entities",
            entity_class=dict,
            key_field="key",
        )

    def test_repository_initialization(self, pydantic_repository, mock_provider):
        """Test repository initialization"""
        assert pydantic_repository.provider == mock_provider
        assert pydantic_repository.table_name == "test_entities"
        assert pydantic_repository.key_field == "id"
        assert pydantic_repository.entity_class == SampleEntity

    def test_repository_initialization_accepts_rls_policy(self, mock_provider):
        """GenericRepository should forward an RLS policy to SQLRepository."""
        policy = RowLevelSecurityPolicy(columns=[ScopeColumn("tenant_id")])
        repo = GenericRepository[SampleEntity, int](
            provider=mock_provider,
            table_name="test_entities",
            entity_class=SampleEntity,
            key_field="id",
            rls_policy=policy,
        )

        assert repo._rls_policy is policy

    # Test _entity_to_dict method
    def test_entity_to_dict_pydantic(self, pydantic_repository):
        """Test converting Pydantic entity to dict"""
        entity = SampleEntity(id=1, name="test", value=42)
        result = pydantic_repository._entity_to_dict(entity)
        assert result == {"id": 1, "name": "test", "value": 42}

    def test_entity_to_dict_regular_class(self, regular_repository):
        """Test converting regular class entity to dict"""
        entity = SampleEntityRegular(id=1, name="test", value=42)
        result = regular_repository._entity_to_dict(entity)
        assert result == {"id": 1, "name": "test", "value": 42}

    def test_entity_to_dict_dict_entity(self, dict_repository):
        """Test converting dict entity to dict"""
        entity = {"key": "test_key", "name": "test", "value": 42}
        result = dict_repository._entity_to_dict(entity)
        assert result == {"key": "test_key", "name": "test", "value": 42}

    def test_entity_to_dict_invalid_entity(self, pydantic_repository):
        """Test converting invalid entity raises error"""
        entity = "invalid_entity"
        with pytest.raises(RepositoryError, match="Cannot convert entity of type"):
            pydantic_repository._entity_to_dict(entity)

    # Test _row_to_entity method
    def test_row_to_entity_pydantic(self, pydantic_repository):
        """Test converting row to Pydantic entity"""
        row = {"id": 1, "name": "test", "value": 42}
        entity = pydantic_repository._row_to_entity(row)
        assert isinstance(entity, SampleEntity)
        assert entity.id == 1
        assert entity.name == "test"
        assert entity.value == 42

    def test_row_to_entity_regular_class(self, regular_repository):
        """Test converting row to regular class entity"""
        row = {"id": 1, "name": "test", "value": 42}
        entity = regular_repository._row_to_entity(row)
        assert isinstance(entity, SampleEntityRegular)
        assert entity.id == 1
        assert entity.name == "test"
        assert entity.value == 42

    def test_row_to_entity_dict(self, dict_repository):
        """Test converting row to dict entity"""
        row = {"key": "test_key", "name": "test", "value": 42}
        entity = dict_repository._row_to_entity(row)
        assert isinstance(entity, dict)
        assert entity == {"key": "test_key", "name": "test", "value": 42}

    # Test find_by_id
    @pytest.mark.asyncio
    async def test_find_by_id_success(self, pydantic_repository, mock_provider):
        """Test finding entity by ID successfully"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"id": 1, "name": "test", "value": 42}]
        mock_provider.execute_query.return_value = query_result

        result = await pydantic_repository.find_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.name == "test"
        assert result.value == 42

        mock_provider.execute_query.assert_called_once_with(
            'SELECT * FROM "test_entities" WHERE "id" = ?', [1],
        )

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, pydantic_repository, mock_provider):
        """Test finding entity by ID when not found"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = []
        mock_provider.execute_query.return_value = query_result

        result = await pydantic_repository.find_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_id_failure(self, pydantic_repository, mock_provider):
        """Test finding entity by ID with database failure"""
        mock_provider.execute_query.side_effect = DatabaseError("database error")

        with pytest.raises(RepositoryError, match="Failed to find entity by id 1"):
            await pydantic_repository.find_by_id(1)

    # Test find_one
    @pytest.mark.asyncio
    async def test_find_one_success(self, pydantic_repository, mock_provider):
        """Test finding one entity with criteria"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"id": 1, "name": "test", "value": 42}]
        mock_provider.execute_query.return_value = query_result

        result = await pydantic_repository.find_one(name="test", value=42)

        assert result is not None
        assert result.name == "test"
        assert result.value == 42

        mock_provider.execute_query.assert_called_once_with(
            'SELECT * FROM "test_entities" WHERE "name" = ? AND "value" = ? LIMIT 1',
            ["test", 42],
        )

    @pytest.mark.asyncio
    async def test_find_one_not_found(self, pydantic_repository, mock_provider):
        """Test finding one entity when not found"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = []
        mock_provider.execute_query.return_value = query_result

        result = await pydantic_repository.find_one(name="nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_find_one_failure(self, pydantic_repository, mock_provider):
        """Test finding one entity with database failure"""
        mock_provider.execute_query.side_effect = DatabaseError("database error")

        with pytest.raises(RepositoryError, match="Failed to find entity"):
            await pydantic_repository.find_one(name="test")

    # Test find_many
    @pytest.mark.asyncio
    async def test_find_many_success(self, pydantic_repository, mock_provider):
        """Test finding many entities with criteria"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [
            {"id": 1, "name": "test", "value": 42},
            {"id": 2, "name": "test", "value": 43},
        ]
        mock_provider.execute_query.return_value = query_result

        results = await pydantic_repository.find_many(name="test")

        assert len(results) == 2
        assert results[0].name == "test"
        assert results[1].name == "test"

        mock_provider.execute_query.assert_called_once_with(
            'SELECT * FROM "test_entities" WHERE "name" = ?', ["test"],
        )

    @pytest.mark.asyncio
    async def test_find_many_no_criteria(self, pydantic_repository, mock_provider):
        """Test finding many entities with no criteria"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"id": 1, "name": "all", "value": 1}]
        mock_provider.execute_query.return_value = query_result

        results = await pydantic_repository.find_many()

        assert len(results) == 1
        mock_provider.execute_query.assert_called_once_with(
            'SELECT * FROM "test_entities" WHERE 1=1', None,
        )

    @pytest.mark.asyncio
    async def test_find_many_failure(self, pydantic_repository, mock_provider):
        """Test finding many entities with database failure"""
        mock_provider.execute_query.side_effect = DatabaseError("database error")

        with pytest.raises(
            RepositoryError, match="Failed to find entities with criteria",
        ):
            await pydantic_repository.find_many(name="test")

    # Test find_many
    @pytest.mark.asyncio
    async def test_find_all_no_limits(self, pydantic_repository, mock_provider):
        """Test finding all entities without limits"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [
            {"id": 1, "name": "first", "value": 10},
            {"id": 2, "name": "second", "value": 20},
        ]
        mock_provider.execute_query.return_value = query_result

        results = await pydantic_repository.find_many()

        assert len(results) == 2
        assert results[0].id == 1
        assert results[1].id == 2

        mock_provider.execute_query.assert_called_once_with(
            'SELECT * FROM "test_entities" WHERE 1=1', None,
        )

    @pytest.mark.asyncio
    async def test_find_all_with_limit(self, pydantic_repository, mock_provider):
        """Test finding all entities with limit"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"id": 1, "name": "first", "value": 10}]
        mock_provider.execute_query.return_value = query_result

        results = await pydantic_repository.find_many(limit=1)

        assert len(results) == 1
        mock_provider.execute_query.assert_called_once_with(
            'SELECT * FROM "test_entities" WHERE 1=1 LIMIT ?', [1],
        )

    @pytest.mark.asyncio
    async def test_find_all_with_offset(self, pydantic_repository, mock_provider):
        """Test finding all entities with offset"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"id": 2, "name": "second", "value": 20}]
        mock_provider.execute_query.return_value = query_result

        results = await pydantic_repository.find_many(offset=1)

        assert len(results) == 1
        mock_provider.execute_query.assert_called_once_with(
            'SELECT * FROM "test_entities" WHERE 1=1 OFFSET ?', [1],
        )

    @pytest.mark.asyncio
    async def test_find_all_with_limit_and_offset(
        self, pydantic_repository, mock_provider,
    ):
        """Test finding all entities with both limit and offset"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"id": 2, "name": "second", "value": 20}]
        mock_provider.execute_query.return_value = query_result

        results = await pydantic_repository.find_many(limit=1, offset=1)

        assert len(results) == 1
        mock_provider.execute_query.assert_called_once_with(
            'SELECT * FROM "test_entities" WHERE 1=1 LIMIT ? OFFSET ?', [1, 1],
        )

    @pytest.mark.asyncio
    async def test_find_many_query_failure(self, pydantic_repository, mock_provider):
        """Test find_many when query fails"""
        query_result = Mock()
        query_result.success = False
        query_result.rows = []
        mock_provider.execute_query.return_value = query_result

        results = await pydantic_repository.find_many(name="test")

        assert results == []

    @pytest.mark.asyncio
    async def test_find_all_query_failure(self, pydantic_repository, mock_provider):
        """Test find_many when query fails"""
        query_result = Mock()
        query_result.success = False
        query_result.rows = []
        mock_provider.execute_query.return_value = query_result

        results = await pydantic_repository.find_many()

        assert results == []

    @pytest.mark.asyncio
    async def test_find_all_exception(self, pydantic_repository, mock_provider):
        """Test find_many when execute_query raises exception"""
        mock_provider.execute_query.side_effect = DatabaseError("database error")

        with pytest.raises(RepositoryError, match="Failed to find entities"):
            await pydantic_repository.find_many()

    # Test create
    @pytest.mark.asyncio
    async def test_create_new_entity_pydantic(self, pydantic_repository, mock_provider):
        """Test creating a new Pydantic entity"""
        entity = SampleEntity(name="new", value=100)

        insert_result = Mock()
        insert_result.success = True
        insert_result.inserted_id = 123
        mock_provider.execute_insert.return_value = insert_result

        result = await pydantic_repository.create(entity)

        assert result.id == 123
        assert result.name == "new"
        assert result.value == 100

        called_args = mock_provider.execute_insert.call_args[0]
        assert called_args[0] == "test_entities"
        insert_data = called_args[1]
        assert insert_data["name"] == "new"
        assert insert_data["value"] == 100
        assert "created_at" in insert_data and "updated_at" in insert_data

    @pytest.mark.asyncio
    async def test_create_entity_with_existing_id(
        self, pydantic_repository, mock_provider,
    ):
        """Test creating an entity that already has an ID"""
        entity = SampleEntity(id=456, name="existing", value=200)

        insert_result = Mock()
        insert_result.success = True
        insert_result.inserted_id = 456
        mock_provider.execute_insert.return_value = insert_result

        result = await pydantic_repository.create(entity)

        assert result.id == 456
        # Note: ID is included in insert data since it's not None
        called_args = mock_provider.execute_insert.call_args[0]
        assert called_args[0] == "test_entities"
        insert_data = called_args[1]
        assert insert_data["id"] == 456
        assert insert_data["name"] == "existing"
        assert insert_data["value"] == 200
        assert "created_at" in insert_data and "updated_at" in insert_data

    @pytest.mark.asyncio
    async def test_create_regular_class_entity(self, regular_repository, mock_provider):
        """Test creating a regular class entity"""
        entity = SampleEntityRegular(name="regular", value=300)

        insert_result = Mock()
        insert_result.success = True
        insert_result.inserted_id = 789
        mock_provider.execute_insert.return_value = insert_result

        result = await regular_repository.create(entity)

        assert result.id == 789
        assert result.name == "regular"
        assert result.value == 300

    @pytest.mark.asyncio
    async def test_create_dict_entity(self, dict_repository, mock_provider):
        """Test creating a dict entity"""
        entity = {"name": "dict_entity", "value": 400}

        insert_result = Mock()
        insert_result.success = True
        insert_result.inserted_id = "new_key"
        mock_provider.execute_insert.return_value = insert_result

        result = await dict_repository.create(entity)

        assert result["key"] == "new_key"
        assert result["name"] == "dict_entity"
        assert result["value"] == 400

    @pytest.mark.asyncio
    async def test_create_failure(self, pydantic_repository, mock_provider):
        """Test create with database failure"""
        entity = SampleEntity(name="fail", value=500)
        mock_provider.execute_insert.side_effect = DatabaseError("insert failed")

        with pytest.raises(RepositoryError, match="Failed to create entity"):
            await pydantic_repository.create(entity)

    # Test update
    @pytest.mark.asyncio
    async def test_update_entity_pydantic(self, pydantic_repository, mock_provider):
        """Test updating a Pydantic entity"""
        entity = SampleEntity(id=1, name="updated", value=600)

        update_result = Mock()
        update_result.success = True
        mock_provider.execute_update.return_value = update_result

        result = await pydantic_repository.update(entity)

        assert result == entity

        called_args = mock_provider.execute_update.call_args[0]
        assert called_args[0] == "test_entities"
        update_data = called_args[1]
        assert update_data["name"] == "updated"
        assert update_data["value"] == 600
        assert "updated_at" in update_data
        assert called_args[2] == '"id" = ?'
        assert called_args[3] == [1]

    @pytest.mark.asyncio
    async def test_update_entity_without_id(self, pydantic_repository):
        """Test updating entity without ID raises error"""
        entity = SampleEntity(name="no_id", value=700)

        with pytest.raises(
            RepositoryError, match="Entity must have a primary key value for update",
        ):
            await pydantic_repository.update(entity)

    @pytest.mark.asyncio
    async def test_update_query_failure(self, pydantic_repository, mock_provider):
        """Test update when query fails"""
        entity = SampleEntity(id=1, name="fail", value=200)

        update_result = Mock()
        update_result.success = False
        update_result.error_message = "update failed"
        mock_provider.execute_update.return_value = update_result

        with pytest.raises(RepositoryError, match="Update failed: update failed"):
            await pydantic_repository.update(entity)

    # Test delete
    @pytest.mark.asyncio
    async def test_delete_entity_success(self, pydantic_repository, mock_provider):
        """Test deleting an entity successfully"""
        delete_result = Mock()
        delete_result.success = True
        delete_result.affected_rows = 1
        mock_provider.execute_delete.return_value = delete_result

        result = await pydantic_repository.delete(1)

        assert result is True

        mock_provider.execute_delete.assert_called_once_with(
            "test_entities", '"id" = ?', [1],
        )

    @pytest.mark.asyncio
    async def test_delete_entity_not_found(self, pydantic_repository, mock_provider):
        """Test deleting an entity that doesn't exist"""
        delete_result = Mock()
        delete_result.success = True
        delete_result.affected_rows = 0
        mock_provider.execute_delete.return_value = delete_result

        result = await pydantic_repository.delete(999)

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_failure(self, pydantic_repository, mock_provider):
        """Test delete with database failure"""
        mock_provider.execute_delete.side_effect = DatabaseError("delete failed")

        with pytest.raises(RepositoryError, match="Failed to delete entity"):
            await pydantic_repository.delete(1)

    # Test count
    @pytest.mark.asyncio
    async def test_count_with_criteria(self, pydantic_repository, mock_provider):
        """Test counting entities with criteria"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"count": 5}]
        mock_provider.execute_query.return_value = query_result

        result = await pydantic_repository.count(status="active")

        assert result == 5

        mock_provider.execute_query.assert_called_once_with(
            'SELECT COUNT(*) as count FROM "test_entities" WHERE "status" = ?', ["active"],
        )

    @pytest.mark.asyncio
    async def test_count_with_filters_dict(self, pydantic_repository, mock_provider):
        """Test counting entities with dict-style filters (mirrors find())"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"count": 3}]
        mock_provider.execute_query.return_value = query_result

        result = await pydantic_repository.count(filters={"status": "active"})

        assert result == 3

        mock_provider.execute_query.assert_called_once_with(
            'SELECT COUNT(*) as count FROM "test_entities" WHERE "status" = ?', ["active"],
        )

    @pytest.mark.asyncio
    async def test_count_no_criteria(self, pydantic_repository, mock_provider):
        """Test counting all entities"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"count": 10}]
        mock_provider.execute_query.return_value = query_result

        result = await pydantic_repository.count()

        assert result == 10

        mock_provider.execute_query.assert_called_once_with(
            'SELECT COUNT(*) as count FROM "test_entities"', [],
        )

    @pytest.mark.asyncio
    async def test_count_no_rows(self, pydantic_repository, mock_provider):
        """Test count when query succeeds but returns no rows"""
        query_result = QueryResult(
            rows=[], row_count=0, execution_time=0.01, success=True,
        )
        mock_provider.execute_query.return_value = query_result

        result = await pydantic_repository.count(name="test")

        assert result == 0

    # Test exists
    @pytest.mark.asyncio
    async def test_exists_true(self, pydantic_repository, mock_provider):
        """Test checking existence when entity exists"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"count": 1}]
        mock_provider.execute_query.return_value = query_result

        result = await pydantic_repository.exists(name="test")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, pydantic_repository, mock_provider):
        """Test checking existence when entity doesn't exist"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"count": 0}]
        mock_provider.execute_query.return_value = query_result

        result = await pydantic_repository.exists(name="nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_exists_failure(self, pydantic_repository, mock_provider):
        """Test exists with database failure"""
        mock_provider.execute_query.side_effect = DatabaseError("database error")

        with pytest.raises(
            RepositoryError, match="Failed to check existence with criteria",
        ):
            await pydantic_repository.exists(name="test")
