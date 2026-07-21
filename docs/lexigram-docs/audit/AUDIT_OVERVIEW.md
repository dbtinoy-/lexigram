# AUDIT_OVERVIEW.md — Lexigram Framework Package Overview

> **Source**: Package directories and `pyproject.toml` metadata.

---

## Summary

- Packages discovered: 54
- Packages with tests: 54

## Packages

| Package | Version | Tests | Description |
|---------|---------|-------|-------------|
| `lexigram` | 0.1.3009 | yes | Async-first DI/IoC framework for Python — core package |
| `lexigram-admin` | 0.1.3010 | yes | Modern Python-first admin framework for Lexigram - HTMX, CRUD, dashboards, and extensions |
| `lexigram-ai` | 0.1.3007 | yes | AI Layer for Lexigram Framework - Native LLM, Vector, RAG integration |
| `lexigram-ai-agents` | 0.1.3007 | yes | Agent system for Lexigram Framework - AI agents with tools, strategies, and execution |
| `lexigram-ai-evaluation` | 0.1.3007 | yes | AI Evaluation framework for the Lexigram Framework |
| `lexigram-ai-feedback` | 0.1.3007 | yes | AI feedback collection for the Lexigram Framework — collection, processing, and storage |
| `lexigram-ai-governance` | 0.1.3007 | yes | AI governance for the Lexigram Framework — policy enforcement, audit trails, budget tracking |
| `lexigram-ai-guard` | 0.1.3007 | yes | AI input/output guard pipeline for the Lexigram Framework — LLM safety and content filtering |
| `lexigram-ai-llm` | 0.1.3007 | yes | LLM client layer for the Lexigram Framework — OpenAI, Anthropic, Ollama, Cohere, Groq, Mistral |
| `lexigram-ai-mcp` | 0.1.3007 | yes | MCP Server for Lexigram Framework - Model Context Protocol server for AI agents |
| `lexigram-ai-memory` | 0.1.3007 | yes | AI memory system for the Lexigram Framework — episodic, semantic, and working memory |
| `lexigram-ai-observability` | 0.1.3007 | yes | AI observability for the Lexigram Framework — tracing, metrics, and monitoring |
| `lexigram-ai-prompt` | 0.1.3007 | yes | AI prompt management for the Lexigram Framework — templates, composition, optimization |
| `lexigram-ai-rag` | 0.1.3007 | yes | Retrieval-Augmented Generation (RAG) pipeline for the Lexigram Framework |
| `lexigram-ai-relay` | 0.1.3007 | yes | Protocol-neutral conversion engine for the Lexigram AI relay — OpenAI Chat, Responses, Claude, and Gemini |
| `lexigram-ai-relay-gateway` | 0.1.3007 | yes | Protocol-facing relay gateway for the Lexigram AI relay — channel selection, orchestration, upstream I/O, and SSE handling |
| `lexigram-ai-session` | 0.1.3007 | yes | AI session management for the Lexigram Framework — branching, checkpointing, multi-agent sessions |
| `lexigram-ai-skills` | 0.1.3007 | yes | AI skills and tools for the Lexigram Framework — registry, executor, builtin tools, discovery |
| `lexigram-ai-workers` | 0.1.3007 | yes | AI background workers for the Lexigram Framework — batch embedding, document ingestion, DLQ, maintenance |
| `lexigram-audit` | 0.1.3007 | yes | Unified audit trail for the Lexigram Framework — append-only, HMAC-verified, retention-managed |
| `lexigram-auth` | 0.1.3007 | yes | Authentication and authorization for Lexigram Framework - JWT, OAuth2, SAML, LDAP, RBAC, and multi-tenancy |
| `lexigram-cache` | 0.1.3007 | yes | Multi-backend caching system for Lexigram Framework - Redis, Memcached, and in-memory caching |
| `lexigram-cli` | 0.1.3007 | yes | Command-line interface for Lexigram Framework - Project scaffolding, code generation, and development tools |
| `lexigram-contracts` | 0.1.3007 | yes | Core types and protocols for the Lexigram Framework |
| `lexigram-events` | 0.1.3007 | yes | Event Sourcing and CQRS engine for Lexigram Framework - Domain events, aggregates, and projections |
| `lexigram-features` | 0.1.3007 | yes | Feature flag management for the Lexigram Framework |
| `lexigram-graph` | 0.1.3007 | yes | Graph database support for the Lexigram Framework (Neo4j, in-memory) |
| `lexigram-graphql` | 0.1.3007 | yes | GraphQL support for Lexigram Framework - Strawberry, Apollo Federation, and subscriptions |
| `lexigram-http` | 0.1.3007 | yes | Outbound HTTP client for the Lexigram Framework |
| `lexigram-monitor` | 0.1.3007 | yes | Monitoring and observability for Lexigram Framework - Health checks, metrics, and system monitoring |
| `lexigram-multimedia` | 0.1.3007 | yes | Audio/video/image generation orchestrator for the Lexigram Framework |
| `lexigram-multimedia-beat` | 0.1.3007 | yes | Audio tempo/beat analysis for the Lexigram Framework — librosa and madmom backends |
| `lexigram-multimedia-image` | 0.1.3007 | yes | Image generation for the Lexigram Framework — local and API-based backends |
| `lexigram-multimedia-interpolate` | 0.1.3007 | yes | Video frame-rate interpolation for the Lexigram Framework — RIFE backend |
| `lexigram-multimedia-music` | 0.1.3007 | yes | Music generation for the Lexigram Framework — local and API-based backends |
| `lexigram-multimedia-tts` | 0.1.3007 | yes | Text-to-speech generation for the Lexigram Framework — local and API-based backends |
| `lexigram-multimedia-upscale` | 0.1.3007 | yes | Image and video super-resolution for the Lexigram Framework — Real-ESRGAN and HAT backends |
| `lexigram-multimedia-video` | 0.1.3007 | yes | Video generation for the Lexigram Framework — local and API-based backends |
| `lexigram-nosql` | 0.1.3007 | yes | NoSQL document store support for the Lexigram Framework (MongoDB, DynamoDB, Firestore) |
| `lexigram-notification` | 0.1.3007 | yes | SMS, push, and email notification delivery with Named DI multi-backend support for the Lexigram Framework |
| `lexigram-queue` | 0.1.3007 | yes | Message bus and queue with Named DI multi-backend support for the Lexigram Framework |
| `lexigram-resilience` | 0.1.3007 | yes | Resilience patterns for the Lexigram Framework (circuit breaker, retry, bulkhead, rate limiting, throttle, fallback) |
| `lexigram-search` | 0.1.3007 | yes | Full-text search and indexing for Lexigram Framework - Elasticsearch, Meilisearch, and Algolia |
| `lexigram-secrets` | 0.1.3007 | yes | Secret vaults with rotation, tenant scoping, and audit for Lexigram Framework |
| `lexigram-sql` | 0.1.3007 | yes | SQL database abstractions for Lexigram Framework — Postgres, MySQL, SQLite with migrations, repositories, and query building |
| `lexigram-storage` | 0.1.3007 | yes | Unified blob storage abstraction for Lexigram Framework - S3, GCS, Azure Blob, and local filesystem |
| `lexigram-tasks` | 0.1.3007 | yes | Background task processing for Lexigram Framework - Scheduling, workers, and job queues |
| `lexigram-tenancy` | 0.1.3007 | yes | Multi-tenant resolution, lifecycle, and isolation for the Lexigram Framework |
| `lexigram-testing` | 0.1.3007 | yes | Centralized testing infrastructure for Lexigram Framework - Fixtures, factories, and utilities |
| `lexigram-ui` | 0.1.3009 | yes | HTMX/htpy component library for Lexigram web applications |
| `lexigram-vector` | 0.1.3007 | yes | Vector store backends for the Lexigram Framework |
| `lexigram-web` | 0.1.3007 | yes | Web layer for Lexigram Framework - ASGI, routing, middleware, and API tooling |
| `lexigram-webhook` | 0.1.3007 | yes | Webhook management for the Lexigram Framework — subscription CRUD, delivery tracking, HMAC verification, and dead-letter queue |
| `lexigram-workflow` | 0.1.3007 | yes | Workflow orchestration for the Lexigram Framework (pipelines, bulk ops, sagas, graph engine) |

