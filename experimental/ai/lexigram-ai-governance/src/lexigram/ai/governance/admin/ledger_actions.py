"""Admin actions for the relay ledger (settle top-up, run check-in).

Handlers follow the ``(container, **params) -> dict[str, object]``
shape used by the admin dashboard.  They validate parameters
server-side, resolve the ledger service protocol via the container,
and echo the outcome.  Award amounts are caller-supplied: reward
policy (how much, how often) belongs to the application layer, not
the framework.
"""

from __future__ import annotations

from typing import Any

from lexigram.contracts.ai.relay import RelayLedgerServiceProtocol

__all__ = ["run_checkin", "settle_topup"]

_STATUSES = ("pending", "completed", "failed")


async def _ledger(container: Any) -> RelayLedgerServiceProtocol | None:
    """Resolve the ledger service, or ``None`` when not registered.

    Args:
        container: The DI container resolver.

    Returns:
        The ledger service, or ``None`` when nothing is bound.
    """
    try:
        service = await container.resolve(RelayLedgerServiceProtocol)
    except Exception:
        return None
    return service


async def settle_topup(container: Any, **params: object) -> dict[str, object]:
    """Settle one pending top-up reference as completed.

    Args:
        container: The DI container resolver.
        **params: ``reference_id`` (required) and ``expected_status``
            (default ``"pending"``).

    Returns:
        Outcome dict: ``ok``, ``message``, optional ``code``, and
        ``echo`` with the submitted parameters.
    """
    reference_id = params.get("reference_id")
    if not isinstance(reference_id, str) or not reference_id.strip():
        return {"ok": False, "message": "reference_id is required"}
    expected_status = params.get("expected_status", "pending")
    if not isinstance(expected_status, str) or expected_status not in _STATUSES:
        return {
            "ok": False,
            "message": f"expected_status must be one of {_STATUSES}",
        }
    echo: dict[str, object] = {
        "reference_id": reference_id.strip(),
        "expected_status": expected_status,
    }
    service = await _ledger(container)
    if service is None:
        return {"ok": False, "message": "relay ledger service is not registered"}
    result = await service.settle_topup(reference_id.strip(), expected_status)
    if result.is_err():
        error = result.unwrap_err()
        return {
            "ok": False,
            "code": error.code,
            "message": str(error.message),
            "echo": echo,
        }
    return {
        "ok": True,
        "message": f"top-up {reference_id!r} settled",
        "echo": echo,
    }


async def run_checkin(container: Any, **params: object) -> dict[str, object]:
    """Record a caller-supplied daily award for a user.

    Args:
        container: The DI container resolver.
        **params: ``user_id`` and ``award`` (both required).

    Returns:
        Outcome dict: ``ok``, ``message``, optional ``code``, and
        ``echo`` with the submitted parameters.
    """
    user_id = params.get("user_id")
    if not isinstance(user_id, str) or not user_id.strip():
        return {"ok": False, "message": "user_id is required"}
    award = params.get("award")
    if not isinstance(award, str) or not award.strip():
        return {"ok": False, "message": "award is required"}
    echo: dict[str, object] = {"user_id": user_id.strip(), "award": award.strip()}
    service = await _ledger(container)
    if service is None:
        return {"ok": False, "message": "relay ledger service is not registered"}
    result = await service.checkin(user_id.strip(), award.strip())
    if result.is_err():
        error = result.unwrap_err()
        return {
            "ok": False,
            "code": error.code,
            "message": str(error.message),
            "echo": echo,
        }
    record = result.unwrap()
    return {
        "ok": True,
        "message": f"check-in recorded for {user_id!r} on {record.day}",
        "echo": echo,
    }
