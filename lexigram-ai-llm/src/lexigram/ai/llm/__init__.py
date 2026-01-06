"""LLM module exports."""

from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING, Any

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from lexigram.ai.llm.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.ai.llm.caching.core import (
        CacheEntry,
        CacheStats,
        LLMCache,
        RedisLLMCache,
    )
    from lexigram.ai.llm.clients.anthropic import AnthropicClient
    from lexigram.ai.llm.clients.cohere import CohereClient
    from lexigram.ai.llm.clients.groq import GroqClient
    from lexigram.ai.llm.clients.mistral import MistralClient
    from lexigram.ai.llm.clients.ollama import OllamaClient
    from lexigram.ai.llm.clients.openai import OpenAIClient
    from lexigram.ai.llm.clients.openrouter import OpenRouterClient
    from lexigram.ai.llm.config import ClientConfig
    from lexigram.ai.llm.conversation.manager import (
        ConversationConfig,
        ConversationManager,
        ConversationStats,
    )
    from lexigram.ai.llm.events import LLMCompletionEvent
    from lexigram.ai.llm.extraction.extractor import InstructorExtractor
    from lexigram.ai.llm.hooks import (
        LLMProviderRegisteredHook,
        LLMRequestSentHook,
        LLMResponseReceivedHook,
    )
from lexigram.ai.llm.pricing import (
    AbstractPricingSource,
    JSONFilePricingSource,
    StaticPricingSource,
)
from lexigram.ai.llm.pricing.registry import TokenCounterRegistry
from lexigram.ai.llm.protocols import LLMCacheProtocol
from lexigram.ai.llm.rate_limiting.core import RateLimiter
from lexigram.ai.llm.registry.core import ProviderInfo, ProviderRegistry
from lexigram.ai.llm.routing.config import (
    GenerationDefaults,
    LLMConfig,
    LogConfig,
    ProviderConfig,
    QuotaConfig,
)
from lexigram.ai.llm.security.core import (
    OutputFilter,
    SecureLLMClient,
    SecurePromptTemplate,
    create_assistant_template,
    create_data_extraction_template,
)
from lexigram.ai.llm.selection.core import (
    ModelCapabilities,
    ModelSelector,
    SelectionCriteria,
    SelectionStrategy,
    create_balanced_selector,
    create_cost_optimized_selector,
    create_quality_optimized_selector,
)
from lexigram.ai.llm.structured.exceptions import (
    ParseError,
    SchemaValidationError,
    StructuredOutputError,
)
from lexigram.ai.llm.structured.extractor import JSONExtractor
from lexigram.ai.llm.structured.formatter import ResponseFormatter
from lexigram.ai.llm.structured.parser import StructuredOutputParser
from lexigram.ai.llm.structured.utils import (
    complete_with_json,
    complete_with_schema,
    create_json_mode_messages,
)
from lexigram.ai.llm.types import (
    ChatMessage,
    Completion,
    FunctionCall,
    LLMError,
    Role,
    StreamChunk,
    TokenUsage,
    ToolCall,
)
from lexigram.contracts.ai.multimodal import (
    ContentPart,
    ImageBase64Part,
    ImageUrlPart,
    MessageContent,
    TextPart,
)

_LAZY_IMPORTS: dict[str, str] = {
    "normalize_thinking_text": "lexigram.ai.llm.thinking",
    # Events
    "LLMCompletionEvent": "lexigram.ai.llm.events",
    # Hooks
    "LLMProviderRegisteredHook": "lexigram.ai.llm.hooks",
    "LLMRequestSentHook": "lexigram.ai.llm.hooks",
    "LLMResponseReceivedHook": "lexigram.ai.llm.hooks",
    # Types
    "AnthropicClient": "lexigram.ai.llm.clients.anthropic",
    "APIPricingSource": "lexigram.ai.llm.pricing",
    "CacheEntry": "lexigram.ai.llm.caching.core",
    "CacheStats": "lexigram.ai.llm.caching.core",
    "ChatMessage": "lexigram.ai.llm.types",
    "ContentPart": "lexigram.contracts.ai.multimodal",
    # Config
    "ClientConfig": "lexigram.ai.llm.config",
    "CohereClient": "lexigram.ai.llm.clients.cohere",
    "Completion": "lexigram.ai.llm.types",
    "ConversationConfig": "lexigram.ai.llm.conversation.manager",
    "ConversationManager": "lexigram.ai.llm.conversation.manager",
    "ConversationStats": "lexigram.ai.llm.conversation.manager",
    "CostEstimate": "lexigram.ai.llm.pricing.tokens",
    "FunctionCall": "lexigram.ai.llm.types",
    "GenerationDefaults": "lexigram.ai.llm.routing.config",
    "GroqClient": "lexigram.ai.llm.clients.groq",
    "ImageBase64Part": "lexigram.contracts.ai.multimodal",
    "ImageUrlPart": "lexigram.contracts.ai.multimodal",
    "InstructorExtractor": "lexigram.ai.llm.extraction.extractor",
    "JSONExtractor": "lexigram.ai.llm.structured.extractor",
    "JSONFilePricingSource": "lexigram.ai.llm.pricing",
    "LLMCache": "lexigram.ai.llm.caching.core",
    "LLMCacheProtocol": "lexigram.ai.llm.protocols",
    "LLMConfig": "lexigram.ai.llm.routing.config",
    "LogConfig": "lexigram.ai.llm.routing.config",
    "LLMError": "lexigram.ai.llm.types",
    "LLMAuthenticationError": "lexigram.ai.llm.exceptions",
    "LLMContentFilterError": "lexigram.ai.llm.exceptions",
    "LLMModelNotFoundError": "lexigram.ai.llm.exceptions",
    "ModelRevisionMismatchError": "lexigram.ai.llm.exceptions",
    "LLMQuotaExceededError": "lexigram.ai.llm.exceptions",
    "LLMRateLimitError": "lexigram.ai.llm.exceptions",
    "InvalidRequestError": "lexigram.ai.llm.exceptions",
    "ModelNotFoundError": "lexigram.ai.llm.exceptions",
    "ProviderConnectionError": "lexigram.ai.llm.exceptions",
    "StreamError": "lexigram.ai.llm.exceptions",
    "TokenLimitError": "lexigram.ai.llm.exceptions",
    "ExtractionError": "lexigram.ai.llm.exceptions",
    "ExtractionParseError": "lexigram.ai.llm.exceptions",
    "ExtractionValidationError": "lexigram.ai.llm.exceptions",
    "ExtractionMaxRetriesError": "lexigram.ai.llm.exceptions",
    "MessageContent": "lexigram.contracts.ai.multimodal",
    "MistralClient": "lexigram.ai.llm.clients.mistral",
    "ModelCapabilities": "lexigram.ai.llm.selection.core",
    "ModelPricing": "lexigram.ai.llm.pricing",
    "ModelSelector": "lexigram.ai.llm.selection.core",
    "OllamaClient": "lexigram.ai.llm.clients.ollama",
    "OpenAIClient": "lexigram.ai.llm.clients.openai",
    "OpenRouterClient": "lexigram.ai.llm.clients.openrouter",
    "OutputFilter": "lexigram.ai.llm.security.core",
    "ParseError": "lexigram.ai.llm.structured.exceptions",
    "PricingManager": "lexigram.ai.llm.pricing",
    "PricingManagerBuilder": "lexigram.ai.llm.pricing",
    "AbstractPricingSource": "lexigram.ai.llm.pricing",
    "ProviderConfig": "lexigram.ai.llm.routing.config",
    # Pinning
    "ModelPinPolicy": "lexigram.ai.llm.pinning",
    "enforce_pin_policy": "lexigram.ai.llm.pinning",
    # Audit
    "LLMAuditBridge": "lexigram.ai.llm.audit_bridge",
    # Parsers
    "ParserRegistry": "lexigram.ai.llm.parsers.registry",
    "JSONOutputParser": "lexigram.ai.llm.parsers.json",
    "PydanticOutputParser": "lexigram.ai.llm.parsers.pydantic",
    "EnumOutputParser": "lexigram.ai.llm.parsers.enum",
    "CSVOutputParser": "lexigram.ai.llm.parsers.csv",
    "FormatFixingParser": "lexigram.ai.llm.parsers.fixing",
    "ProviderInfo": "lexigram.ai.llm.registry.core",
    "ProviderRegistry": "lexigram.ai.llm.registry.core",
    "QuotaConfig": "lexigram.ai.llm.routing.config",
    "RateLimiter": "lexigram.ai.llm.rate_limiting.core",
    "RedisLLMCache": "lexigram.ai.llm.caching.core",
    "ResponseFormatter": "lexigram.ai.llm.structured.formatter",
    "Role": "lexigram.ai.llm.types",
    "SchemaValidationError": "lexigram.ai.llm.structured.exceptions",
    "SecureLLMClient": "lexigram.ai.llm.security.core",
    "SecurePromptTemplate": "lexigram.ai.llm.security.core",
    "SelectionCriteria": "lexigram.ai.llm.selection.core",
    "SelectionStrategy": "lexigram.ai.llm.selection.core",
    "StaticPricingSource": "lexigram.ai.llm.pricing",
    "StreamChunk": "lexigram.ai.llm.types",
    "StructuredOutputError": "lexigram.ai.llm.structured.exceptions",
    "StructuredOutputParser": "lexigram.ai.llm.structured.parser",
    "TextPart": "lexigram.contracts.ai.multimodal",
    "TokenCount": "lexigram.ai.llm.pricing.tokens",
    "TiktokenCounter": "lexigram.ai.llm.pricing.tokens",
    "CharEstimateCounter": "lexigram.ai.llm.pricing.tokens",
    "HuggingFaceCounter": "lexigram.ai.llm.pricing.tokens",
    "MistralCounter": "lexigram.ai.llm.pricing.tokens",
    "TokenCounterRegistry": "lexigram.ai.llm.pricing.registry",
    "TokenUsage": "lexigram.ai.llm.types",
    "ToolCall": "lexigram.ai.llm.types",
    "complete_with_json": "lexigram.ai.llm.structured.utils",
    "complete_with_schema": "lexigram.ai.llm.structured.utils",
    "create_assistant_template": "lexigram.ai.llm.security.core",
    "create_balanced_selector": "lexigram.ai.llm.selection.core",
    "create_cost_optimized_selector": "lexigram.ai.llm.selection.core",
    "create_data_extraction_template": "lexigram.ai.llm.security.core",
    "create_json_mode_messages": "lexigram.ai.llm.structured.utils",
    "create_quality_optimized_selector": "lexigram.ai.llm.selection.core",
    "create_token_counter": "lexigram.ai.llm.pricing.tokens",
    # DI
    "LLMModule": "lexigram.ai.llm.module",
    "LLMProvider": "lexigram.ai.llm.di.provider",
    "LLMRoutingProvider": "lexigram.ai.llm.di.routing_provider",
    # Runnable composition
    "RunnableBranch": "lexigram.ai.llm.runnable",
    "RunnableLambda": "lexigram.ai.llm.runnable",
    "RunnableMixin": "lexigram.ai.llm.runnable",
    "RunnableParallel": "lexigram.ai.llm.runnable",
    "RunnablePassthrough": "lexigram.ai.llm.runnable",
    "RunnableSequence": "lexigram.ai.llm.runnable",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib as _importlib

        module = _importlib.import_module(_LAZY_IMPORTS[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = list(_LAZY_IMPORTS.keys())
