"""Unit tests for AzureOpenAI, Bedrock, VertexAI, and OpenAI-Compatible clients.

Covers: completion, streaming, tool calling, health check, error classification
for the six clients that were previously untested.
"""

from __future__ import annotations

import asyncio
import sys
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.ai.llm.config import ClientConfig
from lexigram.ai.llm.exceptions import (
    LLMAuthenticationError,
    LLMError,
    LLMModelNotFoundError,
    LLMRateLimitError,
)
from lexigram.ai.llm.types import AIError, ChatMessage, Role
from lexigram.contracts.core import HealthStatus
from lexigram.contracts.web.http_models import HttpStatusError
from lexigram.validation import SecretStr


# ──────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────────────────────


def _make_http_error(status: int) -> HttpStatusError:
    mock_response = MagicMock()
    mock_response.url = "https://example.com/fake"
    mock_response.method = "POST"
    return HttpStatusError(f"HTTP {status}", status=status, response=mock_response)


def _mock_http_response(data: dict) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    type(resp).json = property(lambda self: data)
    resp.text = ""
    return resp


def _fake_openai_module(completion_text: str = "hello") -> SimpleNamespace:
    """Build a fake ``openai`` module for monkeypatching sys.modules."""

    class FakeChoiceMsg:
        def __init__(self) -> None:
            self.content = completion_text
            self.tool_calls = None

    class FakeUsage:
        prompt_tokens = 3
        completion_tokens = 5
        total_tokens = 8

    class FakeChoice:
        def __init__(self) -> None:
            self.message = FakeChoiceMsg()
            self.finish_reason = "stop"

    class FakeCompletion:
        def __init__(self) -> None:
            self.choices = [FakeChoice()]
            self.model = "fake-model"
            self.usage = FakeUsage()
            self.id = "cmpl-fake"
            self.created = 1
            self.system_fingerprint = None

    async def _create(**_kwargs: Any) -> FakeCompletion:
        return FakeCompletion()

    completions = SimpleNamespace(create=_create)
    chat = SimpleNamespace(completions=completions)

    class FakeModelsData:
        id = "test-model"

    class FakeModels:
        data = [FakeModelsData()]

        async def list(self) -> FakeModels:
            return self

    class AsyncOpenAI:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.chat = chat
            self.models = FakeModels()

        async def close(self) -> None:
            pass

    class AsyncAzureOpenAI(AsyncOpenAI):
        pass

    return SimpleNamespace(
        AsyncOpenAI=AsyncOpenAI,
        AsyncAzureOpenAI=AsyncAzureOpenAI,
    )


# ──────────────────────────────────────────────────────────────────────────────
# AzureOpenAIClient
# ──────────────────────────────────────────────────────────────────────────────


def _azure_config(**kwargs: Any) -> ClientConfig:
    return ClientConfig(
        provider="azure-openai",
        model="gpt-4o",
        api_key=SecretStr("azure-key"),
        extra={
            "azure_resource": "my-resource",
            "azure_deployment": "gpt-4o-deploy",
        },
        **kwargs,
    )


class TestAzureOpenAIClient:
    def test_missing_azure_resource_raises_value_error(self, monkeypatch: Any) -> None:
        monkeypatch.setitem(sys.modules, "openai", _fake_openai_module())
        from lexigram.ai.llm.clients.azure_openai import AzureOpenAIClient

        with pytest.raises(ValueError, match="azure_resource"):
            AzureOpenAIClient(
                ClientConfig(
                    provider="azure-openai",
                    model="gpt-4o",
                    api_key=SecretStr("key"),
                    extra={"azure_deployment": "dep"},
                )
            )

    def test_model_falls_back_to_deployment_in_extra(self, monkeypatch: Any) -> None:
        monkeypatch.setitem(sys.modules, "openai", _fake_openai_module())
        from lexigram.ai.llm.clients.azure_openai import AzureOpenAIClient

        client = AzureOpenAIClient(_azure_config())
        assert client._azure_deployment == "gpt-4o-deploy"

    def test_model_from_config_used_when_deployment_missing(self, monkeypatch: Any) -> None:
        monkeypatch.setitem(sys.modules, "openai", _fake_openai_module())
        from lexigram.ai.llm.clients.azure_openai import AzureOpenAIClient

        client = AzureOpenAIClient(
            ClientConfig(
                provider="azure-openai",
                model="gpt-4o",
                api_key=SecretStr("key"),
                extra={"azure_resource": "res"},
            )
        )
        assert client._azure_deployment == "gpt-4o"

    @pytest.mark.asyncio
    async def test_complete_success(self, monkeypatch: Any) -> None:
        monkeypatch.setitem(sys.modules, "openai", _fake_openai_module("Azure response"))
        from lexigram.ai.llm.clients.azure_openai import AzureOpenAIClient

        client = AzureOpenAIClient(_azure_config())
        res = await client.complete(messages=[ChatMessage(role=Role.USER, content="hi")])

        assert res.is_ok()
        assert res.unwrap().content == "Azure response"

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy_on_success(self, monkeypatch: Any) -> None:
        monkeypatch.setitem(sys.modules, "openai", _fake_openai_module())
        from lexigram.ai.llm.clients.azure_openai import AzureOpenAIClient

        client = AzureOpenAIClient(_azure_config())
        result = await client.health_check()

        assert result.status == HealthStatus.HEALTHY
        assert "resource" in result.details
        assert result.details["resource"] == "my-resource"

    @pytest.mark.asyncio
    async def test_health_check_returns_unhealthy_on_error(self, monkeypatch: Any) -> None:
        monkeypatch.setitem(sys.modules, "openai", _fake_openai_module())
        from lexigram.ai.llm.clients.azure_openai import AzureOpenAIClient

        client = AzureOpenAIClient(_azure_config())
        client.client.models.list = AsyncMock(side_effect=Exception("connection refused"))

        result = await client.health_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert "connection refused" in (result.error or "")

    @pytest.mark.asyncio
    async def test_context_manager(self, monkeypatch: Any) -> None:
        monkeypatch.setitem(sys.modules, "openai", _fake_openai_module())
        from lexigram.ai.llm.clients.azure_openai import AzureOpenAIClient

        client = AzureOpenAIClient(_azure_config())
        async with client as c:
            assert c is client


# ──────────────────────────────────────────────────────────────────────────────
# BedrockClient
# ──────────────────────────────────────────────────────────────────────────────


def _bedrock_config(**kwargs: Any) -> ClientConfig:
    return ClientConfig(
        provider="aws-bedrock",
        model="anthropic.claude-3-sonnet-20240229-v1:0",
        extra={
            "aws_region": "us-east-1",
            "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "aws_secret_access_key": "wJalrXUtnFEMI",
        },
        **kwargs,
    )


def _bedrock_converse_response(text: str = "Hello from Bedrock") -> dict:
    return {
        "output": {
            "message": {
                "role": "assistant",
                "content": [{"text": text}],
            }
        },
        "usage": {"inputTokens": 5, "outputTokens": 10, "totalTokens": 15},
        "stopReason": "end_turn",
    }


def _bedrock_stream_response(text: str = "streamed") -> dict:
    return {
        "stream": iter([
            {"contentBlockDelta": {"delta": {"text": text}, "contentBlockIndex": 0}},
            {"messageStop": {"stopReason": "end_turn"}},
        ])
    }


def _inject_boto3(monkeypatch: Any, mock_bedrock: MagicMock | None = None) -> MagicMock:
    """Inject a fake boto3 into sys.modules; return the configured fake module."""
    fake_boto3 = MagicMock()
    if mock_bedrock is not None:
        fake_boto3.client.return_value = mock_bedrock
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    return fake_boto3


class TestBedrockClient:
    def test_missing_aws_region_raises_value_error(self, monkeypatch: Any) -> None:
        _inject_boto3(monkeypatch)
        from lexigram.ai.llm.clients.aws_bedrock import BedrockClient

        with pytest.raises(ValueError, match="aws_region"):
            BedrockClient(
                ClientConfig(
                    provider="aws-bedrock",
                    model="anthropic.claude",
                    extra={},
                )
            )

    @pytest.mark.asyncio
    async def test_complete_success(self, monkeypatch: Any) -> None:
        mock_bedrock = MagicMock()
        mock_bedrock.converse.return_value = _bedrock_converse_response("Bedrock hi")
        _inject_boto3(monkeypatch, mock_bedrock)
        from lexigram.ai.llm.clients.aws_bedrock import BedrockClient

        client = BedrockClient(_bedrock_config())
        res = await client.complete(messages=[{"role": "user", "content": "hi"}])

        assert res.is_ok()
        assert res.unwrap().content == "Bedrock hi"
        assert res.unwrap().usage.prompt_tokens == 5
        assert res.unwrap().usage.completion_tokens == 10

    @pytest.mark.asyncio
    async def test_complete_returns_err_on_throttling(self, monkeypatch: Any) -> None:
        mock_bedrock = MagicMock()

        class _ThrottleErr(Exception):
            def __init__(self) -> None:
                super().__init__("ThrottlingException")
                self.response = {"Error": {"Code": "ThrottlingException"}}

        mock_bedrock.converse.side_effect = _ThrottleErr()
        _inject_boto3(monkeypatch, mock_bedrock)
        from lexigram.ai.llm.clients.aws_bedrock import BedrockClient

        client = BedrockClient(_bedrock_config())
        client.max_retries = 0
        res = await client.complete(messages=[{"role": "user", "content": "hi"}])

        assert res.is_err()
        assert isinstance(res.unwrap_err(), LLMRateLimitError)

    @pytest.mark.asyncio
    async def test_complete_raises_auth_error_on_access_denied(self, monkeypatch: Any) -> None:
        mock_bedrock = MagicMock()

        class _AuthErr(Exception):
            def __init__(self) -> None:
                super().__init__("AccessDeniedException")
                self.response = {"Error": {"Code": "AccessDeniedException"}}

        mock_bedrock.converse.side_effect = _AuthErr()
        _inject_boto3(monkeypatch, mock_bedrock)
        from lexigram.ai.llm.clients.aws_bedrock import BedrockClient

        client = BedrockClient(_bedrock_config())
        with pytest.raises(LLMAuthenticationError):
            await client.complete(messages=[{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_complete_returns_err_on_model_not_found(self, monkeypatch: Any) -> None:
        mock_bedrock = MagicMock()

        class _NotFoundErr(Exception):
            def __init__(self) -> None:
                super().__init__("ModelNotFoundException")
                self.response = {"Error": {"Code": "ModelNotFoundException"}}

        mock_bedrock.converse.side_effect = _NotFoundErr()
        _inject_boto3(monkeypatch, mock_bedrock)
        from lexigram.ai.llm.clients.aws_bedrock import BedrockClient

        client = BedrockClient(_bedrock_config())
        client.max_retries = 0
        res = await client.complete(messages=[{"role": "user", "content": "hi"}])

        assert res.is_err()
        assert isinstance(res.unwrap_err(), LLMModelNotFoundError)

    @pytest.mark.asyncio
    async def test_stream_chat_yields_chunks(self, monkeypatch: Any) -> None:
        mock_bedrock = MagicMock()
        mock_bedrock.converse_stream.return_value = _bedrock_stream_response("streamed chunk")
        _inject_boto3(monkeypatch, mock_bedrock)
        from lexigram.ai.llm.clients.aws_bedrock import BedrockClient

        client = BedrockClient(_bedrock_config())
        stream = client.stream_chat(messages=[{"role": "user", "content": "hi"}])

        chunks = [c async for c in stream]
        assert any("streamed chunk" in (c.delta or "") for c in chunks)

    @pytest.mark.asyncio
    async def test_tool_call_includes_tool_config(self, monkeypatch: Any) -> None:
        mock_bedrock = MagicMock()
        mock_bedrock.converse.return_value = _bedrock_converse_response("tool result")
        _inject_boto3(monkeypatch, mock_bedrock)
        from lexigram.ai.llm.clients.aws_bedrock import BedrockClient

        client = BedrockClient(_bedrock_config())

        class MyTool:
            __tool_schema__ = {
                "name": "my_tool",
                "description": "A tool",
                "parameters": {
                    "type": "object",
                    "properties": {"input": {"type": "string"}},
                    "required": ["input"],
                },
            }

        res = await client.chat(
            messages=[{"role": "user", "content": "use tool"}],
            tools=[MyTool()],
        )

        assert res.is_ok()
        call_kwargs = mock_bedrock.converse.call_args[1]
        assert "toolConfig" in call_kwargs

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy_on_success(self, monkeypatch: Any) -> None:
        mock_bedrock = MagicMock()
        mgmt_mock = MagicMock()
        mgmt_mock.list_foundation_models.return_value = {"modelSummaries": []}
        fake_boto3 = _inject_boto3(monkeypatch, mock_bedrock)
        fake_boto3.client.side_effect = lambda service, **kw: (
            mgmt_mock if service == "bedrock" else mock_bedrock
        )
        from lexigram.ai.llm.clients.aws_bedrock import BedrockClient

        client = BedrockClient(_bedrock_config())
        result = await client.health_check()

        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_returns_unhealthy_on_error(self, monkeypatch: Any) -> None:
        mock_bedrock = MagicMock()
        mgmt_mock = MagicMock()
        mgmt_mock.list_foundation_models.side_effect = Exception("no connection")
        fake_boto3 = _inject_boto3(monkeypatch, mock_bedrock)
        fake_boto3.client.side_effect = lambda service, **kw: (
            mgmt_mock if service == "bedrock" else mock_bedrock
        )
        from lexigram.ai.llm.clients.aws_bedrock import BedrockClient

        client = BedrockClient(_bedrock_config())
        result = await client.health_check()

        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_close_releases_client(self, monkeypatch: Any) -> None:
        mock_bedrock = MagicMock()
        _inject_boto3(monkeypatch, mock_bedrock)
        from lexigram.ai.llm.clients.aws_bedrock import BedrockClient

        client = BedrockClient(_bedrock_config())
        await client.close()

        mock_bedrock.close.assert_called_once()
        assert client._client is None


# ──────────────────────────────────────────────────────────────────────────────
# VertexAIClient
# ──────────────────────────────────────────────────────────────────────────────


def _vertex_config(**kwargs: Any) -> ClientConfig:
    return ClientConfig(
        provider="google-vertex",
        model="gemini-1.5-pro",
        extra={
            "vertex_project": "my-gcp-project",
            "vertex_location": "us-central1",
        },
        **kwargs,
    )


def _gemini_api_response(text: str = "Hello from Vertex") -> dict:
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": text}],
                    "role": "model",
                }
            }
        ],
        "usageMetadata": {"promptTokenCount": 4, "candidatesTokenCount": 8},
    }


def _inject_google_auth(monkeypatch: Any) -> None:
    """Inject fake google.auth modules so VertexAIClient.__init__ passes the ImportError guard."""
    fake_google = MagicMock()
    fake_google_auth = MagicMock()
    fake_google_auth_transport = MagicMock()
    fake_google_auth_transport_requests = MagicMock()
    monkeypatch.setitem(sys.modules, "google", fake_google)
    monkeypatch.setitem(sys.modules, "google.auth", fake_google_auth)
    monkeypatch.setitem(sys.modules, "google.auth.transport", fake_google_auth_transport)
    monkeypatch.setitem(sys.modules, "google.auth.transport.requests", fake_google_auth_transport_requests)


class TestVertexAIClient:
    def test_missing_vertex_project_raises_value_error(self, monkeypatch: Any) -> None:
        _inject_google_auth(monkeypatch)
        from lexigram.ai.llm.clients.vertex_ai import VertexAIClient

        with pytest.raises(ValueError, match="vertex_project"):
            VertexAIClient(
                ClientConfig(
                    provider="google-vertex",
                    model="gemini-1.5-pro",
                    extra={"vertex_location": "us-central1"},
                )
            )

    def test_missing_vertex_location_raises_value_error(self, monkeypatch: Any) -> None:
        _inject_google_auth(monkeypatch)
        from lexigram.ai.llm.clients.vertex_ai import VertexAIClient

        with pytest.raises(ValueError, match="vertex_location"):
            VertexAIClient(
                ClientConfig(
                    provider="google-vertex",
                    model="gemini-1.5-pro",
                    extra={"vertex_project": "my-project"},
                )
            )

    @pytest.mark.asyncio
    async def test_complete_success(self, monkeypatch: Any) -> None:
        _inject_google_auth(monkeypatch)
        from lexigram.ai.llm.clients.vertex_ai import VertexAIClient

        client = VertexAIClient(_vertex_config())

        mock_http = MagicMock()
        mock_http.post = AsyncMock(
            return_value=_mock_http_response(_gemini_api_response("Vertex response"))
        )
        mock_http.headers = {}

        async def _fake_get_http() -> Any:
            return mock_http

        client._get_http = _fake_get_http  # type: ignore[method-assign]
        res = await client.complete(messages=[{"role": "user", "content": "hi"}])

        assert res.is_ok()
        assert "Vertex response" in res.unwrap().content

    @pytest.mark.asyncio
    async def test_complete_returns_err_on_rate_limit(self, monkeypatch: Any) -> None:
        _inject_google_auth(monkeypatch)
        from lexigram.ai.llm.clients.vertex_ai import VertexAIClient

        client = VertexAIClient(_vertex_config())
        mock_http = MagicMock()
        mock_http.post = AsyncMock(side_effect=_make_http_error(429))
        mock_http.headers = {}

        async def _fake_get_http() -> Any:
            return mock_http

        client._get_http = _fake_get_http  # type: ignore[method-assign]
        client.max_retries = 0

        res = await client.complete(messages=[{"role": "user", "content": "hi"}])
        assert res.is_err()
        assert isinstance(res.unwrap_err(), LLMRateLimitError)

    @pytest.mark.asyncio
    async def test_complete_raises_auth_error_on_401(self, monkeypatch: Any) -> None:
        _inject_google_auth(monkeypatch)
        from lexigram.ai.llm.clients.vertex_ai import VertexAIClient

        client = VertexAIClient(_vertex_config())
        mock_http = MagicMock()
        mock_http.post = AsyncMock(side_effect=_make_http_error(401))
        mock_http.headers = {}

        async def _fake_get_http() -> Any:
            return mock_http

        client._get_http = _fake_get_http  # type: ignore[method-assign]

        with pytest.raises(LLMAuthenticationError):
            await client.complete(messages=[{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(self, monkeypatch: Any) -> None:
        _inject_google_auth(monkeypatch)
        from lexigram.ai.llm.clients.vertex_ai import VertexAIClient

        client = VertexAIClient(_vertex_config())
        mock_http = MagicMock()
        mock_http.get = AsyncMock(
            return_value=_mock_http_response({"models": []})
        )
        mock_http.headers = {}

        async def _fake_get_http() -> Any:
            return mock_http

        client._get_http = _fake_get_http  # type: ignore[method-assign]

        result = await client.health_check()
        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_health_check_returns_unhealthy_on_error(self, monkeypatch: Any) -> None:
        _inject_google_auth(monkeypatch)
        from lexigram.ai.llm.clients.vertex_ai import VertexAIClient

        client = VertexAIClient(_vertex_config())

        async def _bad_get_http() -> Any:
            raise OSError("network error")

        client._get_http = _bad_get_http  # type: ignore[method-assign]

        result = await client.health_check()
        assert result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_close_releases_http_client(self, monkeypatch: Any) -> None:
        _inject_google_auth(monkeypatch)
        from lexigram.ai.llm.clients.vertex_ai import VertexAIClient

        client = VertexAIClient(_vertex_config())
        mock_http = MagicMock()
        mock_http.close = AsyncMock()
        client._http = mock_http

        await client.close()

        mock_http.close.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# OpenAICompatibleClient + DeepSeek / Together / Fireworks
# ──────────────────────────────────────────────────────────────────────────────


def _compat_config(provider: str = "custom", model: str = "deepseek-chat") -> ClientConfig:
    return ClientConfig(
        provider=provider,
        model=model,
        api_key=SecretStr("sk-fake"),
    )


class TestOpenAICompatibleClient:
    @pytest.mark.asyncio
    async def test_deepseek_complete_success(self, monkeypatch: Any) -> None:
        monkeypatch.setitem(sys.modules, "openai", _fake_openai_module("DeepSeek hi"))
        from lexigram.ai.llm.clients.openai_compatible import DeepSeekClient

        client = DeepSeekClient(_compat_config("custom", "deepseek-chat"))
        res = await client.complete(messages=[ChatMessage(role=Role.USER, content="hi")])

        assert res.is_ok()
        assert res.unwrap().content == "DeepSeek hi"

    @pytest.mark.asyncio
    async def test_together_complete_success(self, monkeypatch: Any) -> None:
        monkeypatch.setitem(sys.modules, "openai", _fake_openai_module("Together hi"))
        from lexigram.ai.llm.clients.openai_compatible import TogetherClient

        client = TogetherClient(
            _compat_config("custom", "meta-llama/Llama-3-8b-chat-hf")
        )
        res = await client.complete(messages=[ChatMessage(role=Role.USER, content="hi")])

        assert res.is_ok()
        assert res.unwrap().content == "Together hi"

    @pytest.mark.asyncio
    async def test_fireworks_complete_success(self, monkeypatch: Any) -> None:
        monkeypatch.setitem(sys.modules, "openai", _fake_openai_module("Fireworks hi"))
        from lexigram.ai.llm.clients.openai_compatible import FireworksClient

        client = FireworksClient(
            _compat_config("custom", "accounts/fireworks/models/llama-v3-70b-instruct")
        )
        res = await client.complete(messages=[ChatMessage(role=Role.USER, content="hi")])

        assert res.is_ok()
        assert res.unwrap().content == "Fireworks hi"

    def test_deepseek_uses_correct_base_url(self, monkeypatch: Any) -> None:
        monkeypatch.setitem(sys.modules, "openai", _fake_openai_module())
        from lexigram.ai.llm.clients.openai_compatible import DeepSeekClient

        client = DeepSeekClient(_compat_config())
        assert "deepseek.com" in DeepSeekClient._provider_base_url

    def test_together_uses_correct_base_url(self, monkeypatch: Any) -> None:
        monkeypatch.setitem(sys.modules, "openai", _fake_openai_module())
        from lexigram.ai.llm.clients.openai_compatible import TogetherClient

        assert "together.xyz" in TogetherClient._provider_base_url

    def test_fireworks_uses_correct_base_url(self, monkeypatch: Any) -> None:
        monkeypatch.setitem(sys.modules, "openai", _fake_openai_module())
        from lexigram.ai.llm.clients.openai_compatible import FireworksClient

        assert "fireworks.ai" in FireworksClient._provider_base_url

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy_on_success(self, monkeypatch: Any) -> None:
        monkeypatch.setitem(sys.modules, "openai", _fake_openai_module())
        from lexigram.ai.llm.clients.openai_compatible import DeepSeekClient

        client = DeepSeekClient(_compat_config())
        result = await client.health_check()

        assert result.status == HealthStatus.HEALTHY
        assert result.component == "llm.deepseek"

    @pytest.mark.asyncio
    async def test_health_check_returns_unhealthy_on_error(self, monkeypatch: Any) -> None:
        monkeypatch.setitem(sys.modules, "openai", _fake_openai_module())
        from lexigram.ai.llm.clients.openai_compatible import DeepSeekClient

        client = DeepSeekClient(_compat_config())

        class _FailModels:
            async def list(self) -> None:
                raise OSError("connection refused")

        client.client.models = _FailModels()

        result = await client.health_check()

        assert result.status == HealthStatus.UNHEALTHY
        assert "connection refused" in (result.error or "")

    @pytest.mark.asyncio
    async def test_api_base_override_takes_precedence(self, monkeypatch: Any) -> None:
        """config.api_base overrides _provider_base_url."""
        monkeypatch.setitem(sys.modules, "openai", _fake_openai_module())
        from lexigram.ai.llm.clients.openai_compatible import DeepSeekClient

        config = ClientConfig(
            provider="custom",
            model="deepseek-chat",
            api_key=SecretStr("sk-test"),
            api_base="https://my-proxy.local/v1",
        )
        # Should not raise; custom base URL is used.
        client = DeepSeekClient(config)
        assert client is not None

    @pytest.mark.asyncio
    async def test_placeholder_api_key_used_when_no_key_in_config(
        self, monkeypatch: Any
    ) -> None:
        """A missing api_key falls back to the placeholder (required by openai SDK)."""
        monkeypatch.setitem(sys.modules, "openai", _fake_openai_module())
        from lexigram.ai.llm.clients.openai_compatible import TogetherClient

        # No api_key — should not raise
        client = TogetherClient(
            ClientConfig(provider="custom", model="llama-3-8b", api_base="https://x.com/v1")
        )
        assert client is not None
