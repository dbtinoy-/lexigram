---
title: "AI Architecture"
description: "How the AI packages compose — LLM client, RAG, agents, memory, sessions, skills, and MCP."
---

The Lexigram AI subsystem is organized into six layers. Each layer builds on the one below it, and all AI packages follow a strict dependency rule: they import only from `lexigram` and `lexigram-contracts`, never from each other.

```mermaid
graph TD
    A["Integration Layer<br/>lexigram-ai-mcp"] --> B["Infrastructure Layer<br/>lexigram-ai-workers, -observability, -feedback"]
    B --> C["Memory Layer<br/>lexigram-ai-memory, -session"]
    C --> D["Reasoning Layer<br/>lexigram-ai-agents, -skills"]
    D --> E["Knowledge Layer<br/>lexigram-ai-rag, lexigram-vector"]
    E --> F["Base Layer<br/>lexigram-ai-llm"]
```

## 1. Base Layer — `lexigram-ai-llm`

The LLM client protocol. Provides:

- **Provider routing**: Route requests to OpenAI, Anthropic, Google, and local models via a unified interface
- **Thinking suppression**: Configurable control over chain-of-thought output from reasoning models
- **Token tracking**: Usage accounting and cost estimation

All higher layers depend on this package for model access.

## 2. Knowledge Layer — `lexigram-ai-rag` + `lexigram-vector`

Retrieval-Augmented Generation and vector storage.

- **Document ingestion**: Chunking, embedding, and indexing pipelines
- **Retrieval**: Hybrid search (semantic + keyword), re-ranking, contextual compression
- **Vector storage**: Abstraction over pgvector, Qdrant, Pinecone, and in-memory

:::note
`lexigram-vector` is also used outside the AI subsystem — for example, by recommendation engines. It lives as a general-purpose package, not an AI-only one.
:::

## 3. Reasoning Layer — `lexigram-ai-agents` + `lexigram-ai-skills`

Multi-step reasoning and tool use.

- **Agents**: Loop-based reasoning with tool selection, error recovery, and structured output
- **Skills**: Reusable tool definitions that agents can discover and invoke at runtime
- **Orchestration**: Parallel tool execution, conditional branching, sub-agent delegation

## 4. Memory Layer — `lexigram-ai-memory` + `lexigram-ai-session`

Conversation history and persistent knowledge.

- **Episodic memory**: Per-conversation message history with summarization
- **Semantic memory**: Cross-session facts, user preferences, learned knowledge
- **Session management**: Conversation lifecycle, state persistence, expiry

## 5. Integration Layer — `lexigram-ai-mcp`

Expose AI capabilities as Model Context Protocol tools, resources, and prompts.

- **MCP server**: Wrap agents, RAG pipelines, and skills as MCP tools
- **MCP client**: Connect to external MCP servers from within agents
- **Discovery**: Dynamic tool registration and capability advertisement

## 6. Infrastructure Layer — `lexigram-ai-workers` + `lexigram-ai-observability` + `lexigram-ai-feedback`

Production-grade AI infrastructure.

- **Background processing**: Async task execution for embedding, indexing, and batch inference
- **Observability**: Token usage logging, latency tracking, cost attribution per-user/per-conversation
- **Feedback loops**: User feedback collection, preference fine-tuning data pipelines

:::note
**Architectural rule**: AI packages must never import from each other. `lexigram-ai-agents` does not import `lexigram-ai-rag` — it receives RAG results through its interfaces. This keeps the dependency graph flat and avoids circular coupling.
:::

## Dependency Direction

Each layer depends only on the layers below it. The base layer depends only on `lexigram` and `lexigram-contracts`. The integration layer can optionally consume any layer below it, but never introduces upward dependencies.

See the [Packages](/packages/) reference for individual package APIs and the [Choosing Backends](/ecosystem/choosing-backends/) guide for vector store comparisons.

For version requirements and known constraints, refer to [Compatibility & Dependencies](/ecosystem/compatibility/).
