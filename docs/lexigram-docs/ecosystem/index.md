---
title: The Ecosystem
description: Every open-source Lexigram package, grouped by what it does.
sidebar:
  order: 1
---

Lexigram is a monorepo of small, focused packages. The two foundation packages — `lexigram` and `lexigram-contracts` — are all you need to start. Everything else is an **extension**: install only what your application uses.

Every extension depends **only** on `lexigram` and `lexigram-contracts`, never on another extension. That boundary is what keeps the ecosystem composable — see [Architecture](/fundamentals/architecture/).

:::note[Maturity]
All packages are **alpha (0.1.x)** and MIT-licensed. Public APIs may change before 1.0.
:::

```bash
# Install the foundation plus only the extensions you need
pip install lexigram lexigram-web lexigram-sql lexigram-auth
```

---

## Foundation

| Package | What it does |
|---------|--------------|
| [`lexigram`](/packages/lexigram/) | Async-first DI container, `Application` lifecycle, modules, providers, config, and the `Result` type. |
| [`lexigram-contracts`](/packages/lexigram-contracts/) | Zero-dependency protocols, value types, and exceptions shared across every package. |

---

## Web & API

| Package | What it does |
|---------|--------------|
| [`lexigram-web`](/packages/lexigram-web/) | ASGI web layer — controllers, routing, middleware, OpenAPI docs, CORS, CSRF, rate limiting. `WebProvider`. |
| [`lexigram-graphql`](/packages/lexigram-graphql/) | GraphQL server (Strawberry) — schema, subscriptions, depth/complexity limits, persisted queries. |
| [`lexigram-http`](/packages/lexigram-http/) | Outbound HTTP client with resilience and observability built in. |

---

## Data & Persistence

| Package | What it does |
|---------|--------------|
| [`lexigram-sql`](/packages/lexigram-sql/) | Async SQL for Postgres / MySQL / SQLite — repositories, migrations, query building. `DatabaseProvider`. |
| [`lexigram-nosql`](/packages/lexigram-nosql/) | Document-store abstraction (MongoDB, DynamoDB, Firestore). |
| [`lexigram-cache`](/packages/lexigram-cache/) | Multi-backend caching — Redis, Memcached, in-memory — behind `CacheBackendProtocol`. |
| [`lexigram-storage`](/packages/lexigram-storage/) | Unified blob storage — S3, GCS, Azure Blob, R2, local filesystem. |
| [`lexigram-search`](/packages/lexigram-search/) | Full-text search — Elasticsearch, Meilisearch, Typesense, and SQL backends. |
| [`lexigram-vector`](/packages/lexigram-vector/) | Vector store backends (pgvector, Qdrant, Pinecone, in-memory) for embeddings. |
| [`lexigram-graph`](/packages/lexigram-graph/) | Graph database support (Neo4j, in-memory). |

---

## AI

| Package | What it does |
|---------|--------------|
| [`lexigram-ai`](/packages/lexigram-ai/) | Orchestration layer that discovers and wires the AI subsystems below. |
| [`lexigram-ai-llm`](/packages/lexigram-ai-llm/) | Multi-provider LLM client (OpenAI, Anthropic, Gemini, Ollama, Groq, Mistral, …) with routing and thinking suppression. |
| [`lexigram-ai-rag`](/packages/lexigram-ai-rag/) | Retrieval-augmented generation — chunking, retrieval, synthesis, citations. |
| [`lexigram-ai-agents`](/packages/lexigram-ai-agents/) | Agents with tools and strategies (ReAct, plan-and-execute). |
| [`lexigram-ai-memory`](/packages/lexigram-ai-memory/) | Episodic, semantic, and working memory for AI systems. |
| [`lexigram-ai-skills`](/packages/lexigram-ai-skills/) | Skill/tool registry, executor, and built-in tools. |
| [`lexigram-ai-session`](/packages/lexigram-ai-session/) | AI conversation sessions — branching, checkpointing, multi-agent. |
| [`lexigram-ai-mcp`](/packages/lexigram-ai-mcp/) | Model Context Protocol server and client for AI agents. |
| [`lexigram-ai-workers`](/packages/lexigram-ai-workers/) | Background AI work — batch embedding, document ingestion, maintenance. |
| [`lexigram-ai-feedback`](/packages/lexigram-ai-feedback/) | Collect, process, and store feedback on AI responses. |
| [`lexigram-ai-guard`](/packages/lexigram-ai-guard/) | Input/output guard pipeline — LLM safety and content filtering. |
| [`lexigram-ai-governance`](/packages/lexigram-ai-governance/) | AI governance — policy enforcement, audit trails, budget tracking. |
| [`lexigram-ai-evaluation`](/packages/lexigram-ai-evaluation/) | Evaluation framework — benchmarks and quality gates for AI outputs. |
| [`lexigram-ai-prompt`](/packages/lexigram-ai-prompt/) | Prompt management — templates, composition, optimization. |

---

## Messaging, Events & Workflow

| Package | What it does |
|---------|--------------|
| [`lexigram-events`](/packages/lexigram-events/) | Event sourcing and CQRS — domain events, aggregates, command/query buses, projections. |
| [`lexigram-queue`](/packages/lexigram-queue/) | Message bus / queue with named multi-backend support (Redis, RabbitMQ, Kafka, SQS, …). |
| [`lexigram-notification`](/packages/lexigram-notification/) | Email, SMS, and push delivery with multi-backend support. |
| [`lexigram-webhook`](/packages/lexigram-webhook/) | Webhook management — subscriptions, delivery tracking, HMAC verification, dead-letter queue. |
| [`lexigram-workflow`](/packages/lexigram-workflow/) | Workflow orchestration — pipelines, bulk ops, sagas, graph engine. |

---

## Background Work

| Package | What it does |
|---------|--------------|
| [`lexigram-tasks`](/packages/lexigram-tasks/) | Background tasks — scheduling, workers, and job queues over memory / Redis / AMQP / Postgres. |

---

## Observability & Reliability

| Package | What it does |
|---------|--------------|
| [`lexigram-monitor`](/packages/lexigram-monitor/) | Health checks, metrics, tracing, and structured logging (Prometheus / OpenTelemetry). |
| [`lexigram-resilience`](/packages/lexigram-resilience/) | Circuit breaker, retry, bulkhead, rate limiting, throttle, fallback. |
| [`lexigram-audit`](/packages/lexigram-audit/) | Append-only, HMAC-verified, retention-managed audit trail. |
| [`lexigram-ai-observability`](/packages/lexigram-ai-observability/) | Tracing, metrics, and health checks specific to AI calls. |

---

## Security & Multi-Tenancy

| Package | What it does |
|---------|--------------|
| [`lexigram-auth`](/packages/lexigram-auth/) | Authentication & authorization — JWT, OAuth2, RBAC, password hashing, web guards. |
| [`lexigram-tenancy`](/packages/lexigram-tenancy/) | Multi-tenant resolution, lifecycle, and isolation strategies. |
| [`lexigram-features`](/packages/lexigram-features/) | Feature-flag management with caching and pluggable providers. |

---

## Developer Tooling

| Package | What it does |
|---------|--------------|
| [`lexigram-cli`](/packages/lexigram-cli/) | `lexigram` command — project scaffolding (`new`), dev server (`run`/`dev`), migrations (`db`), inspection. |
| [`lexigram-testing`](/packages/lexigram-testing/) | Fakes, test clients/beds, fixed clock, and protocol compliance suites for fast, decoupled tests. |

---

## Choosing Packages

A typical web application starts with:

```bash
pip install lexigram lexigram-web lexigram-sql lexigram-auth lexigram-cache
```

Add capabilities as you need them — `lexigram-ai-llm` for an LLM feature, `lexigram-tasks` for background jobs, `lexigram-events` for an event-driven domain. Because every package targets a contract, you can adopt one without rewriting the rest of your app.

---

## Next Steps

- [Installation](/getting-started/installation/) — set up your environment
- [Architecture](/fundamentals/architecture/) — the boundary rules that hold the ecosystem together
- [Your First App](/getting-started/first-app/) — wire `lexigram-web` end to end
