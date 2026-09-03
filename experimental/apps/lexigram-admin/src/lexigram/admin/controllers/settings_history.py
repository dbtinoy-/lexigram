"""Snapshot capture and rollback resolution for the settings controller.

Kept beside the controller rather than inside it so the save handler stays
readable and the file stays within its size budget.
"""

from __future__ import annotations

from typing import Any

from starlette.requests import Request

from lexigram.admin.settings.panel import SecretNode
from lexigram.admin.settings.snapshots import SettingsSnapshotService
from lexigram.logging import get_logger

logger = get_logger(__name__)

__all__ = ["SettingsHistoryMixin"]


class SettingsHistoryMixin:
    """Records pre-change settings state and resolves rollback payloads."""

    _snapshots: SettingsSnapshotService

    @staticmethod
    def _secret_keys(spec: type[Any]) -> frozenset[str]:
        """Return the spec's secret node names."""
        return frozenset(
            key
            for key, node in spec.get_nodes().items()
            if isinstance(node, SecretNode)
        )

    @staticmethod
    def _actor_id(request: Request) -> str:
        """Best-effort principal identifier for history attribution."""
        user = getattr(request.state, "user", None)
        return str(
            getattr(user, "user_id", None) or getattr(user, "id", None) or "system"
        )

    async def _capture_snapshot(
        self,
        request: Request,
        spec: type[Any],
        namespace: str,
        values: dict[str, Any],
        tenant_id: str | None,
        comment: str = "",
    ) -> None:
        """Record pre-change values, never failing the save if history breaks."""
        try:
            await self._snapshots.capture(
                namespace,
                values,
                secret_keys=self._secret_keys(spec),
                tenant_id=tenant_id,
                actor_id=self._actor_id(request),
                comment=comment,
            )
        except Exception:  # noqa: BLE001 — history is auxiliary to the save
            logger.warning("admin.settings_snapshot_failed", namespace=namespace)

    async def _resolve_rollback(
        self,
        form: Any,
        spec: type[Any],
        namespace: str,
        tenant_id: str | None,
    ) -> dict[str, Any] | None:
        """Return submitted rollback values, or ``None`` for a normal save.

        A rollback re-enters the ordinary save path rather than writing
        directly, so validation, permissions, concurrency, and auditing all
        continue to apply to it.
        """
        getter = getattr(form, "get", None)
        snapshot_id = str(getter("rollback_to") or "") if callable(getter) else ""
        if not snapshot_id:
            return None

        values = await self._snapshots.rollback_values(
            snapshot_id, namespace=namespace, tenant_id=tenant_id
        )
        if values is None:
            return None

        # Only currently-declared, editable, non-secret nodes may be restored.
        nodes = spec.get_nodes()
        secrets = self._secret_keys(spec)
        return {
            key: value
            for key, value in values.items()
            if key in nodes and not nodes[key].readonly and key not in secrets
        }
