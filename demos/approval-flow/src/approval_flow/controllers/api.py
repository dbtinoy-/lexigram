"""Browser API for the focused Lexigram workflow demo."""

from __future__ import annotations

from typing import Any

from approval_flow.services.flow import ApprovalFlowService
from lexigram.web import Controller, get, post


class ApprovalFlowApiController(Controller):
    """Expose state-machine controls without leaking workflow internals."""

    prefix = "/api/workflow"

    def __init__(self, service: ApprovalFlowService | None = None) -> None:
        self._service = service

    @get("")
    async def snapshot(self) -> dict[str, Any]:
        """Return the current workflow state, available events, and history."""
        return self._service.snapshot()

    @post("/request")
    async def request(self, body: dict[str, Any]) -> dict[str, Any]:
        """Create a new approval request from title, amount, and owner."""
        try:
            return await self._service.create_request(
                str(body.get("title", "")),
                int(body.get("amount", 0)),
                str(body.get("owner", "Requester")),
            )
        except (TypeError, ValueError) as exc:
            return {"error": str(exc)}

    @post("/transition")
    async def transition(self, body: dict[str, Any]) -> dict[str, Any]:
        """Advance the workflow by applying an event as the given actor."""
        try:
            return await self._service.transition(
                str(body.get("event", "")), str(body.get("actor", "operator"))
            )
        except Exception as exc:  # StateError is a domain error for this demo API
            return {"error": str(exc)}

    @post("/policy")
    async def policy(self, body: dict[str, Any]) -> dict[str, Any]:
        """Preview approval-chain outcome without mutating workflow state."""
        return await self._service.policy_preview(
            manager_approved=body.get("manager_approved") is not False,
            finance_approved=body.get("finance_approved") is not False,
        )

    @post("/retry")
    async def retry(self, body: dict[str, Any]) -> dict[str, Any]:
        """Retry a rejected request by re-entering manager review."""
        return await self.transition(
            {"event": "retry", "actor": body.get("actor", "operator")}
        )

    @post("/rollback")
    async def rollback(self, body: dict[str, Any]) -> dict[str, Any]:
        """Roll back an approved request to the manager review stage."""
        return await self.transition(
            {"event": "rollback", "actor": body.get("actor", "operator")}
        )

    @get("/health")
    async def health(self) -> dict[str, Any]:
        """Return a health check response indicating service availability."""
        return {"status": "ok", "service": "approval-flow", "offline": True}


__all__ = ["ApprovalFlowApiController"]
