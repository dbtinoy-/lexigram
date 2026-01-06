---
title: lexigram-nosql Backends
description: Compare MongoDB, DynamoDB, and Firestore backends for lexigram-nosql
sidebar:
  order: 3
---

`lexigram-nosql` provides document store backends behind the `DocumentStoreProtocol` contract from `lexigram-contracts`. All backends extend `AbstractDocumentStore` and expose the same collection, query, and session APIs.

## Supported Backends

| Backend | Extra | Driver | Provider-wired | Best for |
|---------|-------|--------|---------------|----------|
| MongoDB | `lexigram-nosql[mongodb]` | `motor>=3.0` | Yes (fully wired) | Document store with rich queries, aggregations |
| DynamoDB | `lexigram-nosql[dynamodb]` | `aioboto3>=11.0.0` | No (direct use) | AWS-native, auto-scaling, single-table designs |
| Firestore | `lexigram-nosql[firestore]` | `google-cloud-firestore>=2.19.0` | No (direct use) | GCP-native, real-time sync, serverless |

Install extras: `pip install lexigram-nosql[mongodb,dynamodb,firestore]`.

:::caution Provider Wiring
`NoSQLProvider` wires MongoDB via `MongoDBDocumentStore` at dependency-injection time. DynamoDB and Firestore backends (`DynamoDBBackend`, `FirestoreBackend`) exist in `src/lexigram/nosql/backends/` but are not yet wired in `NoSQLProvider._create_store()`. Use them directly by instantiating the backend class.
:::

## Backend Details

### MongoDB

Production-grade document store backed by `motor`, the official async MongoDB driver.

- **Strengths:** Rich query DSL, powerful aggregation pipelines, native replication and sharding, flexible schema. Read/write concern, retry logic, connection pooling, and full authentication support. The `MongoDBDocumentStore` class provides collection management, session-backed transactions, and TLS.
- **Weaknesses:** Requires a running MongoDB server. Schema flexibility can lead to data drift without discipline.
- **When to choose:** Document-oriented workloads, content management, event sourcing, user profiles, or any workload needing ad-hoc queries and aggregations.

Config fields mirror the `MongoDBConfig` model:

```yaml
nosql:
  driver: mongodb
  mongodb:
    uri: mongodb://localhost:27017
    database: lexigram
    max_pool_size: 100
    retry_writes: true
    retry_reads: true
```

### DynamoDB

AWS DynamoDB backend via `aioboto3`. Each logical collection maps to a separate DynamoDB table.

- **Strengths:** Fully managed, auto-scaling, predictable single-digit-millisecond performance at any scale. No server management. Works well with single-table designs.
- **Weaknesses:** Limited query capabilities compared to MongoDB — no ad-hoc aggregations, no joins. Requires careful key design. Higher latency for infrequent access patterns. Table-per-collection model (DynamoDB has a 256-table per-region soft limit).
- **When to choose:** You're already on AWS, need auto-scaling, or have a well-partitioned access pattern that fits single-table design.

Config:

```yaml
nosql:
  driver: dynamodb
  dynamodb:
    region: us-east-1
    endpoint_url: http://localhost:8000  # LocalStack / DynamoDB Local
    pk_field: _id
```

Use directly:

```python
from lexigram.nosql.backends.dynamodb.backend import DynamoDBBackend
from lexigram.nosql.config import DynamoDBConfig

store = DynamoDBBackend(config=DynamoDBConfig(region="us-east-1"))
await store.connect()
```

### Firestore

Google Cloud Firestore backend using `google-cloud-firestore`'s async client (`AsyncClient`).

- **Strengths:** Serverless, real-time listeners, strong consistency, multi-region replication. Tight integration with Firebase and GCP ecosystem. No cluster management.
- **Weaknesses:** Scaling limits (1 write/sec per document), no ad-hoc aggregations, limited query capabilities (no `!=`, no `OR` in a single query). Document size limit of 1 MiB. Only suitable for moderate-traffic applications.
- **When to choose:** You're on GCP, need real-time sync to clients, have moderate write throughput, or want a serverless document store.

Config:

```yaml
nosql:
  driver: firestore
  firestore:
    project_id: my-gcp-project
    database_id: "(default)"
```

Use directly:

```python
from lexigram.nosql.backends.firestore.backend import FirestoreBackend
from lexigram.nosql.config import FirestoreConfig

store = FirestoreBackend(config=FirestoreConfig(project_id="my-gcp-project"))
await store.connect()
```

## Quick Selection Guide

- **I need rich queries, aggregations, or flexible schema** → `mongodb`.
- **I'm on AWS and want auto-scaling** → `dynamodb`.
- **I'm on GCP or need real-time sync** → `firestore`.
- **I'm writing unit tests** → Point any backend at a local emulator (MongoDB memory server, DynamoDB Local, Firestore emulator).

## Multi-Backend Configuration

Named backends work with MongoDB (added via `NoSQLConfig.backends`):

```yaml
nosql:
  backends:
    - name: primary
      driver: mongodb
      primary: true
      mongodb:
        uri: mongodb://localhost:27017
        database: app
    - name: analytics
      driver: mongodb
      mongodb:
        uri: mongodb://analytics-host:27017
        database: analytics
```

Resolve:

```python
from typing import Annotated
from lexigram.contracts.data.nosql import DocumentStoreProtocol
from lexigram.di import Named

class AnalyticsService:
    def __init__(
        self,
        primary: DocumentStoreProtocol,
        analytics: Annotated[DocumentStoreProtocol, Named("analytics")],
    ):
        ...
```
