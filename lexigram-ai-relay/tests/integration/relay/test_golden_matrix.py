"""Golden matrix: every directed route reproduces the reference output.

The 36 fixtures (12 request + 12 response + 12 stream) were recorded
from new-api's ``relaykit/relayconvert``.  Each test drives one route
through the engine (or, for streams, through the shared ``StreamSession``
state machine) and compares the normalized wire output against the
recorded golden snapshot, dropping only the documented relaykit-only
host/artifact fields in ``drop_relaykit_only``.
"""

from __future__ import annotations

import pytest

from lexigram.ai.relay import route_quality
from lexigram.ai.relay.engine import (
    convert_request_by_id,
    convert_response_by_id,
)
from lexigram.ai.relay.stream import (
    StreamSession,
    claude_emitter,
    gemini_emitter,
    openai_chat_emitter,
    openai_responses_emitter,
)
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.relay.ir import StreamDelta
from lexigram.contracts.ai.relay.types import RelayFormat
from lexigram.contracts.core.result import Ok, Result

from ._fixtures import (
    FORMAT_SLUGS,
    REQUEST_FIXTURES,
    RESPONSE_FIXTURES,
    routes,
)
from .conftest import (
    REQUEST_DTOS,
    RESPONSE_DTOS,
    STREAM_DELTAS,
    STREAM_ID,
    STREAM_MODEL,
    drop_relaykit_only,
    load_golden,
    normalize_volatile,
)

EMITTERS = {
    "openai": openai_chat_emitter,
    "openai_responses": openai_responses_emitter,
    "claude": claude_emitter,
    "gemini": gemini_emitter,
}


def _assert_tree_equal(got: object, want: object, where: str) -> None:
    """Assert deep equality of JSON trees with a readable diff on failure."""
    if isinstance(got, dict) and isinstance(want, dict):
        for key in sorted(set(got) | set(want)):
            if key not in got:
                pytest.fail(f"{where}.{key}: expected {want[key]!r}, missing from output")
            if key not in want:
                pytest.fail(f"{where}.{key}: unexpected {got[key]!r} in output")
            _assert_tree_equal(got[key], want[key], f"{where}.{key}")
        return
    if isinstance(got, list) and isinstance(want, list):
        if len(got) != len(want):
            pytest.fail(f"{where}: length {len(got)} != {len(want)}")
        for index, (g, w) in enumerate(zip(got, want)):
            _assert_tree_equal(g, w, f"{where}[{index}]")
        return
    if got != want:
        pytest.fail(f"{where}: {got!r} != {want!r}")


def _assert_dto_matches_payload(dto, golden: object, route: str) -> None:
    got = drop_relaykit_only(normalize_volatile(dto.to_dict()))
    want = drop_relaykit_only(normalize_volatile(golden))
    _assert_tree_equal(got, want, f"{route} payload")


class _SequenceNormalizer:
    """Yields the pre-transcribed canonical deltas for one stream source."""

    def __init__(self, deltas: list[StreamDelta]) -> None:
        self._deltas = list(deltas)

    def __call__(
        self, event: object, *, state: object
    ) -> Result[tuple[StreamDelta, ...], RelayError]:
        del event, state
        if not self._deltas:
            return Ok(())
        return Ok((self._deltas.pop(0),))


@pytest.mark.parametrize("route", routes("request"))
def test_request_matrix(route: str, registry, ctx) -> None:
    source_slug, target_slug = route.split("_to_", 1)
    source = FORMAT_SLUGS[source_slug]
    target = FORMAT_SLUGS[target_slug]
    payload = REQUEST_DTOS[source_slug].from_dict(REQUEST_FIXTURES[source_slug])
    result = convert_request_by_id(
        registry, payload, f"{source}_to_{target}", context=ctx
    )
    assert result.is_ok(), result.unwrap_err()
    outcome = result.unwrap()
    assert outcome.converter_id == f"{source}_to_{target}"
    assert outcome.source == RelayFormat(source)
    assert outcome.target == RelayFormat(target)
    assert outcome.quality == route_quality(
        RelayFormat(source), RelayFormat(target)
    )
    _assert_dto_matches_payload(outcome.value, load_golden("request", route), route)


@pytest.mark.parametrize("route", routes("response"))
def test_response_matrix(route: str, registry, ctx) -> None:
    source_slug, target_slug = route.split("_to_", 1)
    source = FORMAT_SLUGS[source_slug]
    target = FORMAT_SLUGS[target_slug]
    payload = RESPONSE_DTOS[source_slug].from_dict(RESPONSE_FIXTURES[source_slug])
    result = convert_response_by_id(
        registry, payload, f"{source}_to_{target}", context=ctx
    )
    assert result.is_ok(), result.unwrap_err()
    outcome = result.unwrap()
    assert outcome.converter_id == f"{source}_to_{target}"
    assert outcome.source == RelayFormat(source)
    assert outcome.target == RelayFormat(target)
    assert outcome.quality == route_quality(
        RelayFormat(source), RelayFormat(target)
    )
    assert outcome.usage is not None
    _assert_dto_matches_payload(outcome.value, load_golden("response", route), route)


@pytest.mark.parametrize("route", routes("stream"))
def test_stream_matrix(route: str, ctx) -> None:
    source_slug, target_slug = route.split("_to_", 1)
    source = FORMAT_SLUGS[source_slug]
    target = FORMAT_SLUGS[target_slug]
    session = StreamSession(
        source=RelayFormat(source),
        target=RelayFormat(target),
        model=STREAM_MODEL[source_slug],
        stream_id=STREAM_ID[source_slug],
        created=1700000000,
        normalizer=_SequenceNormalizer(STREAM_DELTAS[source_slug]),
        emitter=EMITTERS[target_slug],
    )
    events: list[object] = []
    for delta in STREAM_DELTAS[source_slug]:
        events.extend(session.accept(delta))
    events.extend(session.finalize())
    assert session.finalize() == ()

    golden_events = drop_relaykit_only(
        normalize_volatile(load_golden("stream", route)["events"])
    )
    got_events = [
        drop_relaykit_only(normalize_volatile(event.to_dict())) for event in events
    ]
    _assert_tree_equal(got_events, golden_events, f"{route} stream events")

    snapshot = session.snapshot()
    assert snapshot.finish_reason is not None
    assert snapshot.is_done