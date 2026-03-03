"""
╔══════════════════════════════════════════════════════════╗
║  Lexigram Tool Calling — every provider, one demo       ║
╚══════════════════════════════════════════════════════════╝

This demo exercises native function/tool calling through every
LLM provider Lexigram ships. Two live round trips hit a real
server (Ollama: native + its OpenAI-compatible endpoint), then
offline wire-format checks print the exact JSON each provider
sends and parses the response — so a mismatched payload is
visible immediately.

Run:  uv run python3 app.py     (requires local Ollama on :11434
       for the live sections; the offline checks always run)
"""

import asyncio
import os
import sys
import time

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


def p(text):
    print(text)
    sys.stdout.flush()


def section_pause():
    time.sleep(2.0)


def final_pause():
    time.sleep(2.0)


def banner(title, sub):
    p("  " + title)
    p("  " + sub)


def check(label, ok):
    p(f"    {'OK   ' if ok else 'FAIL '}{label}")


OLLAMA_BASE = "http://localhost:11434"
OLLAMA_MODEL = "gemma4:12b"

WEATHER_TOOL = {
    "name": "get_weather",
    "description": "Current weather for a city.",
    "parameters": {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
    },
}

##1
# ═══════════════════════════════════════════════════════════
# EXAMPLE 1: Live OpenAI-compatible round trip on Ollama /v1
# ═══════════════════════════════════════════════════════════
# The OpenAI client (shared by openai, groq, mistral,
# openrouter, cloudflare, azure) converts the ToolDefinition
# to wire format, then parses tool_calls back. A real server
# round trip exposes any conversion/parse mismatch.


async def example1_live_openai_compat():
    from lexigram.ai.llm.clients.openai import OpenAIClient
    from lexigram.ai.llm.config import ClientConfig
    from lexigram.ai.llm.types import ChatMessage, Role
    from lexigram.contracts.ai.agents import ToolDefinition
    from lexigram.validation import SecretStr

    config = ClientConfig(
        provider="openai",
        model=OLLAMA_MODEL,
        api_key=SecretStr("dummy"),
        api_base=f"{OLLAMA_BASE}/v1",
    )
    client = OpenAIClient(config)
    tool = ToolDefinition(**WEATHER_TOOL)

    res = await client.complete(
        [
            ChatMessage(
                role=Role.USER,
                content="Use the weather tool for Paris, reply with only the tool call.",
            )
        ],
        tools=[tool],
    )
    assert res.is_ok(), f"complete failed: {res.unwrap_err()}"
    comp = res.unwrap()
    p(f"    tool_calls -> {comp.tool_calls}")
    check(
        "tool_calls parsed from OpenAI-compatible response",
        comp.tool_calls is not None
        and comp.tool_calls[0].function.name == "get_weather",
    )


##2
# ═══════════════════════════════════════════════════════════
# EXAMPLE 2: Live native tool calling on Ollama
# ═══════════════════════════════════════════════════════════
# FunctionCallingStrategy sends ToolDefinitions as Ollama's
# native tools, executes the call, feeds the result back, and
# produces a final answer. Exercises the full loop that used
# to crash with "tools must be a list of ToolDefinition"?


async def example2_live_native_ollama():
    from lexigram import Application
    from lexigram.ai.agents import tool
    from lexigram.ai.agents.strategies import FunctionCallingStrategy
    from lexigram.ai.llm import ClientConfig, LLMModule
    from lexigram.contracts.ai import LLMClientProtocol

    KNOWLEDGE = {
        "providers": "Lexigram supports 15+ AI providers out of the box:\n"
        "- ollama, openai, anthropic, groq, cohere, mistral, deepseek, gemini\n"
        "- fireworks, together, openrouter, azure-openai, aws-bedrock, cloudflare, google-vertex",
    }

    @tool
    async def search_knowledge(topic: str) -> str:
        """Search the Lexigram knowledge base."""
        for key, info in KNOWLEDGE.items():
            if key in topic.lower():
                return info
        return "Topics: AI providers, modules, agents, extraction"

    async with Application.boot(
        modules=[
            LLMModule.configure(ClientConfig(provider="ollama", model=OLLAMA_MODEL))
        ]
    ) as app:
        llm = await app._container.resolve(LLMClientProtocol)
        strategy = FunctionCallingStrategy(max_iterations=2)
        for _ in range(2):
            try:
                result = await asyncio.wait_for(
                    strategy.execute(
                        message="What AI providers does Lexigram support? List them.",
                        tools=[search_knowledge],
                        history=[],
                        llm=llm,
                    ),
                    timeout=45,
                )
            except TimeoutError:
                p("    attempt timed out — retrying")
                continue
            if result.is_ok():
                response = result.unwrap()
                for step in response.steps:
                    if step.tool_call:
                        tc = step.tool_call
                        p(
                            f"    Tool: {tc.tool_name}({tc.arguments}) -> {str(tc.result)[:50]}"
                        )
                p(f"    Answer: {response.message[:80]}")
                check(
                    "native tool loop completed",
                    response.steps is not None and len(response.steps) >= 2,
                )
                return
            p(f"    failed: {result.unwrap_err()} — retrying")
        p("    Tool calling could not complete")
        check("native tool loop completed", False)


##3
# ═══════════════════════════════════════════════════════════
# EXAMPLE 3: OpenAI-family wire format (offline)
# ═══════════════════════════════════════════════════════════
# Shared helpers convert ToolDefinition -> {"type":"function",
# "function":{...}} and round-trip tool_calls. Shared by
# openai, groq, mistral, openrouter, cloudflare, azure_openai.


def example3_openai_family_wire():
    import json

    from lexigram.ai.llm.clients._tools_utils import (
        parse_openai_tool_calls,
        serialize_message_for_openai,
        tool_to_openai_format,
    )
    from lexigram.ai.llm.types import (
        ChatMessage,
        FunctionCall,
        Role,
        ToolCall,
    )
    from lexigram.contracts.ai.agents import ToolDefinition

    tool = ToolDefinition(**WEATHER_TOOL)
    wire = tool_to_openai_format(tool)
    p(f"    tools[{0}] -> {json.dumps(wire)}")
    check(
        "tool converted to OpenAI function format",
        wire["type"] == "function" and wire["function"]["name"] == "get_weather",
    )

    assistant = ChatMessage(
        role=Role.ASSISTANT,
        content="",
        tool_calls=[
            ToolCall(
                id="call-1",
                type="function",
                function=FunctionCall(name="get_weather", arguments={"city": "Paris"}),
            )
        ],
    )
    msgs = [serialize_message_for_openai(assistant)]
    check(
        "assistant tool_calls serialized with JSON-encoded arguments",
        msgs[0]["tool_calls"][0]["function"]["name"] == "get_weather"
        and isinstance(msgs[0]["tool_calls"][0]["function"]["arguments"], str),
    )

    parsed = parse_openai_tool_calls(
        [
            {
                "id": "1",
                "type": "function",
                "function": {"name": "get_weather", "arguments": {"city": "Paris"}},
            }
        ]
    )
    check(
        "tool_calls parsed back into ToolCall objects",
        parsed is not None
        and parsed[0].function.name == "get_weather"
        and parsed[0].function.arguments == {"city": "Paris"},
    )


##4
# ═══════════════════════════════════════════════════════════
# EXAMPLE 4: Anthropic wire format (offline)
# ═══════════════════════════════════════════════════════════
# ToolDefinition -> {"name","description","input_schema"};
# tool results become user turns with a tool_result block;
# assistant tool_calls become tool_use blocks.


def example4_anthropic_wire():
    import json

    from lexigram.ai.llm.clients.anthropic import (
        AnthropicClient,
        _tool_to_anthropic,
    )
    from lexigram.ai.llm.types import (
        ChatMessage,
        FunctionCall,
        Role,
        ToolCall,
    )

    # Bypass __init__ (no 'anthropic' SDK installed); _convert_message is stateless
    client = object.__new__(AnthropicClient)

    tool = _tool_to_anthropic({"function": WEATHER_TOOL})
    p(f"    tools[{0}] -> {json.dumps(tool)}")
    check(
        "tool converted to Anthropic input_schema",
        tool["name"] == "get_weather" and "input_schema" in tool,
    )

    tool_result = client._convert_message(
        ChatMessage(role=Role.TOOL, content="22C, sunny", tool_call_id="call-1")
    )
    check(
        "tool result becomes user turn with tool_result block",
        tool_result["role"] == "user"
        and tool_result["content"][0]["type"] == "tool_result"
        and tool_result["content"][0]["tool_use_id"] == "call-1",
    )

    assistant = client._convert_message(
        ChatMessage(
            role=Role.ASSISTANT,
            content="",
            tool_calls=[
                ToolCall(
                    id="call-1",
                    type="function",
                    function=FunctionCall(
                        name="get_weather", arguments={"city": "Paris"}
                    ),
                )
            ],
        )
    )
    check(
        "assistant tool_calls become tool_use blocks",
        any(
            b.get("type") == "tool_use" and b.get("name") == "get_weather"
            for b in assistant["content"]
        ),
    )


##5
# ═══════════════════════════════════════════════════════════
# EXAMPLE 5: Gemini + Vertex wire format (offline)
# ═══════════════════════════════════════════════════════════
# ToolDefinition -> {"functionDeclarations":[...]}; assistant
# tool_calls -> functionCall parts; tool results ->
# functionResponse parts (Gemini + Vertex share these helpers).


def example5_gemini_wire():
    import json

    from lexigram.ai.llm.clients.gemini_helpers import (
        messages_to_gemini,
        parse_gemini_response_with_tools,
        tool_to_gemini_function,
    )
    from lexigram.ai.llm.types import (
        ChatMessage,
        FunctionCall,
        Role,
        ToolCall,
    )
    from lexigram.contracts.ai.agents import ToolDefinition

    fn = tool_to_gemini_function(ToolDefinition(**WEATHER_TOOL))
    p(f"    functionDeclaration -> {json.dumps(fn)}")
    check(
        "tool converted to Gemini functionDeclaration",
        fn["name"] == "get_weather" and "parameters" in fn,
    )

    contents = messages_to_gemini(
        [
            ChatMessage(role=Role.USER, content="Weather for Paris?"),
            ChatMessage(
                role=Role.ASSISTANT,
                content="",
                tool_calls=[
                    ToolCall(
                        id="get_weather",
                        type="function",
                        function=FunctionCall(
                            name="get_weather", arguments={"city": "Paris"}
                        ),
                    )
                ],
            ),
            # Gemini keys responses by the function name; see parse below
            ChatMessage(
                role=Role.TOOL, content="22C, sunny", tool_call_id="get_weather"
            ),
        ]
    )
    model_parts = contents[1]["parts"]
    tool_round_trip = contents[2]["parts"]
    check(
        "assistant tool_calls become functionCall parts",
        any(
            "functionCall" in part and part["functionCall"]["name"] == "get_weather"
            for part in model_parts
        ),
    )
    check(
        "tool result becomes functionResponse part",
        tool_round_trip[0]["functionResponse"]["name"] == "get_weather",
    )

    completion = parse_gemini_response_with_tools(
        {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "functionCall": {
                                    "name": "get_weather",
                                    "args": {"city": "Paris"},
                                }
                            }
                        ]
                    }
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 5,
                "candidatesTokenCount": 3,
                "totalTokenCount": 8,
            },
        },
        model="gemini-test",
    )
    check(
        "functionCall response parsed into ToolCall",
        completion.tool_calls is not None
        and completion.tool_calls[0].function.name == "get_weather",
    )


##6
# ═══════════════════════════════════════════════════════════
# EXAMPLE 6: Bedrock + Cohere wire format (offline)
# ═══════════════════════════════════════════════════════════
# Bedrock: toolSpec + toolResult/toolUse round trip.
# Cohere: parameter_definitions + tool_calls/tool_results.


async def example6_bedrock_cohere_wire():
    import json

    from lexigram.ai.llm.clients._bedrock_mappers import (
        parse_bedrock_response,
        tool_to_bedrock,
    )
    from lexigram.ai.llm.clients._cohere_mappers import map_cohere_tools
    from lexigram.ai.llm.clients.aws_bedrock import BedrockClient
    from lexigram.ai.llm.types import (
        ChatMessage,
        FunctionCall,
        Role,
        ToolCall,
    )
    from lexigram.contracts.ai.agents import ToolDefinition

    tool = ToolDefinition(**WEATHER_TOOL)

    spec = tool_to_bedrock(tool)
    p(f"    bedrock toolSpec -> {json.dumps(spec)}")
    check(
        "bedrock tool converted to toolSpec",
        spec["toolSpec"]["name"] == "get_weather"
        and "json" in spec["toolSpec"]["inputSchema"],
    )

    client = object.__new__(BedrockClient)

    async def _bedrock_msgs():
        return await client._to_bedrock_messages_async(
            [
                ChatMessage(
                    role=Role.ASSISTANT,
                    content="",
                    tool_calls=[
                        ToolCall(
                            id="tool-1",
                            type="function",
                            function=FunctionCall(
                                name="get_weather", arguments={"city": "Paris"}
                            ),
                        )
                    ],
                ),
                ChatMessage(
                    role=Role.TOOL, content="22C, sunny", tool_call_id="tool-1"
                ),
            ]
        )

    blocks = await _bedrock_msgs()
    used_tool_use = any(
        b.get("toolUse") and b["toolUse"]["name"] == "get_weather"
        for b in blocks[0]["content"]
    )
    used_result = blocks[1]["role"] == "user" and any(
        b.get("toolResult") and b["toolResult"]["toolUseId"] == "tool-1"
        for b in blocks[1]["content"]
    )
    check("bedrock assistant tool_calls become toolUse blocks", used_tool_use)
    check("bedrock tool result becomes toolResult user turn", used_result)

    bedrock_completion = parse_bedrock_response(
        {
            "output": {
                "message": {
                    "content": [
                        {
                            "toolUse": {
                                "toolUseId": "tool-1",
                                "name": "get_weather",
                                "input": {"city": "Paris"},
                            }
                        }
                    ]
                }
            },
            "usage": {"inputTokens": 5, "outputTokens": 3, "totalTokens": 8},
            "stopReason": "tool_use",
        },
        model="bedrock-test",
    )
    check(
        "bedrock toolUse parsed into ToolCall",
        bedrock_completion.tool_calls is not None
        and bedrock_completion.tool_calls[0].function.name == "get_weather",
    )

    cohere_tools = map_cohere_tools([tool])
    p(f"    cohere tools[0] -> {json.dumps(cohere_tools[0])}")
    check(
        "cohere tool converted to parameter_definitions",
        cohere_tools[0]["name"] == "get_weather"
        and "city" in cohere_tools[0]["parameter_definitions"],
    )

    from lexigram.ai.llm.clients._cohere_mappers import _cohere_assistant_tool_calls

    calls = _cohere_assistant_tool_calls(
        [
            ToolCall(
                id="call-1",
                type="function",
                function=FunctionCall(name="get_weather", arguments={"city": "Paris"}),
            )
        ]
    )
    check(
        "cohere assistant tool_calls serialized",
        calls == [{"name": "get_weather", "parameters": {"city": "Paris"}}],
    )


# ═══════════════════════════════════════════════════════════
# RUNNABLE DEMO
# ═══════════════════════════════════════════════════════════


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
