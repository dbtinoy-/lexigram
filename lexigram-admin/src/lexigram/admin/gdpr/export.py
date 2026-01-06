"""SAR export helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import lexigram.serialization as json

if TYPE_CHECKING:
    from lexigram.admin.gdpr.models import SubjectAccessRequest


def export_sar_json(sar: SubjectAccessRequest) -> str:
    """Serialize an SAR to a portable JSON string for delivery.

    Args:
        sar: Completed :class:`SubjectAccessRequest`.

    Returns:
        JSON string suitable for download or email attachment.
    """
    payload = {
        "sar_id": sar.sar_id,
        "subject_id": sar.subject_id,
        "subject_email": sar.subject_email,
        "status": sar.status.value,
        "requested_at": sar.requested_at.isoformat(),
        "completed_at": sar.completed_at.isoformat() if sar.completed_at else None,
        "data": sar.data_snapshot,
    }
    result = json.dumps(payload, indent=2, default=str)
    return result if isinstance(result, str) else result.decode()


__all__ = [
    "export_sar_json",
]
