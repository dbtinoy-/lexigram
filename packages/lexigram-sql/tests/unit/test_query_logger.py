"""Comprehensive tests for query logger implementations"""

from datetime import datetime, timedelta
import tempfile
from unittest.mock import patch

import pytest

from lexigram import serialization as json
from lexigram.sql.logging import (
    ConsoleQueryLogger,
    FileQueryLogger,
    MemoryQueryLogger,
    QueryLogEntry,
    QueryLoggerBase,
)

"""Comprehensive tests for query logger implementations"""


class TestQueryLogEntry:
    """Test QueryLogEntry dataclass"""

    def test_query_log_entry_creation(self):
        """Test creating a QueryLogEntry"""
        timestamp = datetime.now()
        entry = QueryLogEntry(
            sql="SELECT * FROM users",
            params=["param1", "param2"],
            execution_time=0.5,
            success=True,
            error_message=None,
            connection_id="conn_123",
            transaction_id="txn_456",
            user_id="user_789",
            request_id="req_123",
            trace_id="trace_456",
            timestamp=timestamp,
        )

        assert entry.sql == "SELECT * FROM users"
        assert entry.params == ["param1", "param2"]
        assert entry.execution_time == 0.5
        assert entry.success is True
        assert entry.error_message is None
        assert entry.connection_id == "conn_123"
        assert entry.transaction_id == "txn_456"
        assert entry.user_id == "user_789"
        assert entry.request_id == "req_123"
        assert entry.trace_id == "trace_456"
        assert entry.timestamp == timestamp

    def test_query_log_entry_defaults(self):
        """Test QueryLogEntry with default values"""
        timestamp = datetime.now()
        entry = QueryLogEntry(
            sql="SELECT 1",
            execution_time=0.1,
            success=True,
            timestamp=timestamp,
            params=None,
            error_message=None,
            connection_id=None,
            transaction_id=None,
            user_id=None,
            request_id=None,
            trace_id=None,
        )

        assert entry.params is None
        assert entry.error_message is None
        assert entry.connection_id is None
        assert entry.transaction_id is None
        assert entry.user_id is None
        assert entry.request_id is None
        assert entry.trace_id is None


class TestBaseQueryLogger:
    """Test QueryLoggerBase class"""

    def test_base_query_logger_init(self):
        """Test QueryLoggerBase initialization"""
        logger = QueryLoggerBase(slow_query_threshold=2.0, max_entries=500)

        assert logger.slow_query_threshold == 2.0
        assert logger.max_entries == 500
        assert len(logger._entries) == 0
        assert logger.logger is not None
        assert hasattr(logger.logger, "info")
        assert hasattr(logger.logger, "warning")
        assert hasattr(logger.logger, "error")

    def test_base_query_logger_defaults(self):
        """Test QueryLoggerBase default values"""
        logger = QueryLoggerBase()

        assert logger.slow_query_threshold == 1.0
        assert logger.max_entries == 1000

    @pytest.mark.asyncio
    async def test_log_query_success(self):
        """Test logging a successful query"""
        logger = QueryLoggerBase()

        entry = QueryLogEntry(
            sql="SELECT * FROM users",
            execution_time=0.5,
            success=True,
            timestamp=datetime.now(),
            params=None,
            error_message=None,
            connection_id=None,
            transaction_id=None,
            user_id=None,
        )

        await logger.log_query(entry)

        assert len(logger._entries) == 1
        assert logger._entries[0] == entry

    @pytest.mark.asyncio
    async def test_log_query_slow(self):
        """Test logging a slow query"""
        logger = QueryLoggerBase(slow_query_threshold=0.1)

        entry = QueryLogEntry(
            sql="SELECT * FROM users",
            execution_time=0.5,
            success=True,
            timestamp=datetime.now(),
            params=None,
            error_message=None,
            connection_id=None,
            transaction_id=None,
            user_id=None,
        )

        assert logger.logger is not None
        await logger.log_query(entry)

    @pytest.mark.asyncio
    async def test_log_query_error(self):
        """Test logging a failed query"""
        logger = QueryLoggerBase()

        entry = QueryLogEntry(
            sql="SELECT * FROM invalid_table",
            execution_time=0.1,
            success=False,
            error_message="Table does not exist",
            timestamp=datetime.now(),
            params=None,
            connection_id=None,
            transaction_id=None,
            user_id=None,
        )

        assert logger.logger is not None
        await logger.log_query(entry)

    @pytest.mark.asyncio
    async def test_get_recent_queries(self):
        """Test getting recent queries"""
        logger = QueryLoggerBase(max_entries=5)

        # Add some entries
        entries = []
        for i in range(7):  # More than max_entries
            entry = QueryLogEntry(
                sql=f"SELECT {i}",
                execution_time=0.1,
                success=True,
                timestamp=datetime.now(),
                params=None,
                error_message=None,
                connection_id=None,
                transaction_id=None,
                user_id=None,
            )
            entries.append(entry)
            await logger.log_query(entry)

        # Should only keep max_entries
        assert len(logger._entries) == 5

        recent = await logger.get_recent_queries(3)
        assert len(recent) == 3
        assert recent[0].sql == "SELECT 4"
        assert recent[1].sql == "SELECT 5"
        assert recent[2].sql == "SELECT 6"

    @pytest.mark.asyncio
    async def test_get_slow_queries(self):
        """Test getting slow queries"""
        logger = QueryLoggerBase()

        # Add queries with different execution times
        entries = [
            QueryLogEntry(
                sql="FAST",
                execution_time=0.1,
                success=True,
                timestamp=datetime.now(),
                params=None,
                error_message=None,
                connection_id=None,
                transaction_id=None,
                user_id=None,
            ),
            QueryLogEntry(
                sql="SLOW1",
                execution_time=2.0,
                success=True,
                timestamp=datetime.now(),
                params=None,
                error_message=None,
                connection_id=None,
                transaction_id=None,
                user_id=None,
            ),
            QueryLogEntry(
                sql="SLOW2",
                execution_time=3.0,
                success=True,
                timestamp=datetime.now(),
                params=None,
                error_message=None,
                connection_id=None,
                transaction_id=None,
                user_id=None,
            ),
            QueryLogEntry(
                sql="MEDIUM",
                execution_time=1.5,
                success=True,
                timestamp=datetime.now(),
                params=None,
                error_message=None,
                connection_id=None,
                transaction_id=None,
                user_id=None,
            ),
        ]

        for entry in entries:
            await logger.log_query(entry)

        slow_queries = await logger.get_slow_queries(1.0, limit=2)

        assert len(slow_queries) == 2
        # Should be sorted by execution time descending
        assert slow_queries[0].sql == "SLOW2"
        assert slow_queries[1].sql == "SLOW1"

    @pytest.mark.asyncio
    async def test_get_query_stats_empty(self):
        """Test getting query stats when no queries logged"""
        logger = QueryLoggerBase()

        stats = await logger.get_query_stats()

        expected_stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "average_execution_time": 0.0,
            "slow_queries_count": 0,
            "time_range_seconds": 3600,
        }

        for key, value in expected_stats.items():
            assert stats[key] == value

    @pytest.mark.asyncio
    async def test_get_query_stats_with_data(self):
        """Test getting query stats with logged queries"""
        logger = QueryLoggerBase(slow_query_threshold=1.0)

        # Add some test entries
        entries = [
            QueryLogEntry(
                sql="Q1",
                execution_time=0.5,
                success=True,
                timestamp=datetime.now(),
                params=None,
                error_message=None,
                connection_id=None,
                transaction_id=None,
                user_id=None,
            ),
            QueryLogEntry(
                sql="Q2",
                execution_time=2.0,
                success=True,
                timestamp=datetime.now(),
                params=None,
                error_message=None,
                connection_id=None,
                transaction_id=None,
                user_id=None,
            ),
            QueryLogEntry(
                sql="Q3",
                execution_time=0.8,
                success=False,
                error_message="Error",
                timestamp=datetime.now(),
                params=None,
                connection_id=None,
                transaction_id=None,
                user_id=None,
            ),
        ]

        for entry in entries:
            await logger.log_query(entry)

        stats = await logger.get_query_stats(time_range_seconds=3600)

        assert stats["total_queries"] == 3
        assert stats["successful_queries"] == 2
        assert stats["failed_queries"] == 1
        assert stats["average_execution_time"] == (0.5 + 2.0 + 0.8) / 3
        assert stats["slow_queries_count"] == 1  # Only Q2 is slow
        assert stats["success_rate"] == 2 / 3


class TestConsoleQueryLogger:
    """Test ConsoleQueryLogger class"""

    def test_console_query_logger_init(self):
        """Test ConsoleQueryLogger initialization"""
        logger = ConsoleQueryLogger(
            slow_query_threshold=2.0,
            max_entries=500,
            log_level="DEBUG",
        )

        assert logger.slow_query_threshold == 2.0
        assert logger.max_entries == 500
        assert hasattr(logger, "console_logger")

    @pytest.mark.asyncio
    async def test_log_query_success_console(self):
        """Test logging successful query to console"""
        logger = ConsoleQueryLogger()

        entry = QueryLogEntry(
            sql="SELECT * FROM users",
            params=["param1"],
            execution_time=0.5,
            success=True,
            timestamp=datetime.now(),
            error_message=None,
            connection_id=None,
            transaction_id=None,
            user_id=None,
        )

        assert logger.console_logger is not None
        await logger.log_query(entry)

    @pytest.mark.asyncio
    async def test_log_query_error_console(self):
        """Test logging failed query to console"""
        logger = ConsoleQueryLogger()

        entry = QueryLogEntry(
            sql="SELECT * FROM invalid",
            execution_time=0.1,
            success=False,
            error_message="Table not found",
            timestamp=datetime.now(),
            params=None,
            connection_id=None,
            transaction_id=None,
            user_id=None,
        )

        assert logger.console_logger is not None
        await logger.log_query(entry)


class TestFileQueryLogger:
    """Test FileQueryLogger class"""

    def test_file_query_logger_init(self):
        """Test FileQueryLogger initialization"""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            logger = FileQueryLogger(
                log_file=temp_file.name,
                slow_query_threshold=2.0,
                max_entries=500,
            )

            assert logger.log_file == temp_file.name
            assert logger.slow_query_threshold == 2.0
            assert logger.max_entries == 500
            assert hasattr(logger, "file_logger")

    @pytest.mark.asyncio
    async def test_log_query_file(self):
        """Test logging query to file"""
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
            logger = FileQueryLogger(log_file=temp_file.name)

            entry = QueryLogEntry(
                sql="SELECT * FROM users",
                params=["param1"],
                execution_time=0.5,
                success=True,
                connection_id="conn_123",
                timestamp=datetime.now(),
                error_message=None,
                transaction_id=None,
                user_id=None,
            )

            with patch.object(logger.file_logger, "info") as mock_info:
                await logger.log_query(entry)

                mock_info.assert_called_once()
                logged_data = json.loads(mock_info.call_args[0][0])

                assert logged_data["sql"] == "SELECT * FROM users"
                assert logged_data["params"] == ["param1"]
                assert logged_data["execution_time"] == 0.5
                assert logged_data["success"] is True
                assert logged_data["connection_id"] == "conn_123"


class TestMemoryQueryLogger:
    """Test MemoryQueryLogger class"""

    def test_memory_query_logger_init(self):
        """Test MemoryQueryLogger initialization"""
        logger = MemoryQueryLogger(slow_query_threshold=2.0, max_entries=500)

        assert logger.slow_query_threshold == 2.0
        assert logger.max_entries == 500

    @pytest.mark.asyncio
    async def test_clear_logs(self):
        """Test clearing logs"""
        logger = MemoryQueryLogger()

        # Add some entries
        entries = [
            QueryLogEntry(
                sql="Q1",
                execution_time=0.1,
                success=True,
                timestamp=datetime.now(),
                params=None,
                error_message=None,
                connection_id=None,
                transaction_id=None,
                user_id=None,
            ),
            QueryLogEntry(
                sql="Q2",
                execution_time=0.2,
                success=True,
                timestamp=datetime.now(),
                params=None,
                error_message=None,
                connection_id=None,
                transaction_id=None,
                user_id=None,
            ),
        ]

        for entry in entries:
            await logger.log_query(entry)

        assert len(logger._entries) == 2

        await logger.clear_logs()
        assert len(logger._entries) == 0

    @pytest.mark.asyncio
    async def test_get_entries_by_sql(self):
        """Test getting entries by SQL pattern"""
        logger = MemoryQueryLogger()

        entries = [
            QueryLogEntry(
                sql="SELECT * FROM users",
                execution_time=0.1,
                success=True,
                timestamp=datetime.now(),
                params=None,
                error_message=None,
                connection_id=None,
                transaction_id=None,
                user_id=None,
            ),
            QueryLogEntry(
                sql="INSERT INTO users",
                execution_time=0.2,
                success=True,
                timestamp=datetime.now(),
                params=None,
                error_message=None,
                connection_id=None,
                transaction_id=None,
                user_id=None,
            ),
            QueryLogEntry(
                sql="SELECT * FROM posts",
                execution_time=0.3,
                success=True,
                timestamp=datetime.now(),
                params=None,
                error_message=None,
                connection_id=None,
                transaction_id=None,
                user_id=None,
            ),
        ]

        for entry in entries:
            await logger.log_query(entry)

        # Search for SELECT queries
        select_entries = await logger.get_entries_by_sql("SELECT")
        assert len(select_entries) == 2
        assert all("SELECT" in entry.sql for entry in select_entries)

        # Search for users table
        user_entries = await logger.get_entries_by_sql("users")
        assert len(user_entries) == 2

    @pytest.mark.asyncio
    async def test_get_failed_queries(self):
        """Test getting failed queries"""
        logger = MemoryQueryLogger()

        entries = [
            QueryLogEntry(
                sql="SELECT 1",
                execution_time=0.1,
                success=True,
                timestamp=datetime.now(),
                params=None,
                error_message=None,
                connection_id=None,
                transaction_id=None,
                user_id=None,
            ),
            QueryLogEntry(
                sql="INVALID QUERY",
                execution_time=0.2,
                success=False,
                error_message="Syntax error",
                timestamp=datetime.now(),
                params=None,
                connection_id=None,
                transaction_id=None,
                user_id=None,
            ),
            QueryLogEntry(
                sql="SELECT 2",
                execution_time=0.3,
                success=True,
                timestamp=datetime.now(),
                params=None,
                error_message=None,
                connection_id=None,
                transaction_id=None,
                user_id=None,
            ),
            QueryLogEntry(
                sql="BROKEN QUERY",
                execution_time=0.1,
                success=False,
                error_message="Table not found",
                timestamp=datetime.now(),
                params=None,
                connection_id=None,
                transaction_id=None,
                user_id=None,
            ),
        ]

        for entry in entries:
            await logger.log_query(entry)

        failed_queries = await logger.get_failed_queries()
        assert len(failed_queries) == 2
        assert all(not entry.success for entry in failed_queries)
        failed_sql = [entry.sql for entry in failed_queries]
        assert "INVALID QUERY" in failed_sql
        assert "BROKEN QUERY" in failed_sql


class TestQueryLoggerIntegration:
    """Integration tests for query loggers"""

    @pytest.mark.asyncio
    async def test_multiple_loggers_same_entry(self):
        """Test logging the same entry to multiple loggers"""
        base_logger = QueryLoggerBase()
        memory_logger = MemoryQueryLogger()

        entry = QueryLogEntry(
            sql="SELECT * FROM test_table",
            execution_time=1.5,
            success=True,
            timestamp=datetime.now(),
            params=None,
            error_message=None,
            connection_id=None,
            transaction_id=None,
            user_id=None,
        )

        # Log to both
        await base_logger.log_query(entry)
        await memory_logger.log_query(entry)

        # Both should have the entry
        assert len(base_logger._entries) == 1
        assert len(memory_logger._entries) == 1

        assert base_logger._entries[0] == entry
        assert memory_logger._entries[0] == entry

    @pytest.mark.asyncio
    async def test_query_logger_with_real_timestamps(self):
        """Test query logger with real timestamp handling"""
        logger = MemoryQueryLogger()

        # Create entries with timestamps in the past
        past_time = datetime.now() - timedelta(seconds=2)

        entry1 = QueryLogEntry(
            sql="SELECT 1",
            execution_time=0.1,
            success=True,
            timestamp=past_time,
            params=None,
            error_message=None,
            connection_id=None,
            transaction_id=None,
            user_id=None,
        )

        entry2 = QueryLogEntry(
            sql="SELECT 2",
            execution_time=0.2,
            success=True,
            timestamp=past_time + timedelta(seconds=1),
            params=None,
            error_message=None,
            connection_id=None,
            transaction_id=None,
            user_id=None,
        )

        await logger.log_query(entry1)
        await logger.log_query(entry2)

        # Test time-based filtering in stats - should include both entries
        recent_stats = await logger.get_query_stats(time_range_seconds=10)
        assert recent_stats["total_queries"] == 2

        # Test with very short time range - should exclude old entries
        old_stats = await logger.get_query_stats(time_range_seconds=0.5)
        assert old_stats["total_queries"] == 0

    @pytest.mark.asyncio
    async def test_query_logger_max_entries_behavior(self):
        """Test behavior when max entries is exceeded"""
        logger = MemoryQueryLogger(max_entries=3)

        # Add more entries than max_entries
        for i in range(5):
            entry = QueryLogEntry(
                sql=f"SELECT {i}",
                execution_time=0.1,
                success=True,
                timestamp=datetime.now(),
                params=None,
                error_message=None,
                connection_id=None,
                transaction_id=None,
                user_id=None,
            )
            await logger.log_query(entry)

        # Should only keep the last 3 entries
        assert len(logger._entries) == 3

        recent = await logger.get_recent_queries()
        assert len(recent) == 3
        assert recent[0].sql == "SELECT 2"
        assert recent[1].sql == "SELECT 3"
        assert recent[2].sql == "SELECT 4"
