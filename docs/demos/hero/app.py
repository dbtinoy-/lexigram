"""
╔══════════════════════════════════════════════════════════╗
║  Lexigram — The Python framework that gives your        ║
║  AI a pattern to follow.                                ║
╚══════════════════════════════════════════════════════════╝

This demo shows the progression from raw API calls to
the full power of Lexigram's contract-based, DI-driven
AI framework.
"""

import asyncio
import os
from dataclasses import dataclass

# Suppress framework logging BEFORE any Lexigram imports
import structlog

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        structlog.stdlib.logging.ERROR,
    ),
)
os.environ.setdefault("LEX_LOGGING__LEVEL", "ERROR")
os.environ.setdefault("LEX_QUIET", "1")


# ═══════════════════════════════════════════════════════════
# STAGE 1: Raw Ollama — the manual way
# ═══════════════════════════════════════════════════════════
# Direct HTTP to Ollama via the `ollama` package.
# Dict access, no types, no DI, fragile error handling.

async def stage1_raw_ollama():
    import ollama

    client = ollama.AsyncClient(host="http://localhost:11434")
    messages = [{"role": "user", "content": "Explain the Result pattern in 1 sentence."}]
    resp = await client.chat(model="gemma4:12b", messages=messages)
    print(f"  {resp['message']['content']}")


# ═══════════════════════════════════════════════════════════
# STAGE 2: Enter Lexigram
# ═══════════════════════════════════════════════════════════
# Application.boot() + LLMModule — DI, protocols, Result[T,E].
# Same LLM call, now clean, testable, provider-agnostic.

from lexigram import Application
from lexigram.ai.llm import LLMModule, ClientConfig
from lexigram.ai.llm.structured import StructuredExtractor
from lexigram.contracts.ai import LLMClientProtocol, ChatMessage, Role


async def stage2_lexigram_llm():
    async with Application.boot(modules=[
        LLMModule.configure(ClientConfig(
            provider="ollama", model="gemma4:12b",
        ))
    ]) as app:
        llm = await app._container.resolve(LLMClientProtocol)
        result = await llm.complete([
            ChatMessage(role=Role.USER, content="Explain the Result pattern in 1 sentence."),
        ])
        print(f"  {result.unwrap().content}")


# ═══════════════════════════════════════════════════════════
# STAGE 3: Structured Output
# ═══════════════════════════════════════════════════════════
# Typed extraction — dataclasses from the LLM, validated.
# No string parsing, no fragile regex.

@dataclass
class Explanation:
    concept: str
    summary: str
    benefit: str


async def stage3_structured():
    async with Application.boot(modules=[
        LLMModule.configure(ClientConfig(
            provider="ollama", model="gemma4:12b",
        ))
    ]) as app:
        llm = await app._container.resolve(LLMClientProtocol)
        extractor = StructuredExtractor(llm)
        result = await extractor.extract(
            "Explain the Result pattern.",
            Explanation,
        )
        if result.is_ok():
            ex = result.unwrap()
            print(f"  Concept: {ex.concept}")
            print(f"  Summary: {ex.summary}")
            print(f"  Benefit: {ex.benefit}")
        else:
            print(f"  Extraction failed: {result.unwrap_err()}")


# ═══════════════════════════════════════════════════════════
# STAGE 4: Streaming — real-time token output
# ═══════════════════════════════════════════════════════════
# stream_chat() returns AsyncStream — tokens as they arrive.
# No waiting for the full response.

async def stage4_streaming():
    async with Application.boot(modules=[
        LLMModule.configure(ClientConfig(
            provider="ollama", model="gemma4:12b",
        ))
    ]) as app:
        llm = await app._container.resolve(LLMClientProtocol)
        stream = llm.stream_chat([
            ChatMessage(role=Role.USER, content="Explain the Result pattern in 1 sentence."),
        ])
        async for chunk in stream:
            if chunk.delta:
                print(chunk.delta, end="", flush=True)
        print()


# ═══════════════════════════════════════════════════════════
# STAGE 5: Provider Flexibility
# ═══════════════════════════════════════════════════════════
# Swap providers with one env var. Same code, 15 built-in providers.

AVAILABLE_PROVIDERS = [
    "ollama", "openai", "anthropic", "groq", "cohere",
    "mistral", "deepseek", "gemini", "fireworks", "together",
    "openrouter", "azure-openai", "aws-bedrock", "cloudflare",
    "google-vertex",
]


async def stage5_flexibility():
    provider = os.environ.get("LLM_PROVIDER", "ollama")
    async with Application.boot(modules=[
        LLMModule.configure(ClientConfig(
            provider=provider, model="gemma4:12b",
        ))
    ]) as app:
        llm = await app._container.resolve(LLMClientProtocol)
        result = await llm.complete([
            ChatMessage(role=Role.USER, content="Explain the Result pattern in 1 sentence."),
        ])
        print(f"  [{provider}] {result.unwrap().content}")


# ═══════════════════════════════════════════════════════════
# RUNNABLE DEMO
# ═══════════════════════════════════════════════════════════

async def main():
    print()
    print("  ── STAGE 1: Raw Ollama ── manual API call")
    print("  ───────────────────────────────────────────")
    await stage1_raw_ollama()
    print()

    print("  ── STAGE 2: Lexigram LLMModule ── DI & protocols")
    print("  ───────────────────────────────────────────")
    await stage2_lexigram_llm()
    print()

    print("  ── STAGE 3: Structured Output ── typed extraction")
    print("  ───────────────────────────────────────────")
    await stage3_structured()
    print()

    print("  ── STAGE 4: Streaming ── real-time token output")
    print("  ───────────────────────────────────────────")
    await stage4_streaming()

    print()
    print("  ── STAGE 5: Provider Flexibility ── 15 providers")
    print("  ───────────────────────────────────────────")
    print(f"  Built-in: {', '.join(AVAILABLE_PROVIDERS)}")
    await stage5_flexibility()
    print()

    print("  ✅ Done — Lexigram handled all of this.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
