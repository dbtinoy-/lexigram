"""Unit tests for vector exceptions."""

from __future__ import annotations

import pytest

from lexigram.vector.exceptions import (
    CollectionAlreadyExistsError,
    CollectionNotFoundError,
    DimensionMismatchError,
    FilterCompilationError,
    VectorConfigError,
    VectorConnectionError,
    VectorDeleteError,
    VectorError,
    VectorSearchError,
    VectorTimeoutError,
    VectorUpsertError,
)


class TestVectorError:
    def test_base_error_code(self) -> None:
        error = VectorError("test message")
        assert error._code == "LEX_ERR_VEC_005"

    def test_inherits_from_infrastructure_error(self) -> None:
        error = VectorError("test message")
        assert isinstance(error, Exception)


class TestVectorConnectionError:
    def test_error_code(self) -> None:
        error = VectorConnectionError("connection failed")
        assert error._code == "LEX_ERR_VEC_006"


class TestCollectionNotFoundError:
    def test_error_code(self) -> None:
        error = CollectionNotFoundError("test-collection")
        assert error._code == "LEX_ERR_VEC_007"

    def test_message_includes_collection_name(self) -> None:
        error = CollectionNotFoundError("my-collection")
        assert "my-collection" in str(error)

    def test_stores_collection_name(self) -> None:
        error = CollectionNotFoundError("test-collection")
        assert error.collection_name == "test-collection"


class TestCollectionAlreadyExistsError:
    def test_error_code(self) -> None:
        error = CollectionAlreadyExistsError("test-collection")
        assert error._code == "LEX_ERR_VEC_008"

    def test_message_includes_collection_name(self) -> None:
        error = CollectionAlreadyExistsError("existing-collection")
        assert "existing-collection" in str(error)

    def test_stores_collection_name(self) -> None:
        error = CollectionAlreadyExistsError("existing-collection")
        assert error.collection_name == "existing-collection"


class TestDimensionMismatchError:
    def test_error_code(self) -> None:
        error = DimensionMismatchError(expected=1536, actual=768)
        assert error._code == "LEX_ERR_VEC_009"

    def test_message_includes_dimensions(self) -> None:
        error = DimensionMismatchError(expected=1536, actual=768)
        msg = str(error)
        assert "1536" in msg
        assert "768" in msg

    def test_message_includes_record_id(self) -> None:
        error = DimensionMismatchError(expected=1536, actual=768, record_id="rec-123")
        msg = str(error)
        assert "rec-123" in msg

    def test_stores_dimensions_and_record(self) -> None:
        error = DimensionMismatchError(expected=1536, actual=768, record_id="rec-123")
        assert error.expected == 1536
        assert error.actual == 768
        assert error.record_id == "rec-123"


class TestVectorConfigError:
    def test_error_code(self) -> None:
        error = VectorConfigError("invalid config")
        assert error._code == "LEX_ERR_VEC_010"


class TestFilterCompilationError:
    def test_error_code(self) -> None:
        error = FilterCompilationError("invalid filter", "qdrant")
        assert error._code == "LEX_ERR_VEC_011"

    def test_message_includes_backend_and_error(self) -> None:
        error = FilterCompilationError("syntax error", "pinecone")
        msg = str(error)
        assert "pinecone" in msg
        assert "syntax error" in msg

    def test_stores_backend(self) -> None:
        error = FilterCompilationError("test error", "qdrant")
        assert error.backend == "qdrant"


class TestVectorUpsertError:
    def test_error_code(self) -> None:
        error = VectorUpsertError("upsert failed")
        assert error._code == "LEX_ERR_VEC_012"


class TestVectorSearchError:
    def test_error_code(self) -> None:
        error = VectorSearchError("search failed")
        assert error._code == "LEX_ERR_VEC_013"


class TestVectorDeleteError:
    def test_error_code(self) -> None:
        error = VectorDeleteError("delete failed")
        assert error._code == "LEX_ERR_VEC_014"


class TestVectorTimeoutError:
    def test_error_code(self) -> None:
        error = VectorTimeoutError("operation timed out")
        assert error._code == "LEX_ERR_VEC_015"


class TestExceptionInheritance:
    def test_all_exceptions_inherit_from_vector_error(self) -> None:
        exceptions = [
            VectorConnectionError("msg"),
            CollectionNotFoundError("col"),
            CollectionAlreadyExistsError("col"),
            DimensionMismatchError(1, 2),
            VectorConfigError("msg"),
            FilterCompilationError("msg", "be"),
            VectorUpsertError("msg"),
            VectorSearchError("msg"),
            VectorDeleteError("msg"),
            VectorTimeoutError("msg"),
        ]
        for exc in exceptions:
            assert isinstance(exc, VectorError)

    def test_all_exceptions_have_unique_codes(self) -> None:
        codes = set()
        exception_classes = [
            VectorError,
            VectorConnectionError,
            CollectionNotFoundError,
            CollectionAlreadyExistsError,
            DimensionMismatchError,
            VectorConfigError,
            FilterCompilationError,
            VectorUpsertError,
            VectorSearchError,
            VectorDeleteError,
            VectorTimeoutError,
        ]
        for cls in exception_classes:
            if cls.__name__ == "VectorError":
                instance = cls("msg")
            elif cls.__name__ == "CollectionNotFoundError":
                instance = cls("col")
            elif cls.__name__ == "CollectionAlreadyExistsError":
                instance = cls("col")
            elif cls.__name__ == "DimensionMismatchError":
                instance = cls(1, 2)
            elif cls.__name__ == "FilterCompilationError":
                instance = cls("msg", "be")
            else:
                instance = cls("msg")

            codes.add(instance._code)

        assert len(codes) == len(exception_classes)