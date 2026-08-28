"""HTTPRequestSkill — make outbound HTTP GET/POST requests."""

from __future__ import annotations

from typing import Any
import urllib.error
import urllib.request

from lexigram.ai.skills.base import BaseSkill
from lexigram.ai.skills.exceptions import SkillExecutionError
from lexigram.contracts.ai.skills import SkillDefinition, SkillError, SkillResult
from lexigram.contracts.security import is_safe_url_for_request
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)

_ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """urllib redirect handler that refuses private/reserved redirect targets.

    ``urlopen`` follows redirects automatically; the pre-request SSRF check
    only covers the initial URL, so a public URL redirecting to an internal
    host (metadata endpoint, loopback service) would otherwise bypass it.
    Each ``Location`` target is re-validated with
    :func:`is_safe_url_for_request` and the redirect is aborted when unsafe.
    """

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        if not is_safe_url_for_request(newurl):
            raise urllib.error.URLError(f"Unsafe redirect target: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class HTTPRequestSkill(BaseSkill):
    """Make outbound HTTP requests and return the response body.

    By default the skill uses :mod:`urllib.request` (stdlib) to avoid
    requiring an extra HTTP client dependency.  For production workloads
    integrate with the ``lexigram-http`` ``HTTPClientProtocol``.

    Required permission: ``http.request``.
    """

    @property
    def definition(self) -> SkillDefinition:  # type: ignore[override]
        """Return the skill definition.

        Returns:
            SkillDefinition for the http_request skill.
        """
        return SkillDefinition(
            name="http_request",
            description=(
                "Perform an outbound HTTP request and return the response body "
                "as a string."
            ),
            parameters_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Target URL (must be https:// or http://).",
                    },
                    "method": {
                        "type": "string",
                        "description": "HTTP method. Defaults to 'GET'.",
                        "enum": list(_ALLOWED_METHODS),
                        "default": "GET",
                    },
                    "body": {
                        "type": "string",
                        "description": "Request body string (for POST/PUT/PATCH).",
                        "default": "",
                    },
                    "headers": {
                        "type": "object",
                        "description": "Additional request headers as key-value pairs.",
                        "default": {},
                    },
                    "timeout_seconds": {
                        "type": "number",
                        "description": "Request timeout in seconds. Defaults to 30.",
                        "default": 30,
                    },
                },
                "required": ["url"],
            },
            category="web",
            permissions=["http.request"],
        )

    async def execute(self, **kwargs: Any) -> Result[SkillResult, SkillError]:
        """Execute the HTTP request (stdlib urllib, sync-in-thread).

        Args:
            **kwargs: Requires ``url``; accepts ``method``, ``body``,
                ``headers``, ``timeout_seconds``.

        Returns:
            Ok result with ``status_code``, ``body``, and ``url``, or Err on
            network/validation failure.
        """
        import asyncio
        import urllib.error
        import urllib.request

        url: str = kwargs.get("url", "")
        method: str = kwargs.get("method", "GET").upper()
        body_raw: str = kwargs.get("body", "")
        headers: dict[str, str] = kwargs.get("headers") or {}
        timeout: float = float(kwargs.get("timeout_seconds", 30))

        if method not in _ALLOWED_METHODS:
            return Err(
                SkillExecutionError(
                    f"Unsupported HTTP method '{method}'. "
                    f"Allowed: {sorted(_ALLOWED_METHODS)}"
                )
            )

        if not url.startswith(("http://", "https://")):
            return Err(
                SkillExecutionError(f"URL must start with http:// or https://: {url!r}")
            )

        if not is_safe_url_for_request(url):
            return Err(
                SkillExecutionError(
                    f"URL is not publicly reachable (SSRF guard): {url!r}"
                )
            )

        body_bytes = body_raw.encode() if body_raw else None

        # Guarded opener: refuses redirects whose target is a private or
        # reserved address (metadata endpoint, loopback service, ...).
        _opener = urllib.request.build_opener(_SafeRedirectHandler)

        req = urllib.request.Request(url, data=body_bytes, method=method)  # noqa: S310
        for header_name, header_value in headers.items():
            req.add_header(header_name, header_value)

        def _do_request() -> tuple[int, str]:
            with _opener.open(req, timeout=timeout) as resp:  # noqa: S310
                return resp.status, resp.read().decode(errors="replace")

        try:
            status, response_body = await asyncio.get_event_loop().run_in_executor(
                None, _do_request
            )
        except urllib.error.HTTPError as exc:
            status = exc.code
            response_body = exc.read().decode(errors="replace")
        except (urllib.error.URLError, OSError) as exc:
            logger.error("http_request_error", url=url, error=str(exc))
            raise RuntimeError(f"HTTP request failed: {exc}") from exc

        return Ok(
            SkillResult(
                skill_name="http_request",
                success=True,
                output={"status_code": status, "body": response_body, "url": url},
            )
        )
