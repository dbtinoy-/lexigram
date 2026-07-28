"""Provider registry for LLM clients.

This module provides a registry for discovering and managing LLM providers,
making it easy to add custom providers and query available options.

Example:
    >>> from lexigram.ai.llm.registry.core import ProviderRegistry
    >>> from lexigram.di.container import Container
    >>>
    >>> # Resolve via the DI container (recommended)
    >>> container = Container()
    >>> registry = await container.resolve(ProviderRegistry)
    >>>
    >>> # Get built-in provider
    >>> info = registry.get_provider("openai")
    >>> print(f"Models: {info.default_models}")
    >>>
    >>> # Register custom provider
    >>> from my_package import CustomLLMClient
    >>> registry.register(
    ...     name="custom",
    ...     client_class=CustomLLMClient,
    ...     default_models=["custom-gpt-1"],
    ...     supports_streaming=True
    ... )

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from lexigram.contracts.ai import LLMClientProtocol
    from lexigram.contracts.ai.providers import ModelInfo
    from lexigram.contracts.ai.types import ModelCapability

from lexigram.logging import (
    get_logger,
)
from lexigram.primitives.registry import Registry

logger = get_logger(__name__)


__all__ = [
    "ProviderInfo",
    "ProviderRegistry",
]


@dataclass
class ProviderInfo:
    """Information about an LLM provider.

    Attributes:
        name: Provider identifier (e.g., "openai", "anthropic").
        client_class: LLMClientProtocol implementation class.
        default_models: List of default/recommended models.
        supports_streaming: Whether streaming is supported.
        supports_tools: Whether function/tool calling is supported.
        supports_vision: Whether vision/image inputs are supported.
        base_url: Default base URL for API (optional).
        docs_url: Documentation URL (optional).
        pricing_url: Pricing page URL (optional).
        description: Human-readable description.

    """

    name: str
    # Concrete provider implementations are stored as classes for metadata and
    # instantiation. Structural protocol conformance is enforced on instances.
    client_class: type[object]
    default_models: list[str] = field(default_factory=list)
    supports_streaming: bool = True
    supports_tools: bool = False
    supports_vision: bool = False
    base_url: str | None = None
    docs_url: str | None = None
    pricing_url: str | None = None
    description: str = ""


class ProviderRegistry(Registry[str, ProviderInfo]):
    """Registry for LLM providers.

    Singleton registry that maintains information about all available
    LLM providers, both built-in and custom.
    """

    def __init__(self) -> None:
        """Initialize provider registry."""
        if getattr(self, "_initialized", False):
            return
        super().__init__(name="providers")
        self._provider_clients: dict[str, LLMClientProtocol] = {}
        self._provider_models: dict[str, list[ModelInfo]] = {}
        self._initialize_builtin_providers()
        self._initialized = True

    @staticmethod
    def _validate_provider_name(name: str) -> None:
        """Validate a provider registry key."""
        if not name or " " in name or name != name.lower():
            msg = "Provider name must be lowercase with no spaces (e.g., 'my-provider')"
            raise ValueError(msg)

    def _initialize_builtin_providers(self) -> None:
        """Register built-in providers using per-provider lazy imports.

        Each client module is imported only when its block executes inside
        this method (which is called once at registry construction time).
        This keeps all SDK imports deferred away from the module top-level
        while still loading all providers eagerly enough to populate the
        registry catalogue — a good trade-off since the registry is a
        singleton that is only constructed when first requested.
        """
        # OpenAI
        from lexigram.ai.llm.clients.openai import OpenAIClient

        self._items["openai"] = ProviderInfo(
            name="openai",
            client_class=OpenAIClient,
            default_models=[
                "gpt-4-turbo",
                "gpt-4o",
                "gpt-4o-mini",
                "gpt-3.5-turbo",
            ],
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
            base_url="https://api.openai.com/v1",
            docs_url="https://platform.openai.com/docs",
            pricing_url="https://openai.com/pricing",
            description="OpenAI GPT models - industry standard for general purpose AI",
        )

        # Anthropic (Claude)
        from lexigram.ai.llm.clients.anthropic import AnthropicClient

        self._items["anthropic"] = ProviderInfo(
            name="anthropic",
            client_class=AnthropicClient,
            default_models=[
                "claude-3-5-sonnet-20241022",
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
            ],
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
            base_url="https://api.anthropic.com",
            docs_url="https://docs.anthropic.com",
            pricing_url="https://www.anthropic.com/pricing",
            description="Anthropic Claude - strong reasoning and long context (200k tokens)",
        )

        # Groq
        from lexigram.ai.llm.clients.groq import GroqClient

        self._items["groq"] = ProviderInfo(
            name="groq",
            client_class=GroqClient,
            default_models=[
                "llama-3.1-70b-versatile",
                "llama-3.1-8b-instant",
                "mixtral-8x7b-32768",
            ],
            supports_streaming=True,
            supports_tools=True,
            supports_vision=False,
            base_url="https://api.groq.com/openai/v1",
            docs_url="https://console.groq.com/docs",
            pricing_url="https://groq.com/pricing",
            description="Groq - ultra-fast inference with LPU hardware (100+ tokens/sec, currently free)",
        )

        # Mistral
        from lexigram.ai.llm.clients.mistral import MistralClient

        self._items["mistral"] = ProviderInfo(
            name="mistral",
            client_class=MistralClient,
            default_models=[
                "mistral-large-latest",
                "mistral-medium-latest",
                "mistral-small-latest",
                "open-mixtral-8x7b",
            ],
            supports_streaming=True,
            supports_tools=True,
            supports_vision=False,
            base_url="https://api.mistral.ai/v1",
            docs_url="https://docs.mistral.ai",
            pricing_url="https://mistral.ai/technology/#pricing",
            description="Mistral AI - GDPR-compliant EU provider with strong multilingual support",
        )

        # Cohere
        from lexigram.ai.llm.clients.cohere import CohereClient

        self._items["cohere"] = ProviderInfo(
            name="cohere",
            client_class=CohereClient,
            default_models=[
                "command-r-plus",
                "command-r",
                "command",
                "embed-english-v3.0",
            ],
            supports_streaming=True,
            supports_tools=True,
            supports_vision=False,
            base_url="https://api.cohere.ai/v1",
            docs_url="https://docs.cohere.com",
            pricing_url="https://cohere.com/pricing",
            description="Cohere - best-in-class embeddings, reranking, and RAG-optimized models",
        )

        # Ollama
        from lexigram.ai.llm.clients.ollama import OllamaClient

        self._items["ollama"] = ProviderInfo(
            name="ollama",
            client_class=OllamaClient,
            default_models=[
                "llama3:8b",
                "llama3:70b",
                "mistral:7b",
                "codellama:13b",
            ],
            supports_streaming=True,
            supports_tools=False,
            supports_vision=False,
            base_url="http://localhost:11434",
            docs_url="https://ollama.ai/docs",
            pricing_url=None,
            description="Ollama - run LLMs locally with zero API costs and full privacy",
        )

        # OpenRouter
        from lexigram.ai.llm.clients.openrouter import OpenRouterClient

        self.register(
            name="openrouter",
            client_class=OpenRouterClient,
            default_models=["gpt-4o", "gpt-4o-mini"],
            supports_streaming=True,
            supports_tools=True,
            supports_vision=False,
            base_url="https://api.openrouter.ai/v1",
            docs_url="https://docs.openrouter.ai",
            pricing_url=None,
            description="OpenRouter - open and compatible routing layer for many models",
        )

        # Gemini
        from lexigram.ai.llm.clients.gemini import GeminiClient

        self._items["gemini"] = ProviderInfo(
            name="gemini",
            client_class=GeminiClient,
            default_models=[
                "gemini-2.5-flash",
                "gemini-2.0-flash",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
            ],
            supports_streaming=False,
            supports_tools=False,
            supports_vision=True,
            base_url="https://generativelanguage.googleapis.com",
            docs_url="https://ai.google.dev/docs",
            pricing_url="https://ai.google.dev/pricing",
            description="Google Gemini — multimodal models with vision and long context; free tier available",
        )

        # Cloudflare Workers AI
        from lexigram.ai.llm.clients.cloudflare_workers import CloudflareWorkersClient

        self._items["cloudflare"] = ProviderInfo(
            name="cloudflare",
            client_class=CloudflareWorkersClient,
            default_models=[
                "@cf/meta/llama-3.2-11b-vision-instruct",
                "@cf/meta/llama-3.1-8b-instruct",
                "@cf/mistral/mistral-7b-instruct-v0.2",
            ],
            supports_streaming=False,
            supports_tools=False,
            supports_vision=True,
            base_url="https://api.cloudflare.com",
            docs_url="https://developers.cloudflare.com/workers-ai",
            pricing_url="https://developers.cloudflare.com/workers-ai/platform/pricing/",
            description="Cloudflare Workers AI — serverless inference with vision models; free tier available",
        )

        # Azure OpenAI
        from lexigram.ai.llm.clients.azure_openai import AzureOpenAIClient

        self.register(
            name="azure-openai",
            client_class=AzureOpenAIClient,
            default_models=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
            base_url="https://{resource}.openai.azure.com/openai",
            docs_url="https://learn.microsoft.com/azure/ai-services/openai/",
            pricing_url="https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/",
            description="Azure OpenAI — enterprise OpenAI deployment with Azure identity and networking controls",
        )

        # AWS Bedrock
        from lexigram.ai.llm.clients.aws_bedrock import BedrockClient

        self.register(
            name="aws-bedrock",
            client_class=BedrockClient,
            default_models=[
                "anthropic.claude-3-5-sonnet-20240620-v1:0",
                "meta.llama3-70b-instruct-v1:0",
                "amazon.titan-text-express-v1",
            ],
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
            base_url="https://bedrock-runtime.{region}.amazonaws.com",
            docs_url="https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html",
            pricing_url="https://aws.amazon.com/bedrock/pricing/",
            description="AWS Bedrock — managed foundation model platform with native AWS IAM and enterprise controls",
        )

        # Google Vertex AI
        from lexigram.ai.llm.clients.vertex_ai import VertexAIClient

        self.register(
            name="google-vertex",
            client_class=VertexAIClient,
            default_models=["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
            supports_streaming=True,
            supports_tools=True,
            supports_vision=True,
            base_url="https://{region}-aiplatform.googleapis.com",
            docs_url="https://cloud.google.com/vertex-ai/docs/generative-ai/",
            pricing_url="https://cloud.google.com/vertex-ai/pricing",
            description="Google Vertex AI — enterprise Gemini deployment with GCP IAM and regional controls",
        )

        # OpenAI-compatible providers
        from lexigram.ai.llm.clients.openai_compatible import (
            DeepSeekClient,
            FireworksClient,
            TogetherClient,
        )

        self.register(
            name="deepseek",
            client_class=DeepSeekClient,
            default_models=["deepseek-chat", "deepseek-coder"],
            supports_streaming=True,
            supports_tools=True,
            supports_vision=False,
            base_url="https://api.deepseek.com/v1",
            docs_url="https://api-docs.deepseek.com",
            pricing_url="https://www.deepseek.com/",
            description="DeepSeek — cost-efficient OpenAI-compatible inference provider",
        )

        self.register(
            name="together",
            client_class=TogetherClient,
            default_models=[
                "meta-llama/Llama-3-8b-chat-hf",
                "mistralai/Mixtral-8x7B-Instruct-v0.1",
            ],
            supports_streaming=True,
            supports_tools=True,
            supports_vision=False,
            base_url="https://api.together.xyz/v1",
            docs_url="https://docs.together.ai",
            pricing_url="https://www.together.ai/pricing",
            description="Together AI — OpenAI-compatible serving for open-source and fine-tuned models",
        )

        self.register(
            name="fireworks",
            client_class=FireworksClient,
            default_models=[
                "accounts/fireworks/models/llama-v3-70b-instruct",
                "accounts/fireworks/models/mixtral-8x7b-instruct",
            ],
            supports_streaming=True,
            supports_tools=True,
            supports_vision=False,
            base_url="https://api.fireworks.ai/inference/v1",
            docs_url="https://docs.fireworks.ai",
            pricing_url="https://fireworks.ai/pricing",
            description="Fireworks AI — optimized OpenAI-compatible inference platform",
        )

        logger.info("Initialized %d built-in providers", len(self))

    def register(  # type: ignore[override]
        self,
        name: str,
        client_class: type[object],
        default_models: list[str] | None = None,
        supports_streaming: bool = True,
        supports_tools: bool = False,
        supports_vision: bool = False,
        base_url: str | None = None,
        docs_url: str | None = None,
        pricing_url: str | None = None,
        description: str = "",
    ) -> ProviderInfo:
        """Register a new LLM provider."""
        self._validate_provider_name(name)

        info = ProviderInfo(
            name=name,
            client_class=client_class,
            default_models=default_models or [],
            supports_streaming=supports_streaming,
            supports_tools=supports_tools,
            supports_vision=supports_vision,
            base_url=base_url,
            docs_url=docs_url,
            pricing_url=pricing_url,
            description=description,
        )
        return cast("ProviderInfo", super().register(name, info))

    def get_provider(self, name: str) -> ProviderInfo:
        """Get provider information."""
        info = super().get(name)
        if info is None:
            available = ", ".join(self.list_providers())
            msg = f"Provider '{name}' not found. Available providers: {available}"
            raise KeyError(msg)

        return info

    def list_providers(self) -> list[str]:
        """List all registered provider names."""
        return sorted(super().keys())

    def search_providers(
        self,
        supports_streaming: bool | None = None,
        supports_tools: bool | None = None,
        supports_vision: bool | None = None,
    ) -> list[ProviderInfo]:
        """Search providers by capabilities."""
        results = []

        for info in self.values():
            if (
                supports_streaming is not None
                and info.supports_streaming != supports_streaming
            ):
                continue
            if supports_tools is not None and info.supports_tools != supports_tools:
                continue
            if supports_vision is not None and info.supports_vision != supports_vision:
                continue

            results.append(info)

        return results

    def unregister(self, name: str) -> None:
        """Unregister a provider."""
        self._provider_clients.pop(name, None)
        self._provider_models.pop(name, None)
        if super().unregister(name) is None:
            msg = f"Provider '{name}' not found"
            raise KeyError(msg)

    # --- Protocol Implementation ---

    async def register_provider(
        self, name: str, client: LLMClientProtocol, models: list[ModelInfo]
    ) -> None:
        """Register a provider following the ProviderRegistryProtocol."""
        from lexigram.contracts.ai.types import ModelCapability

        self._validate_provider_name(name)

        existing = super().get(name)
        supports_streaming = (
            any(ModelCapability.STREAMING in model.capabilities for model in models)
            if models
            else (existing.supports_streaming if existing is not None else True)
        )
        supports_tools = (
            any(
                ModelCapability.FUNCTION_CALLING in model.capabilities
                for model in models
            )
            if models
            else (existing.supports_tools if existing is not None else False)
        )
        supports_vision = (
            any(ModelCapability.VISION in model.capabilities for model in models)
            if models
            else (existing.supports_vision if existing is not None else False)
        )

        info = ProviderInfo(
            name=name,
            client_class=type(client),
            default_models=(
                [model.model_id for model in models]
                if models
                else (list(existing.default_models) if existing is not None else [])
            ),
            supports_streaming=supports_streaming,
            supports_tools=supports_tools,
            supports_vision=supports_vision,
            base_url=existing.base_url if existing is not None else None,
            docs_url=existing.docs_url if existing is not None else None,
            pricing_url=existing.pricing_url if existing is not None else None,
            description=existing.description if existing is not None else "",
        )
        super().register(name, info, allow_overwrite=True)
        self._provider_clients[name] = client
        if models:
            self._provider_models[name] = list(models)

    async def get_client(self, provider: str) -> LLMClientProtocol | None:
        """Get an initialized client for a provider."""
        return self._provider_clients.get(provider)

    def list_models(
        self, capabilities: set[ModelCapability] | None = None
    ) -> list[ModelInfo]:
        """List all models matching capabilities."""
        from lexigram.contracts.ai.providers import ModelInfo
        from lexigram.contracts.ai.types import ModelCapability

        models: list[ModelInfo] = []
        for provider_info in self.values():
            registered_models = self._provider_models.get(provider_info.name)
            if registered_models is not None:
                provider_models = registered_models
            else:
                provider_capabilities = {ModelCapability.CHAT}
                if provider_info.supports_streaming:
                    provider_capabilities.add(ModelCapability.STREAMING)
                if provider_info.supports_tools:
                    provider_capabilities.add(ModelCapability.FUNCTION_CALLING)
                if provider_info.supports_vision:
                    provider_capabilities.add(ModelCapability.VISION)
                provider_models = [
                    ModelInfo(
                        model_id=model_id,
                        provider=provider_info.name,
                        display_name=model_id,
                        capabilities=frozenset(provider_capabilities),
                        context_window=8192,
                        max_output_tokens=4096,
                        input_cost_per_million=0,
                        output_cost_per_million=0,
                    )
                    for model_id in provider_info.default_models
                ]

            for model in provider_models:
                if capabilities is not None and not capabilities.issubset(
                    model.capabilities
                ):
                    continue
                models.append(model)
        return models

    def get_model_info(self, model_id: str) -> ModelInfo | None:
        """Get information about a specific model."""
        models = self.list_models()
        return next((m for m in models if m.model_id == model_id), None)
