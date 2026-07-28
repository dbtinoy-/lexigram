from __future__ import annotations

import importlib

import pytest

EXPECTED_MODULE_EXPORTS: dict[str, list[str]] = {
    "lexigram.contracts.ai.memory": [
        "ConsolidationError",
        "ConsolidationResult",
        "ConversationMemory",
        "EpisodicMemoryProtocol",
        "MemoryConsolidatorProtocol",
        "MemoryEntry",
        "MemoryProtocol",
        "MemoryQuery",
        "MemorySearchResult",
        "MemoryStoreProtocol",
        "SemanticMemoryProtocol",
        "StorageError",
        "WindowMemory",
        "WorkingMemoryProtocol",
    ],
    "lexigram.contracts.ai.models": ["ModelRequest", "ModelResponse"],
    "lexigram.contracts.ai.multimodal": [
        "ContentPart",
        "ImageBase64Part",
        "ImageUrlPart",
        "MessageContent",
        "TextPart",
    ],
    "lexigram.contracts.ai.providers": [
        "FallbackChainProtocol",
        "ModelInfo",
        "ModelSelectorProtocol",
        "ProviderHealth",
        "ProviderRegistryProtocol",
        "SelectionStrategy",
    ],
    "lexigram.contracts.ai.skills": [
        "SkillDefinition",
        "SkillError",
        "SkillExecutorProtocol",
        "SkillParameter",
        "SkillProtocol",
        "SkillRegistryProtocol",
        "SkillResult",
        "ToolkitProtocol",
    ],
    "lexigram.contracts.auth.guard": [
        "AuthenticatorProtocol",
        "AuthorizerProtocol",
    ],
    "lexigram.contracts.auth.store": [
        "UserReaderProtocol",
        "UserStoreProtocol",
        "UserWriterProtocol",
    ],
    "lexigram.contracts.cli.protocols": ["CliContributorProtocol"],
    "lexigram.contracts.cli.types": ["GeneratorDefinition", "GeneratorOption"],
    "lexigram.contracts.feature_flags.protocols": [
        "FlagManagerProtocol",
        "FlagProviderProtocol",
        "MutableFlagProviderProtocol",
    ],
    "lexigram.contracts.mcp.exceptions": [
        "MCPError",
        "MCPInitializationError",
        "MCPMethodNotFoundError",
        "MCPPromptError",
        "MCPProtocolError",
        "MCPResourceError",
        "MCPToolCallError",
        "MCPTransportError",
    ],
    "lexigram.contracts.mcp.protocols": [
        "MCPPromptHandlerProtocol",
        "MCPPromptProviderProtocol",
        "MCPResourceHandlerProtocol",
        "MCPResourceProviderProtocol",
        "MCPServerProtocol",
        "MCPToolHandlerProtocol",
        "MCPToolProviderProtocol",
        "MCPTransportProtocol",
    ],
    "lexigram.contracts.search.models": [
        "DocumentData",
        "IndexSettings",
        "SearchFilters",
    ],
    "lexigram.contracts.search.types": [
        "DocumentData",
        "IndexSettings",
        "SearchFilters",
        "SearchIndexResult",
    ],
}


@pytest.mark.parametrize(
    ("module_path", "expected_exports"),
    EXPECTED_MODULE_EXPORTS.items(),
)
def test_module_declares_explicit_all(
    module_path: str,
    expected_exports: list[str],
) -> None:
    module = importlib.import_module(module_path)
    exported = getattr(module, "__all__", None)

    assert isinstance(exported, list)
    assert exported == expected_exports
    for name in exported:
        assert not name.startswith("_")
        assert hasattr(module, name)
