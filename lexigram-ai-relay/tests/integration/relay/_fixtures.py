"""Transcribed relaykit golden-fixture sources.

These wire payloads mirror the inline fixtures in new-api's
``relaykit/relayconvert/golden_test.go`` (fixtureRequests,
fixtureResponses, fixtureStreamChunks) verbatim.  The golden files under
``tests/fixtures/relay/{request,response,stream}/`` were copied from
``relaykit/relayconvert/testdata/golden`` and are the expected converter
output for every directed route.

The harness reproduces relaykit's ``TestMain`` fixed media resolver
(``aGVsbG8=`` / ``image/png``) and its ``goldenInfo()`` default options
through :func:`golden_context` in ``conftest.py``.
"""

from __future__ import annotations

from typing import Any

# Fixture filename slug -> RelayFormat.value
FORMAT_SLUGS: dict[str, str] = {
    "openai": "openai_chat",
    "openai_responses": "openai_responses",
    "claude": "claude",
    "gemini": "gemini",
}

REQUEST_FIXTURES: dict[str, dict[str, Any]] = {
    "openai": {
        "model": "gpt-test",
        "max_tokens": 1024,
        "stream": True,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is in this image?"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "https://example.com/cat.png", "detail": "high"},
                    },
                ],
            },
            {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call_abc",
                        "type": "function",
                        "function": {"name": "get_weather", "arguments": '{"city":"Paris"}'},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "call_abc", "content": "15 degrees"},
            {"role": "user", "content": "Summarize."},
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get weather by city",
                    "parameters": {
                        "type": "object",
                        "properties": {"city": {"type": "string"}},
                        "required": ["city"],
                    },
                },
            }
        ],
        "tool_choice": "auto",
    },
    "claude": {
        "model": "claude-test",
        "max_tokens": 1024,
        "stream": True,
        "system": "You are a helpful assistant.",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is in this image?"},
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": "aGVsbG8="},
                    },
                ],
            },
            {
                "role": "assistant",
                "content": [
                    {"type": "thinking", "thinking": "Let me look.", "signature": "sig"},
                    {
                        "type": "tool_use",
                        "id": "toolu_abc",
                        "name": "get_weather",
                        "input": {"city": "Paris"},
                    },
                ],
            },
            {
                "role": "user",
                "content": [{"type": "tool_result", "tool_use_id": "toolu_abc", "content": "15 degrees"}],
            },
        ],
        "tools": [
            {
                "name": "get_weather",
                "description": "Get weather by city",
                "input_schema": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            }
        ],
        "thinking": {"type": "enabled", "budget_tokens": 512},
    },
    "gemini": {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": "What is in this image?"},
                    {"inlineData": {"mimeType": "image/png", "data": "aGVsbG8="}},
                ],
            },
            {"role": "model", "parts": [{"functionCall": {"name": "get_weather", "args": {"city": "Paris"}}}]},
            {
                "role": "user",
                "parts": [{"functionResponse": {"name": "get_weather", "response": {"result": "15 degrees"}}}],
            },
        ],
        "systemInstruction": {"parts": [{"text": "You are a helpful assistant."}]},
        "tools": [
            {
                "functionDeclarations": [
                    {
                        "name": "get_weather",
                        "description": "Get weather by city",
                        "parameters": {
                            "type": "object",
                            "properties": {"city": {"type": "string"}},
                            "required": ["city"],
                        },
                    }
                ]
            }
        ],
        "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.7},
    },
    "openai_responses": {
        "model": "gpt-test",
        "stream": True,
        "max_output_tokens": 1024,
        "instructions": "You are a helpful assistant.",
        "input": [
            {
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": "What is in this image?"},
                    {"type": "input_image", "image_url": "https://example.com/cat.png"},
                ],
            },
            {"type": "function_call", "call_id": "call_abc", "name": "get_weather", "arguments": '{"city":"Paris"}'},
            {"type": "function_call_output", "call_id": "call_abc", "output": "15 degrees"},
        ],
        "tools": [
            {
                "type": "function",
                "name": "get_weather",
                "description": "Get weather by city",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            }
        ],
    },
}

RESPONSE_FIXTURES: dict[str, dict[str, Any]] = {
    "openai": {
        "id": "chatcmpl-fixed",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "gpt-test",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "The answer is 42.",
                    "reasoning_content": "Deep thought.",
                    "tool_calls": [
                        {"id": "call_abc", "type": "function", "function": {"name": "get_weather", "arguments": '{"city":"Paris"}'}}
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
            "prompt_tokens_details": {"cached_tokens": 3},
            "completion_tokens_details": {"reasoning_tokens": 2},
        },
    },
    "claude": {
        "id": "msg_fixed",
        "type": "message",
        "role": "assistant",
        "model": "claude-test",
        "content": [
            {"type": "text", "text": "The answer is 42."},
            {"type": "tool_use", "id": "toolu_abc", "name": "get_weather", "input": {"city": "Paris"}},
        ],
        "stop_reason": "tool_use",
        "usage": {
            "input_tokens": 10,
            "output_tokens": 5,
            "cache_read_input_tokens": 3,
            "cache_creation_input_tokens": 2,
        },
    },
    "gemini": {
        "candidates": [
            {
                "finishReason": "STOP",
                "content": {
                    "role": "model",
                    "parts": [
                        {"text": "The answer is 42."},
                        {"functionCall": {"name": "get_weather", "args": {"city": "Paris"}}},
                    ],
                },
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 10,
            "candidatesTokenCount": 5,
            "thoughtsTokenCount": 2,
            "totalTokenCount": 15,
        },
    },
    "openai_responses": {
        "id": "resp_fixed",
        "object": "response",
        "model": "gpt-test",
        "status": "completed",
        "output": [
            {"type": "reasoning", "summary": [{"type": "summary_text", "text": "Deep thought."}]},
            {
                "type": "message",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": "The answer is 42."}],
            },
            {"type": "function_call", "call_id": "call_abc", "name": "get_weather", "arguments": '{"city":"Paris"}', "status": "completed"},
        ],
        "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
    },
}

STREAM_FIXTURES: dict[str, list[dict[str, Any]]] = {
    "openai": [
        {
            "id": "chatcmpl-fixed",
            "object": "chat.completion.chunk",
            "created": 1700000000,
            "model": "gpt-test",
            "choices": [{"index": 0, "delta": {"role": "assistant", "content": "Hello"}}],
        },
        {
            "id": "chatcmpl-fixed",
            "object": "chat.completion.chunk",
            "created": 1700000000,
            "model": "gpt-test",
            "choices": [{"index": 0, "delta": {"content": " world"}}],
        },
        {
            "id": "chatcmpl-fixed",
            "object": "chat.completion.chunk",
            "created": 1700000000,
            "model": "gpt-test",
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
        },
    ],
    "claude": [
        {
            "type": "message_start",
            "message": {
                "id": "msg_fixed",
                "type": "message",
                "role": "assistant",
                "model": "claude-test",
                "content": [],
                "usage": {"input_tokens": 4, "output_tokens": 0},
            },
        },
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello world"}},
        {"type": "content_block_stop", "index": 0},
        {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 2}},
        {"type": "message_stop"},
    ],
    "gemini": [
        {"candidates": [{"content": {"role": "model", "parts": [{"text": "Hello"}]}}]},
        {
            "candidates": [{"finishReason": "STOP", "content": {"role": "model", "parts": [{"text": " world"}]}}],
            "usageMetadata": {"promptTokenCount": 4, "candidatesTokenCount": 2, "totalTokenCount": 6},
        },
    ],
    "openai_responses": [
        {"type": "response.output_text.delta", "delta": "Hello"},
        {"type": "response.output_text.delta", "delta": " world"},
        {
            "type": "response.completed",
            "response": {
                "id": "resp_fixed",
                "object": "response",
                "status": "completed",
                "model": "gpt-test",
                "usage": {"input_tokens": 4, "output_tokens": 2, "total_tokens": 6},
            },
        },
    ],
}


def routes(kind: str) -> list[str]:
    """Return the 12 directed routes for a fixture kind."""
    return [
        f"{source}_to_{target}"
        for source in FORMAT_SLUGS
        for target in FORMAT_SLUGS
        if source != target
    ]