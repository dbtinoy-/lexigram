"""REST + SSE endpoints for the builder API."""

from __future__ import annotations

import asyncio
import json as stdjson  # noqa: TID251 - SSE wire format needs str, serialization returns bytes
from typing import Any

import httpx
from starlette.requests import Request
from starlette.responses import JSONResponse

from lexigram.builder.config import BuilderConfig
from lexigram.builder.constants import GRAPH_SCHEMA_VERSION, __version__
from lexigram.builder.exceptions import (
    BuilderError,
    GraphValidationError,
    InvalidProjectNameError,
    ProjectNotFoundError,
)
from lexigram.builder.graph.palette import (
    DB_PRESETS,
    ENTITY_OPS,
    FIELD_TYPES,
    KNOWN_KINDS,
)
from lexigram.builder.graph.parsing import document_to_dict, parse_document
from lexigram.builder.services.generation import GenerationService
from lexigram.builder.services.preview import PreviewService
from lexigram.builder.services.projects import ProjectService
from lexigram.contracts.exceptions.domain import (
    ConflictError,
    DomainError,
    NotFoundError,
)
from lexigram.result import Err, Ok, Result
from lexigram.web import Controller, delete, get, post, put
from lexigram.web.routing.result_bridge import error_status
from lexigram.web.transport.sse import EventSourceResponse, ServerSentEvent


@error_status(GraphValidationError, 422)
@error_status(InvalidProjectNameError, 422)
@error_status(ProjectNotFoundError, 404)
class BuilderController(Controller):
    """Expose the builder HTTP surface under ``/builder``."""

    def __init__(
        self,
        projects: ProjectService,
        generations: GenerationService,
        previews: PreviewService,
        config: BuilderConfig | None = None,
    ) -> None:
        self.projects = projects
        self.generations = generations
        self.previews = previews
        self.config = config or BuilderConfig()
        self._generation_tasks: set[asyncio.Task[Result[None, BuilderError]]] = set()

    # ── meta ──────────────────────────────────────────────────────────

    @get("/builder/health")
    async def health(self) -> dict[str, Any]:
        """Report builder liveness and version."""
        return {"status": "ok", "version": __version__}

    @get("/builder/palette")
    async def palette(self) -> dict[str, Any]:
        """Describe the v1 node palette for canvas rendering."""
        return {
            "schema_version": GRAPH_SCHEMA_VERSION,
            "kinds": sorted(KNOWN_KINDS),
            "field_types": sorted(FIELD_TYPES),
            "ops": sorted(ENTITY_OPS),
            "db_presets": sorted(DB_PRESETS),
            "edges": [{"src": "route", "dst": "entity"}],
        }

    # ── projects ──────────────────────────────────────────────────────

    @post("/builder/projects", status_code=201)
    async def create_project(
        self, request: Request
    ) -> Result[dict, InvalidProjectNameError]:
        body = stdjson.loads(await request.body() or b"{}")
        name = str(body.get("name", ""))
        created = self.projects.create(name)
        if created.is_err():
            return Err(created.unwrap_err())
        return Ok({"name": name})

    @get("/builder/projects")
    async def list_projects(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for name in self.projects.list_projects():
            preview = self.previews.info(name)
            out.append(
                {
                    "name": name,
                    "preview": {"port": preview.port, "pid": preview.pid}
                    if preview
                    else None,
                }
            )
        return out

    @delete("/builder/projects/{name}")
    async def delete_project(self, name: str) -> Result[bool, DomainError]:
        if self.previews.info(name) is not None:
            return Err(ConflictError(f"project {name!r} has a live preview"))
        deleted = self.projects.delete(name)
        if deleted.is_err():
            return Err(deleted.unwrap_err())
        return Ok(True)

    @get("/builder/projects/{name}/graph")
    async def get_graph(self, name: str) -> Result[dict[str, Any], BuilderError]:
        loaded = self.projects.load_graph(name)
        if loaded.is_err():
            return Err(loaded.unwrap_err())
        return Ok(document_to_dict(loaded.unwrap()))

    @put("/builder/projects/{name}/graph")
    async def put_graph(self, name: str, request: Request) -> Result[Any, BuilderError]:
        try:
            payload = stdjson.loads(await request.body())
        except ValueError as exc:
            return Ok(
                _json_problem(
                    422, {"detail": f"malformed JSON body: {exc}", "diagnostics": []}
                )
            )

        parsed = parse_document(payload)
        if parsed.is_err():
            parse_err = parsed.unwrap_err()
            return Ok(_json_problem(422, {"detail": str(parse_err), "diagnostics": []}))

        document = parsed.unwrap()
        saved = self.projects.save_graph(name, document)
        if saved.is_err():
            save_err = saved.unwrap_err()
            if isinstance(save_err, GraphValidationError):
                return Ok(
                    _json_problem(
                        422,
                        {
                            "detail": save_err.args[0]
                            if save_err.args
                            else "validation failed",
                            "diagnostics": [
                                {
                                    "node_id": d.node_id,
                                    "severity": str(d.severity),
                                    "code": d.code,
                                    "message": d.message,
                                }
                                for d in save_err.diagnostics
                            ],
                        },
                    )
                )
            return Err(save_err)
        return Ok({"saved": True})

    # ── generation ────────────────────────────────────────────────────

    @post("/builder/projects/{name}/generate", status_code=202)
    async def generate(self, name: str) -> Result[dict[str, Any], BuilderError]:
        if not self.projects.graph_path(name).is_file():
            return Err(ProjectNotFoundError(f"unknown project {name!r}"))
        task = asyncio.create_task(self._run_generation(name))
        self._generation_tasks.add(task)
        task.add_done_callback(self._generation_tasks.discard)
        return Ok({"generation_id": name})

    async def _run_generation(self, name: str) -> Result[None, BuilderError]:
        outcome = await self.generations.generate(name)
        if outcome.is_err():
            err = outcome.unwrap_err()
            self.previews.publish(
                {
                    "type": "diagnostic",
                    "node_id": None,
                    "code": "generation-failed",
                    "message": err.args[0] if err.args else "generation failed",
                }
            )
            return Err(err)
        return Ok(None)

    # ── preview ───────────────────────────────────────────────────────

    @get("/builder/projects/{name}/preview/stream")
    async def stream(self, name: str, request: Request) -> EventSourceResponse:
        queue = self.previews.subscribe()

        async def events() -> Any:
            try:
                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    except TimeoutError:
                        yield ServerSentEvent(event="ping", data="{}")
                        continue
                    yield ServerSentEvent(
                        event=str(event.get("type", "message")),
                        data=stdjson.dumps(event),
                    )
            finally:
                self.previews.unsubscribe(queue)

        return EventSourceResponse(events())

    @post("/builder/projects/{name}/preview/request")
    async def proxy(
        self, name: str, request: Request
    ) -> Result[Any, NotFoundError] | JSONResponse:
        port = self.previews.port_of(name)
        if port is None:
            return Err(NotFoundError(f"no live preview for project {name!r}"))
        forward_path = request.query_params.get("path", "/")
        target = f"http://127.0.0.1:{port}{forward_path}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                upstream = await client.request(
                    request.method,
                    target,
                    content=await request.body(),
                    headers={
                        k: v
                        for k, v in request.headers.items()
                        if k.lower() in {"content-type"}
                    },
                )
        except httpx.HTTPError as exc:
            return Err(NotFoundError(f"preview unreachable: {exc}"))
        return JSONResponse(
            status_code=upstream.status_code,
            content=upstream.content,
            media_type=upstream.headers.get("content-type"),
        )

    @post("/builder/projects/{name}/preview/stop")
    async def stop_preview(self, name: str) -> dict[str, bool]:
        await self.previews.stop(name)
        return {"stopped": True}


def _json_problem(status: int, payload: dict[str, Any]) -> JSONResponse:
    """Explicit problem+json-style response carrying builder diagnostics."""
    return JSONResponse(status_code=status, content=payload)
