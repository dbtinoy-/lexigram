---
title: lexigram-monitor How-Tos
description: Task-oriented recipes for common monitoring operations.
---

## How do I create and increment a counter?

```python
from lexigram.monitor import Counter

provider = await container.resolve(MonitorProvider)
counter = provider.create_counter(
    "api_requests_total",
    "Total API requests",
    labels={"method": "", "endpoint": ""},
)
counter.increment(labels={"method": "GET", "endpoint": "/users"})
counter.increment(5, labels={"method": "POST", "endpoint": "/users"})
```

## How do I track request durations with a histogram?

```python
provider = await container.resolve(MonitorProvider)
histogram = provider.create_histogram(
    "api_latency_seconds",
    "API request latency",
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)
histogram.observe(0.125, labels={"method": "GET"})
```

## How do I set up Prometheus with a /metrics endpoint?

```python
from lexigram.monitor import MonitorProvider
from lexigram.monitor.backends.prometheus import PrometheusBackend
from lexigram.monitor.middleware import PrometheusMiddleware

backend = PrometheusBackend(port=8000, path="/metrics")
app.add_provider(MonitorProvider(backend=backend))

# Wrap the web ASGI app (if using lexigram-web):
# web_app = await container.resolve(WebProvider).get_app()
# app = PrometheusMiddleware(web_app, path="/metrics")
```

## How do I create a custom health check?

```python
from lexigram.monitor.health import (
    HealthCheck,
    HealthCheckResult,
    HealthStatus,
    HealthCheckRegistry,
)


class RedisHealthCheck(HealthCheck):
    def __init__(self, redis_client) -> None:
        self.redis = redis_client

    async def check(self, timeout: float = 5.0) -> HealthCheckResult:
        try:
            await self.redis.ping()
            return HealthCheckResult(
                component="redis", status=HealthStatus.HEALTHY
            )
        except ConnectionError as e:
            return HealthCheckResult(
                component="redis",
                status=HealthStatus.UNHEALTHY,
                error=str(e),
            )


# Register
registry = await container.resolve(HealthCheckRegistry)
registry.register("redis", RedisHealthCheck(redis=client))
```

## How do I trace a function with OpenTelemetry?

```python
from lexigram.monitor import traced

@traced("process_payment")
async def process_payment(order_id: str, amount: float) -> None:
    with tracer.start_span("validate") as span:
        span.set_attribute("order_id", order_id)
        span.set_attribute("amount", amount)
        # ... validation logic

    # This function call will be traced with span name "process_payment"
    result = await payment_gateway.charge(amount)
```

## How do I use the Prometheus Pushgateway for batch jobs?

```python
from lexigram.monitor.backends.prometheus import PrometheusBackend

# Configure pushgateway
config = PrometheusConfig(
    pushgateway_url="http://pushgateway:9091",
    push_interval=10.0,
)
backend = PrometheusBackend(config=config)
app.add_provider(MonitorProvider(backend=backend))

# Metrics are automatically pushed every 10 seconds
```

## How do I record an HTTP request manually?

```python
provider = await container.resolve(MonitorProvider)
provider.record_request(
    method="GET",
    path="/api/users",
    duration=0.125,
    status_code=200,
)
```

## How do I configure SLO monitoring?

```python
from lexigram.monitor.slo import SLO, SLOMonitor

slo = SLO(
    name="api_availability",
    description="API availability SLO",
    target=99.9,  # 99.9%
    window_seconds=86400,  # 1 day
)
monitor = SLOMonitor(slos=[slo])

# Record observations
monitor.record_observation(success=True)  # successful request
monitor.record_observation(success=False)  # failed request

# Check compliance
status = monitor.get_status("api_availability")
print(f"Compliance: {status.compliance}%")
```

## How do I profile a function?

```python
from lexigram.monitor import profile_async_function

result = await profile_async_function(my_function, arg1, arg2)
print(f"Duration: {result.duration_ms}ms")
print(f"Calls: {result.call_count}")
```
