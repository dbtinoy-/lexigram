"""Relay gateway preflight authorization short-circuit tests.

Verifies the auth gate (``AUTHORIZE``) and other preflight failures
(``AUTH_DENIED``, channel selection, conversion) fail fast and never
reach the upstream call.
"""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.contracts.ai.exceptions import RelayError, RelayErrorCode
from lexigram.contracts.core.result import Err
from service_test_helpers import (
    REQUEST_ID,
    RecordingAuthorizer,
    RecordingBilling,
    RecordingConverter,
    make_channel,
    make_request,
    make_service,
)


class TestShortCircuit:
    """Failures before the upstream call must short-circuit the pipeline."""

    @pytest.mark.asyncio
    async def test_authorize_failure_short_circuits(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(
            calls=calls,
            authorizer=RecordingAuthorizer(calls, allowed=False),
            billing=RecordingBilling(calls),
        )
        result = await service.handle(make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "AUTH_DENIED"
        assert err.status_code == 403
        assert err.request_id == REQUEST_ID
        assert [call[0] for call in calls] == ["authorize"]

    @pytest.mark.asyncio
    async def test_channel_selection_failure_short_circuits(self) -> None:
        calls: list[tuple[Any, ...]] = []
        service = make_service(
            calls=calls,
            channels=(make_channel("a", models=("other-model",)),),
            authorizer=RecordingAuthorizer(calls),
            billing=RecordingBilling(calls),
        )
        result = await service.handle(make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "MODEL_NOT_FOUND"
        assert err.status_code == 404
        assert err.request_id == REQUEST_ID
        assert [call[0] for call in calls] == ["authorize", "select"]

    @pytest.mark.asyncio
    async def test_request_conversion_failure_releases_reservation(self) -> None:
        calls: list[tuple[Any, ...]] = []
        converter = RecordingConverter(
            calls,
            request_result=Err(
                RelayError("malformed", RelayErrorCode.MALFORMED_PAYLOAD)
            ),
        )
        billing = RecordingBilling(calls)
        service = make_service(
            calls=calls,
            converter=converter,
            authorizer=RecordingAuthorizer(calls),
            billing=billing,
        )
        result = await service.handle(make_request())
        assert result.is_err()
        err = result.unwrap_err()
        assert err.code == "INVALID_REQUEST"
        assert err.status_code == 400
        assert err.request_id == REQUEST_ID
        assert err.message == "malformed"
        assert "upstream" not in [call[0] for call in calls]
        assert billing.release_count == 1
        assert billing.settle_statuses == []
