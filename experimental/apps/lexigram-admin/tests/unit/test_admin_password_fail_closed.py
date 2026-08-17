"""Admin password hashing must fail closed when bcrypt is unavailable (F4)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from lexigram.admin.lib.password import hash_password


def test_hash_password_raises_when_bcrypt_missing() -> None:
    with patch.dict("sys.modules", {"bcrypt": None}):
        with pytest.raises(RuntimeError, match="bcrypt"):
            hash_password("test-password")


def test_hash_password_never_returns_sha256() -> None:
    hashed = hash_password("test-password")
    assert hashed.startswith("$2b$")
    assert len(hashed) != 64
