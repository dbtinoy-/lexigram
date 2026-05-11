"""Caller-owned relay registry with derived directed routes.

The registry stores one :class:`FormatMapper` per wire format and derives
the twelve directed route objects (including their static route metadata)
on demand.  It implements :class:`RelayRegistryProtocol`; concrete routes
also carry a :class:`RouteSpec` so the engine can attach quality, loss,
and capability metadata to every conversion result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.errors import duplicate_registration, unsupported_format
from lexigram.ai.relay.mappers.base import FormatMapper
from lexigram.ai.relay.mappers.claude import ClaudeMapper
from lexigram.ai.relay.mappers.gemini import GeminiMapper
from lexigram.ai.relay.mappers.openai_chat import OpenAIChatMapper
from lexigram.ai.relay.mappers.openai_responses import OpenAIResponsesMapper
from lexigram.ai.relay.quality import route_quality
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.relay.ir import (
    RelayRequest,
    RelayResponse,
    StreamDelta,
    StreamState,
)
from lexigram.contracts.ai.relay.protocols import (
    RelayMapperProtocol,
    RelayRegistryProtocol,
)
from lexigram.contracts.ai.relay.types import ConversionQuality, RelayFormat
from lexigram.contracts.core.result import Result

__all__ = [
    "CONVERTER_VERSION",
    "RelayConverterRegistry",
    "Route",
    "RouteSpec",
]

CONVERTER_VERSION = "1.0.0"
"""Converter engine version reported in operational diagnostics."""


@dataclass(frozen=True)
class RouteSpec:
    """Static metadata for one directed conversion route.

    Attributes:
        source: Source wire format.
        target: Target wire format.
        quality: Semantic closeness of the conversion.
        request_supported: Whether request conversion is available.
        response_supported: Whether response conversion is available.
        stream_supported: Whether stateful stream conversion is available.
        feature_loss_policy: Machine-readable loss reasons this route is
            expected to record, in order.

    Properties:
        converter_id: Stable ``"<source>_to_<target>"`` identifier.
    """

    source: RelayFormat
    target: RelayFormat
    quality: ConversionQuality
    request_supported: bool = True
    response_supported: bool = True
    stream_supported: bool = False
    feature_loss_policy: tuple[str, ...] = ()

    @property
    def converter_id(self) -> str:
        """Stable ``"<source>_to_<target>"`` identifier for this route."""
        return f"{self.source.value}_to_{self.target.value}"


@dataclass(frozen=True)
class Route:
    """A delegating mapper for one directed pair plus its route spec.

    ``request_to_ir`` / ``ir_to_request`` delegate to the source/target
    mapper respectively; stream operations delegate the same way and are
    finalized by the shared stream lifecycle in a later task.
    """

    spec: RouteSpec
    source_mapper: FormatMapper
    target_mapper: FormatMapper

    def request_to_ir(
        self, payload: Any, *, context: ConversionContext | None = None
    ) -> Result[RelayRequest, RelayError]:
        """Convert a source request DTO into the canonical IR."""
        return self.source_mapper.request_to_ir(
            payload, context=context or ConversionContext()
        )

    def ir_to_request(
        self, request: RelayRequest, *, context: ConversionContext | None = None
    ) -> Result[Any, RelayError]:
        """Convert the canonical IR into the target request DTO."""
        return self.target_mapper.ir_to_request(
            request, context=context or ConversionContext()
        )

    def response_to_ir(
        self, payload: Any, *, context: ConversionContext | None = None
    ) -> Result[RelayResponse, RelayError]:
        """Convert a source response DTO into the canonical IR."""
        return self.source_mapper.response_to_ir(
            payload, context=context or ConversionContext()
        )

    def ir_to_response(
        self, response: RelayResponse, *, context: ConversionContext | None = None
    ) -> Result[Any, RelayError]:
        """Convert the canonical IR into the target response DTO."""
        return self.target_mapper.ir_to_response(
            response, context=context or ConversionContext()
        )

    def stream_to_delta(
        self, event: Any, *, state: StreamState
    ) -> Result[tuple[StreamDelta, ...], RelayError]:
        """Convert one source stream event into canonical deltas."""
        return self.source_mapper.stream_to_delta(event, state=state)

    def delta_to_stream(
        self, delta: StreamDelta, *, state: StreamState
    ) -> Result[tuple[Any, ...], RelayError]:
        """Convert one canonical delta into target stream events."""
        return self.target_mapper.delta_to_stream(delta, state=state)


class RelayConverterRegistry(RelayRegistryProtocol):
    """Caller-owned registry of format mappers with derived routes.

    ``__init__`` creates an empty registry; :meth:`with_defaults` prepopulates
    the four built-in mappers.  A caller may build and mutate their own
    instance without touching the process-global default registry.
    """

    def __init__(self) -> None:
        """Create an empty registry."""
        self._mappers: dict[RelayFormat, FormatMapper] = {}
        self._routes: dict[tuple[RelayFormat, RelayFormat], Route] = {}

    @classmethod
    def with_defaults(cls) -> RelayConverterRegistry:
        """Return a registry prepopulated with the four built-in mappers."""
        registry = cls()
        registry.register(OpenAIChatMapper())
        registry.register(OpenAIResponsesMapper())
        registry.register(ClaudeMapper())
        registry.register(GeminiMapper())
        return registry

    def register(self, mapper: FormatMapper) -> None:
        """Register a mapper for its declared wire format.

        Args:
            mapper: A mapper exposing a ``format`` :class:`RelayFormat`
                attribute.

        Raises:
            RelayError: With code ``duplicate_registration`` when a mapper
                is already registered for the format, or
                ``unsupported_format`` when the mapper does not declare a
                ``RelayFormat`` ``format`` attribute.
        """
        fmt = getattr(mapper, "format", None)
        if not isinstance(fmt, RelayFormat):
            raise unsupported_format(
                f"mapper {type(mapper).__name__} must declare a RelayFormat 'format' attribute"
            )
        if fmt in self._mappers:
            raise duplicate_registration(
                f"a mapper is already registered for {fmt.value}"
            )
        self._mappers[fmt] = mapper

    def mapper(
        self,
        source: RelayFormat,
        target: RelayFormat,
    ) -> RelayMapperProtocol | None:
        """Return the delegating route for a directed pair, or ``None``.

        Same-format pairs return ``None``; the engine treats those as a
        no-op conversion.

        Args:
            source: Source wire format.
            target: Target wire format.

        Returns:
            The route mapper, or ``None`` when no route exists.
        """
        if source is target:
            return None
        route = self._obtain_route(source, target)
        if route is None:
            return None
        return cast("RelayMapperProtocol", route)

    def converter_routes(self) -> tuple[tuple[RelayFormat, RelayFormat], ...]:
        """Return every supported directed route pair.

        Returns:
            Sorted route pairs, excluding same-format no-op pairs.
        """
        return tuple(
            (spec.source, spec.target)
            for spec in self.routes()
            if spec.source is not spec.target
        )

    def mapper_ids(self) -> tuple[str, ...]:
        """Return the registered mapper wire-format identifiers.

        Returns:
            Sorted mapper ids, one per registered mapper.
        """
        return tuple(sorted(mapper.format.value for mapper in self._mappers.values()))

    def converter_version(self) -> str:
        """Return the converter engine version string.

        Returns:
            The module-level ``CONVERTER_VERSION`` constant.
        """
        return CONVERTER_VERSION

    def route_quality(
        self,
        source: RelayFormat,
        target: RelayFormat,
    ) -> ConversionQuality:
        """Return the semantic-closeness quality for a directed pair.

        Same-format pairs and unconfigured routes fall back to
        ``GOOD``/``DISCOURAGED`` via the quality matrix.

        Args:
            source: Source wire format.
            target: Target wire format.

        Returns:
            The stable quality value for the pair.
        """
        return route_quality(source, target)

    def route(self, source: RelayFormat, target: RelayFormat) -> RouteSpec | None:
        """Return the route spec for a directed pair, or ``None``.

        Same-format pairs return ``None`` (no-op conversion).

        Args:
            source: Source wire format.
            target: Target wire format.

        Returns:
            The route spec, or ``None`` when no route exists.
        """
        if source is target:
            return None
        route = self._obtain_route(source, target)
        return route.spec if route is not None else None

    def route_by_id(self, converter_id: str) -> RouteSpec | None:
        """Return the route spec carrying *converter_id*, or ``None``.

        Args:
            converter_id: A stable ``"<source>_to_<target>"`` identifier.

        Returns:
            The matching route spec, or ``None`` when unknown.
        """
        for spec in self.routes():
            if spec.converter_id == converter_id:
                return spec
        return None

    def routes(self) -> tuple[RouteSpec, ...]:
        """Return specs for every registered directed pair, sorted by id."""
        specs: list[RouteSpec] = []
        for source in RelayFormat:
            for target in RelayFormat:
                if source is target:
                    continue
                route = self._obtain_route(source, target)
                if route is not None:
                    specs.append(route.spec)
        return tuple(sorted(specs, key=lambda spec: spec.converter_id))

    def _obtain_route(self, source: RelayFormat, target: RelayFormat) -> Route | None:
        """Return (caching) the route for *source* to *target*, or ``None``."""
        key_pair = (source, target)
        cached = self._routes.get(key_pair)
        if cached is not None:
            return cached
        source_mapper = self._mappers.get(source)
        target_mapper = self._mappers.get(target)
        if source_mapper is None or target_mapper is None:
            return None
        route = Route(
            spec=RouteSpec(
                source=source,
                target=target,
                quality=route_quality(source, target),
            ),
            source_mapper=source_mapper,
            target_mapper=target_mapper,
        )
        self._routes[key_pair] = route
        return route
