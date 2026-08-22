"""JSON API for the prompt lab console — no HTML lives here."""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import JSONResponse

from lexigram.ai.prompt.exceptions import (
    PromptNotFoundError,
    PromptRenderError,
)
from lexigram.web import Controller, get, post
from prompt_lab.ab_runner import ABRunner
from prompt_lab.templates import VARIANT_LABELS
from prompt_lab.versioning import LabVersions


def _error(message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


class LabApiController(Controller):
    """Endpoints consumed by ui/static/app.js."""

    def __init__(self, versions: LabVersions, runner: ABRunner) -> None:
        self._versions = versions
        self._runner = runner

    @get("/api/templates")
    async def templates(self, request: Request) -> JSONResponse:
        rows = []
        for variant in ("v1", "v2"):
            rev, _tpl = self._versions.active(variant)
            rows.append(
                {
                    "variant": variant,
                    "label": VARIANT_LABELS[variant],
                    "active_rev": rev,
                },
            )
        return JSONResponse(rows)

    @post("/api/render")
    async def render(self, request: Request) -> JSONResponse:
        """Render one variant at an optional revision with supplied vars."""
        data = await request.json()
        variant = str(data.get("variant", ""))
        if variant not in VARIANT_LABELS:
            return _error(f"unknown variant: {variant!r}", 404)

        vars_in = {str(k): str(v) for k, v in dict(data.get("vars", {})).items()}
        try:
            if data.get("rev") is not None:
                _rev, template = self._versions.get_revision(
                    variant,
                    int(data["rev"]),
                )
            else:
                _rev, template = self._versions.active(variant)
            missing = [v for v in template.get_variables() if v not in vars_in]
            if missing:
                return _error(f"missing variables: {missing}", 400)
            rendered = template.render_as_string(**vars_in)
        except (PromptNotFoundError, PromptRenderError) as exc:
            return _error(str(exc), 400)
        except ValueError as exc:
            return _error(str(exc), 400)
        return JSONResponse({"rendered": rendered})

    @get("/api/history/{variant}")
    async def history(self, request: Request) -> JSONResponse:
        variant = request.path_params["variant"]
        if variant not in VARIANT_LABELS:
            return _error(f"unknown variant: {variant!r}", 404)
        return JSONResponse({"entries": self._versions.history(variant)})

    @post("/api/rollback")
    async def rollback(self, request: Request) -> JSONResponse:
        data = await request.json()
        variant = str(data.get("variant", ""))
        if variant not in VARIANT_LABELS:
            return _error(f"unknown variant: {variant!r}", 404)
        steps = int(data.get("steps", 1))
        active_rev = self._versions.rollback(variant, steps=steps)
        return JSONResponse({"active_rev": active_rev})

    @post("/api/ab")
    async def ab(self, request: Request) -> JSONResponse:
        """Score both variants over the seeded cases (byte-stable)."""
        return JSONResponse(await self._runner.run_all())


__all__ = ["LabApiController"]
