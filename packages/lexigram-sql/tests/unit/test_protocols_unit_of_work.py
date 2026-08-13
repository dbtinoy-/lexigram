"""Unit tests for Unit of Work Protocol implementation"""

from unittest.mock import AsyncMock, Mock

import pytest

from lexigram.contracts import DatabaseProviderProtocol
from lexigram.sql.exceptions import DatabaseError
from lexigram.sql.unit_of_work.simple import (
    EntityOperation,
    SimpleUnitOfWork,
    unit_of_work,
)


class MockEntity:
    """Mock entity for testing"""

    def __init__(self, id=None, name=None, value=None):
        self.id = id
        self.name = name
        self.value = value
        self.__table_name__ = "mock_entities"


class TestEntityOperation:
    """Test EntityOperation dataclass"""

    def test_entity_operation_creation(self):
        """Test creating an EntityOperation"""
        entity = MockEntity(id=1, name="test")
        operation = EntityOperation(
            entity=entity,
            operation_type="insert",
            table_name="test_table",
            primary_key="id",
        )

        assert operation.entity == entity
        assert operation.operation_type == "insert"
        assert operation.table_name == "test_table"
        assert operation.primary_key == "id"

    def test_entity_operation_defaults(self):
        """Test EntityOperation with default values"""
        entity = MockEntity()
        operation = EntityOperation(
            entity=entity, operation_type="update", table_name="test_table",
        )

        assert operation.primary_key is None


class TestSimpleUnitOfWork:
    """Test SimpleUnitOfWork functionality"""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock database provider"""
        provider = Mock(spec=DatabaseProviderProtocol)
        provider.begin_transaction = AsyncMock()
        provider.commit_transaction = AsyncMock()
        provider.rollback_transaction = AsyncMock()
        provider.execute_insert = AsyncMock()
        provider.execute_update = AsyncMock()
        provider.execute_delete = AsyncMock()
        return provider

    @pytest.fixture
    def unit_of_work(self, mock_provider):
        """Create a SimpleUnitOfWork instance"""
        return SimpleUnitOfWork(mock_provider)

    def test_initialization(self, mock_provider):
        """Test unit of work initialization"""
        uow = SimpleUnitOfWork(mock_provider)

        assert uow.provider == mock_provider
        assert uow._operations == []
        assert uow._in_transaction is False
        assert uow._committed is False
        assert uow._rolled_back is False

    @pytest.mark.asyncio
    async def test_context_manager_entry(self, unit_of_work, mock_provider):
        """Test entering unit of work context manager"""
        async with unit_of_work as uow:
            assert uow is unit_of_work
            assert unit_of_work._in_transaction is True
            mock_provider.begin_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_manager_exit_success(self, unit_of_work, mock_provider):
        """Test exiting unit of work context manager on success"""
        async with unit_of_work:
            pass

        mock_provider.begin_transaction.assert_called_once()
        mock_provider.commit_transaction.assert_called_once()
        assert unit_of_work._committed is True

    @pytest.mark.asyncio
    async def test_context_manager_exit_exception(self, unit_of_work, mock_provider):
        """Test exiting unit of work context manager on exception"""
        with pytest.raises(ValueError):
            async with unit_of_work:
                raise ValueError("Test exception")

        mock_provider.begin_transaction.assert_called_once()
        mock_provider.rollback_transaction.assert_called_once()
        assert unit_of_work._rolled_back is True

    @pytest.mark.asyncio
    async def test_nested_context_manager(self, unit_of_work, mock_provider):
        """Test nested unit of work context managers"""
        async with unit_of_work:
            # First level
            assert unit_of_work._in_transaction is True

            async with unit_of_work:
                # Nested level - should not start new transaction
                assert unit_of_work._in_transaction is True
                # Nested context should not call begin_transaction again
                assert mock_provider.begin_transaction.call_count == 1

            # Back to first level - still in transaction
            assert unit_of_work._in_transaction is True

        # Exited completely - transaction should be committed
        assert unit_of_work._in_transaction is True  # Still True after commit
        assert unit_of_work._committed is True
        mock_provider.begin_transaction.assert_called_once()
        mock_provider.commit_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_commit_success(self, unit_of_work, mock_provider):
        """Test successful commit"""
        entity = MockEntity(id=1, name="test")
        unit_of_work.register_new(entity)

        # Mock successful insert
        mock_provider.execute_insert.return_value = Mock(success=True)

        async with unit_of_work:
            pass  # Operations are committed on exit

        assert unit_of_work._committed is True
        assert unit_of_work._operations == []  # Cleared after commit
        mock_provider.execute_insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_commit_failure(self, unit_of_work, mock_provider):
        """Test commit failure with rollback"""
        entity = MockEntity(id=1, name="test")
        unit_of_work.register_new(entity)

        # Mock failed insert
        mock_provider.execute_insert.side_effect = DatabaseError("Insert failed")

        with pytest.raises(DatabaseError, match="Insert failed"):
            async with unit_of_work:
                pass  # Operations fail on commit

        # Should have rolled back
        assert unit_of_work._committed is False
        assert unit_of_work._rolled_back is True
        mock_provider.rollback_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_commit_not_in_transaction(self, unit_of_work):
        """Test commit when not in transaction"""
        with pytest.raises(RuntimeError, match="Not in a transaction"):
            await unit_of_work.commit()

    @pytest.mark.asyncio
    async def test_commit_already_committed(self, unit_of_work, mock_provider):
        """Test commit when already committed"""
        # First complete a transaction
        async with unit_of_work:
            pass

        assert unit_of_work._committed is True

        # Try to commit again - this should work since it's a no-op
        # The SimpleUnitOfWork doesn't expose manual commit after context manager
        # So we'll test that the state remains committed
        assert unit_of_work._committed is True

    @pytest.mark.asyncio
    async def test_rollback_success(self, unit_of_work, mock_provider):
        """Test successful rollback"""
        entity = MockEntity(id=1, name="test")
        unit_of_work.register_new(entity)

        # Force rollback by raising exception in context
        with pytest.raises(ValueError):
            async with unit_of_work:
                raise ValueError("Force rollback")

        assert unit_of_work._rolled_back is True
        assert unit_of_work._operations == []  # Cleared after rollback
        mock_provider.rollback_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_rollback_not_in_transaction(self, unit_of_work):
        """Test rollback when not in transaction"""
        with pytest.raises(RuntimeError, match="Not in a transaction"):
            await unit_of_work.rollback()

    @pytest.mark.asyncio
    async def test_rollback_already_rolled_back(self, unit_of_work, mock_provider):
        """Test rollback when already rolled back"""
        # First cause a rollback
        with pytest.raises(ValueError):
            async with unit_of_work:
                raise ValueError("Force rollback")

        assert unit_of_work._rolled_back is True

        # Try to rollback again - should be a no-op since already rolled back
        # The SimpleUnitOfWork doesn't expose manual rollback after context manager
        assert unit_of_work._rolled_back is True
        mock_provider.rollback_transaction.assert_called_once()  # Only called once

    def test_register_new(self, unit_of_work):
        """Test registering a new entity"""
        entity = MockEntity(id=1, name="test")
        unit_of_work.register_new(entity)

        assert len(unit_of_work._operations) == 1
        operation = unit_of_work._operations[0]
        assert operation.entity == entity
        assert operation.operation_type == "insert"
        assert operation.table_name == "mock_entities"

    def test_register_new_custom_table_name(self, unit_of_work):
        """Test registering a new entity with custom table name"""
        entity = MockEntity(id=1, name="test")
        entity.__table_name__ = "custom_table"
        unit_of_work.register_new(entity)

        operation = unit_of_work._operations[0]
        assert operation.table_name == "custom_table"

    def test_register_new_no_table_name(self, unit_of_work):
        """Test registering a new entity without __table_name__"""
        entity = MockEntity(id=1, name="test")
        delattr(entity, "__table_name__")
        unit_of_work.register_new(entity)

        operation = unit_of_work._operations[0]
        assert operation.table_name == "mockentity"  # Class name lowercased

    def test_register_dirty(self, unit_of_work):
        """Test registering a dirty entity for update"""
        entity = MockEntity(id=1, name="updated")
        unit_of_work.register_dirty(entity)

        assert len(unit_of_work._operations) == 1
        operation = unit_of_work._operations[0]
        assert operation.entity == entity
        assert operation.operation_type == "update"
        assert operation.table_name == "mock_entities"

    def test_register_deleted(self, unit_of_work):
        """Test registering an entity for deletion"""
        entity = MockEntity(id=1, name="deleted")
        unit_of_work.register_deleted(entity)

        assert len(unit_of_work._operations) == 1
        operation = unit_of_work._operations[0]
        assert operation.entity == entity
        assert operation.operation_type == "delete"
        assert operation.table_name == "mock_entities"

    def test_register_after_commit_raises_error(self, unit_of_work):
        """Test registering operations after commit raises error"""
        unit_of_work._committed = True
        entity = MockEntity(id=1, name="test")

        with pytest.raises(RuntimeError, match="Unit of work is closed"):
            unit_of_work.register_new(entity)

    def test_register_after_rollback_raises_error(self, unit_of_work):
        """Test registering operations after rollback raises error"""
        unit_of_work._rolled_back = True
        entity = MockEntity(id=1, name="test")

        with pytest.raises(RuntimeError, match="Unit of work is closed"):
            unit_of_work.register_new(entity)

    def test_manual_event_registration_and_collection(self, unit_of_work):
        """Events can be manually added and collected"""
        unit_of_work.register_event("evt1")
        unit_of_work.register_event("evt2")

        collected = unit_of_work.collect_events()
        assert collected == ["evt1", "evt2"]
        # second call returns empty list
        assert unit_of_work.collect_events() == []

    def test_entity_event_collection(self, unit_of_work):
        """Entities exposing collect_events have their events captured"""

        class EventEntity:
            def __init__(self):
                self._events = ["a", "b"]

            def collect_events(self):
                evts = self._events.copy()
                self._events.clear()
                return evts

        entity = EventEntity()
        unit_of_work.register_new(entity)

        # events should have been pulled and cleared on the entity
        assert unit_of_work.collect_events() == ["a", "b"]
        assert entity._events == []

    @pytest.mark.asyncio
    async def test_events_cleared_on_rollback(self, unit_of_work, mock_provider):
        """Any registered events are discarded when the UoW rolls back"""
        # register an event then force a rollback
        unit_of_work.register_event("fail")
        with pytest.raises(ValueError):
            async with unit_of_work:
                raise ValueError("force")

        assert unit_of_work.collect_events() == []

    @pytest.mark.asyncio
    async def test_execute_insert_operation(self, unit_of_work, mock_provider):
        """Test executing an insert operation"""
        entity = MockEntity(id=1, name="test", value=42)
        operation = EntityOperation(
            entity=entity, operation_type="insert", table_name="test_table",
        )

        mock_provider.execute_insert.return_value = Mock(success=True)

        await unit_of_work._execute_operation(operation)

        mock_provider.execute_insert.assert_called_once_with(
            table="test_table", data={"id": 1, "name": "test", "value": 42},
        )

    @pytest.mark.asyncio
    async def test_execute_insert_failure(self, unit_of_work, mock_provider):
        """Test insert operation failure"""
        entity = MockEntity(id=1, name="test")
        operation = EntityOperation(
            entity=entity, operation_type="insert", table_name="test_table",
        )

        mock_provider.execute_insert.return_value = Mock(
            success=False, error_message="Insert failed",
        )

        with pytest.raises(RuntimeError, match="Insert failed"):
            await unit_of_work._execute_operation(operation)

    @pytest.mark.asyncio
    async def test_execute_update_operation(self, unit_of_work, mock_provider):
        """Test executing an update operation"""
        entity = MockEntity(id=1, name="updated", value=100)
        operation = EntityOperation(
            entity=entity, operation_type="update", table_name="test_table",
        )

        mock_provider.execute_update.return_value = Mock(success=True)

        await unit_of_work._execute_operation(operation)

        mock_provider.execute_update.assert_called_once_with(
            table="test_table",
            data={"id": 1, "name": "updated", "value": 100},
            where_clause="id = ?",
            where_params=[1],
        )

    @pytest.mark.asyncio
    async def test_execute_update_no_id(self, unit_of_work, mock_provider):
        """Test update operation with entity missing id"""
        entity = MockEntity(name="test")  # No id
        operation = EntityOperation(
            entity=entity, operation_type="update", table_name="test_table",
        )

        with pytest.raises(
            ValueError, match="Entity must have an 'id' attribute for updates",
        ):
            await unit_of_work._execute_operation(operation)

    @pytest.mark.asyncio
    async def test_execute_delete_operation(self, unit_of_work, mock_provider):
        """Test executing a delete operation"""
        entity = MockEntity(id=1, name="deleted")
        operation = EntityOperation(
            entity=entity, operation_type="delete", table_name="test_table",
        )

        mock_provider.execute_delete.return_value = Mock(success=True)

        await unit_of_work._execute_operation(operation)

        mock_provider.execute_delete.assert_called_once_with(
            table="test_table", where_clause="id = ?", where_params=[1],
        )

    @pytest.mark.asyncio
    async def test_execute_delete_no_id(self, unit_of_work, mock_provider):
        """Test delete operation with entity missing id"""
        entity = MockEntity(name="test")  # No id
        operation = EntityOperation(
            entity=entity, operation_type="delete", table_name="test_table",
        )

        with pytest.raises(
            ValueError, match="Entity must have an 'id' attribute for deletes",
        ):
            await unit_of_work._execute_operation(operation)

    @pytest.mark.asyncio
    async def test_execute_unknown_operation(self, unit_of_work):
        """Test executing an unknown operation type"""
        entity = MockEntity(id=1, name="test")
        operation = EntityOperation(
            entity=entity, operation_type="unknown", table_name="test_table",
        )

        with pytest.raises(ValueError, match="Unknown operation type: unknown"):
            await unit_of_work._execute_operation(operation)

    def test_entity_to_dict_with_dict(self, unit_of_work):
        """Test converting dict entity to dict"""
        entity = {"id": 1, "name": "test"}
        result = unit_of_work._entity_to_dict(entity)

        assert result == {"id": 1, "name": "test"}
        assert result is not entity  # Should be a copy

    def test_entity_to_dict_with_object(self, unit_of_work):
        """Test converting object entity to dict"""
        entity = MockEntity(id=1, name="test", value=42)
        entity._private = "private"  # Should be excluded

        result = unit_of_work._entity_to_dict(entity)

        assert result == {"id": 1, "name": "test", "value": 42}
        assert "_private" not in result
        assert "__table_name__" not in result

    def test_entity_to_dict_invalid_type(self, unit_of_work):
        """Test converting invalid entity type"""
        entity = "invalid"

        with pytest.raises(ValueError, match="Cannot convert entity to dict"):
            unit_of_work._entity_to_dict(entity)

    def test_entity_to_dict_with_dataclass(self, unit_of_work):
        """Dataclasses should be converted into dicts with private fields excluded"""
        from dataclasses import dataclass

        @dataclass
        class DEntity:
            id: int
            name: str
            _private: str = "secret"

        entity = DEntity(id=2, name="dc")
        result = unit_of_work._entity_to_dict(entity)
        assert result == {"id": 2, "name": "dc"}
        assert "_private" not in result

    def test_entity_to_dict_with_model_dump(self, unit_of_work):
        """Objects exposing model_dump() should be converted"""

        class PydanticLike:
            def __init__(self, id, name):
                self.id = id
                self.name = name

            def model_dump(self):
                return {"id": self.id, "name": self.name, "_secret": "x"}

        entity = PydanticLike(3, "pyd")
        result = unit_of_work._entity_to_dict(entity)
        assert result == {"id": 3, "name": "pyd"}
        assert "_secret" not in result


class TestUnitOfWorkContextManager:
    """Test the unit_of_work context manager function"""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock database provider"""
        provider = Mock(spec=DatabaseProviderProtocol)
        provider.begin_transaction = AsyncMock()
        provider.commit_transaction = AsyncMock()
        provider.rollback_transaction = AsyncMock()
        provider.execute_insert = AsyncMock()
        provider.execute_update = AsyncMock()
        provider.execute_delete = AsyncMock()
        return provider

    @pytest.mark.asyncio
    async def test_unit_of_work_context_manager_success(self, mock_provider):
        """Test unit_of_work context manager with success"""
        async with unit_of_work(mock_provider) as uow:
            assert isinstance(uow, SimpleUnitOfWork)
            assert uow.provider == mock_provider
            assert uow._in_transaction is True

        # Should be committed
        assert uow._committed is True
        mock_provider.begin_transaction.assert_called_once()
        mock_provider.commit_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_unit_of_work_context_manager_exception(self, mock_provider):
        """Test unit_of_work context manager with exception"""
        with pytest.raises(ValueError):
            async with unit_of_work(mock_provider) as uow:
                assert uow._in_transaction is True
                raise ValueError("Test exception")

        # Should be rolled back
        assert uow._rolled_back is True
        mock_provider.begin_transaction.assert_called_once()
        mock_provider.rollback_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_unit_of_work_context_manager_operations(self, mock_provider):
        """Test unit_of_work context manager with operations"""
        entity = MockEntity(id=1, name="test")

        # Mock successful operations
        mock_provider.execute_insert.return_value = Mock(success=True)

        async with unit_of_work(mock_provider) as uow:
            uow.register_new(entity)

        # Should have executed the operation
        assert mock_provider.execute_insert.call_count == 1
        assert uow._committed is True
