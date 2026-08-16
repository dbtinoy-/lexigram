#!/usr/bin/env python3
"""Unit tests for RepositoryProtocol"""

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from lexigram.sql.exceptions import DatabaseError, RepositoryError
from lexigram.sql.repositories.base import SQLRepository


class TestRepositoryHookInitialization:
    """SQLRepository must properly initialize post-save/post-delete hooks."""

    @pytest.fixture
    def mock_provider(self):
        provider = Mock()
        provider.execute_query = AsyncMock()
        provider.execute_insert = AsyncMock()
        provider.execute_update = AsyncMock()
        provider.execute_delete = AsyncMock()
        return provider

    @pytest.fixture
    def concrete_repository(self, mock_provider):
        class TestEntity:
            def __init__(self, id=None, name=""):
                self.id = id
                self.name = name

        class ConcreteRepository(SQLRepository[TestEntity, int]):
            def _entity_to_dict(self, entity):
                return {"id": entity.id, "name": entity.name}
            def _row_to_entity(self, row):
                return TestEntity(id=row.get("id"), name=row.get("name", ""))

        return ConcreteRepository(mock_provider, "test_entities", "id")

    def test_hook_lists_initialized(self, concrete_repository):
        """_post_save_hooks and _post_delete_hooks must be empty lists."""
        assert concrete_repository._post_save_hooks == []
        assert concrete_repository._post_delete_hooks == []

    def test_register_post_save_hook_appends(self, concrete_repository):
        """register_post_save_hook adds callback."""
        callback = Mock()
        concrete_repository.register_post_save_hook(callback)
        assert callback in concrete_repository._post_save_hooks

    def test_register_post_delete_hook_appends(self, concrete_repository):
        """register_post_delete_hook adds callback."""
        callback = Mock()
        concrete_repository.register_post_delete_hook(callback)
        assert callback in concrete_repository._post_delete_hooks

    @pytest.mark.asyncio
    async def test_delete_fires_post_delete_hooks(self, concrete_repository, mock_provider):
        """SQLRepository.delete() must fire registered post-delete hooks."""
        hook = AsyncMock()
        concrete_repository.register_post_delete_hook(hook)
        entity = concrete_repository._row_to_entity({"id": 42, "name": "del"})
        delete_result = Mock()
        delete_result.success = True
        mock_provider.execute_delete.return_value = delete_result

        await concrete_repository.delete(entity)

        hook.assert_awaited_once_with(42)


class TestRepositoryError:
    """Test RepositoryError exception"""

    def test_repository_error_creation(self):
        """Test creating a RepositoryError"""
        error = RepositoryError("test error")
        assert "[LEX_ERR_SQL_023]" in str(error)
        assert "test error" in str(error)


class TestRepository:
    """Test RepositoryProtocol functionality"""

    @pytest.fixture
    def mock_provider(self):
        """Mock database provider"""
        provider = Mock()
        provider.execute_query = AsyncMock()
        provider.execute_insert = AsyncMock()
        provider.execute_update = AsyncMock()
        provider.execute_delete = AsyncMock()
        return provider

    @pytest.fixture
    def concrete_repository(self, mock_provider):
        """Create a concrete repository for testing"""

        class TestEntity:
            def __init__(self, id=None, name="", value=0):
                self.id = id
                self.name = name
                self.value = value

        class ConcreteRepository(SQLRepository[TestEntity, int]):
            def _entity_to_dict(self, entity: TestEntity) -> dict[str, Any]:
                return {"id": entity.id, "name": entity.name, "value": entity.value}

            def _row_to_entity(self, row: dict[str, Any]) -> TestEntity:
                return TestEntity(
                    id=row.get("id"),
                    name=row.get("name", ""),
                    value=row.get("value", 0),
                )

        return ConcreteRepository(mock_provider, "test_entities", "id")

    @pytest.mark.asyncio
    async def test_repository_initialization(self, concrete_repository, mock_provider):
        """Test repository initialization"""
        assert concrete_repository.provider == mock_provider
        assert concrete_repository.table_name == "test_entities"
        assert concrete_repository.key_field == "id"

    @pytest.mark.asyncio
    async def test_find_by_id_success(self, concrete_repository, mock_provider):
        """Test finding entity by ID successfully"""
        # Mock successful query result
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"id": 1, "name": "test", "value": 42}]
        mock_provider.execute_query.return_value = query_result

        result = await concrete_repository.find_by_id(1)

        assert result is not None
        assert result.id == 1
        assert result.name == "test"
        assert result.value == 42

        mock_provider.execute_query.assert_called_once_with(
            'SELECT * FROM "test_entities" WHERE "id" = ?', [1],
        )

    @pytest.mark.asyncio
    async def test_find_by_id_not_found(self, concrete_repository, mock_provider):
        """Test finding entity by ID when not found"""
        # Mock empty result
        query_result = Mock()
        query_result.success = True
        query_result.rows = []
        mock_provider.execute_query.return_value = query_result

        result = await concrete_repository.find_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_find_by_id_failure(self, concrete_repository, mock_provider):
        """Test finding entity by ID with database failure"""
        mock_provider.execute_query.side_effect = DatabaseError("database error")

        with pytest.raises(RepositoryError, match="Failed to find entity by id 1"):
            await concrete_repository.find_by_id(1)

    @pytest.mark.asyncio
    async def test_find_all_no_limits(self, concrete_repository, mock_provider):
        """Test finding all entities without limits"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [
            {"id": 1, "name": "first", "value": 10},
            {"id": 2, "name": "second", "value": 20},
        ]
        mock_provider.execute_query.return_value = query_result

        results = await concrete_repository.find_many()

        assert len(results) == 2
        assert results[0].id == 1
        assert results[1].id == 2

        mock_provider.execute_query.assert_called_once_with(
            'SELECT * FROM "test_entities" WHERE 1=1', None,
        )

    @pytest.mark.asyncio
    async def test_find_all_with_limit(self, concrete_repository, mock_provider):
        """Test finding all entities with limit"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"id": 1, "name": "first", "value": 10}]
        mock_provider.execute_query.return_value = query_result

        results = await concrete_repository.find_many(limit=1)

        assert len(results) == 1
        mock_provider.execute_query.assert_called_once_with(
            'SELECT * FROM "test_entities" WHERE 1=1 LIMIT ?', [1],
        )

    @pytest.mark.asyncio
    async def test_find_all_with_offset(self, concrete_repository, mock_provider):
        """Test finding all entities with offset"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"id": 2, "name": "second", "value": 20}]
        mock_provider.execute_query.return_value = query_result

        results = await concrete_repository.find_many(offset=1)

        assert len(results) == 1
        mock_provider.execute_query.assert_called_once_with(
            'SELECT * FROM "test_entities" WHERE 1=1 OFFSET ?', [1],
        )

    @pytest.mark.asyncio
    async def test_find_all_with_limit_and_offset(
        self, concrete_repository, mock_provider,
    ):
        """Test finding all entities with both limit and offset"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"id": 2, "name": "second", "value": 20}]
        mock_provider.execute_query.return_value = query_result

        results = await concrete_repository.find_many(limit=1, offset=1)

        assert len(results) == 1
        mock_provider.execute_query.assert_called_once_with(
            'SELECT * FROM "test_entities" WHERE 1=1 LIMIT ? OFFSET ?', [1, 1],
        )

    @pytest.mark.asyncio
    async def test_find_many_with_criteria(self, concrete_repository, mock_provider):
        """Test finding entities with criteria"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"id": 1, "name": "test", "value": 42}]
        mock_provider.execute_query.return_value = query_result

        results = await concrete_repository.find_many(name="test", value=42)

        assert len(results) == 1
        assert results[0].name == "test"

        mock_provider.execute_query.assert_called_once_with(
            'SELECT * FROM "test_entities" WHERE "name" = ? AND "value" = ?', ["test", 42],
        )

    @pytest.mark.asyncio
    async def test_find_many_no_criteria(self, concrete_repository, mock_provider):
        """Test finding entities with no criteria"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"id": 1, "name": "all", "value": 1}]
        mock_provider.execute_query.return_value = query_result

        results = await concrete_repository.find_many()

        assert len(results) == 1
        mock_provider.execute_query.assert_called_once_with(
            'SELECT * FROM "test_entities" WHERE 1=1', None,
        )

    @pytest.mark.asyncio
    async def test_find_one_with_results(self, concrete_repository, mock_provider):
        """Test finding one entity when results exist"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"id": 1, "name": "first", "value": 10}]
        mock_provider.execute_query.return_value = query_result

        result = await concrete_repository.find_one(name="first")

        assert result is not None
        assert result.name == "first"

    @pytest.mark.asyncio
    async def test_find_one_no_results(self, concrete_repository, mock_provider):
        """Test finding one entity when no results"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = []
        mock_provider.execute_query.return_value = query_result

        result = await concrete_repository.find_one(name="nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_exists_true(self, concrete_repository, mock_provider):
        """Test checking existence when entity exists"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"count": 1}]
        mock_provider.execute_query.return_value = query_result

        result = await concrete_repository.exists(name="test")

        assert result is True

    @pytest.mark.asyncio
    async def test_exists_false(self, concrete_repository, mock_provider):
        """Test checking existence when entity doesn't exist"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"count": 0}]
        mock_provider.execute_query.return_value = query_result

        result = await concrete_repository.exists(name="nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_count_with_criteria(self, concrete_repository, mock_provider):
        """Test counting entities with criteria"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"count": 5}]
        mock_provider.execute_query.return_value = query_result

        result = await concrete_repository.count(status="active")

        assert result == 5

    @pytest.mark.asyncio
    async def test_count_no_criteria(self, concrete_repository, mock_provider):
        """Test counting all entities"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = [{"count": 10}]
        mock_provider.execute_query.return_value = query_result

        result = await concrete_repository.count()

        assert result == 10

    @pytest.mark.asyncio
    async def test_create_new_entity(self, concrete_repository, mock_provider):
        """Test creating a new entity"""
        # Create entity without ID
        entity = concrete_repository._row_to_entity({"name": "new", "value": 100})

        # Mock insert result
        insert_result = Mock()
        insert_result.success = True
        insert_result.inserted_id = 123
        mock_provider.execute_insert.return_value = insert_result

        result = await concrete_repository.create(entity)

        assert result.id == 123
        assert result.name == "new"
        assert result.value == 100

        # Timestamps are automatically added; assert essential fields and presence of timestamps
        called_args = mock_provider.execute_insert.call_args[0]
        assert called_args[0] == "test_entities"
        insert_data = called_args[1]
        assert insert_data["name"] == "new"
        assert insert_data["value"] == 100
        assert "created_at" in insert_data and "updated_at" in insert_data

    @pytest.mark.asyncio
    async def test_create_entity_with_existing_id(
        self, concrete_repository, mock_provider,
    ):
        """Test creating an entity that already has an ID"""
        entity = concrete_repository._row_to_entity(
            {"id": 456, "name": "existing", "value": 200},
        )

        insert_result = Mock()
        insert_result.success = True
        insert_result.inserted_id = 456
        mock_provider.execute_insert.return_value = insert_result

        result = await concrete_repository.create(entity)

        assert result.id == 456
        # Should still include ID in insert data since it's not None
        called_args = mock_provider.execute_insert.call_args[0]
        assert called_args[0] == "test_entities"
        insert_data = called_args[1]
        assert insert_data["id"] == 456
        assert insert_data["name"] == "existing"
        assert insert_data["value"] == 200
        assert "created_at" in insert_data and "updated_at" in insert_data

    @pytest.mark.asyncio
    async def test_update_entity(self, concrete_repository, mock_provider):
        """Test updating an existing entity"""
        entity = concrete_repository._row_to_entity(
            {"id": 1, "name": "updated", "value": 300},
        )

        update_result = Mock()
        update_result.success = True
        mock_provider.execute_update.return_value = update_result

        result = await concrete_repository.update(entity)

        assert result == entity

        called_args = mock_provider.execute_update.call_args[0]
        assert called_args[0] == "test_entities"
        update_data = called_args[1]
        assert update_data["name"] == "updated"
        assert update_data["value"] == 300
        assert "updated_at" in update_data
        assert called_args[2] == '"id" = ?'
        assert called_args[3] == [1]

    @pytest.mark.asyncio
    async def test_update_entity_without_id(self, concrete_repository):
        """Test updating entity without ID raises error"""
        entity = concrete_repository._row_to_entity({"name": "no_id", "value": 400})

        with pytest.raises(
            RepositoryError, match="Entity must have a primary key value for update",
        ):
            await concrete_repository.update(entity)

    @pytest.mark.asyncio
    async def test_delete_entity(self, concrete_repository, mock_provider):
        """Test deleting an entity"""
        entity = concrete_repository._row_to_entity(
            {"id": 1, "name": "to_delete", "value": 500},
        )

        delete_result = Mock()
        delete_result.success = True
        mock_provider.execute_delete.return_value = delete_result

        await concrete_repository.delete(entity)

        mock_provider.execute_delete.assert_called_once_with(
            "test_entities", '"id" = ?', [1],
        )

    @pytest.mark.asyncio
    async def test_delete_entity_without_id(self, concrete_repository):
        """Test deleting entity without ID raises error"""
        entity = concrete_repository._row_to_entity({"name": "no_id", "value": 600})

        with pytest.raises(
            RepositoryError, match="Entity must have a primary key value for deletion",
        ):
            await concrete_repository.delete(entity)

    @pytest.mark.asyncio
    async def test_delete_by_id(self, concrete_repository, mock_provider):
        """Test deleting entity by ID"""
        delete_result = Mock()
        delete_result.success = True
        mock_provider.execute_delete.return_value = delete_result

        await concrete_repository.delete_by_id(42)

        mock_provider.execute_delete.assert_called_once_with(
            "test_entities", '"id" = ?', [42],
        )

    # Error handling tests
    @pytest.mark.asyncio
    async def test_find_all_failure(self, concrete_repository, mock_provider):
        """Test find_many with database failure"""
        mock_provider.execute_query.side_effect = DatabaseError("query failed")

        with pytest.raises(RepositoryError, match="Failed to find entities with criteria"):
            await concrete_repository.find_many()

    @pytest.mark.asyncio
    async def test_find_many_failure(self, concrete_repository, mock_provider):
        """Test find_many with database failure"""
        mock_provider.execute_query.side_effect = DatabaseError("query failed")

        with pytest.raises(
            RepositoryError, match="Failed to find entities with criteria",
        ):
            await concrete_repository.find_many(name="test")

    @pytest.mark.asyncio
    async def test_exists_failure(self, concrete_repository, mock_provider):
        """Test exists with database failure"""
        mock_provider.execute_query.side_effect = DatabaseError("query failed")

        with pytest.raises(
            RepositoryError, match="Failed to check existence with criteria",
        ):
            await concrete_repository.exists(name="test")

    @pytest.mark.asyncio
    async def test_count_failure(self, concrete_repository, mock_provider):
        """Test count with database failure"""
        mock_provider.execute_query.side_effect = DatabaseError("query failed")

        with pytest.raises(
            RepositoryError, match="Failed to count entities with criteria",
        ):
            await concrete_repository.count(name="test")

    @pytest.mark.asyncio
    async def test_create_failure(self, concrete_repository, mock_provider):
        """Test create with database failure"""
        entity = concrete_repository._row_to_entity({"name": "fail", "value": 700})
        mock_provider.execute_insert.side_effect = DatabaseError("insert failed")

        with pytest.raises(RepositoryError, match="Failed to create entity"):
            await concrete_repository.create(entity)

    @pytest.mark.asyncio
    async def test_update_failure(self, concrete_repository, mock_provider):
        """Test update with database failure"""
        entity = concrete_repository._row_to_entity(
            {"id": 1, "name": "fail", "value": 800},
        )
        mock_provider.execute_update.side_effect = DatabaseError("update failed")

        with pytest.raises(RepositoryError, match="Failed to update entity"):
            await concrete_repository.update(entity)

    @pytest.mark.asyncio
    async def test_delete_failure(self, concrete_repository, mock_provider):
        """Test delete with database failure"""
        entity = concrete_repository._row_to_entity(
            {"id": 1, "name": "fail", "value": 900},
        )
        mock_provider.execute_delete.side_effect = DatabaseError("delete failed")

        with pytest.raises(RepositoryError, match="Failed to delete entity"):
            await concrete_repository.delete(entity)

    @pytest.mark.asyncio
    async def test_find_all_query_failure(self, concrete_repository, mock_provider):
        """Test find_many when query fails"""
        query_result = Mock()
        query_result.success = False
        query_result.rows = []
        mock_provider.execute_query.return_value = query_result

        results = await concrete_repository.find_many()

        assert results == []

    @pytest.mark.asyncio
    async def test_find_many_query_failure(self, concrete_repository, mock_provider):
        """Test find_many when query fails"""
        query_result = Mock()
        query_result.success = False
        query_result.rows = []
        mock_provider.execute_query.return_value = query_result

        results = await concrete_repository.find_many(name="test")

        assert results == []

    @pytest.mark.asyncio
    async def test_exists_no_rows(self, concrete_repository, mock_provider):
        """Test exists when query succeeds but returns no rows"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = []
        mock_provider.execute_query.return_value = query_result

        result = await concrete_repository.exists(name="test")

        assert result is False

    @pytest.mark.asyncio
    async def test_count_no_rows(self, concrete_repository, mock_provider):
        """Test count when query succeeds but returns no rows"""
        query_result = Mock()
        query_result.success = True
        query_result.rows = []
        mock_provider.execute_query.return_value = query_result

        result = await concrete_repository.count(name="test")

        assert result == 0

    @pytest.mark.asyncio
    async def test_create_without_inserted_id(self, concrete_repository, mock_provider):
        """Test create when insert succeeds but no inserted_id"""
        entity = concrete_repository._row_to_entity({"name": "no_id", "value": 100})

        insert_result = Mock()
        insert_result.success = True
        insert_result.inserted_id = None
        mock_provider.execute_insert.return_value = insert_result

        result = await concrete_repository.create(entity)

        assert result == entity
        assert result.id is None  # Should remain None

    @pytest.mark.asyncio
    async def test_update_query_failure(self, concrete_repository, mock_provider):
        """Test update when query fails"""
        entity = concrete_repository._row_to_entity(
            {"id": 1, "name": "fail", "value": 200},
        )

        update_result = Mock()
        update_result.success = False
        update_result.error_message = "update failed"
        mock_provider.execute_update.return_value = update_result

        with pytest.raises(RepositoryError, match="Update failed: update failed"):
            await concrete_repository.update(entity)

    @pytest.mark.asyncio
    async def test_delete_query_failure(self, concrete_repository, mock_provider):
        """Test delete when query fails"""
        entity = concrete_repository._row_to_entity(
            {"id": 1, "name": "fail", "value": 300},
        )

        delete_result = Mock()
        delete_result.success = False
        delete_result.error_message = "delete failed"
        mock_provider.execute_delete.return_value = delete_result

        with pytest.raises(RepositoryError, match="Delete failed: delete failed"):
            await concrete_repository.delete(entity)

    @pytest.mark.asyncio
    async def test_delete_by_id_query_failure(self, concrete_repository, mock_provider):
        """Test delete_by_id when query fails"""
        delete_result = Mock()
        delete_result.success = False
        delete_result.error_message = "delete failed"
        mock_provider.execute_delete.return_value = delete_result

        with pytest.raises(RepositoryError, match="Delete failed: delete failed"):
            await concrete_repository.delete_by_id(1)

    @pytest.mark.asyncio
    async def test_bulk_create(self, concrete_repository, mock_provider):
        """Test default bulk_create implementation"""
        entities = [
            concrete_repository._row_to_entity({"name": "first", "value": 1}),
            concrete_repository._row_to_entity({"name": "second", "value": 2}),
        ]
        
        insert_results = [Mock(success=True, inserted_id=1), Mock(success=True, inserted_id=2)]
        mock_provider.execute_insert.side_effect = insert_results
        
        results = await concrete_repository.bulk_create(entities)
        
        assert len(results) == 2
        assert results[0].id == 1
        assert results[1].id == 2
        assert mock_provider.execute_insert.call_count == 2

    @pytest.mark.asyncio
    async def test_paginate(self, concrete_repository, mock_provider):
        """Test default paginate implementation"""
        query_result = Mock(success=True)
        query_result.rows = [{"id": 1, "name": "first", "value": 1}]
        mock_provider.execute_query.side_effect = [
            query_result,  # for find_many
            Mock(success=True, rows=[{"count": 5}])  # for count
        ]
        
        result = await concrete_repository.paginate(page=2, per_page=2, status="active")
        
        assert result["total"] == 5
        assert result["page"] == 2
        assert result["per_page"] == 2
        assert result["total_pages"] == 3
        assert len(result["data"]) == 1
        assert result["data"][0].id == 1
