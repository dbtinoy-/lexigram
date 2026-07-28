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
from dataclasses import dataclass
import os

# Suppress framework logging BEFORE any Lexigram imports
import structlog

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        structlog.stdlib.logging.ERROR,
    ),
)
os.environ.setdefault("LEX_LOGGING__LEVEL", "ERROR")
os.environ.setdefault("LEX_QUIET", "1")
os.environ.setdefault("OPENAI_API_KEY", "dummy-key")


# ═══════════════════════════════════════════════════════════
# EXAMPLE 1: Raw Ollama — the manual way
# ═══════════════════════════════════════════════════════════
# Direct HTTP to Ollama via the `ollama` package.
# Dict access, no types, no DI, fragile error handling.


async def stage1_raw_ollama():
    import ollama

    client = ollama.AsyncClient(host="http://localhost:11434")
    messages = [
        {"role": "user", "content": "Explain dependency injection in 1 sentence."}
    ]
    resp = await client.chat(model="gemma4:12b", messages=messages)
    print(f"  {resp['message']['content']}")


# ═══════════════════════════════════════════════════════════
# EXAMPLE 2: Enter Lexigram
# ═══════════════════════════════════════════════════════════
# Application.boot() + LLMModule — DI, protocols, Result[T,E].
# Same LLM call, now clean, testable, provider-agnostic.

from lexigram import Application
from lexigram.ai.llm import ClientConfig, LLMModule
from lexigram.ai.llm.structured import build_json_schema, extract_json_block
from lexigram.ai.llm.thinking import normalize_thinking_text
from lexigram.contracts.ai import ChatMessage, LLMClientProtocol, Role
from lexigram.serialization import dumps_str


async def stage2_lexigram_llm():
    async with Application.boot(
        modules=[
            LLMModule.configure(
                ClientConfig(
                    provider="ollama",
                    model="gemma4:12b",
                )
            )
        ]
    ) as app:
        llm = await app._container.resolve(LLMClientProtocol)
        result = await llm.complete(
            [
                ChatMessage(
                    role=Role.USER,
                    content="What is the provider pattern? Answer in 1 sentence.",
                ),
            ]
        )
        print(f"  {result.unwrap().content}")


# ═══════════════════════════════════════════════════════════
# EXAMPLE 3: Structured Output
# ═══════════════════════════════════════════════════════════
# Typed extraction — dataclasses from the LLM, validated.
# No string parsing, no fragile regex.


@dataclass
class Explanation:
    concept: str
    summary: str
    benefit: str


async def stage3_structured():
    async with Application.boot(
        modules=[
            LLMModule.configure(
                ClientConfig(
                    provider="ollama",
                    model="gemma4:12b",
                )
            )
        ]
    ) as app:
        llm = await app._container.resolve(LLMClientProtocol)

        schema = dumps_str(build_json_schema(Explanation), indent=2)
        result = await llm.complete(
            [
                ChatMessage(role=Role.SYSTEM, content=f"Respond with JSON:\n{schema}"),
                ChatMessage(role=Role.USER, content="Explain the strategy pattern."),
            ]
        )
        if result.is_ok():
            completion = result.unwrap()
            if completion.thinking:
                think = completion.thinking.content.strip()
                # Truncate verbose thinking to preserve demo flow
                if len(think) > 250:
                    think = think[:250] + "..."
                print(f"  [thinking] {think}")
            ex = Explanation(**extract_json_block(completion.content))
            print(f"  Concept: {ex.concept}")
            print(f"  Summary: {ex.summary}")
            print(f"  Benefit: {ex.benefit}")
        else:
            print(f"  Extraction failed: {result.unwrap_err()}")


# ═══════════════════════════════════════════════════════════
# EXAMPLE 4: Streaming — real-time token output
# ═══════════════════════════════════════════════════════════
# stream_chat() returns AsyncStream — tokens as they arrive.
# No waiting for the full response.


async def stage4_streaming():
    async with Application.boot(
        modules=[
            LLMModule.configure(
                ClientConfig(
                    provider="openai",
                    model="qwen3-30b-a3b-thinking-2507",
                    api_base="http://localhost:1234/v1",
                    max_tokens=256,
                )
            )
        ]
    ) as app:
        llm = await app._container.resolve(LLMClientProtocol)
        stream = llm.stream_chat(
            [
                ChatMessage(
                    role=Role.USER,
                    content="Explain the observer pattern in 1 sentence.",
                ),
            ]
        )

        collected = []
        async for chunk in stream:
            if chunk.delta:
                collected.append(chunk.delta)
                print("·", end="", flush=True)
        print()

        full = "".join(collected)
        clean_response, thinking_text = normalize_thinking_text(full)
        if thinking_text:
            lines = thinking_text.strip().split("\n")
            short = lines[0][:200] + (
                "..." if len(lines) > 1 or len(lines[0]) > 200 else ""
            )
            print(f"  [thinking] {short}")
        print(f"  {clean_response}")


# ═══════════════════════════════════════════════════════════
# EXAMPLE 5: Tool Calling — LLM autonomously uses tools
# ═══════════════════════════════════════════════════════════
# @tool decorator + ReAct strategy = agentic AI.
# The LLM decides when to call a tool, processes the
# result, and produces a final answer.

from lexigram.ai.agents import tool
from lexigram.ai.agents.strategies import ReActStrategy

KNOWLEDGE_BASE = {
    "providers": """Lexigram supports 15+ AI providers out of the box:
- ollama, openai, anthropic, groq, cohere, mistral, deepseek, gemini
- fireworks, together, openrouter, azure-openai, aws-bedrock, cloudflare, google-vertex
All share the same LLMClientProtocol — swap via one env var.""",
    "modules": """Modules bundle providers, register services, and export contracts.
Defined with @module() decorator. Container resolves dependencies automatically.
Extensions use DynamicModule for parameterized configuration.""",
    "agents": """Agents combine LLM + tools + strategy (ReAct, PlanExecute).
@tool decorator wraps any async function with auto-generated JSON schema.
Memory backends, governance policies, and skill integration included.""",
    "extraction": """StructuredExtractor converts LLM output to typed dataclasses.
Returns Result[T, ExtractionError] — no string parsing, no fragile regex.
Works with any provider via LLMClientProtocol.""",
}


@tool
async def search_knowledge(topic: str) -> str:
    """Search the Lexigram knowledge base for framework information."""
    for key, info in KNOWLEDGE_BASE.items():
        if key in topic.lower() or topic.lower() in key:
            return info
    return "Topics: AI providers, modules, agents, extraction"


async def stage5_tool_calling():
    async with Application.boot(
        modules=[
            LLMModule.configure(
                ClientConfig(
                    provider="ollama",
                    model="gemma4:12b",
                )
            )
        ]
    ) as app:
        llm = await app._container.resolve(LLMClientProtocol)
        strategy = ReActStrategy(max_iterations=2)
        result = await strategy.execute(
            message="What AI providers does Lexigram support? List them.",
            tools=[search_knowledge],
            history=[],
            llm=llm,
        )
        if result.is_ok():
            response = result.unwrap()
            for step in response.steps:
                if step.tool_call:
                    tc = step.tool_call
                    print(f"  Tool: {tc.tool_name}({tc.arguments})")
            print(f"  Answer: {response.message}")


# ═══════════════════════════════════════════════════════════
# EXAMPLE 6: Observe — automatic observability
# ═══════════════════════════════════════════════════════════
# Every call captures model, tokens, timing, and provenance
# — zero extra code. The framework fills it all in for you.


async def stage6_observability():
    async with Application.boot(
        modules=[
            LLMModule.configure(
                ClientConfig(
                    provider="ollama",
                    model="gemma4:12b",
                )
            )
        ]
    ) as app:
        llm = await app._container.resolve(LLMClientProtocol)
        result = await llm.complete(
            [
                ChatMessage(
                    role=Role.USER,
                    content="Explain the decorator pattern in 1 sentence.",
                ),
            ]
        )
        c = result.unwrap()
        duration = c.metadata.get("total_duration", 0) / 1e9
        print(f"  Provider: {c.provider}")
        print(f"  Model: {c.model}")
        print(f"  Tokens: {c.usage.total_tokens} ({c.usage.prompt_tokens}+{c.usage.completion_tokens})")
        print(f"  Latency: {duration:.1f}s")
        print(f"  → {c.content}")


# ═══════════════════════════════════════════════════════════
# RUNNABLE DEMO
# ═══════════════════════════════════════════════════════════


async def main():
    print()
    print("  ── Example 1: Before ── raw library API call to Ollama")
    print("  ────  fragile dict access, no framework")
    await stage1_raw_ollama()
    print()
    print("  ----------------")
    print()

    print("  ── Example 2: After ── same call through Lexigram DI")
    print("  ────  contracts, Result types, provider-agnostic")
    await stage2_lexigram_llm()
    print()
    print("  ----------------")
    print()

    print("  ── Example 3: Extract ── typed output from the LLM")
    print("  ────  dataclass extraction, no fragile string parsing")
    await stage3_structured()
    print()
    print("  ----------------")
    print()

    print("  ── Example 4: Stream ── real-time token output")
    print("  ────  streaming with thinking normalization via Lexigram")
    await stage4_streaming()
    print()
    print("  ----------------")
    print()

    print("  ── Example 5: Agent ── LLM calls tools autonomously")
    print("  ────  @tool + ReAct strategy")
    await stage5_tool_calling()
    print()
    print("  ----------------")
    print()

    print("  ── Example 6: Observe ── automatic observability")
    print("  ────  model, tokens, latency — zero extra code")
    await stage6_observability()
    print()
    print("  ----------------")
    print()
    print("  ... and many more")


if __name__ == "__main__":
    asyncio.run(main())
