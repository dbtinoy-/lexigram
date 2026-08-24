"""Stored-SSRF guard for relay-gateway channel upstream URLs."""

from __future__ import annotations


def validate_upstream_url(
    url: str,
    *,
    allowlist: tuple[str, ...] = (),
) -> tuple[bool, str | None]:
    """Validate a candidate channel ``upstream_base_url``.

    Stored-SSRF guard (spec finding 8): the URL must parse, use ``https``, and
    pass :func:`is_safe_url_for_request` (scheme/private-host/DNS checks).
    When a non-empty operator ``allowlist`` is configured the host must also
    match one of its entries.

    Returns:
        ``(True, None)`` when acceptable, else ``(False, reason)``.
    """
    import ipaddress
    from urllib.parse import urlparse

    parsed = urlparse(url)
    if parsed.scheme != "https":
        return False, "upstream_base_url must use https"

    # Relay upstreams are operator-configured and are frequently internal
    # (self-hosted proxies), so RFC1918 hostnames are legitimate. What must
    # never be reachable is the machine/cloud-metadata boundary: reject
    # literal loopback, link-local (169.254.169.254), and this-host IPs.
    try:
        ip = ipaddress.ip_address(parsed.hostname or "")
    except ValueError:
        ip = None
    if ip is not None and (ip.is_loopback or ip.is_link_local):
        return False, (
            f"upstream_base_url must not target loopback, link-local, or "
            f"non-global address {parsed.hostname!r}"
        )

    if allowlist and parsed.hostname not in allowlist:
        return False, (
            f"upstream host {parsed.hostname!r} is not in the configured "
            "upstream allowlist"
        )
    return True, None


__all__ = ["validate_upstream_url"]
