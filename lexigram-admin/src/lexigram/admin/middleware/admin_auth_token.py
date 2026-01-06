"""Example admin/debug middleware.

This middleware is an opt-in example that projects can use to gate admin
endpoints like `/debug/routes`. It sets `request.state.is_admin` to True when
it recognizes a configured secret token or other auth signals.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)


@inject
class DebugAdminAuthMiddleware:
    """Example middleware that grants admin access based on a secret token.

    Usage:
        web = WebProvider(middleware=[AdminAuthMiddleware(token="s3cr3t")])
    """

    def __init__(self, token: str):
        self.token = token

    async def __call__(
        self,
        request: Any,
        call_next: Callable[[Any], Awaitable[Any]],
    ) -> Any:
        # Lexigram middleware adapter will pass a Lexigram `Request` wrapper
        try:
            header_val = request.headers.get("x-debug-token")
        except AttributeError as e:
            logger.debug("Request has no headers attribute: %s", e)
            header_val = None

        try:
            if header_val == self.token:
                request.state.is_admin = True
            else:
                request.state.is_admin = False
        except AttributeError as e:
            logger.debug("Request has no state attribute to set admin flag: %s", e)

        return await call_next(request)
