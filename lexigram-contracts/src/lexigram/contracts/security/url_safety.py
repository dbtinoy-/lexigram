"""SSRF URL-safety primitive shared by every outbound HTTP consumer.

Pure standard-library only (``ipaddress``, ``socket``, ``urllib.parse``) so
that any extension package — including ``lexigram-webhook``, ``lexigram-ai-rag``
and ``lexigram-ai-mcp``, which may not import ``lexigram.security`` — can
consume it directly. Keep this file stdlib-only (import-linter Contract 1).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
import ipaddress
import socket
import urllib.parse

_PRIVATE_IPV4_NETWORKS: tuple[ipaddress.IPv4Network, ...] = (
    ipaddress.IPv4Network("0.0.0.0/8"),
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("100.64.0.0/10"),
    ipaddress.IPv4Network("127.0.0.0/8"),
    ipaddress.IPv4Network("169.254.0.0/16"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
    ipaddress.IPv4Network("224.0.0.0/4"),
    ipaddress.IPv4Network("240.0.0.0/4"),
)

_PRIVATE_IPV6_NETWORKS: tuple[ipaddress.IPv6Network, ...] = (
    ipaddress.IPv6Network("::/128"),
    ipaddress.IPv6Network("::1/128"),
    ipaddress.IPv6Network("fc00::/7"),
    ipaddress.IPv6Network("fe80::/10"),
)

HostResolver = Callable[
    [str], Sequence[ipaddress.IPv4Address | ipaddress.IPv6Address]
]


def resolve_hostname(
    hostname: str,
) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    """Resolve a hostname to all its address records via the system resolver.

    Args:
        hostname: DNS name to resolve.

    Returns:
        List of resolved addresses (A/AAAA records).

    Raises:
        OSError: If the hostname cannot be resolved.
    """
    infos = socket.getaddrinfo(
        hostname, None, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
    )
    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for _family, _stype, _proto, _canonname, sockaddr in infos:
        try:
            addresses.append(ipaddress.ip_address(sockaddr[0]))
        except ValueError:
            continue
    return addresses


def is_safe_url_for_request(
    url: str,
    *,
    resolver: HostResolver | None = None,
) -> bool:
    """Return False when requesting ``url`` could reach a private/reserved host.

    Checks the scheme (http/https only), rejects literal private/reserved IP
    hostnames, and — for DNS hostnames — resolves via ``resolver`` (defaults to
    the system ``getaddrinfo``) and rejects when ANY resolved address is
    private/reserved. Fails closed: an unresolvable or empty resolution is
    rejected.

    Args:
        url: Candidate absolute URL.
        resolver: Optional hostname resolver for hermetic tests. Defaults to
            the system resolver via :func:`resolve_hostname`.

    Returns:
        True only when a request to ``url`` cannot reach a private/reserved IP.
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return False

    if parsed.scheme.lower() not in {"http", "https"}:
        return False

    hostname = parsed.hostname
    if not hostname:
        return False

    hostname = hostname.strip("[]")
    try:
        addr = ipaddress.ip_address(hostname)
    except ValueError:
        return _hostname_is_public(hostname, resolver)

    return not _is_private(addr)


def _hostname_is_public(
    hostname: str, resolver: HostResolver | None
) -> bool:
    try:
        addresses = resolve_hostname(hostname) if resolver is None else resolver(hostname)
    except OSError:
        return False
    if not addresses:
        return False
    return all(not _is_private(address) for address in addresses)


def _is_private(
    addr: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> bool:
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    if isinstance(addr, ipaddress.IPv4Address):
        return any(addr in network for network in _PRIVATE_IPV4_NETWORKS)
    return any(addr in network for network in _PRIVATE_IPV6_NETWORKS)


__all__ = ["HostResolver", "is_safe_url_for_request", "resolve_hostname"]
