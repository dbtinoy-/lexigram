from __future__ import annotations

from lexigram.vector.embedding.config import EmbeddingClientConfig


def test_embedding_client_config_stays_embedding_local() -> None:
    assert EmbeddingClientConfig.__name__ == "EmbeddingClientConfig"
    assert EmbeddingClientConfig.__module__ == "lexigram.vector.embedding.config"
