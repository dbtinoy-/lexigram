"""Browser API for the focused Lexigram feature-flags demo."""

from __future__ import annotations

from typing import Any

from lexigram.web import Controller, get, post
from release_control.services.control import ReleaseControlService


class ReleaseControlApiController(Controller):
    """Expose flag evaluation and safe runtime controls."""

    prefix = "/api/flags"

    def __init__(self, service: ReleaseControlService | None = None) -> None:
        self._service = service

    @get("")
    async def snapshot(
        self, user_id: str = "demo-user-42", plan: str = "pro"
    ) -> dict[str, Any]:
        """Evaluate the three lab flags for a deterministic user context."""
        return await self._service.snapshot(user_id, plan)

    @post("/evaluate")
    async def evaluate(self, body: dict[str, Any]) -> dict[str, Any]:
        """Evaluate one flag for the context supplied by the browser."""
        try:
            return await self._service.evaluate(
                str(body.get("name", "")),
                str(body.get("user_id", "demo-user-42")),
                str(body.get("plan", "free")),
            )
        except ValueError as exc:
            return {"error": str(exc)}

    @post("/override")
    async def override(self, body: dict[str, Any]) -> dict[str, Any]:
        """Force a flag on or off and record the actor in FlagManager's audit log."""
        try:
            name = str(body.get("name", ""))
            enabled = body.get("enabled") is True
            self._service.set_override(name, enabled, str(body.get("actor", "")))
            return {
                "ok": True,
                "message": f"{name} forced {'on' if enabled else 'off'}",
            }
        except ValueError as exc:
            return {"error": str(exc)}

    @post("/override/clear")
    async def clear_override(self, body: dict[str, Any]) -> dict[str, Any]:
        """Remove an override so the configured provider is authoritative again."""
        try:
            name = str(body.get("name", ""))
            self._service.clear_override(name)
            return {"ok": True, "message": f"{name} returned to provider control"}
        except ValueError as exc:
            return {"error": str(exc)}

    @post("/cache/clear")
    async def clear_cache(self) -> dict[str, Any]:
        """Flush manager TTL results so the next evaluation is fresh."""
        await self._service.clear_cache()
        return {"ok": True, "message": "Evaluation cache cleared"}

    @get("/audit")
    async def audit(self) -> dict[str, Any]:
        """Return runtime override history from ``FlagManager``."""
        entries = self._service.audit()
        return {"count": len(entries), "entries": entries}

    @get("/health")
    async def health(self) -> dict[str, Any]:
        """Report that the in-memory release desk is ready."""
        return {"status": "ok", "service": "release-control", "offline": True}


__all__ = ["ReleaseControlApiController"]
