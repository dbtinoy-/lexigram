# AUDIT_INTEGRATIONS.md — Lexigram Framework Integrations

> **Source**: Backend-style directories and dependency hints from `pyproject.toml`.

---

## Packages With Integration Signals

- Packages with integration signals: 21

| Package | Implementations | External Services |
|---------|-----------------|-------------------|
| `lexigram` | json | - |
| `lexigram-admin` | api_adapter, csv, excel, export_adapter, memory_adapter, pdf, repository, repository_adapter | - |
| `lexigram-ai` | - | Anthropic, Chroma, OpenAI, PostgreSQL, Qdrant, Redis, Weaviate |
| `lexigram-ai-llm` | anthropic, aws_bedrock, azure_openai, base, cloudflare_workers, cohere, database, gemini, gemini_helpers, groq, memory, mistral, ollama, openai, openai_compatible, openrouter, vertex_ai | Anthropic, OpenAI, Redis |
| `lexigram-ai-mcp` | agent_tools, skill_adapter, tool_adapter | - |
| `lexigram-ai-memory` | cache, database, in_memory, vector | Redis |
| `lexigram-ai-workers` | loader_worker, rag_adapter, tasks_adapter | - |
| `lexigram-cache` | factory, hash, memcached, memory, memory_lock, memory_secrets, memory_state, redis, registry | Redis |
| `lexigram-events` | adapter_wirers, azure_servicebus, base, kafka, rabbitmq, registry, retry | Kafka, PostgreSQL, SQLite |
| `lexigram-features` | base, cache, chained, env, local, testing | - |
| `lexigram-graph` | base, memory, neo4j | - |
| `lexigram-monitor` | db_exporter, exporters, opentelemetry, prometheus, registry | - |
| `lexigram-nosql` | base, dynamodb, firestore, mongodb | MongoDB |
| `lexigram-notification` | push, slack, sms | - |
| `lexigram-queue` | azure_servicebus, gcp_pubsub, kafka, memory, rabbitmq, redis, sqs | Kafka, Redis |
| `lexigram-search` | base, cached, elasticsearch, factory, meilisearch, mongodb, mysql, null, opensearch, postgres, sqlite, translate, typesense | MySQL, PostgreSQL, SQLite |
| `lexigram-sql` | cockroachdb, mysql, postgres, sqlite | MySQL, PostgreSQL, SQLite |
| `lexigram-storage` | azure, base, gcs, local, memory, protocols, registry, s3, unavailable | S3 |
| `lexigram-tasks` | memory, postgres, rabbitmq, redis, registry | Redis |
| `lexigram-testing` | ai, auth, cache, db, events, search, storage, tasks, ui, web | Kafka, PostgreSQL, Qdrant, Redis, SQLite |
| `lexigram-vector` | base, chroma, chroma_filters, document_store, memory, pgvector, pinecone, qdrant, vector_store, weaviate | Chroma, PostgreSQL, Qdrant, Weaviate |

