"""ImportService mass-assignment guard tests."""

from __future__ import annotations

from lexigram.admin.services.import_ import AdminImportService


def _service(allowed=None):
    return AdminImportService(data_source=object(), allowed_fields=allowed)


def test_unknown_field_rejected_when_allowlist_set():
    svc = _service({"name"})
    errors = svc._validate_rows([{"name": "Rex", "role": "root"}])
    assert any(e.field == "role" for e in errors)


def test_known_fields_pass_when_allowlist_set():
    svc = _service({"name", "is_active"})
    errors = svc._validate_rows([{"name": "Rex", "is_active": "on"}])
    assert errors == []


def test_no_allowlist_keeps_passthrough():
    svc = _service(None)
    errors = svc._validate_rows([{"anything": "goes"}])
    assert errors == []
