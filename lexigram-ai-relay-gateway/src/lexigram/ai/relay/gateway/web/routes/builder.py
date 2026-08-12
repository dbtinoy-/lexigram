from __future__ import annotations

"""Route assembly for the relay gateway web layer."""

from functools import partial

from starlette.routing import Route

from lexigram.ai.relay.gateway.web.audio_endpoints import AUDIO_ROUTE_TABLE
from lexigram.ai.relay.gateway.web.image_endpoints import build_image_routes
from lexigram.ai.relay.gateway.web.routes.common import (
    ResolveGateway,
    ResolveJobPassthrough,
    ResolveModelCatalog,
    _with_auth_guard,
)
from lexigram.ai.relay.gateway.web.routes.jobs import (
    job_status_endpoint,
    job_submit_endpoint,
)
from lexigram.ai.relay.gateway.web.routes.models import (
    model_detail_endpoint,
    models_endpoint,
)
from lexigram.ai.relay.gateway.web.routes.passthrough import passthrough_endpoint
from lexigram.ai.relay.gateway.web.routes.relay import relay_endpoint
from lexigram.ai.relay.gateway.web.routes.tables import (
    _AUDIO_HANDLERS,
    _JOB_ROUTE_TABLE,
    _JOB_STATUS_PATH,
    _PASSTHROUGH_ROUTE_TABLE,
    _ROUTE_TABLE,
)
from lexigram.ai.relay.gateway.web.shared import ResolvePassthrough
from lexigram.contracts.ai.relay import RelayFormat


def build_routes(
    resolve_gateway: ResolveGateway,
    *,
    resolve_passthrough: ResolvePassthrough | None = None,
    resolve_job_passthrough: ResolveJobPassthrough | None = None,
    resolve_model_catalog: ResolveModelCatalog | None = None,
) -> list[Route]:
    """Build the relay POST routes bound to gateway resolvers.

    Args:
        resolve_gateway: Async callable resolving a ``RelayGatewayProtocol``
            from the request; wired to request-time DI by the contributor.
        resolve_passthrough: Optional async callable resolving a
            ``PassthroughService`` from the request; when provided, the
            passthrough routes (e.g. ``/v1/embeddings``), the audio
            routes (``/v1/audio/*``), and the image routes
            (``/v1/images/*``) are appended.
        resolve_job_passthrough: Optional async callable resolving a
            ``JobPassthroughService`` from the request; when provided,
            the job-relay routes (``POST /v1/videos`` and
            ``GET /v1/videos/{job_id}``) are appended.
        resolve_model_catalog: Optional async callable resolving a
            ``ModelCatalogService`` from the request; when provided, the
            model-list and model-detail routes (``GET /v1/models``,
            ``GET /v1beta/models``, and their detail variants) are
            appended.

    Returns:
        One ``Route`` per inbound relay format, in ``RELAY_ROUTE_PATHS``
        order, followed by the passthrough, audio, image, job-relay, and
        model-catalog routes when their resolver is provided.
    """
    routes = [
        Route(
            path,
            _with_auth_guard(partial(relay_endpoint, source, resolve_gateway)),
            methods=["POST"],
        )
        for path, source in _ROUTE_TABLE
    ]
    if resolve_passthrough is not None:
        routes.extend(
            Route(
                path,
                _with_auth_guard(
                    partial(passthrough_endpoint, kind, resolve_passthrough)
                ),
                methods=["POST"],
            )
            for path, kind in _PASSTHROUGH_ROUTE_TABLE
        )
        routes.extend(
            Route(
                path,
                _with_auth_guard(partial(_AUDIO_HANDLERS[kind], resolve_passthrough)),
                methods=["POST"],
            )
            for path, kind in AUDIO_ROUTE_TABLE
        )
        guarded_image_routes = [
            Route(
                route.path,
                _with_auth_guard(route.endpoint),
                methods=route.methods or ["POST"],
            )
            for route in build_image_routes(resolve_passthrough)
        ]
        routes.extend(guarded_image_routes)
    if resolve_job_passthrough is not None:
        routes.extend(
            Route(
                path,
                _with_auth_guard(
                    partial(job_submit_endpoint, kind, resolve_job_passthrough)
                ),
                methods=["POST"],
            )
            for path, kind in _JOB_ROUTE_TABLE
        )
        routes.extend(
            Route(
                _JOB_STATUS_PATH,
                _with_auth_guard(
                    partial(job_status_endpoint, kind, resolve_job_passthrough)
                ),
                methods=["GET"],
            )
            for _, kind in _JOB_ROUTE_TABLE
        )
    if resolve_model_catalog is not None:
        routes.append(
            Route(
                "/v1beta/models",
                _with_auth_guard(
                    partial(models_endpoint, RelayFormat.GEMINI, resolve_model_catalog)
                ),
                methods=["GET"],
            )
        )
        routes.append(
            Route(
                "/v1/models",
                _with_auth_guard(partial(models_endpoint, None, resolve_model_catalog)),
                methods=["GET"],
            )
        )
        routes.append(
            Route(
                "/v1beta/models/{model}",
                _with_auth_guard(
                    partial(model_detail_endpoint, True, resolve_model_catalog)
                ),
                methods=["GET"],
            )
        )
        routes.append(
            Route(
                "/v1/models/{model}",
                _with_auth_guard(
                    partial(model_detail_endpoint, False, resolve_model_catalog)
                ),
                methods=["GET"],
            )
        )
    return routes
