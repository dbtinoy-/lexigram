"""OpenTelemetry instrumentation for messaging (email, SMS, push).

Provides automatic tracing and metrics for message publishing and consuming.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import time
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.propagate import inject
from opentelemetry.trace import Span, StatusCode

tracer = trace.get_tracer("lexigram.messaging")
meter = metrics.get_meter("lexigram.messaging")

# Metrics
messages_published = meter.create_counter(
    "messaging.messages_published_total",
    unit="1",
    description="Total number of messages published",
)

messages_consumed = meter.create_counter(
    "messaging.messages_consumed_total",
    unit="1",
    description="Total number of messages consumed",
)

message_duration = meter.create_histogram(
    "messaging.operation_duration",
    unit="ms",
    description="Duration of messaging operations",
)

message_errors = meter.create_counter(
    "messaging.errors_total",
    unit="1",
    description="Total number of messaging errors",
)


@asynccontextmanager
async def trace_publish(
    channel: str,
    message_type: str = "email",
    recipient: str | None = None,
    **attributes: Any,
) -> AsyncGenerator[Span, None]:
    """Context manager for tracing message publishing.

    Usage:
        async with trace_publish("notifications", "email", "user@example.com") as span:
            await send_email(...)
    """
    start_time = time.time()
    span_name = f"publish {message_type}"

    with tracer.start_as_current_span(
        span_name,
        kind=trace.SpanKind.PRODUCER,
    ) as span:
        span.set_attribute("messaging.system", "lexigram")
        span.set_attribute("messaging.operation", "publish")
        span.set_attribute("messaging.destination", channel)
        span.set_attribute("messaging.message_type", message_type)

        if recipient:
            # Redact full recipient for privacy
            span.set_attribute(
                "messaging.recipient_type",
                _get_recipient_type(recipient),
            )

        for key, value in attributes.items():
            span.set_attribute(f"messaging.{key}", str(value))

        try:
            yield span
            span.set_status(trace.Status(StatusCode.OK))
            messages_published.add(
                1,
                {
                    "messaging.message_type": message_type,
                    "messaging.destination": channel,
                },
            )
        except (OSError, ConnectionError, RuntimeError, ValueError) as e:
            span.record_exception(e)
            span.set_status(trace.Status(StatusCode.ERROR, str(e)))
            message_errors.add(
                1,
                {
                    "messaging.message_type": message_type,
                    "messaging.destination": channel,
                },
            )
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            message_duration.record(
                duration_ms,
                {
                    "messaging.operation": "publish",
                    "messaging.message_type": message_type,
                },
            )


@asynccontextmanager
async def trace_consume(
    channel: str,
    message_type: str = "unknown",
    carrier: dict[str, Any] | None = None,
    **attributes: Any,
) -> AsyncGenerator[Span, None]:
    """Context manager for tracing message consumption.

    Usage:
        async with trace_consume("notifications", carrier=headers) as span:
            await process_message(...)
    """
    start_time = time.time()
    span_name = f"consume {message_type}"

    # Extract parent context from carrier if provided
    parent_context = None
    if carrier:
        from opentelemetry.propagate import extract

        parent_context = extract(carrier)

    with tracer.start_as_current_span(
        span_name,
        context=parent_context,
        kind=trace.SpanKind.CONSUMER,
    ) as span:
        span.set_attribute("messaging.system", "lexigram")
        span.set_attribute("messaging.operation", "consume")
        span.set_attribute("messaging.destination", channel)
        span.set_attribute("messaging.message_type", message_type)

        for key, value in attributes.items():
            span.set_attribute(f"messaging.{key}", str(value))

        try:
            yield span
            span.set_status(trace.Status(StatusCode.OK))
            messages_consumed.add(
                1,
                {
                    "messaging.message_type": message_type,
                    "messaging.destination": channel,
                },
            )
        except (OSError, ConnectionError, RuntimeError, ValueError) as e:
            span.record_exception(e)
            span.set_status(trace.Status(StatusCode.ERROR, str(e)))
            message_errors.add(
                1,
                {
                    "messaging.message_type": message_type,
                    "messaging.destination": channel,
                },
            )
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            message_duration.record(
                duration_ms,
                {
                    "messaging.operation": "consume",
                    "messaging.message_type": message_type,
                },
            )


def inject_trace_context(carrier: dict[str, Any]) -> None:
    """Inject current trace context into carrier for propagation.

    Call this before sending a message to propagate trace context.
    """
    inject(carrier)


def _get_recipient_type(recipient: str) -> str:
    """Determine recipient type from address format."""
    if "@" in recipient:
        return "email"
    if recipient.startswith("+"):
        return "phone"
    return "device_token"


__all__ = [
    "inject_trace_context",
    "message_duration",
    "message_errors",
    "messages_consumed",
    "messages_published",
    "trace_consume",
    "trace_publish",
]
