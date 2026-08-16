from __future__ import annotations

from lexigram.nosql.cli.generators import DocumentRepositoryGenerator


class TestGeneratorsInit:
    def test_exports_document_repository_generator(self) -> None:
        assert DocumentRepositoryGenerator is not None
