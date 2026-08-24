"""
╔══════════════════════════════════════════════════════════╗
║  Lexigram Tool Calling — every provider, one demo       ║
╚══════════════════════════════════════════════════════════╝

Run:  uv run python3 app.py     (requires local Ollama on :11434
       for the live sections; the offline checks always run)
"""

import asyncio
import os
import time

import structlog

from lexigram.ai.llm.docs.gifs.tools.registry import p
from lexigram.ai.llm.docs.gifs.tools.live_examples import (
    example1_live_openai_compat,
    example2_live_native_ollama,
)
from lexigram.ai.llm.docs.gifs.tools.openai_anthropic_wire import (
    example3_openai_family_wire,
    example4_anthropic_wire,
)
from lexigram.ai.llm.docs.gifs.tools.gemini_bedrock_wire import (
    example5_gemini_wire,
    example6_bedrock_cohere_wire,
)

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(
        structlog.stdlib.logging.ERROR,
    ),
)
os.environ.setdefault("LEX_LOGGING__LEVEL", "ERROR")
os.environ.setdefault("LEX_QUIET", "1")
os.environ.setdefault("OPENAI_API_KEY", "dummy-key")


def section_pause():
    time.sleep(2.0)


def final_pause():
    time.sleep(2.0)


async def main():
    print()
    print("  ── Example 1: Live OpenAI-compatible on Ollama /v1")
    print("  ────  OpenAI client round trip against a real server")
    try:
        await example1_live_openai_compat()
    except Exception as exc:  # noqa: BLE001 — demo wraps network failures
        p(f"    (skipped: {type(exc).__name__}: {exc})")
    print()
    print("  ----------------")
    print()
    section_pause()

    print("  ── Example 2: Live native tool calling on Ollama")
    print("  ────  FunctionCallingStrategy full loop")
    try:
        await example2_live_native_ollama()
    except Exception as exc:  # noqa: BLE001 — demo wraps network failures
        p(f"    (skipped: {type(exc).__name__}: {exc})")
    print()
    print("  ----------------")
    print()
    section_pause()

    print("  ── Example 3: OpenAI-family wire format")
    print("  ────  openai / groq / mistral / openrouter / cloudflare")
    example3_openai_family_wire()
    print()
    print("  ----------------")
    print()
    section_pause()

    print("  ── Example 4: Anthropic wire format")
    print("  ────  input_schema + tool_result/tool_use blocks")
    example4_anthropic_wire()
    print()
    print("  ----------------")
    print()
    section_pause()

    print("  ── Example 5: Gemini + Vertex wire format")
    print("  ────  functionDeclarations + functionCall/Response")
    example5_gemini_wire()
    print()
    print("  ----------------")
    print()
    section_pause()

    print("  ── Example 6: Bedrock + Cohere wire format")
    print("  ────  toolSpec/toolUse + parameter_definitions")
    await example6_bedrock_cohere_wire()
    print()
    print("  ----------------")
    print()
    section_pause()

    print("  ... all provider wire checks complete")
    final_pause()


if __name__ == "__main__":
    asyncio.run(main())
