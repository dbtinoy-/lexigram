---
title: lexigram-queue Configuration
description: Every config key, type, default, and environment variable.
sidebar:
  order: 4
---

Configuration is loaded from the `queue:` section of `application.yaml`. Unlike most extension packages, `QueueConfig` is passed explicitly to `QueueModule.configure(config)` rather than auto-injected via `config_key`.

## Env-Var Prefix

All keys can be overridden with environment variables using the prefix `LEX_QUEUE__`:

```bash
LEX_QUEUE__BACKENDS__0__DRIVER=redis \
LEX_QUEUE__BACKENDS__0__NAME=cache \
LEX_QUEUE__BACKENDS__0__PRIMARY=true \
LEX_QUEUE__BACKENDS__0__REDIS__URL=redis://localhost:6379/0
```

## Top Level: `QueueConfig`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `backends` | `list[NamedQueueConfig]` | `[]` | Named queue backend declarations |

## `NamedQueueConfig`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `name` | `str` | *(required)* | Unique backend ID, used as `Named()` DI key |
| `primary` | `bool` | `False` | Also register under unnamed `QueueProtocol` binding |
| `driver` | `str` | `"memory"` | Backend driver: `memory`, `redis`, `rabbitmq`, `kafka`, `sqs`, `azure_servicebus`, `gcp_pubsub` |
| `delivery_guarantee` | `str` | `"at_least_once"` | Delivery semantics |
| `max_retries` | `int` | `3` | Max retries before DLQ routing |
| `redis` | `RedisDriverConfig \| None` | `None` | Redis-specific settings |
| `rabbitmq` | `RabbitMQDriverConfig \| None` | `None` | RabbitMQ-specific settings |
| `kafka` | `KafkaDriverConfig \| None` | `None` | Kafka-specific settings |
| `sqs` | `SQSDriverConfig \| None` | `None` | SQS-specific settings |
| `azure_servicebus` | `AzureServiceBusDriverConfig \| None` | `None` | Azure Service Bus settings |
| `gcp_pubsub` | `GCPPubSubDriverConfig \| None` | `None` | GCP Pub/Sub settings |

## Driver Configs

### `RedisDriverConfig`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `url` | `str \| None` | `None` | Redis URL (`redis://host:port/db`) |
| `max_connections` | `int` | `10` | Connection pool size |
| `socket_timeout` | `float` | `5.0` | Socket timeout in seconds |

### `RabbitMQDriverConfig`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `url` | `str \| None` | `None` | AMQP URL (`amqp://user:pass@host/`) |
| `exchange` | `str` | `"lexigram"` | Exchange name |
| `prefetch_count` | `int` | `10` | Consumer prefetch count |

### `KafkaDriverConfig`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `bootstrap_servers` | `str \| None` | `None` | Kafka broker(s) (`host:port,host:port`) |
| `client_id` | `str` | `"lexigram"` | Client ID |
| `group_id` | `str` | `"lexigram-consumers"` | Consumer group ID |
| `auto_offset_reset` | `str` | `"latest"` | Offset reset: `earliest` or `latest` |

### `SQSDriverConfig`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `region` | `str` | `"us-east-1"` | AWS region |
| `queue_url` | `str \| None` | `None` | SQS queue URL |
| `visibility_timeout` | `int` | `30` | Visibility timeout in seconds |

### `AzureServiceBusDriverConfig`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `connection_str` | `str \| None` | `None` | Service Bus connection string |
| `queue_name` | `str` | `""` | Queue name |
| `max_message_count` | `int` | `10` | Max messages per receive call |
| `max_wait_time` | `float` | `5.0` | Max wait per receive call (seconds) |

### `GCPPubSubDriverConfig`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `project_id` | `str \| None` | `None` | GCP project ID |
| `topic_id` | `str` | `""` | Pub/Sub topic ID |
| `subscription_id` | `str` | `""` | Subscription ID for consuming |
| `max_messages` | `int` | `10` | Max messages per pull call |
| `max_wait_time` | `float` | `5.0` | gRPC pull timeout (seconds) |

## Minimal YAML Example

```yaml
queue:
  backends:
    - name: default
      driver: memory
      primary: true
```

## Multi-Backend YAML Example

```yaml
queue:
  backends:
    - name: notifications
      driver: redis
      primary: true
      max_retries: 5
      redis:
        url: "redis://localhost:6379/1"
        max_connections: 20

    - name: events
      driver: kafka
      delivery_guarantee: at_least_once
      kafka:
        bootstrap_servers: "localhost:9092,localhost:9093"
        group_id: order-consumers
        auto_offset_reset: earliest

    - name: audit
      driver: sqs
      sqs:
        region: us-west-2
        queue_url: "https://sqs.us-west-2.amazonaws.com/123456789/audit"
```

## Env-Var Form

```bash
LEX_QUEUE__BACKENDS__0__NAME=default \
LEX_QUEUE__BACKENDS__0__DRIVER=redis \
LEX_QUEUE__BACKENDS__0__PRIMARY=true \
LEX_QUEUE__BACKENDS__0__MAX_RETRIES=5 \
LEX_QUEUE__BACKENDS__0__REDIS__URL=redis://localhost:6379/1 \
LEX_QUEUE__BACKENDS__0__REDIS__MAX_CONNECTIONS=20
```
