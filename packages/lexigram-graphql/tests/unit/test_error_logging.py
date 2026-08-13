from __future__ import annotations

from lexigram.graphql.core.error_logging import ErrorLogEntry, ErrorLogger, QueryLogger


class TestErrorLogEntry:
    def test_to_dict(self) -> None:
        entry = ErrorLogEntry(
            error_type="ValueError",
            message="bad thing",
            query="{ hello }",
            variables={"x": 1},
            path=["users", 0],
            extensions={"code": "ERR"},
            context={"request_id": "abc"},
        )
        d = entry.to_dict()
        assert d["error_type"] == "ValueError"
        assert d["message"] == "bad thing"
        assert d["query"] == "{ hello }"
        assert d["variables"] == {"x": 1}
        assert d["path"] == ["users", 0]
        assert d["extensions"] == {"code": "ERR"}
        assert d["context"] == {"request_id": "abc"}
        assert "timestamp" in d


class TestErrorLogger:
    def test_log_error(self) -> None:
        logger = ErrorLogger(log_queries=True, log_variables=True, log_stacktrace=False)
        entry = logger.log_error(
            error=ValueError("test error"),
            query="{ hello }",
            variables={"id": "1"},
            path=["users"],
            extensions={"code": "ERR"},
            context={"req": "abc"},
        )
        assert isinstance(entry, ErrorLogEntry)
        assert entry.error_type == "ValueError"
        assert "test error" in entry.message
        assert entry.query == "{ hello }"
        assert entry.variables == {"id": "1"}

    def test_log_error_masks_variables(self) -> None:
        logger = ErrorLogger(log_queries=True, log_variables=False, log_stacktrace=False)
        entry = logger.log_error(
            error=ValueError("oops"),
            query="{ hello }",
            variables={"password": "secret123", "name": "bob"},
        )
        assert entry.variables == {"password": "***REDACTED***", "name": "bob"}

    def test_log_error_no_query(self) -> None:
        logger = ErrorLogger(log_queries=True, log_variables=True, log_stacktrace=False)
        entry = logger.log_error(error=ValueError("test"))
        assert entry.query is None

    def test_log_error_no_stacktrace(self) -> None:
        logger = ErrorLogger(log_queries=False, log_variables=False, log_stacktrace=False)
        entry = logger.log_error(error=ValueError("test"))
        assert entry.stacktrace is None

    def test_log_error_with_stacktrace(self) -> None:
        logger = ErrorLogger(log_stacktrace=True)
        entry = logger.log_error(error=ValueError("test"))
        assert entry.stacktrace is not None

    def test_log_error_query_truncation(self) -> None:
        logger = ErrorLogger(log_queries=True, log_variables=False, log_stacktrace=False, max_query_length=10)
        entry = logger.log_error(error=ValueError("test"), query="x" * 100)
        assert entry.query is not None
        assert len(entry.query) == 10

    def test_log_error_does_not_mask_non_sensitive(self) -> None:
        logger = ErrorLogger(log_queries=True, log_variables=True, log_stacktrace=False)
        entry = logger.log_error(
            error=ValueError("test"),
            variables={"safe_key": "visible"},
        )
        assert entry.variables == {"safe_key": "visible"}


class TestQueryLogger:
    def test_log_query_disabled(self) -> None:
        logger = QueryLogger(enabled=False)
        # Should not raise
        logger.log_query(query="{ hello }", duration_ms=10.0)

    def test_extract_operation_type_mutation(self) -> None:
        logger = QueryLogger()
        assert logger._extract_operation_type("mutation { createUser }") == "mutation"

    def test_extract_operation_type_subscription(self) -> None:
        logger = QueryLogger()
        assert logger._extract_operation_type("subscription { onUpdate }") == "subscription"

    def test_extract_operation_type_query(self) -> None:
        logger = QueryLogger()
        assert logger._extract_operation_type("query { users }") == "query"

    def test_extract_operation_type_default_query(self) -> None:
        logger = QueryLogger()
        assert logger._extract_operation_type("  { users }") == "query"

    def test_log_query_with_errors(self) -> None:
        logger = QueryLogger(enabled=True)
        logger.log_query(query="{ hello }", operation_name="TestOp", duration_ms=5.0, errors_count=2)


class TestDefaultInstances:
    def test_default_error_logger(self) -> None:
        from lexigram.graphql.core.error_logging import default_error_logger

        assert isinstance(default_error_logger, ErrorLogger)

    def test_default_query_logger(self) -> None:
        from lexigram.graphql.core.error_logging import default_query_logger

        assert isinstance(default_query_logger, QueryLogger)
