from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.contracts.data.nosql.nosql import BulkWriteResult, DocumentResult
from lexigram.nosql.backends.firestore.repository import FirestoreRepository
from lexigram.nosql.exceptions import DocumentNotFoundError, DuplicateKeyError, NoSQLError


class TestFirestoreRepository:
    """Tests for FirestoreRepository."""

    @pytest.fixture
    def col_ref(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def repo(self, col_ref: MagicMock) -> FirestoreRepository:
        return FirestoreRepository(col_ref, "test_collection")

    def test_name(self, repo: FirestoreRepository) -> None:
        assert repo.name == "test_collection"

    # ── Insert ─────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_insert_returns_document_result(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        doc_ref = MagicMock()
        doc_ref.id = "auto-id-123"
        col_ref.add = AsyncMock(return_value=(MagicMock(), doc_ref))

        result = await repo.insert({"name": "Alice"})

        assert isinstance(result, DocumentResult)
        assert result.document_id == "auto-id-123"
        assert result.acknowledged is True

    @pytest.mark.asyncio
    async def test_insert_wraps_error(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        col_ref.add = AsyncMock(side_effect=RuntimeError("firestore error"))

        with pytest.raises(NoSQLError, match="insert failed"):
            await repo.insert({"name": "Alice"})

    # ── Find by ID ──────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_find_by_id_returns_document(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        snapshot = MagicMock()
        snapshot.exists = True
        snapshot.id = "doc-1"
        snapshot.to_dict.return_value = {"name": "Alice"}
        col_ref.document.return_value.get = AsyncMock(return_value=snapshot)

        doc = await repo.find_by_id("doc-1")

        assert doc is not None
        assert doc["name"] == "Alice"
        assert doc["_id"] == "doc-1"

    @pytest.mark.asyncio
    async def test_find_by_id_returns_none_when_missing(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        snapshot = MagicMock()
        snapshot.exists = False
        col_ref.document.return_value.get = AsyncMock(return_value=snapshot)

        doc = await repo.find_by_id("missing")
        assert doc is None

    @pytest.mark.asyncio
    async def test_find_by_id_wraps_error(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        col_ref.document.return_value.get = AsyncMock(side_effect=RuntimeError("network error"))

        with pytest.raises(NoSQLError, match="find_by_id failed"):
            await repo.find_by_id("doc-1")

    # ── Find by filter ──────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_find_by_filter_returns_matching_docs(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        snap1 = MagicMock()
        snap1.id = "1"
        snap1.to_dict.return_value = {"name": "Alice"}
        snap2 = MagicMock()
        snap2.id = "2"
        snap2.to_dict.return_value = {"name": "Bob"}

        col_ref.where.return_value.stream.return_value.__aiter__.return_value = [snap1, snap2]

        results = await repo.find_by_filter({"age": 30})

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_find_by_filter_wraps_error(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        col_ref.where.side_effect = RuntimeError("bad query")

        with pytest.raises(NoSQLError, match="find failed"):
            await repo.find_by_filter({"x": 1})

    # ── Update ──────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_update_succeeds(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        snapshot = MagicMock()
        snapshot.exists = True
        col_ref.document.return_value.get = AsyncMock(return_value=snapshot)
        col_ref.document.return_value.update = AsyncMock()

        result = await repo.update("doc-1", {"name": "Alicia"})

        assert result.document_id == "doc-1"
        assert result.modified_count == 1

    @pytest.mark.asyncio
    async def test_update_raises_not_found(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        snapshot = MagicMock()
        snapshot.exists = False
        col_ref.document.return_value.get = AsyncMock(return_value=snapshot)

        with pytest.raises(DocumentNotFoundError, match="not found"):
            await repo.update("ghost", {"name": "X"})

    @pytest.mark.asyncio
    async def test_update_wraps_error(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        snapshot = MagicMock()
        snapshot.exists = True
        col_ref.document.return_value.get = AsyncMock(return_value=snapshot)
        col_ref.document.return_value.update = AsyncMock(side_effect=RuntimeError("update failed"))

        with pytest.raises(NoSQLError, match="update failed"):
            await repo.update("doc-1", {"name": "X"})

    # ── Delete ──────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_delete_succeeds(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        col_ref.document.return_value.delete = AsyncMock()

        result = await repo.delete("doc-1")

        assert result.matched_count == 1

    @pytest.mark.asyncio
    async def test_delete_wraps_error(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        col_ref.document.return_value.delete = AsyncMock(side_effect=RuntimeError("delete failed"))

        with pytest.raises(NoSQLError, match="delete failed"):
            await repo.delete("doc-1")

    # ── CollectionProtocol interface ────────────────────────────────────

    @pytest.mark.asyncio
    async def test_insert_one_delegates_to_insert(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        doc_ref = MagicMock()
        doc_ref.id = "id-1"
        col_ref.add = AsyncMock(return_value=(MagicMock(), doc_ref))

        result = await repo.insert_one({"name": "Alice"})
        assert isinstance(result, DocumentResult)
        assert result.document_id == "id-1"

    @pytest.mark.asyncio
    async def test_insert_many_returns_bulk_result(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        batch = MagicMock()
        batch.set = MagicMock()
        batch.commit = AsyncMock()
        col_ref._client.batch.return_value = batch

        doc_ref1 = MagicMock()
        doc_ref1.id = "1"
        doc_ref2 = MagicMock()
        doc_ref2.id = "2"
        col_ref.document.side_effect = [doc_ref1, doc_ref2]

        result = await repo.insert_many([{"a": 1}, {"b": 2}])

        assert isinstance(result, BulkWriteResult)
        assert result.inserted_count == 2
        batch.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_insert_many_raises_duplicate_key(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        batch = MagicMock()
        batch.set = MagicMock()
        batch.commit = AsyncMock(side_effect=RuntimeError("already exists"))
        col_ref._client.batch.return_value = batch

        with pytest.raises(DuplicateKeyError):
            await repo.insert_many([{"a": 1}])

    @pytest.mark.asyncio
    async def test_insert_many_raises_nosql_error(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        batch = MagicMock()
        batch.set = MagicMock()
        batch.commit = AsyncMock(side_effect=RuntimeError("batch failed"))
        col_ref._client.batch.return_value = batch

        with pytest.raises(NoSQLError, match="insert_many failed"):
            await repo.insert_many([{"a": 1}])

    @pytest.mark.asyncio
    async def test_find_one_delegates_to_find_by_filter(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        snap = MagicMock()
        snap.id = "1"
        snap.to_dict.return_value = {"name": "Alice"}
        col_ref.where.return_value.stream.return_value.__aiter__.return_value = [snap]

        doc = await repo.find_one({"name": "Alice"})
        assert doc is not None
        assert doc["_id"] == "1"

    @pytest.mark.asyncio
    async def test_find_one_returns_none(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        col_ref.where.return_value.stream.return_value.__aiter__.return_value = []

        doc = await repo.find_one({"name": "Ghost"})
        assert doc is None

    @pytest.mark.asyncio
    async def test_find_yields_documents(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        snap = MagicMock()
        snap.id = "1"
        snap.to_dict.return_value = {"name": "Alice"}
        col_ref.where.return_value.stream.return_value.__aiter__.return_value = [snap]

        results = [doc async for doc in repo.find({"name": "Alice"})]
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_find_raises_nosql_error(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        col_ref.where.side_effect = RuntimeError("query failed")

        with pytest.raises(NoSQLError, match="find failed"):
            async for _ in repo.find({"x": 1}):
                pass

    @pytest.mark.asyncio
    async def test_update_one_matches_and_updates(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        snap = MagicMock()
        snap.id = "1"
        snap.to_dict.return_value = {"name": "Alice"}
        col_ref.where.return_value.stream.return_value.__aiter__.return_value = [snap]
        col_ref.document.return_value.get = AsyncMock(return_value=snap)
        col_ref.document.return_value.update = AsyncMock()

        result = await repo.update_one({"name": "Alice"}, {"name": "Alicia"})

        assert result.modified_count == 1

    @pytest.mark.asyncio
    async def test_update_one_no_match(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        col_ref.where.return_value.stream.return_value.__aiter__.return_value = []

        result = await repo.update_one({"name": "Ghost"}, {"name": "X"})
        assert result.matched_count == 0

    @pytest.mark.asyncio
    async def test_update_one_upserts(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        col_ref.where.return_value.stream.return_value.__aiter__.return_value = []
        doc_ref = MagicMock()
        doc_ref.id = "new-id"
        col_ref.add = AsyncMock(return_value=(MagicMock(), doc_ref))

        result = await repo.update_one({"name": "New"}, {"name": "New"}, upsert=True)

        assert result.upserted_id == "new-id"

    @pytest.mark.asyncio
    async def test_update_many(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        snap1 = MagicMock()
        snap1.id = "1"
        snap1.to_dict.return_value = {"name": "Alice"}
        snap2 = MagicMock()
        snap2.id = "2"
        snap2.to_dict.return_value = {"name": "Bob"}
        col_ref.where.return_value.stream.return_value.__aiter__.return_value = [snap1, snap2]
        col_ref.document.return_value.get = AsyncMock(return_value=snap1)
        col_ref.document.return_value.update = AsyncMock()

        result = await repo.update_many({"active": True}, {"flag": False})

        assert result.matched_count == 2
        assert result.modified_count == 2

    @pytest.mark.asyncio
    async def test_delete_one(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        snap = MagicMock()
        snap.id = "1"
        snap.to_dict.return_value = {"name": "Alice"}
        col_ref.where.return_value.stream.return_value.__aiter__.return_value = [snap]
        col_ref.document.return_value.delete = AsyncMock()

        result = await repo.delete_one({"name": "Alice"})
        assert result.matched_count == 1

    @pytest.mark.asyncio
    async def test_delete_one_no_match(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        col_ref.where.return_value.stream.return_value.__aiter__.return_value = []

        result = await repo.delete_one({"name": "Ghost"})
        assert result.matched_count == 0

    @pytest.mark.asyncio
    async def test_delete_many(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        snap1 = MagicMock()
        snap1.id = "1"
        snap1.to_dict.return_value = {"name": "Alice"}
        snap2 = MagicMock()
        snap2.id = "2"
        snap2.to_dict.return_value = {"name": "Bob"}
        col_ref.where.return_value.stream.return_value.__aiter__.return_value = [snap1, snap2]
        col_ref.document.return_value.delete = AsyncMock()

        result = await repo.delete_many({"active": False})
        assert result.matched_count == 2

    @pytest.mark.asyncio
    async def test_count_documents(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        row = MagicMock()
        row.value = 5
        col_ref.where.return_value.count.return_value.get = AsyncMock(
            return_value=[[row]]
        )

        count = await repo.count_documents({"status": "active"})
        assert count == 5

    @pytest.mark.asyncio
    async def test_count_documents_fallback(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        """When count().get() fails, fallback to streaming."""
        col_ref.where.return_value.count.return_value.get = AsyncMock(
            side_effect=RuntimeError("count unavailable")
        )
        col_ref.where.return_value.stream.return_value.__aiter__.return_value = [
            MagicMock(), MagicMock(), MagicMock()
        ]

        count = await repo.count_documents({"status": "active"})
        assert count == 3

    @pytest.mark.asyncio
    async def test_replace_one(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        snap = MagicMock()
        snap.id = "1"
        snap.to_dict.return_value = {"name": "Alice"}
        col_ref.where.return_value.stream.return_value.__aiter__.return_value = [snap]
        col_ref.document.return_value.set = AsyncMock()

        result = await repo.replace_one({"name": "Alice"}, {"name": "Alice Smith"})

        assert result.matched_count == 1
        assert result.modified_count == 1

    @pytest.mark.asyncio
    async def test_replace_one_upserts(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        col_ref.where.return_value.stream.return_value.__aiter__.return_value = []
        doc_ref = MagicMock()
        doc_ref.id = "new-id"
        col_ref.add = AsyncMock(return_value=(MagicMock(), doc_ref))

        result = await repo.replace_one({"name": "New"}, {"name": "New"}, upsert=True)

        assert result.upserted_id == "new-id"

    @pytest.mark.asyncio
    async def test_replace_one_no_match(self, repo: FirestoreRepository, col_ref: MagicMock) -> None:
        col_ref.where.return_value.stream.return_value.__aiter__.return_value = []

        result = await repo.replace_one({"name": "Ghost"}, {"name": "X"})
        assert result.matched_count == 0
