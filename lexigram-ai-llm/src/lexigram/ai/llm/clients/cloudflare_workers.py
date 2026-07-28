"""Cloudflare Workers AI client for the Lexigram LLM routing system.

Implements the :class:`~lexigram.contracts.ai.protocols.LLMClientProtocol` protocol
against the Cloudflare Workers AI REST API.

Authentication uses a Bearer token (CF API token) and an ``account_id`` in
the URL path.  Both are sourced from ``ClientConfig.extra`` because
``ClientConfig.api_key`` represents a generic key and Cloudflare requires an
additional account-scoped identifier.

Notes:
    Cloudflare Workers AI does not consistently return token usage metadata.
    ``Completion.usage`` may contain zeroes for token counts when omitted.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.llm.clients._message_utils import serialize_text_only
from lexigram.ai.llm.clients.base import AbstractLLMClient
from lexigram.ai.llm.exceptions import (
    LLMAuthenticationError,
    LLMError,
    LLMModelNotFoundError,
    LLMRateLimitError,
)
from lexigram.ai.llm.http.client import ResilientHTTPClient
from lexigram.ai.llm.types import (
    AIError,
    ChatMessage,
    Completion,
    FunctionCall,
    StreamChunk,
    TokenUsage,
    ToolCall,
)
from lexigram.contracts.core.health import HealthCheckResult, HealthStatus
from lexigram.contracts.web.http_models import HttpStatusError
from lexigram.logging import (
    get_logger,
)
from lexigram.result import Err, Ok, Result
from lexigram.serialization import dumps_str
from lexigram.serialization import loads as _loads

logger = get_logger(__name__)

_CF_BASE_URL = "https://api.cloudflare.com"

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from lexigram.ai.llm.config import ClientConfig

__all__ = ["CloudflareWorkersClient"]


class CloudflareWorkersClient(AbstractLLMClient):
    """Client for the Cloudflare Workers AI REST API.

    Routes requests to
    ``/client/v4/accounts/{account_id}/ai/run/{model}``
    and normalises the response to a standard :class:`~lexigram.ai.llm.types.Completion`.

    Required ``config.extra`` keys:

    * ``cf_account_id`` — Cloudflare account identifier.
    * ``cf_api_token`` — Cloudflare API token with Workers AI permission.

    Example:
        >>> config = ClientConfig(
        ...     provider="cloudflare",
        ...     model="@cf/meta/llama-3.2-11b-vision-instruct",
        ...     extra={
        ...         "cf_account_id": "abc123",
        ...         "cf_api_token": "…",
        ...     },
        ...     timeout=45.0,
        ... )
        >>> client = CloudflareWorkersClient(config)
        >>> completion = await client.complete(
        ...     messages=[{"role": "user", "content": "Hello!"}],
        ... )
    """

    def __init__(self, config: ClientConfig) -> None:
        """Initialise the Cloudflare Workers AI client.

        Args:
            config: LLM configuration.  Required extra fields:
                ``cf_account_id`` (str) and ``cf_api_token`` (str).

        Raises:
            LLMAuthenticationError: When ``cf_account_id`` or ``cf_api_token``
                are absent from ``config.extra``.
        """
        super().__init__(config=config)
        self._http: ResilientHTTPClient | None = None

        account_id: str = config.extra.get("cf_account_id", "")
        api_token: str = config.extra.get("cf_api_token", "")
        if not account_id or not api_token:
            msg = (
                "CloudflareWorkersClient requires config.extra['cf_account_id'] "
                "and config.extra['cf_api_token']"
            )
            raise LLMAuthenticationError(msg)
        self._account_id = account_id
        self._api_token = api_token

    @property
    def _base_url(self) -> str:
        """Return the API base URL, using config override when provided."""
        return self.config.api_base or _CF_BASE_URL

    def _get_http(self) -> ResilientHTTPClient:
        """Return a lazily-created HTTP client instance."""
        if self._http is None:
            self._http = ResilientHTTPClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_token}",
                    "Content-Type": "application/json",
                },
                timeout=self.config.timeout,
                name="cloudflare-workers-client",
            )
        return self._http

    # ──────────────────────────────────────────────────────────────────
    # LLMClientProtocol protocol implementation
    # ──────────────────────────────────────────────────────────────────

    async def _do_complete(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> Result[Completion, LLMError]:
        """Generate a completion from Cloudflare Workers AI.

        Args:
            messages: Chat messages.
            model: Model override.  When ``None``, uses ``config.model``.
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.
            **kwargs: Ignored for protocol compatibility.

        Returns:
            ``Ok(Completion)`` on success.  ``Err(LLMError)`` for recoverable
            failures (rate limit, quota, content filter, model not found).

        Raises:
            LLMLLMAuthenticationError: When credentials are invalid (HTTP 401/403).
            AIError: For unexpected infrastructure failures.
        """
        active_model = model or self.config.model
        cf_messages = _convert_messages_for_cloudflare(messages)
        payload: dict[str, Any] = {
            "messages": cf_messages,
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        path = f"/client/v4/accounts/{self._account_id}/ai/run/{active_model}"

        try:
            http = self._get_http()
            response = await http.post(path, json=payload)
            response.raise_for_status()
        except (
            HttpStatusError,
            OSError,
            ConnectionError,
            TimeoutError,
            RuntimeError,
        ) as exc:
            return self._handle_error_as_result(exc)

        data: dict[str, Any] = response.json
        if not data.get("success", False):
            errors = data.get("errors", [])
            return Err(LLMError(f"Cloudflare Workers AI request failed: {errors}"))

        return Ok(_parse_cf_response(data, active_model))

    async def _do_stream_chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> Result[AsyncIterator[StreamChunk], LLMError]:
        """Stream completion tokens from Cloudflare Workers AI.

        Sends ``stream: true`` to the Cloudflare REST endpoint, which responds
        with an SSE body.  Each ``data:`` line carries a JSON object with a
        ``response`` field containing the incremental text delta.

        Args:
            messages: Chat messages.
            model: Model override.
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.
            **kwargs: Ignored for protocol compatibility.

        Returns:
            ``Ok(AsyncIterator[StreamChunk])`` on successful connection.
            ``Err(LLMError)`` for recoverable failures.

        Raises:
            LLMLLMAuthenticationError: When credentials are invalid.
            AIError: For unexpected infrastructure failures.
        """
        active_model = model or self.config.model
        cf_messages = _convert_messages_for_cloudflare(messages)
        payload: dict[str, Any] = {
            "messages": cf_messages,
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        path = f"/client/v4/accounts/{self._account_id}/ai/run/{active_model}"
        try:
            http = self._get_http()
            response = await http.post(path, json=payload)
            response.raise_for_status()
        except (
            HttpStatusError,
            OSError,
            ConnectionError,
            TimeoutError,
            RuntimeError,
        ) as exc:
            return self._handle_error_as_result(exc)

        return Ok(_parse_cf_sse_body(response.text or "", active_model))

    async def _do_chat(
        self,
        messages: list[ChatMessage],
        tools: list[Any] | None = None,
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> Result[Completion, LLMError]:
        """Generate completion with optional Cloudflare tool/function calling.

        Cloudflare Workers AI supports the OpenAI-compatible tools format.
        ``tool_calls`` in the response are parsed back into :class:`ToolCall`
        objects.

        Args:
            messages: Chat messages.
            tools: Optional tool descriptors.
            model: Model override.
            temperature: Sampling temperature.
            max_tokens: Maximum output tokens.
            **kwargs: Ignored for protocol compatibility.

        Returns:
            ``Ok(Completion)`` on success.  ``Err(LLMError)`` for recoverable
            failures.

        Raises:
            LLMLLMAuthenticationError: When credentials are invalid.
            AIError: For unexpected infrastructure failures.
        """
        active_model = model or self.config.model
        cf_messages = _convert_messages_for_cloudflare(messages)
        payload: dict[str, Any] = {
            "messages": cf_messages,
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = [_tool_to_cf_function(t) for t in tools]

        path = f"/client/v4/accounts/{self._account_id}/ai/run/{active_model}"
        try:
            http = self._get_http()
            response = await http.post(path, json=payload)
            response.raise_for_status()
        except (
            HttpStatusError,
            OSError,
            ConnectionError,
            TimeoutError,
            RuntimeError,
        ) as exc:
            return self._handle_error_as_result(exc)

        data: dict[str, Any] = response.json
        if not data.get("success", False):
            errors = data.get("errors", [])
            return Err(LLMError(f"Cloudflare Workers AI request failed: {errors}"))

        return Ok(_parse_cf_response_with_tools(data, active_model))

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Perform a lightweight health check against Cloudflare Workers AI.

        Lists the first model as a zero-inference probe to verify credentials
        and service reachability.

        Args:
            timeout: Seconds to wait (informational; uses client-level timeout).

        Returns:
            :class:`~lexigram.contracts.core.health.HealthCheckResult`.
        """
        try:
            http = self._get_http()
            path = f"/client/v4/accounts/{self._account_id}/ai/models/search?per_page=1"
            response = await http.get(path)
            response.raise_for_status()
            return HealthCheckResult(
                component="cloudflare", status=HealthStatus.HEALTHY
            )
        except (OSError, ConnectionError, TimeoutError, RuntimeError) as exc:
            return HealthCheckResult(
                component="cloudflare",
                status=HealthStatus.UNHEALTHY,
                error=str(exc),
            )

    async def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        if self._http is not None:
            await self._http.close()
            self._http = None
        await super().close()

    def _handle_error_as_result(self, error: Exception) -> Result[Any, LLMError]:
        """Map a caught exception to ``Err`` (recoverable) or re-raise (infra)."""
        status: int | None = None
        if isinstance(error, HttpStatusError):
            status = error.status

        if status in (401, 403):
            raise LLMAuthenticationError(
                f"cloudflare: authentication failed ({status}): {error}"
            ) from error
        if status == 429:
            return Err(LLMRateLimitError(f"cloudflare: rate limit exceeded: {error}"))
        if status == 400:
            err_str = str(error).lower()
            if "not found" in err_str or "does not exist" in err_str:
                return Err(
                    LLMModelNotFoundError(f"cloudflare: model not found: {error}")
                )
            return Err(LLMError(f"cloudflare: invalid request: {error}"))
        if status == 404:
            return Err(LLMModelNotFoundError(f"cloudflare: model not found: {error}"))
        raise AIError(f"cloudflare: infrastructure error: {error}") from error


# ──────────────────────────────────────────────────────────────────────
# Private helpers
# ──────────────────────────────────────────────────────────────────────


def _convert_messages_for_cloudflare(
    messages: list[ChatMessage] | list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Convert ChatMessage objects to Cloudflare API format.

    Cloudflare Workers AI accepts only ``role`` and ``content`` (string).
    Uses ``serialize_text_only`` to extract text from multimodal content,
    warning when image parts are encountered.

    Args:
        messages: List of ChatMessage objects or dicts (for backward compatibility).

    Returns:
        Cleaned message list compatible with the Cloudflare API.
    """
    result: list[dict[str, Any]] = []
    for msg in messages:
        if isinstance(msg, dict):
            # Backward compatibility: handle dict messages
            role: str = msg.get("role", "user")
            content: Any = msg.get("content", "")
        else:
            # ChatMessage object
            role = msg.role.value
            content = msg.content

        # Serialize content using text-only for non-vision clients
        text_content = serialize_text_only(
            content,
            logger=logger,
            client_name="cloudflare",
        )
        result.append({"role": role, "content": text_content})
    return result


def _parse_cf_response(data: dict[str, Any], model: str) -> Completion:
    """Parse a Cloudflare Workers AI response into a ``Completion``.

    Args:
        data: Parsed JSON response from the Cloudflare API.
        model: Model identifier.

    Returns:
        Normalised :class:`~lexigram.ai.llm.types.Completion`.
    """
    result_obj = data.get("result", {})
    text: str = result_obj.get("response", "")
    usage_data = result_obj.get("usage", {})
    usage = TokenUsage(
        prompt_tokens=usage_data.get("prompt_tokens", 0),
        completion_tokens=usage_data.get("completion_tokens", 0),
        total_tokens=usage_data.get("total_tokens", 0),
    )
    return Completion(content=text, model=model, usage=usage)


def _parse_cf_response_with_tools(data: dict[str, Any], model: str) -> Completion:
    """Parse a Cloudflare Workers AI response that may include tool calls.

    Args:
        data: Parsed JSON response from the Cloudflare API.
        model: Model identifier.

    Returns:
        Normalised :class:`~lexigram.ai.llm.types.Completion` with optional
        :attr:`~Completion.tool_calls` populated.
    """
    result_obj = data.get("result", {})
    text: str = result_obj.get("response", "")
    usage_data = result_obj.get("usage", {})
    usage = TokenUsage(
        prompt_tokens=usage_data.get("prompt_tokens", 0),
        completion_tokens=usage_data.get("completion_tokens", 0),
        total_tokens=usage_data.get("total_tokens", 0),
    )

    raw_calls: list[dict[str, Any]] = result_obj.get("tool_calls", [])
    tool_calls: list[ToolCall] | None = None
    if raw_calls:
        tool_calls = []
        for tc in raw_calls:
            func = tc.get("function", {})
            args = func.get("arguments", {})
            if isinstance(args, dict):
                args = dumps_str(args)
            tool_calls.append(
                ToolCall(
                    id=tc.get("id", func.get("name", "")),
                    type="function",
                    function=FunctionCall(
                        name=func.get("name", ""),
                        arguments=args,
                    ),
                )
            )

    return Completion(content=text, model=model, usage=usage, tool_calls=tool_calls)


async def _parse_cf_sse_body(body: str, model: str) -> AsyncIterator[StreamChunk]:
    """Yield :class:`StreamChunk` objects from a Cloudflare Workers AI SSE body.

    Each ``data:`` line carries a JSON object with a ``response`` field
    containing the incremental text delta.

    Args:
        body: Full SSE response body text.
        model: Model label embedded in each :class:`StreamChunk`.

    Yields:
        :class:`StreamChunk` with incremental text deltas.
    """
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("data:"):
            continue
        raw = stripped[len("data:") :].strip()
        if not raw or raw == "[DONE]":
            continue
        try:
            chunk: dict[str, Any] = _loads(raw)
        except (ValueError, TypeError):
            continue
        delta = chunk.get("response", "")
        yield StreamChunk(
            delta=delta,
            model=model,
            finish_reason=None,
            index=0,
        )


def _tool_to_cf_function(tool: Any) -> dict[str, Any]:
    """Convert a tool descriptor to Cloudflare Workers AI OpenAI-compatible format.

    Args:
        tool: A class with ``__tool_schema__``, or a dict with a ``function``
            key in OpenAI tool format.

    Returns:
        Dict with ``type: "function"`` and nested ``function`` description.
    """
    if hasattr(tool, "__tool_schema__"):
        schema: dict[str, Any] = tool.__tool_schema__
        return {
            "type": "function",
            "function": {
                "name": schema["name"],
                "description": schema.get("description", ""),
                "parameters": schema.get("parameters", {}),
            },
        }
    if isinstance(tool, dict):
        func = tool.get("function", tool)
        return {
            "type": "function",
            "function": {
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "parameters": func.get("parameters", {}),
            },
        }
    return {
        "type": "function",
        "function": {
            "name": getattr(tool, "name", str(tool)),
            "description": getattr(tool, "description", ""),
            "parameters": {},
        },
    }
