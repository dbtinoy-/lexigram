import pytest


def test_skip_ephemeral_sessions_removed():
    pytest.skip(
        "Ephemeral session fallback removed; SessionManager should be attached by AdminAuthAdapter instead",
    )
