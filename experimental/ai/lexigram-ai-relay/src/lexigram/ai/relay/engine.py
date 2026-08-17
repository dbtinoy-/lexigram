"""Public relay conversion engine implementing :class:`RelayConverterProtocol`.

The engine is synchronous, side-effect free, and performs no HTTP,
channel selection, billing, or model selection.  Callers supply the
already-selected upstream model and any host callbacks via
:class:`RelayConversionContext`.
"""

from __future__ import annotations

from typing import Any

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.errors import (
    translate,
    unsupported_feature,
    unsupported_format,
    unsupported_route,
)
from lexigram.ai.relay.mappers.base import warning_messages
from lexigram.ai.relay.quality import route_quality
from lexigram.ai.relay.registry import RelayConverterRegistry, Route, RouteSpec
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.relay.context import RelayConversionContext
from lexigram.contracts.ai.relay.protocols import (
    RelayConverterProtocol,
    RelayRegistryProtocol,
    RelayStreamOptions,
    RelayStreamSessionProtocol,
)
from lexigram.contracts.ai.relay.types import (
    ConversionQuality,
    RelayConvertResult,
    RelayFormat,
    RelayRequestPayload,
    RelayResponsePayload,
)
from lexigram.contracts.core.result import Err, Ok, Result

__all__ = [
    "RelayConverterEngine",
    "convert_request_by_id",
    "convert_request_via",
    "convert_response_by_id",
    "convert_response_via",
]


def _converter_id(source: RelayFormat, target: RelayFormat) -> str:
    """Return the stable ``"<source>_to_<target>"`` converter identifier."""
    return f"{source.value}_to_{target.value}"


def _normalize_steps(source: RelayFormat, target: RelayFormat) -> tuple[str, ...]:
    """Return the canonical conversion path: source, IR, target."""
    return (source.value, "canonical_ir", target.value)


def _route_spec(mapper: Any) -> RouteSpec | None:
    """Extract route metadata from a registry-produced mapper, or ``None``."""
    spec = getattr(mapper, "spec", None)
    return spec if isinstance(spec, RouteSpec) else None


class RelayConverterEngine(RelayConverterProtocol):
    """Explicit source/target conversion over a caller-owned registry.

    Args:
        registry: The registry used when a conversion call does not pass
            its own ``registry`` override.
    """

    def __init__(self, registry: RelayRegistryProtocol) -> None:
        """Initialise the engine with a default registry."""
        self.registry: RelayRegistryProtocol = registry

    def convert_request(
        self,
        payload: RelayRequestPayload,
        source: RelayFormat,
        target: RelayFormat,
        *,
        context: RelayConversionContext | None = None,
        registry: RelayRegistryProtocol | None = None,
    ) -> Result[RelayConvertResult[RelayRequestPayload], RelayError]:
        """Convert a request payload from *source* to *target*."""
        conversion_context = ConversionContext.wrap(context)
        try:
            return self._convert(
                payload, source, target, registry, conversion_context, response=False
            )
        except Exception as exc:  # noqa: BLE001
            return Err(translate(exc, detail="convert_request"))

    def convert_response(
        self,
        payload: RelayResponsePayload,
        source: RelayFormat,
        target: RelayFormat,
        *,
        context: RelayConversionContext | None = None,
        registry: RelayRegistryProtocol | None = None,
    ) -> Result[RelayConvertResult[RelayResponsePayload], RelayError]:
        """Convert a non-stream response payload from *source* to *target*."""
        conversion_context = ConversionContext.wrap(context)
        try:
            return self._convert(
                payload, source, target, registry, conversion_context, response=True
            )
        except Exception as exc:  # noqa: BLE001
            return Err(translate(exc, detail="convert_response"))

    def new_stream_session(
        self,
        source: RelayFormat,
        target: RelayFormat,
        *,
        options: RelayStreamOptions | None = None,
        context: RelayConversionContext | None = None,
        registry: RelayRegistryProtocol | None = None,
    ) -> Result[RelayStreamSessionProtocol, RelayError]:
        """Create a stateful stream session for one upstream stream.

        Stateful stream conversion is delivered by the shared stream
        lifecycle in a later task; every current route reports no stream
        support.
        """
        return Err(
            unsupported_feature("stateful stream conversion is not implemented yet")
        )

    def convert_stream_chunk(
        self,
        session: RelayStreamSessionProtocol,
        event: Any,
    ) -> tuple[Any, ...]:
        """Convert one source stream event through *session*.

        Raises:
            RelayError: Stateful stream conversion is not implemented yet.
        """
        raise unsupported_feature("stateful stream conversion is not implemented yet")

    def finalize(
        self,
        session: RelayStreamSessionProtocol,
    ) -> tuple[Any, ...]:
        """Close a stream deterministically and return terminal events.

        Raises:
            RelayError: Stateful stream conversion is not implemented yet.
        """
        raise unsupported_feature("stateful stream conversion is not implemented yet")

    def _convert(
        self,
        payload: Any,
        source: RelayFormat,
        target: RelayFormat,
        registry: RelayRegistryProtocol | None,
        context: ConversionContext,
        *,
        response: bool,
    ) -> Result[RelayConvertResult[Any], RelayError]:
        """Shared request/response conversion path."""
        if not isinstance(source, RelayFormat):
            return Err(
                unsupported_format(f"source must be a RelayFormat, got {source!r}")
            )
        if not isinstance(target, RelayFormat):
            return Err(
                unsupported_format(f"target must be a RelayFormat, got {target!r}")
            )
        if source is target:
            return Ok(self._noop_result(payload, source, target, context))

        active_registry = registry or self.registry
        route_mapper = active_registry.mapper(source, target)
        if route_mapper is None:
            return Err(
                unsupported_route(
                    f"no relay route from {source.value} to {target.value}"
                )
            )
        route = route_mapper if isinstance(route_mapper, Route) else None
        spec = route.spec if route is not None else _route_spec(route_mapper)
        if spec is not None:
            supported = spec.response_supported if response else spec.request_supported
            if not supported:
                return Err(
                    unsupported_feature(
                        f"{'response' if response else 'request'} conversion "
                        f"{source.value} -> {target.value} is not supported"
                    )
                )
        if response:
            if route is not None:
                ir = route.response_to_ir(payload, context=context)
            else:
                ir = route_mapper.response_to_ir(payload)
            if ir.is_err():
                return ir
            source_ir = ir.unwrap()
            if route is not None:
                target_payload = route.ir_to_response(source_ir, context=context)
            else:
                target_payload = route_mapper.ir_to_response(source_ir)
            if target_payload.is_err():
                return target_payload
            usage = source_ir.usage
        else:
            if route is not None:
                ir = route.request_to_ir(payload, context=context)
            else:
                ir = route_mapper.request_to_ir(payload)
            if ir.is_err():
                return ir
            source_ir = ir.unwrap()
            if route is not None:
                target_payload = route.ir_to_request(source_ir, context=context)
            else:
                target_payload = route_mapper.ir_to_request(source_ir)
            if target_payload.is_err():
                return target_payload
            usage = None
        losses = tuple(context.losses)
        return Ok(
            RelayConvertResult(
                value=target_payload.unwrap(),
                source=source,
                target=target,
                converter_id=_converter_id(source, target),
                quality=route_quality(source, target),
                steps=_normalize_steps(source, target),
                usage=usage,
                losses=losses,
                warnings=warning_messages(losses),
            )
        )

    def _noop_result(
        self,
        value: Any,
        source: RelayFormat,
        target: RelayFormat,
        context: ConversionContext,
    ) -> RelayConvertResult[Any]:
        """Return the original typed payload with a no-op result."""
        losses = tuple(context.losses)
        return RelayConvertResult(
            value=value,
            source=source,
            target=target,
            converter_id=_converter_id(source, target),
            quality=ConversionQuality.GOOD,
            steps=(),
            usage=None,
            losses=losses,
            warnings=warning_messages(losses),
        )


# ---------------------------------------------------------------------------
# Explicit-path helpers
# ---------------------------------------------------------------------------


def convert_request_via(
    registry: RelayRegistryProtocol,
    payload: RelayRequestPayload,
    source: RelayFormat,
    target: RelayFormat,
    *,
    context: RelayConversionContext | None = None,
) -> Result[RelayConvertResult[RelayRequestPayload], RelayError]:
    """Convert a request through an explicit registry.

    Args:
        registry: The registry to resolve the route from.
        payload: The source request DTO.
        source: Source wire format.
        target: Target wire format.
        context: Optional host conversion context.

    Returns:
        A request conversion result, or a relay error.
    """
    return RelayConverterEngine(registry).convert_request(
        payload, source, target, context=context
    )


def convert_response_via(
    registry: RelayRegistryProtocol,
    payload: RelayResponsePayload,
    source: RelayFormat,
    target: RelayFormat,
    *,
    context: RelayConversionContext | None = None,
) -> Result[RelayConvertResult[RelayResponsePayload], RelayError]:
    """Convert a response through an explicit registry.

    Args:
        registry: The registry to resolve the route from.
        payload: The source response DTO.
        source: Source wire format.
        target: Target wire format.
        context: Optional host conversion context.

    Returns:
        A response conversion result, or a relay error.
    """
    return RelayConverterEngine(registry).convert_response(
        payload, source, target, context=context
    )


def convert_request_by_id(
    registry: RelayConverterRegistry,
    payload: RelayRequestPayload,
    converter_id: str,
    *,
    context: RelayConversionContext | None = None,
) -> Result[RelayConvertResult[RelayRequestPayload], RelayError]:
    """Convert a request through the route identified by ``converter_id``.

    Args:
        registry: The registry carrying the route.
        payload: The source request DTO.
        converter_id: A stable ``"<source>_to_<target>"`` identifier.
        context: Optional host conversion context.

    Returns:
        A request conversion result, or a relay error.
    """
    spec = registry.route_by_id(converter_id)
    if spec is None:
        return Err(unsupported_route(f"no relay route with id {converter_id!r}"))
    return RelayConverterEngine(registry).convert_request(
        payload, spec.source, spec.target, context=context
    )


def convert_response_by_id(
    registry: RelayConverterRegistry,
    payload: RelayResponsePayload,
    converter_id: str,
    *,
    context: RelayConversionContext | None = None,
) -> Result[RelayConvertResult[RelayResponsePayload], RelayError]:
    """Convert a response through the route identified by ``converter_id``.

    Args:
        registry: The registry carrying the route.
        payload: The source response DTO.
        converter_id: A stable ``"<source>_to_<target>"`` identifier.
        context: Optional host conversion context.

    Returns:
        A response conversion result, or a relay error.
    """
    spec = registry.route_by_id(converter_id)
    if spec is None:
        return Err(unsupported_route(f"no relay route with id {converter_id!r}"))
    return RelayConverterEngine(registry).convert_response(
        payload, spec.source, spec.target, context=context
    )
