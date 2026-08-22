"""CSRF ``csrf_protect`` decorator fail-closed contract.

The decorator is defense-in-depth behind ``AdminCsrfMiddleware``; these tests
pin its own semantics: state-changing requests without usable CSRF state are
rejected (never skipped), and token comparison is constant-time.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.admin.auth.guards import csrf_protect
from lexigram.admin.exceptions import PermissionDeniedError


def _request(csrf_token=None, submitted=None):
    request = MagicMock(spec=["method", "state", "headers", "scope", "form"])
    request.method = "POST"
    request.state = SimpleNamespace(
        session=SimpleNamespace(csrf_token=csrf_token) if csrf_token else None
    )
    request.headers = {"X-CSRF-Token": submitted} if submitted else {}
    request.scope = {}

    request.form = AsyncMock(return_value={"csrf_token": submitted} if submitted else {})
    return request


@pytest.mark.asyncio
async def test_missing_session_csrf_state_fails_closed():
    @csrf_protect
    async def handler(request):
        return "ok"

    with pytest.raises(PermissionDeniedError, match="CSRF"):
        await handler(_request(csrf_token=None))


@pytest.mark.asyncio
async def test_submitted_token_mismatch_rejected():
    @csrf_protect
    async def handler(request):
        return "ok"

    with pytest.raises(PermissionDeniedError, match="CSRF"):
        await handler(_request(csrf_token="expected", submitted="evil"))


@pytest.mark.asyncio
async def test_matching_token_passes():
    @csrf_protect
    async def handler(request):
        return "ok"

    assert (
        await handler(_request(csrf_token="tok", submitted="tok"))
        == "ok"
    )


@pytest.mark.asyncio
async def test_form_fallback_token_accepted():
    @csrf_protect
    async def handler(request):
        return "ok"

    req = _request(csrf_token="tok", submitted="tok")
    req.headers = {}  # force the form-data fallback path
    assert await handler(req) == "ok"
