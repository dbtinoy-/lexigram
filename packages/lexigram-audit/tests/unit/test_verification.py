"""Tests for HMAC checksum computation and verification."""

from __future__ import annotations

import pytest

from lexigram.audit.verification.checksum import (
    canonicalize_entry,
    compute_audit_checksum,
    verify_audit_checksum,
)


class TestChecksumFunctions:
    """Tests for HMAC checksum computation."""

    def test_canonicalize_sorts_keys(self) -> None:
        data = {"z": 1, "a": 2, "m": 3}
        result = canonicalize_entry(data)
        assert result == '{"a":2,"m":3,"z":1}'

    def test_compute_checksum_deterministic(self) -> None:
        key = b"test-secret"
        data = {"action": "user.login", "actor_id": "user-1"}
        c1 = compute_audit_checksum(data, key, schema_version=2)
        c2 = compute_audit_checksum(data, key, schema_version=2)
        assert c1 == c2
        assert len(c1) == 64  # SHA-256 hex = 64 chars

    def test_verify_checksum_passes_correct(self) -> None:
        key = b"secret"
        data = {"action": "test", "actor_id": "actor", "entry_schema_version": 2}
        checksum = compute_audit_checksum(data, key, schema_version=2)
        assert verify_audit_checksum(data, key, checksum) is True

    def test_verify_checksum_fails_tampered(self) -> None:
        key = b"secret"
        data = {"action": "test", "actor_id": "actor", "entry_schema_version": 2}
        checksum = compute_audit_checksum(data, key, schema_version=2)
        tampered = {**data, "actor_id": "attacker"}
        assert verify_audit_checksum(tampered, key, checksum) is False

    def test_verify_checksum_fails_wrong_key(self) -> None:
        data = {"action": "test", "actor_id": "actor", "entry_schema_version": 2}
        checksum = compute_audit_checksum(data, b"key1", schema_version=2)
        assert verify_audit_checksum(data, b"key2", checksum) is False


class TestChecksumSchemaVersion:
    """LXF-003: HMAC checksum with entry_schema_version."""

    def test_checksum_defaults_to_schema_v2(self) -> None:
        key = b"test-secret"
        data = {"action": "user.login", "actor_id": "user-1"}
        checksum = compute_audit_checksum(data, key)
        v2_checksum = compute_audit_checksum(data, key, schema_version=2)
        assert checksum == v2_checksum

    def test_v1_and_v2_checksums_differ(self) -> None:
        key = b"test-secret"
        data = {"action": "user.login", "actor_id": "user-1"}
        c1 = compute_audit_checksum(data, key, schema_version=1)
        c2 = compute_audit_checksum(data, key, schema_version=2)
        assert c1 != c2

    def test_verify_accepts_v1_checksum(self) -> None:
        key = b"secret"
        data = {"action": "test", "actor_id": "actor"}
        checksum = compute_audit_checksum(data, key, schema_version=1)
        assert verify_audit_checksum(data, key, checksum) is True

    def test_canonical_form_includes_schema_version(self) -> None:
        data = {"action": "test", "actor_id": "actor"}
        result = canonicalize_entry({**data, "entry_schema_version": 2})
        assert '"entry_schema_version"' in result
        assert ":2" in result
