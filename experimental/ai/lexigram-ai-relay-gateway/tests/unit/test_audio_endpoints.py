"""Audio passthrough endpoint layer tests (Relay Gateway audio endpoints plan).

Covers the three audio endpoint handlers (speech, transcriptions,
translations): JSON and multipart request shaping into
``RelayPassthroughBody``, byte-exact multipart forwarding with model
extraction, verbatim binary responses, OpenAI error envelopes, and the
self-contained audio route table.  Handlers are exercised with the same
minimal request double the web-layer tests use.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from starlette.responses import JSONResponse, Response

from lexigram.ai.relay.gateway.passthrough import (
    RelayPassthroughBody,
    RelayPassthroughResult,
)
from lexigram.ai.relay.gateway.web.audio_endpoints import (
    AUDIO_ROUTE_TABLE,
    audio_speech_endpoint,
    audio_transcriptions_endpoint,
    audio_translations_endpoint,
)
from lexigram.contracts.ai.relay import (
    RelayFormat,
    RelayGatewayError,
    RelayGatewayRequest,
)
from lexigram.contracts.core.result import Err, Ok, Result
from lexigram.serialization import loads

MODEL = "whisper-1"
REQUEST_ID = "req-audio-1"
TENANT_ID = "tenant-1"
SPEECH_BODY = {"model": "tts-1", "input": "hello world", "voice": "alloy"}
TRANSLATION_BODY = {"model": MODEL, "input": "bonjour"}
AUDIO_BYTES = b"\xff\xfb\x90\x00MP3BINARY\x00\xffDATA"

MULTIPART_BOUNDARY = "bnd-42"
MULTIPART_CONTENT_TYPE = f"multipart/form-data; boundary={MULTIPART_BOUNDARY}"
FILE_PART = b"MP3FILE\x01\x02\x03BINARY"
MULTIPART_BODY = b"".join(
    [
        f"--{MULTIPART_BOUNDARY}\r\n".encode("ascii"),
        b'Content-Disposition: form-data; name="model"\r\n',
        b"\r\n",
        MODEL.encode("ascii"),
        b"\r\n",
        f"--{MULTIPART_BOUNDARY}\r\n".encode("ascii"),
        b'Content-Disposition: form-data; name="file"; filename="speech.mp3"\r\n',
        b"Content-Type: audio/mpeg\r\n",
        b"\r\n",
        FILE_PART,
        b"\r\n",
        f"--{MULTIPART_BOUNDARY}--\r\n".encode("ascii"),
    ]
)
"""A two-part multipart body: a ``model`` field plus a binary ``file`` part."""


class FakePassthroughService:
    """``PassthroughService`` double recording ``handle`` calls."""

    def __init__(
        self,
        outcome: Result[RelayPassthroughResult, RelayGatewayError],
    ) -> None:
        self._outcome = outcome
        self.calls: list[tuple[str, RelayGatewayRequest]] = []

    async def handle(
        self, kind: str, request: RelayGatewayRequest
    ) -> Result[RelayPassthroughResult, RelayGatewayError]:
        """Record the call and return the canned outcome."""
        self.calls.append((kind, request))
        return self._outcome


class FakePassthroughResolver:
    """Async callable returning the configured fake passthrough service."""

    def __init__(self, service: FakePassthroughService) -> None:
        self._service = service
        self.calls: list[Any] = []

    async def __call__(self, request: Any) -> FakePassthroughService:
        """Record the request and return the fake service."""
        self.calls.append(request)
        return self._service


class FakeRequest:
    """Minimal request double exposing the state/headers surface endpoints use."""

    def __init__(
        self,
        *,
        body: bytes = b"{}",
        request_id: str | None = None,
        user: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._body = body
        self.state = SimpleNamespace(request_id=request_id, user=user, container=None)
        self.headers: dict[str, str] = headers if headers is not None else {}

    async def body(self) -> bytes:
        """Return the canned request body."""
        return self._body


def ok_json(
    payload: dict[str, Any],
) -> Result[RelayPassthroughResult, RelayGatewayError]:
    """A canned Ok JSON passthrough result."""
    return Ok(
        RelayPassthroughResult(
            status_code=200,
            headers={"content-type": "application/json", "x-request-id": REQUEST_ID},
            payload=payload,
            body=payload,
            content_type="application/json",
        )
    )


def ok_audio() -> Result[RelayPassthroughResult, RelayGatewayError]:
    """A canned Ok binary audio passthrough result."""
    return Ok(
        RelayPassthroughResult(
            status_code=200,
            headers={"content-type": "audio/mpeg", "x-request-id": REQUEST_ID},
            body=AUDIO_BYTES,
            content_type="audio/mpeg",
        )
    )


def err_upstream() -> Result[RelayPassthroughResult, RelayGatewayError]:
    """A canned upstream failure mapped to a safe gateway error."""
    return Err(
        RelayGatewayError(
            code="UPSTREAM_TIMEOUT",
            message="upstream request timed out",
            status_code=504,
            request_id=REQUEST_ID,
        )
    )


def speech_request(
    body: bytes = b"",
    *,
    request_id: str | None = REQUEST_ID,
    user: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> FakeRequest:
    """Build a request for the speech endpoint with defaults."""
    payload = body or b'{"model": "tts-1", "input": "hello world", "voice": "alloy"}'
    return FakeRequest(
        body=payload,
        request_id=request_id,
        user=user if user is not None else {"id": "u1", "tenant_id": TENANT_ID},
        headers=headers
        if headers is not None
        else {"content-type": "application/json"},
    )


def transcription_request(
    *,
    request_id: str | None = REQUEST_ID,
    user: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> FakeRequest:
    """Build a multipart request for the transcription endpoint."""
    return FakeRequest(
        body=MULTIPART_BODY,
        request_id=request_id,
        user=user if user is not None else {"id": "u1", "tenant_id": TENANT_ID},
        headers=headers
        if headers is not None
        else {"content-type": MULTIPART_CONTENT_TYPE},
    )


class TestAudioRouteTable:
    """The audio endpoints expose their own route table."""

    def test_table_covers_three_audio_kinds(self) -> None:
        assert AUDIO_ROUTE_TABLE == (
            ("/v1/audio/speech", "audio_speech"),
            ("/v1/audio/transcriptions", "audio_transcriptions"),
            ("/v1/audio/translations", "audio_translations"),
        )


class TestAudioSpeechEndpoint:
    """``POST /v1/audio/speech`` JSON request behavior."""

    async def test_json_request_forwards_verbatim(self) -> None:
        service = FakePassthroughService(ok_json({"audio": "https://cdn/out.mp3"}))
        resolver = FakePassthroughResolver(service)
        response = await audio_speech_endpoint(resolver, speech_request())
        assert isinstance(response, JSONResponse)
        assert response.status_code == 200
        assert loads(response.body) == {"audio": "https://cdn/out.mp3"}
        assert response.headers.get("x-request-id") == REQUEST_ID
        kind, request = service.calls[0]
        assert kind == "audio_speech"
        assert request.request_id == REQUEST_ID
        assert request.tenant_id == TENANT_ID
        assert request.model == "tts-1"
        assert request.source is RelayFormat.OPENAI_CHAT
        assert request.stream is False
        assert request.channel is None
        assert isinstance(request.payload, RelayPassthroughBody)
        assert request.payload.data == SPEECH_BODY
        assert request.payload.content_type == "application/json"

    async def test_binary_audio_response_verbatim(self) -> None:
        service = FakePassthroughService(ok_audio())
        resolver = FakePassthroughResolver(service)
        response = await audio_speech_endpoint(resolver, speech_request())
        assert isinstance(response, Response)
        assert not isinstance(response, JSONResponse)
        assert response.status_code == 200
        assert response.body == AUDIO_BYTES
        assert response.headers.get("content-type") == "audio/mpeg"
        assert response.headers.get("x-request-id") == REQUEST_ID

    async def test_upstream_error_uses_openai_envelope(self) -> None:
        service = FakePassthroughService(err_upstream())
        resolver = FakePassthroughResolver(service)
        response = await audio_speech_endpoint(resolver, speech_request())
        assert response.status_code == 504
        assert loads(response.body) == {
            "error": {
                "message": "upstream request timed out",
                "type": "server_error",
                "code": "UPSTREAM_TIMEOUT",
                "request_id": REQUEST_ID,
            }
        }

    async def test_missing_model_is_400(self) -> None:
        service = FakePassthroughService(ok_json({"audio": "u"}))
        resolver = FakePassthroughResolver(service)
        response = await audio_speech_endpoint(
            resolver, speech_request(body=b'{"input": "hi", "voice": "alloy"}')
        )
        assert response.status_code == 400
        assert loads(response.body)["error"]["code"] == "INVALID_REQUEST"
        assert service.calls == []

    async def test_malformed_json_is_400(self) -> None:
        service = FakePassthroughService(ok_json({"audio": "u"}))
        resolver = FakePassthroughResolver(service)
        response = await audio_speech_endpoint(
            resolver, speech_request(body=b"not json")
        )
        assert response.status_code == 400
        assert service.calls == []

    async def test_request_id_fallback_uuid(self) -> None:
        service = FakePassthroughService(ok_json({"audio": "u"}))
        resolver = FakePassthroughResolver(service)
        response = await audio_speech_endpoint(
            resolver, speech_request(request_id=None)
        )
        assert response.status_code == 200
        rid = service.calls[0][1].request_id
        assert len(rid) == 36
        assert all(character in "0123456789abcdef-" for character in rid.lower())


class TestAudioTranscriptionsEndpoint:
    """``POST /v1/audio/transcriptions`` multipart request behavior."""

    async def test_multipart_request_byte_exact_with_model_extraction(self) -> None:
        service = FakePassthroughService(ok_json({"text": "hello"}))
        resolver = FakePassthroughResolver(service)
        response = await audio_transcriptions_endpoint(
            resolver, transcription_request()
        )
        assert isinstance(response, JSONResponse)
        assert loads(response.body) == {"text": "hello"}
        kind, request = service.calls[0]
        assert kind == "audio_transcriptions"
        assert request.model == MODEL
        assert request.tenant_id == TENANT_ID
        assert request.source is RelayFormat.OPENAI_CHAT
        assert request.stream is False
        assert isinstance(request.payload, RelayPassthroughBody)
        assert request.payload.data == MULTIPART_BODY
        assert request.payload.content_type == MULTIPART_CONTENT_TYPE
        assert FILE_PART in request.payload.data  # type: ignore[operator]

    async def test_multipart_with_binary_response_verbatim(self) -> None:
        service = FakePassthroughService(ok_audio())
        resolver = FakePassthroughResolver(service)
        response = await audio_transcriptions_endpoint(
            resolver, transcription_request()
        )
        assert isinstance(response, Response)
        assert not isinstance(response, JSONResponse)
        assert response.body == AUDIO_BYTES
        assert response.headers.get("content-type") == "audio/mpeg"

    async def test_multipart_without_boundary_is_400(self) -> None:
        service = FakePassthroughService(ok_json({"text": "hi"}))
        resolver = FakePassthroughResolver(service)
        response = await audio_transcriptions_endpoint(
            resolver,
            transcription_request(headers={"content-type": "multipart/form-data"}),
        )
        assert response.status_code == 400
        assert loads(response.body)["error"]["code"] == "INVALID_REQUEST"
        assert service.calls == []

    async def test_multipart_without_model_field_is_400(self) -> None:
        service = FakePassthroughService(ok_json({"text": "hi"}))
        resolver = FakePassthroughResolver(service)
        model_part = b'Content-Disposition: form-data; name="model"\r\n\r\n' + (
            MODEL + "\r\n"
        ).encode("ascii")
        body_without_model = MULTIPART_BODY.replace(model_part, b"", 1)
        assert b'name="model"' not in body_without_model
        response = await audio_transcriptions_endpoint(
            resolver,
            FakeRequest(
                body=body_without_model,
                request_id=REQUEST_ID,
                user={"id": "u1", "tenant_id": TENANT_ID},
                headers={"content-type": MULTIPART_CONTENT_TYPE},
            ),
        )
        assert response.status_code == 400
        assert loads(response.body)["error"]["code"] == "INVALID_REQUEST"
        assert service.calls == []

    async def test_upstream_error_uses_openai_envelope(self) -> None:
        service = FakePassthroughService(err_upstream())
        resolver = FakePassthroughResolver(service)
        response = await audio_transcriptions_endpoint(
            resolver, transcription_request()
        )
        assert response.status_code == 504
        assert loads(response.body)["error"]["type"] == "server_error"


class TestAudioTranslationsEndpoint:
    """``POST /v1/audio/translations`` request behavior."""

    async def test_json_request_forwards_verbatim(self) -> None:
        service = FakePassthroughService(ok_json({"text": "bonjour"}))
        resolver = FakePassthroughResolver(service)
        response = await audio_translations_endpoint(
            resolver,
            FakeRequest(
                body=b'{"model": "whisper-1", "input": "bonjour"}',
                request_id=REQUEST_ID,
                user={"id": "u1", "tenant_id": TENANT_ID},
                headers={"content-type": "application/json"},
            ),
        )
        assert isinstance(response, JSONResponse)
        assert loads(response.body) == {"text": "bonjour"}
        kind, request = service.calls[0]
        assert kind == "audio_translations"
        assert request.model == MODEL
        assert isinstance(request.payload, RelayPassthroughBody)
        assert request.payload.data == TRANSLATION_BODY

    async def test_multipart_request_forwards_verbatim(self) -> None:
        service = FakePassthroughService(ok_json({"text": "bonjour"}))
        resolver = FakePassthroughResolver(service)
        response = await audio_translations_endpoint(resolver, transcription_request())
        assert isinstance(response, JSONResponse)
        kind, request = service.calls[0]
        assert kind == "audio_translations"
        assert request.model == MODEL
        assert request.payload.data == MULTIPART_BODY  # type: ignore[operator]

    async def test_binary_audio_response_verbatim(self) -> None:
        service = FakePassthroughService(ok_audio())
        resolver = FakePassthroughResolver(service)
        response = await audio_translations_endpoint(
            resolver,
            FakeRequest(
                body=b'{"model": "whisper-1", "input": "bonjour"}',
                request_id=REQUEST_ID,
                user={"id": "u1", "tenant_id": TENANT_ID},
                headers={"content-type": "application/json"},
            ),
        )
        assert isinstance(response, Response)
        assert not isinstance(response, JSONResponse)
        assert response.body == AUDIO_BYTES
        assert response.headers.get("content-type") == "audio/mpeg"
