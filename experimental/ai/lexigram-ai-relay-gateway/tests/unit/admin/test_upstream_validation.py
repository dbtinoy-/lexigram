"""Upstream URL validation on channel create/update (stored-SSRF guard)."""

from __future__ import annotations

import pytest

from lexigram.ai.relay.gateway.admin.actions import _validate_upstream_url


@pytest.mark.parametrize(
    "url",
    [
        "http://api.example.com/v1",  # scheme
        "ftp://api.example.com",
        "https://127.0.0.1/v1",  # loopback literal
        "https://169.254.169.254/latest/meta-data",  # cloud metadata
        "not a url",
    ],
)
def test_dangerous_urls_rejected(url):
    ok, err = _validate_upstream_url(url)
    assert not ok
    assert err


def test_internal_hostname_allowed_for_operator_upstreams():
    """Relay upstreams are often internal proxies — RFC1918 hostnames OK."""
    ok, err = _validate_upstream_url("https://10.0.0.5:8080/v1")
    assert ok, err


def test_https_public_url_accepted():
    ok, err = _validate_upstream_url("https://api.example.com/v1")
    assert ok
    assert err is None


def test_allowlist_restricts_hosts():
    ok, _ = _validate_upstream_url(
        "https://evil.example.com", allowlist=("api.openai.com",)
    )
    assert not ok


def test_allowlist_match_accepted():
    ok, err = _validate_upstream_url(
        "https://api.openai.com/v1", allowlist=("api.openai.com",)
    )
    assert ok and err is None
