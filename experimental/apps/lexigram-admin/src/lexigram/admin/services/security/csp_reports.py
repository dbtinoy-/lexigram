"""CSP violation report ingestion (CSP v2 groundwork, docs/09-01-2026/30).

Browsers post violation reports for the ``Content-Security-Policy-Report-Only``
candidate policy emitted by :mod:`lexigram.admin.middleware.security_headers`.
This module normalizes both wire formats (legacy ``application/csp-report``
and the modern Reporting API ``application/reports+json``), dedupes them into
a capped in-memory store, and exposes a superuser-only JSON summary so
operators can drive the strict policy's violations to zero before enforcing
it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from starlette.responses import JSONResponse, PlainTextResponse, Response

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from starlette.requests import Request

logger = get_logger(__name__)

#: Maximum accepted report body size (bytes). Reports are tiny; anything
#: larger is hostile or broken.
MAX_REPORT_BODY_BYTES = 32 * 1024

#: Maximum distinct violation signatures retained (oldest evicted).
MAX_SIGNATURES = 200

#: Content types accepted by the ingest endpoint. ``application/json`` is
#: included for tooling/manual testing; browsers use the first two.
_ACCEPTED_CONTENT_TYPES = (
    "application/csp-report",
    "application/reports+json",
    "application/json",
)


def _pick(data: dict[str, Any], *keys: str) -> str:
    """Return the first non-empty value among kebab/camel key variants."""
    for key in keys:
        value = data.get(key)
        if value:
            return str(value)
    return ""


def _normalize(raw: dict[str, Any]) -> dict[str, str] | None:
    """Normalize one raw report body to canonical string fields."""
    if not isinstance(raw, dict):
        return None
    directive = _pick(
        raw,
        "effective-directive",
        "effectiveDirective",
        "violated-directive",
        "violatedDirective",
    )
    if not directive:
        return None
    return {
        "directive": directive,
        "blocked_uri": _pick(raw, "blocked-uri", "blockedURL", "blockedURI"),
        "document_uri": _pick(raw, "document-uri", "documentURL", "documentURI"),
        "source_file": _pick(raw, "source-file", "sourceFile"),
        "line": _pick(raw, "line-number", "lineNumber"),
    }


def parse_csp_reports(body: bytes, content_type: str) -> list[dict[str, str]]:
    """Parse a report request body into normalized violation dicts.

    Handles the legacy single-report envelope ``{"csp-report": {...}}``,
    Reporting API arrays ``[{"type": "csp-violation", "body": {...}}, ...]``,
    and bare report objects. Malformed input yields an empty list — this
    endpoint must never raise on attacker-controlled bytes.
    """
    del content_type  # both formats are sniffed from the JSON shape
    try:
        payload = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return []

    candidates: list[Any] = []
    if isinstance(payload, dict):
        if isinstance(payload.get("csp-report"), dict):
            candidates.append(payload["csp-report"])
        else:
            candidates.append(payload)
    elif isinstance(payload, list):
        for item in payload:
            if not isinstance(item, dict):
                continue
            if item.get("type") not in (None, "csp-violation"):
                continue
            body_obj = item.get("body")
            candidates.append(body_obj if isinstance(body_obj, dict) else item)

    out: list[dict[str, str]] = []
    for candidate in candidates:
        normalized = _normalize(candidate)
        if normalized is not None:
            out.append(normalized)
    return out


@dataclass
class CspViolation:
    """A deduped violation signature with occurrence bookkeeping."""

    directive: str
    blocked_uri: str
    document_uri: str
    source_file: str
    line: str
    count: int = 1
    first_seen: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds")
    )
    last_seen: str = field(
        default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds")
    )

    def as_dict(self) -> dict[str, Any]:
        return {
            "directive": self.directive,
            "blocked_uri": self.blocked_uri,
            "document_uri": self.document_uri,
            "source_file": self.source_file,
            "line": self.line,
            "count": self.count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }


class CspReportStore:
    """In-memory, signature-deduped violation store.

    Diagnostics, not audit data: contents reset on restart, and the store
    caps at :data:`MAX_SIGNATURES` distinct signatures (oldest evicted).
    A persistent backend can replace this behind the same interface later.
    """

    def __init__(self, max_signatures: int = MAX_SIGNATURES) -> None:
        self._max = max(1, max_signatures)
        self._by_signature: dict[tuple[str, str, str], CspViolation] = {}
        self.total_received = 0

    def add(self, report: dict[str, str]) -> tuple[CspViolation, bool]:
        """Record one normalized report; returns (violation, is_new)."""
        self.total_received += 1
        signature = (
            report.get("directive", ""),
            report.get("blocked_uri", ""),
            report.get("source_file", ""),
        )
        existing = self._by_signature.get(signature)
        if existing is not None:
            existing.count += 1
            existing.last_seen = datetime.now(UTC).isoformat(timespec="seconds")
            return existing, False
        violation = CspViolation(
            directive=report.get("directive", ""),
            blocked_uri=report.get("blocked_uri", ""),
            document_uri=report.get("document_uri", ""),
            source_file=report.get("source_file", ""),
            line=report.get("line", ""),
        )
        if len(self._by_signature) >= self._max:
            oldest = next(iter(self._by_signature))
            del self._by_signature[oldest]
        self._by_signature[signature] = violation
        return violation, True

    def list_violations(self) -> list[CspViolation]:
        """Return violations, most frequent first."""
        return sorted(
            self._by_signature.values(), key=lambda v: v.count, reverse=True
        )


class CspReportEndpoint:
    """HTTP handlers for report ingestion and the operator summary."""

    def __init__(self, store: CspReportStore) -> None:
        self._store = store

    async def ingest(self, request: Request) -> Response:
        """Accept browser violation reports; always terse, never an oracle."""
        content_type = (request.headers.get("content-type") or "").lower()
        if not content_type.startswith(_ACCEPTED_CONTENT_TYPES):
            return Response(status_code=204)

        body = await request.body()
        if len(body) > MAX_REPORT_BODY_BYTES:
            return PlainTextResponse("Report too large", status_code=413)

        for report in parse_csp_reports(body, content_type):
            _violation, is_new = self._store.add(report)
            if is_new:
                logger.warning(
                    "admin.csp_violation",
                    directive=report.get("directive", ""),
                    blocked_uri=report.get("blocked_uri", ""),
                    document_uri=report.get("document_uri", ""),
                    source_file=report.get("source_file", ""),
                )
        return Response(status_code=204)

    async def list_reports(self, request: Request) -> Response:
        """Superuser-only JSON summary of collected violations."""
        user = getattr(request.state, "user", None)
        if user is None:
            return PlainTextResponse("Authentication required", status_code=401)
        if getattr(user, "is_superuser", False) is not True:
            return PlainTextResponse("Forbidden", status_code=403)
        return JSONResponse(
            {
                "total_received": self._store.total_received,
                "violations": [
                    v.as_dict() for v in self._store.list_violations()
                ],
            }
        )


__all__ = [
    "MAX_REPORT_BODY_BYTES",
    "MAX_SIGNATURES",
    "CspReportEndpoint",
    "CspReportStore",
    "CspViolation",
    "parse_csp_reports",
]
