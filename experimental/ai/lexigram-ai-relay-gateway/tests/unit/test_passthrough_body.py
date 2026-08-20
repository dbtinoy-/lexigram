"""Tests for the passthrough request body carrier and multipart rewrite."""

from __future__ import annotations

import pytest

from lexigram.ai.relay.gateway.passthrough import (
    RelayPassthroughBody,
    rewrite_multipart_form_field,
)
from passthrough_test_helpers import (
    MODEL,
    MULTIPART_BODY,
    MULTIPART_BOUNDARY,
    MULTIPART_CONTENT_TYPE,
    WHITESPACE_BODY,
)


class TestRelayPassthroughBody:
    """``RelayPassthroughBody`` construction and value semantics."""

    def test_json_wraps_dict_as_json_content_type(self) -> None:
        body = RelayPassthroughBody.json(dict(WHITESPACE_BODY))
        assert body.data == WHITESPACE_BODY
        assert body.content_type == "application/json"
        assert isinstance(body.data, dict)
        assert dict(body) == WHITESPACE_BODY
        assert body["model"] == MODEL
        assert "model" in body
        assert list(body) == list(WHITESPACE_BODY)
        assert len(body) == len(WHITESPACE_BODY)

    def test_json_wraps_without_mutating_source(self) -> None:
        source = dict(WHITESPACE_BODY)
        body = RelayPassthroughBody.json(source)
        source["model"] = "mutated"
        assert body["model"] == MODEL

    def test_raw_keeps_bytes_and_content_type(self) -> None:
        body = RelayPassthroughBody.raw(MULTIPART_BODY, MULTIPART_CONTENT_TYPE)
        assert body.data == MULTIPART_BODY
        assert body.content_type == MULTIPART_CONTENT_TYPE

    def test_raw_body_is_not_a_json_mapping(self) -> None:
        body = RelayPassthroughBody.raw(b"bytes", "application/octet-stream")
        with pytest.raises(TypeError):
            dict(body)
        with pytest.raises(TypeError):
            body["model"]

    def test_json_and_raw_of_same_bytes_are_distinct(self) -> None:
        raw = RelayPassthroughBody.raw(MULTIPART_BODY, MULTIPART_CONTENT_TYPE)
        assert raw != RelayPassthroughBody.json({"model": MODEL})


class TestMultipartRequestPassthrough:
    """Multipart request bodies forward byte-for-byte."""

    def test_rewrite_swaps_model_value_only(self) -> None:
        rewritten = rewrite_multipart_form_field(
            MULTIPART_BODY, MULTIPART_BOUNDARY, "model", "new-model-name"
        )
        expected = MULTIPART_BODY.replace(
            (MODEL + "\r\n").encode("ascii"), b"new-model-name\r\n", 1
        )
        assert rewritten == expected
        assert b'name="image"' in rewritten
        assert b"\x89PNG\r\n\x1a\nBINARY\x00\xffDATA" in rewritten
        assert rewritten.endswith(f"--{MULTIPART_BOUNDARY}--\r\n".encode("ascii"))

    def test_rewrite_leaves_body_unchanged_when_field_missing(self) -> None:
        model_part = b'Content-Disposition: form-data; name="model"\r\n\r\n' + (
            MODEL + "\r\n"
        ).encode("ascii")
        body_without_model = MULTIPART_BODY.replace(model_part, b"", 1)
        assert b'name="model"' not in body_without_model
        rewritten = rewrite_multipart_form_field(
            body_without_model, MULTIPART_BOUNDARY, "model", "new-model-name"
        )
        assert rewritten == body_without_model

    def test_rewrite_missing_boundary_is_verbatim(self) -> None:
        assert (
            rewrite_multipart_form_field(
                MULTIPART_BODY, "no-such-boundary", "model", "x"
            )
            == MULTIPART_BODY
        )