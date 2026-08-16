---
title: lexigram-queue Troubleshooting
description: Common errors, their causes, and solutions.
sidebar:
  order: 6
---

## QueueProtocol Not Resolved

**Error:**
```
ContainerError: No binding registered for QueueProtocol
```

**Cause:** `QueueModule.configure(config)` was not added to your module's `imports`, or the backends list is empty.

**Fix:**
```python
@module(imports=[QueueModule.configure(config)])
class AppModule(Module):
    pass
```

Verify `config.backends` has at least one entry with `primary=True`.

## Redis Backend: Connection Refused

**Error:**
```
lexigram.queue.exceptions.RedisQueueError: Connection refused
```

**Cause:** Redis server is not running or the URL is wrong.

**Fix:** Check the `url` in `RedisDriverConfig`:
```python
NamedQueueConfig(
    name="default",
    driver="redis",
    redis=RedisDriverConfig(url="redis://localhost:6379/1"),
)
```

## Kafka Backend: Leader Not Available

**Error:**
```
lexigram.queue.exceptions.KafkaQueueError: LeaderNotAvailable
```

**Cause:** Kafka broker is unreachable, or topic does not exist and auto-creation is disabled.

**Fix:** Verify `KafkaDriverConfig.bootstrap_servers` and broker availability:
```bash
kafka-topics.sh --bootstrap-server localhost:9092 --list
```

## SQS Backend: Access Denied

**Error:**
```
lexigram.queue.exceptions.SQSQueueError: AccessDenied
```

**Cause:** AWS credentials lack permission to publish/subscribe to the queue.

**Fix:** Update IAM policy to include `sqs:SendMessage` and `sqs:ReceiveMessage`.

## Azure Service Bus: Authentication Failed

**Error:**
```
lexigram.queue.exceptions.AzureServiceBusQueueError: Authentication failed
```

**Cause:** Connection string is invalid or expired.

**Fix:** Regenerate the connection string in the Azure portal and update `AzureServiceBusDriverConfig.connection_str`.

## GCP Pub/Sub: Topic Not Found

**Error:**
```
lexigram.queue.exceptions.GCPPubSubQueueError: Topic not found
```

**Cause:** The Pub/Sub topic does not exist in the GCP project.

**Fix:** Create the topic or verify `GCPPubSubDriverConfig.topic_id` and `project_id`.

## Unsupported Queue Driver

**Error:**
```
ValueError: Unsupported queue driver: my_driver
```

**Cause:** The `driver` field in `NamedQueueConfig` is not one of the supported values.

**Fix:** Use one of: `memory`, `redis`, `rabbitmq`, `kafka`, `sqs`, `azure_servicebus`, `gcp_pubsub`.

## No Primary Backend Defined

**Runtime behavior:** `QueueProtocol` fails to resolve for unnamed injection.

**Cause:** No backend has `primary=True` when you attempt unnamed `QueueProtocol` resolution.

**Fix:** Set `primary=True` on at least one backend entry, or use named injection (`Annotated[QueueProtocol, Named("name")]`).

## Debug Tips

- Enable logging: set `queue.backends[i].enable_logging` (future) or use the framework logger at `DEBUG` level.
- Check backend health: `queue.health_check(timeout=5.0)` returns aggregated status for all backends.
- Verify container bindings: `container.is_registered(QueueProtocol)` and `container.find(QueueProtocol, name="events")`.
- Override memory backend in tests using `QueueModule.stub()` — no external broker required.
