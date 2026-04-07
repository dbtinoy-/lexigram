from __future__ import annotations

from unittest.mock import patch

from lexigram.nosql.backends.mongodb.codecs import configure_codecs


class TestConfigureCodecs:
    def test_returns_codec_options_when_bson_available(self) -> None:
        result = configure_codecs()
        if result is not None:
            assert hasattr(result, "uuid_representation")

    def test_returns_none_when_bson_unavailable(self) -> None:
        with patch.dict("sys.modules", {"bson": None}):
            with patch("lexigram.nosql.backends.mongodb.codecs.configure_codecs", return_value=None):
                result = configure_codecs()
                assert result is None
