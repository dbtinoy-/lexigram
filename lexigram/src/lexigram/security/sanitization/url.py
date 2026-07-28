"""URL and path sanitization helpers."""

from __future__ import annotations

import ipaddress
import re
import urllib.parse

from lexigram.logging import get_logger

logger = get_logger(__name__)


class UrlSanitizer:
    """Sanitizer for URLs, paths, and SSRF protections."""

    _URL_SCHEME_RE = re.compile(r"^[\x00-\x20]*([^\x00-\x20:]+):", re.IGNORECASE)
    _DANGEROUS_SCHEMES: frozenset[str] = frozenset(
        {"javascript", "vbscript", "data", "file"}
    )
    _PATH_TRAVERSAL_RE = re.compile(r"\.{2,}[/\\]|[/\\]\.{2,}|^\.{2,}$")
    _PRIVATE_IPV4_NETWORKS: tuple[ipaddress.IPv4Network, ...] = (
        ipaddress.IPv4Network("10.0.0.0/8"),
        ipaddress.IPv4Network("172.16.0.0/12"),
        ipaddress.IPv4Network("192.168.0.0/16"),
        ipaddress.IPv4Network("127.0.0.0/8"),
        ipaddress.IPv4Network("169.254.0.0/16"),
        ipaddress.IPv4Network("100.64.0.0/10"),
    )
    _PRIVATE_IPV6_NETWORKS: tuple[ipaddress.IPv6Network, ...] = (
        ipaddress.IPv6Network("::1/128"),
        ipaddress.IPv6Network("fc00::/7"),
        ipaddress.IPv6Network("fe80::/10"),
    )

    def sanitize_url(self, url: str) -> str:
        """Return an empty string when the URL uses a dangerous scheme."""
        if not url:
            return url

        match = self._URL_SCHEME_RE.match(url.lstrip())
        if match:
            scheme = match.group(1).lower().replace("\x00", "").replace(" ", "")
            if scheme in self._DANGEROUS_SCHEMES:
                logger.warning("security.dangerous_url_scheme", scheme=scheme)
                return ""

        return url

    def sanitize_path(self, path: str) -> str:
        """Strip traversal sequences and null bytes from file paths."""
        if not path:
            return path

        sanitized = path.replace("\x00", "")
        previous: str | None = None
        while sanitized != previous:
            previous = sanitized
            sanitized = self._PATH_TRAVERSAL_RE.sub("", sanitized)

        if sanitized != path:
            logger.warning(
                "security.path_traversal_detected",
                original_length=len(path),
                sanitized_length=len(sanitized),
            )

        return sanitized

    def is_safe_url_for_request(self, url: str) -> bool:
        """Return False if the URL resolves to a private or reserved IP."""
        if not url:
            return False

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
            return True

        if isinstance(addr, ipaddress.IPv4Address):
            return not any(addr in network for network in self._PRIVATE_IPV4_NETWORKS)

        return not any(addr in network for network in self._PRIVATE_IPV6_NETWORKS)


__all__ = ["UrlSanitizer"]
