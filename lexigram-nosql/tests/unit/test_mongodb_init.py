from __future__ import annotations

from lexigram.nosql.backends.mongodb import MongoDBCollection, MongoDBDocumentStore


class TestMongoDBInit:
    def test_exports_mongodb_collection(self) -> None:
        assert MongoDBCollection is not None

    def test_exports_mongodb_document_store(self) -> None:
        assert MongoDBDocumentStore is not None
