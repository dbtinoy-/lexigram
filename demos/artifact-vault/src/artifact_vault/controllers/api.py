"""Browser API for the focused Lexigram storage demo."""

from __future__ import annotations

from typing import Any

from artifact_vault.services.vault import ArtifactVaultService
from lexigram.web import Controller, delete, get, post


class ArtifactVaultApiController(Controller):
    """Expose upload, metadata, content, access, and deletion controls."""

    prefix = "/api/artifacts"

    def __init__(self, service: ArtifactVaultService | None = None) -> None:
        self._service = service

    @get("")
    async def list_artifacts(self, prefix: str = "") -> dict[str, Any]:
        artifacts = await self._service.list(prefix)
        return {"count": len(artifacts), "artifacts": artifacts}

    @post("/upload")
    async def upload(self, body: dict[str, Any]) -> dict[str, Any]:
        try:
            artifact = await self._service.upload(
                str(body.get("name", "")),
                str(body.get("content", "")),
                str(body.get("content_type", "text/plain")),
                str(body.get("owner", "demo-user")),
            )
            return {"ok": True, "artifact": artifact}
        except ValueError as exc:
            return {"error": str(exc)}

    @get("/content/{name:path}")
    async def content(self, name: str) -> dict[str, Any]:
        try:
            return await self._service.content(name)
        except Exception as exc:  # backend not-found is rendered as a small API error
            return {"error": str(exc)}

    @get("/access/{name:path}")
    async def access(self, name: str) -> dict[str, Any]:
        try:
            return await self._service.access(name)
        except Exception as exc:
            return {"error": str(exc)}

    @delete("/{name:path}")
    async def delete_artifact(self, name: str) -> dict[str, Any]:
        try:
            await self._service.delete(name)
            return {"ok": True, "deleted": name}
        except Exception as exc:
            return {"error": str(exc)}

    @get("/health")
    async def health(self) -> dict[str, Any]:
        return await self._service.health()


__all__ = ["ArtifactVaultApiController"]
