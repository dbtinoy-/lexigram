---
title: "Choosing Backends"
description: "Comparison matrices and decision guides for cache, search, storage, queue, and database backends."
---

Choosing the right backend for each subsystem depends on your scale, latency requirements, operational budget, and feature needs. This guide compares options across every backend category in the Lexigram ecosystem.

## Cache Backends

| Backend | Best For | Key Trade-off |
|---------|----------|---------------|
| `memory` | Dev, single-process, low-traffic | No persistence, lost on restart, not shared across processes |
| `redis` | Production caching, rate limiting, pub/sub | Requires Redis server; O(1) ops, TTL, persistence optional |
| `memcached` | Simple key-value, high throughput | No persistence, no replication, no data structures |

:::note
For production deployments, **redis** is the recommended default. Use `memory` for testing and local development. Memcached is a viable choice if you only need a simple, fast cache and already operate a memcached cluster.
:::

## Search Backends

| Backend | Best For | Key Trade-off |
|---------|----------|---------------|
| `meilisearch` | Typo-tolerant search, quick setup | Less mature than ES; smaller ecosystem |
| `elasticsearch` | Complex queries, large-scale analytics | Heavy ops overhead, resource hungry |
| `typesense` | Low-latency instant search | Smaller community, fewer integrations |
| `sqlite/postgres fts` | Simple full-text, no extra infra | Limited relevance tuning, basic feature set |

:::tip
Start with **postgres FTS** if you already use PostgreSQL. Reach for **Meilisearch** when you need typo tolerance and instant results. **Elasticsearch** is overkill for most applications — only adopt when you need its analytics or aggregation pipeline.
:::

## Storage Backends

| Backend | Best For | Key Trade-off |
|---------|----------|---------------|
| `local` | Dev, single-server file storage | Not distributed; no CDN, no durability guarantees |
| `s3` | General object storage, high durability | Egress costs, eventual consistency (some regions) |
| `gcs` | GCP-native, strong consistency | Slightly higher cost than S3 in some tiers |
| `azure` | Azure-native, AD integration | Lock-in to Azure ecosystem |
| `r2` | Zero egress fees, S3-compatible | Newer, smaller ecosystem |

:::note
All cloud backends support **presigned URLs** for direct client uploads. R2 is an especially attractive option for bandwidth-heavy workloads due to zero egress fees.
:::

## Queue Backends

| Backend | Best For | Key Trade-off |
|---------|----------|---------------|
| `memory` | Dev, testing, single-process | No durability, lost on restart |
| `redis` | Simple queues, low-latency | No delivery guarantees beyond "at most once" by default |
| `rabbitmq` | Reliable delivery, complex routing | Ops overhead, needs Erlang runtime |
| `kafka` | High-throughput, event streaming, replay | Heavy ops complexity, higher latency per message |
| `sqs` | Managed queues, AWS-native | Lock-in, polling cost at scale |

:::tip
Start with **redis** for most applications. Reach for **RabbitMQ** when you need reliable delivery and routing. Choose **Kafka** only when you need event streaming, replay, or high throughput (10k+ msg/s).
:::

## Database Backends

### SQL

| Backend | Best For | Key Trade-off |
|---------|----------|---------------|
| `sqlite` | Embedded, single-server, dev | No concurrent writers, limited ALTER TABLE |
| `postgres` | Production — most applications | Heavier resource footprint than SQLite |
| `mysql` | Read-heavy workloads, replication | Weaker JSON/array support than Postgres |

### NoSQL

| Backend | Best For | Key Trade-off |
|---------|----------|---------------|
| `mongodb` | Flexible schemas, document store | No joins, weaker consistency |
| `dynamodb` | Managed, auto-scaling, AWS-native | Query patterns must be designed upfront, cost at scale |
| `firestore` | Real-time sync, GCP-native | Limited query capabilities, vendor lock-in |

:::note
**PostgreSQL** is the recommended default for most projects. It handles relational and JSON workloads well. Choose SQLite for embedded or dev use. Reserve NoSQL backends for specific use cases (high-volume time series, real-time sync, flexible schemas at scale).
:::

## Vector Backends

| Backend | Best For | Key Trade-off |
|---------|----------|---------------|
| `memory` | Dev, small datasets (<10k vectors) | No persistence, lost on restart |
| `pgvector` | Postgres-native, integrated with SQL data | Limited index types, slower at scale |
| `qdrant` | High-performance vector search, filtering | Requires separate service |
| `pinecone` | Fully managed, serverless | Vendor lock-in, egress costs |

:::tip
If you already use PostgreSQL, **pgvector** is the easiest path. For production RAG at scale, **Qdrant** offers the best balance of performance and self-hosting flexibility. Pinecone is ideal when you want zero ops, but watch for egress costs.
:::

---

See the [Packages](/packages/) reference for installation and configuration details for each backend.
