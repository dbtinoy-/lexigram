"""Edge case tests for feedback storage."""

import pytest
from unittest.mock import MagicMock
from lexigram.ai.feedback.storage.database import DatabaseFeedbackStore
from lexigram.ai.feedback.types import FeedbackType, FeedbackItem
from lexigram.serialization import dumps_str
import datetime

class TestDatabaseFeedbackStoreEdgeCases:
    def test_row_to_item_handles_invalid_json(self):
        """Test that _row_to_item gracefully handles invalid JSON in rows."""
        db = MagicMock()
        store = DatabaseFeedbackStore(provider=db)
        
        # Row with invalid JSON in value, context, and metadata
        row = {
            "id": "item-1",
            "type": "rating",
            "value": "invalid-json",
            "context": "not-a-dict",
            "metadata": "also-not-a-dict",
            "created_at": datetime.datetime.now().isoformat()
        }
        
        item = store._row_to_item(row)
        
        assert item.id == "item-1"
        assert item.value == "invalid-json"
        assert item.context == {}
        assert item.metadata == {}

    @pytest.mark.asyncio
    async def test_find_by_session_handles_invalid_rows(self):
        """Test find_by_session with a row that has invalid JSON."""
        item_id = "item-err"
        row = {
            "id": item_id,
            "type": "text",
            "value": "some-text", # Valid string but maybe not JSON-serialized if it was direct write
            "context": "{invalid}",
            "metadata": "{invalid}",
            "created_at": datetime.datetime.now().isoformat()
        }
        
        result_mock = MagicMock()
        result_mock.rows = [row]
        
        db = MagicMock()
        db.execute_query = MagicMock(return_value=result_mock)
        # Wrap in AsyncMock for await
        from unittest.mock import AsyncMock
        db.execute_query = AsyncMock(return_value=result_mock)
        db.execute = AsyncMock()
        
        store = DatabaseFeedbackStore(provider=db)
        store._initialised = True
        
        results = await store.find_by_session("session-1")
        assert len(results) == 1
        assert results[0].id == item_id
        assert results[0].context == {}

    @pytest.mark.asyncio
    async def test_aggregate_handles_empty_db(self):
        """Test aggregate when there are no rows."""
        from unittest.mock import AsyncMock
        db = MagicMock()
        db.execute = AsyncMock()
        
        # Return empty rows for all 3 queries
        res_empty = MagicMock(rows=[])
        res_zero = MagicMock(rows=[{"cnt": 0}])
        res_null = MagicMock(rows=[{"avg_rating": None}])
        
        db.execute_query = AsyncMock(side_effect=[res_zero, res_null, res_empty])
        
        store = DatabaseFeedbackStore(provider=db)
        store._initialised = True
        
        summary = await store.aggregate()
        assert summary.total_count == 0
        assert summary.average_rating is None
        assert summary.count_by_type == {}
