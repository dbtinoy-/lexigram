import pytest

pytest.importorskip("tiktoken")


def test_tiktoken_available():
    import tiktoken

    assert callable(getattr(tiktoken, "get_encoding", None)) or callable(
        getattr(tiktoken, "encoding_for_model", None),
    )
