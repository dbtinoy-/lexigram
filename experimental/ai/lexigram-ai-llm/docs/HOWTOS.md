---
title: lexigram-ai-llm How-Tos
description: Common usage patterns for `lexigram-ai-llm`.
---

## 1. Basic completion with error handling

```python
from lexigram.contracts.ai import LLMClientProtocol

llm = await app.container.resolve(LLMClientProtocol)
result = await llm.complete([
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is 2+2?"},
])

if result.is_ok():
    print(result.unwrap().content)  # "4"
else:
    err = result.unwrap_err()
    print(f"LLM error: {err}")
```

## 2. Stream a completion

```python
stream = llm.stream_chat([{"role": "user", "content": "Count to 5"}])

full_response = ""
async for chunk in stream:
    if chunk.delta:
        full_response += chunk.delta
        print(chunk.delta, end="")
```

## 3. Multi-turn conversation

```python
from lexigram.ai.llm import ConversationManager, ConversationConfig

manager = ConversationManager(
    config=ConversationConfig(max_turns=20),
    llm_client=llm,
)

await manager.add_message({"role": "user", "content": "My name is Alice."})
resp1 = await manager.get_response()
print(resp1.content)

await manager.add_message({"role": "user", "content": "What is my name?"})
resp2 = await manager.get_response()
# Alice — the conversation retains context
```

## 4. Enable response caching

```python
from lexigram.ai.llm.config import ClientConfig

config = ClientConfig(
    provider="openai",
    model="gpt-4o",
    enable_cache=True,
    cache_ttl=3600,
)
# Requires CacheBackendProtocol in the container (e.g., RedisCacheBackend)
```

## 5. Structured JSON output

```python
from lexigram.ai.llm import JSONExtractor

extractor = JSONExtractor(llm_client=llm)
result = await extractor.extract(
    "Extract the person's name and age from: John is 30 years old",
    schema={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer"},
        },
        "required": ["name", "age"],
    },
)
if result.is_ok():
    data = result.unwrap()
    print(data["name"], data["age"])
```

## 6. Custom provider registration

```python
from lexigram.ai.llm import ProviderRegistry

registry = ProviderRegistry()
registry.register("my_provider", MyCustomClient)
# Now usable with ClientConfig(provider="my_provider")
```

## 7. Use LLMModule with routing

```python
from lexigram.ai.llm import LLMModule
from lexigram.ai.llm.routing import LLMConfig

module = LLMModule.configure(routing=LLMConfig())
```

## 8. Count tokens and estimate costs

```python
from lexigram.ai.llm import TiktokenCounter

counter = TiktokenCounter(model="gpt-4")
count = counter.count("Hello, world!")
print(f"Tokens: {count.total}")

from lexigram.ai.llm import (
    TokenCounterRegistry,
    TiktokenCounter,
    HuggingFaceCounter,
    CharEstimateCounter,
)

registry = TokenCounterRegistry()
registry.register("gpt-4", TiktokenCounter(model="gpt-4"))
registry.register("gpt-3.5-turbo", TiktokenCounter(model="gpt-3.5-turbo"))
registry.register("llama3", HuggingFaceCounter(model="meta-llama/Llama-3-8b"))
registry.register("claude-3", CharEstimateCounter())

tokens = registry.count("How many tokens?", model="gpt-4")
print(f"Total: {tokens.total}")

cost_est = counter.estimate_cost(
    prompt_tokens=150,
    completion_tokens=50,
)
print(f"Estimated cost: ${cost_est.total_cost:.6f}")
```

## 9. Select the right model for each task

```python
from lexigram.ai.llm import (
    ModelSelector,
    SelectionStrategy,
    SelectionCriteria,
    create_balanced_selector,
    create_cost_optimized_selector,
    create_quality_optimized_selector,
)

selector = ModelSelector(
    default_model="gpt-3.5-turbo",
    strategies=[
        SelectionStrategy(
            name="complex",
            model="gpt-4-turbo",
            conditions={"min_tokens": 1000},
        ),
        SelectionStrategy(
            name="code",
            model="claude-opus-4",
            conditions={"task_type": "code_generation"},
        ),
    ],
    fallback_chain=["gpt-4-turbo", "gpt-3.5-turbo", "ollama/llama3"],
)

model = selector.select("Write a complex analysis...")
print(f"Selected model: {model}")
```

## 10. Compose LLM calls with runnable pipelines

```python
from lexigram.ai.llm import (
    RunnableSequence,
    RunnableParallel,
    RunnablePassthrough,
    RunnableLambda,
)

# Chain: extract entities → summarize → format
pipeline = RunnableSequence(
    extract_entities_lambda,
    RunnableSequence(
        summarize_lambda,
        format_output_lambda,
    ),
)
result = await pipeline.ainvoke({"text": "..."})

# Parallel: run multiple prompts concurrently
parallel = RunnableParallel(
    summary=summarize_lambda,
    topics=extract_topics_lambda,
    sentiment=analyze_sentiment_lambda,
)
results = await parallel.ainvoke(user_input)
# results == {"summary": ..., "topics": ..., "sentiment": ...}

# Passthrough: inject context without transformation
chain = RunnableSequence(
    RunnablePassthrough(),
    final_llm_call_lambda,
)
final = await chain.ainvoke({"query": "Hello", "context": "..."})
```

## 11. Rate limiting

```python
from lexigram.ai.llm import RateLimiter

limiter = RateLimiter(max_calls=10, window_seconds=60)
await limiter.acquire()  # Blocks until a slot is available
result = await llm.complete([{"role": "user", "content": "Hello"}])
```
