# lexigram-example-worker

A reference application demonstrating Lexigram Framework's **async background worker capabilities**.

## What It Demonstrates

| Feature | File | Framework Packages |
|---------|------|--------------------|
| Email campaign sender | `consumers/campaign_consumer.py`, `tasks/send_email_batch.py` | `lexigram-queue`, `lexigram-tasks` |
| Report generator with workflow state machine | `tasks/generate_report.py`, `workflows/report_workflow.py` | `lexigram-workflow`, `lexigram-tasks` |
| Scheduled periodic cleanup | `tasks/cleanup_old_records.py` | `lexigram-tasks` (cron scheduler) |
| Dead letter queue handling | `consumers/campaign_consumer.py`, `di/provider.py` | `lexigram-queue`, `lexigram-tasks` |

## Quick Start

```bash
# Start infrastructure
docker compose up -d

# Run the worker
cd lexigram-example-worker
uv run python -m lexigram_example_worker.main
```

## Running Tests

```bash
# Unit tests (no infrastructure needed)
uv run pytest tests/unit/ -v

# Integration smoke tests
uv run pytest tests/integration/ -v

# All tests with coverage
uv run pytest --cov=lexigram_example_worker --cov-fail-under=80
```

## Architecture Overview

```
WorkerProvider (di/provider.py)
├── registers: SendEmailBatchHandler, GenerateReportHandler, CleanupOldRecordsHandler
├── registers: DeadLetterQueue (tasks DLQ)
├── registers: CampaignConsumer (queue consumer)
└── boots: TasksModule (in-memory queue for dev / Redis for prod)

main.py
└── Application
    └── WorkerProvider
        └── providers: [TaskProvider, QueueProvider]
```

## Key Lexigram Patterns Shown

### 1. `Result[T, E]` — Domain-safe task outcomes
```python
async def execute(self, payload: EmailBatchPayload) -> Result[BatchResult, DomainError]:
    if not payload.recipient_ids:
        return Err(DomainError("recipient_ids cannot be empty"))
    ...
    return Ok(BatchResult(sent=len(payload.recipient_ids)))
```

### 2. Constructor Injection — Tasks receive deps via `__init__`
```python
class GenerateReportHandler:
    def __init__(self, dlq: DeadLetterQueue) -> None:
        self._dlq = dlq
```

### 3. Provider Pattern — `WorkerProvider` wires everything
```python
class WorkerProvider(Provider):
    name = "worker"
    priority = ProviderPriority.NORMAL

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        container.singleton(DeadLetterQueue, DeadLetterQueue())
        ...
```

### 4. State Machine — Report workflow (`queued → processing → done | failed`)
```python
sm = StateMachine(
    states=[
        State("queued", transitions={"start": Transition("start", "processing")}),
        State("processing", transitions={
            "complete": Transition("complete", "done"),
            "fail": Transition("fail", "failed"),
        }),
        State("done"),
        State("failed"),
    ],
    initial_state="queued",
)
await sm.transition("start")
await sm.transition("complete")
```

### 5. Message Consumer — Queue-driven campaign processing
```python
class CampaignConsumer(MessageConsumer):
    topic = "campaigns.queued"

    async def handle(self, message: BusMessage) -> None:
        payload = CampaignPayload(**message.payload)
        result = await self._handler.execute(payload)
        if result.is_err():
            await self._dlq.push(message, str(result.unwrap_err()))
```

### 6. Scheduled Task — Cron-driven cleanup
```python
@scheduled(cron="0 3 * * *", name="cleanup_old_records")
async def cleanup_old_records() -> None:
    ...
```

## Configuration

Copy `.env.example` (not included — configure via environment variables):

| Variable | Default | Description |
|----------|---------|-------------|
| `WORKER_QUEUE_DRIVER` | `memory` | Queue backend (`memory`, `redis`, `rabbitmq`) |
| `WORKER_REDIS_URL` | `redis://localhost:6379/0` | Redis URL |
| `WORKER_RABBITMQ_URL` | `amqp://guest:guest@localhost/` | RabbitMQ URL |
| `WORKER_CONCURRENCY` | `4` | Concurrent task workers |
| `WORKER_DLQ_MAX_SIZE` | `10000` | Dead letter queue capacity |
| `WORKER_DLQ_RETENTION_HOURS` | `168` | Hours to retain DLQ entries (7 days) |

## File Layout

```
src/lexigram_example_worker/
├── main.py                    # Boots Application + WorkerProvider
├── config.py                  # WorkerConfig (Pydantic Settings)
├── module.py                  # WorkerModule (application module)
├── domain/
│   ├── campaign.py            # Campaign dataclass + CampaignQueued event
│   └── report.py              # Report dataclass + ReportStatus enum
├── tasks/
│   ├── send_email_batch.py    # SendEmailBatchHandler (Result-returning)
│   ├── generate_report.py     # GenerateReportHandler (drives workflow state)
│   └── cleanup_old_records.py # @scheduled cleanup task
├── workflows/
│   └── report_workflow.py     # ReportWorkflow (StateMachine wrapper)
├── consumers/
│   └── campaign_consumer.py   # CampaignConsumer (MessageConsumer subclass)
└── di/
    └── provider.py            # WorkerProvider (DI wiring)
```
