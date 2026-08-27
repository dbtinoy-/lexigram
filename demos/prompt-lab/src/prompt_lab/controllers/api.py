"""JSON API for the prompt lab — the **Result-pattern showcase**.

Every handler returns ``Result<Ok, Err>`` instead of raising or returning
raw responses.  The web pipeline then does the boring work:

- ``Ok(payload)``            → serialized as JSON (or rendered)
- ``Err(ValidationError)``   → HTTP 422 ProblemDetail
- ``Err(NotFoundError)``     → HTTP 404

So handlers read like use-cases ("validate → render → respond") and
error-to-HTTP mapping lives in exactly one place.  Compare with the
try/except-and-JSONResponse dance in traditional stacks.
"""

from __future__ import annotations

from starlette.requests import Request

from lexigram.ai.prompt.exceptions import PromptNotFoundError, PromptRenderError
from lexigram.contracts.exceptions import (
    NotFoundError,
    ValidationError,
)
from lexigram.result import Err, Ok, Result
from lexigram.serialization import loads as json_loads
from lexigram.web import Controller, get, post
from prompt_lab.repository.templates import VARIANT_LABELS
from prompt_lab.services.ab_runner import ABRunner
from prompt_lab.services.versioning import LabVersions


def _invalid(message: str) -> ValidationError:
    """Build a validation error for malformed render requests."""
    return ValidationError(message)


async def _body(request: Request) -> dict:
    """Parse the request body through the framework serializer."""
    raw = await request.body()
    if not raw:
        return {}
    parsed = json_loads(raw)
    return dict(parsed) if isinstance(parsed, dict) else {}


class LabApiController(Controller):
    """Prompt lab API consumed by the UI's vanilla-JS client.

    Lexigram pattern: controllers are stateless handlers that receive
    collaborators via constructor injection.  The framework resolves the
    controller when a request matches its routes — you never instantiate
    it manually.

    Route decorators (@get, @post) come from lexigram.web, not Starlette
    directly — they integrate with the framework's middleware stack.
    """

    def __init__(self, versions: LabVersions, runner: ABRunner) -> None:
        self._versions = versions
        self._runner = runner

    @get("/api/templates")
    async def templates(self, request: Request) -> list[dict]:
        """List all variants with their active revision number."""
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
        return rows

    @post("/api/render")
    async def render(
        self,
        request: Request,
    ) -> Result[dict, NotFoundError | ValidationError]:
        """Render one variant at an optional revision with supplied vars.

        Return type uses ``Result[T, E]`` — the web pipeline maps Err
        types to HTTP status codes automatically (ValidationError → 422,
        NotFoundError → 404).
        """
        data = await _body(request)
        variant = str(data.get("variant", ""))
        if variant not in VARIANT_LABELS:
            return Err(NotFoundError(f"unknown variant: {variant!r}"))

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
                return Err(_invalid(f"missing variables: {missing}"))
            rendered = template.render_as_string(**vars_in)
        except (PromptNotFoundError, PromptRenderError) as exc:
            return Err(_invalid(str(exc)))
        except ValueError as exc:
            return Err(_invalid(str(exc)))
        return Ok({"rendered": rendered})

    @get("/api/history/{variant}")
    async def history(self, request: Request) -> Result[dict, NotFoundError]:
        """Revision history for one variant — active revision is flagged."""
        variant = request.path_params["variant"]
        if variant not in VARIANT_LABELS:
            return Err(NotFoundError(f"unknown variant: {variant!r}"))
        return Ok({"entries": self._versions.history(variant)})

    @post("/api/rollback")
    async def rollback(self, request: Request) -> Result[dict, NotFoundError]:
        """Roll one variant back by N revisions; return the new active rev."""
        data = await _body(request)
        variant = str(data.get("variant", ""))
        if variant not in VARIANT_LABELS:
            return Err(NotFoundError(f"unknown variant: {variant!r}"))
        steps = int(data.get("steps", 1))
        active_rev = self._versions.rollback(variant, steps=steps)
        return Ok({"active_rev": active_rev})

    @post("/api/ab")
    async def ab(self, request: Request) -> dict:
        """Score both variants over the seeded cases (byte-stable)."""
        return await self._runner.run_all()


__all__ = ["LabApiController"]
