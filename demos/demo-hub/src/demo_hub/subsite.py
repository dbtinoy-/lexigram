"""ASGI helpers that host a child demo under a single hub origin.

The child applications are written to be served from their own origin
(root-relative URLs such as ``/static/app.js`` or ``fetch("/stats")``).
Mounting them under ``/demos/<slug>`` requires two adjustments:

1. Response rewriting for HTML pages — asset attributes gain the mount
   prefix, and a small bootstrap script teaches ``fetch``, ``EventSource``
   and ``WebSocket`` about the prefix.
2. Header fixing — ``Location`` redirects and ``Path=`` cookie attributes
   are rebased so children stay inside their own subtree.
"""

from __future__ import annotations

import re
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

_ATTR_RE = re.compile(rb"""(\b(?:href|src|action)\s*=\s*)(["'])/(?!/)""")
_HEAD_RE = re.compile(rb"(<head\b[^>]*>)", re.IGNORECASE)

_SHIM_TMPL = """<script>(function(){var B="__BASE__";function P(u){
return typeof u==="string"&&u.charAt(0)==="/"&&u.charAt(1)!=="/"?B+u:u}
var F=window.fetch;window.fetch=function(i,o){try{
if(typeof i==="string")i=P(i);
else if(i&&i instanceof Request)i=new Request(P(i.url),i)}catch(e){}
return F.call(window,i,o)};
if(window.EventSource){var E=window.EventSource;
window.EventSource=function(u,c){return new E(P(u),c)};
window.EventSource.prototype=E.prototype}
if(window.WebSocket){var W=window.WebSocket;
window.WebSocket=function(u,c){return new W(P(u),c)};
window.WebSocket.prototype=W.prototype}})();
</script>"""


def rewrite_html(body: bytes, base: str) -> bytes:
    """Rebase one HTML document so it loads correctly under ``base``."""
    shim = _SHIM_TMPL.replace("__BASE__", base).encode()
    if _HEAD_RE.search(body):
        body = _HEAD_RE.sub(lambda m: m.group(1) + shim, body, count=1)
    else:
        body = shim + body
    return _ATTR_RE.sub(lambda m: m.group(1) + m.group(2) + base.encode() + b"/", body)


def _rebase(value: str, base: str) -> str:
    if value.startswith("/") and not value.startswith((base + "/", "//")):
        return base + value
    return value


class SubsiteMiddleware:
    """Wrap a child ASGI app so it behaves correctly under ``base``."""

    def __init__(self, app: ASGIApp, base: str) -> None:
        self.app = app
        self.base = base.rstrip("/")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        buffered_start: Message | None = None
        chunks: list[bytes] = []
        is_html = False
        outer_send = send

        async def _send(message: Message) -> None:
            nonlocal buffered_start, is_html
            if message["type"] == "http.response.start":
                headers: Any = [(k.decode(), v.decode()) for k, v in message["headers"]]
                headers = [
                    (k, v) for k, v in headers if k.lower() not in {"content-length"}
                ]
                fixed: list[tuple[str, str]] = []
                for k, v in headers:
                    if k.lower() == "location":
                        v = _rebase(v, self.base)
                    elif k.lower() == "set-cookie":
                        v = re.sub(
                            r"(?i);\s*Path=/(?![\w.-])",
                            f"; Path={self.base}/",
                            v,
                        )
                    fixed.append((k, v))
                ctype = next((v for k, v in fixed if k.lower() == "content-type"), "")
                is_html = ctype.split(";")[0].strip() == "text/html"
                if is_html:
                    buffered_start = {
                        "type": "http.response.start",
                        "status": message["status"],
                        "headers": [(k.encode(), v.encode()) for k, v in fixed],
                    }
                    return
                message = dict(message)
                message["headers"] = [(k.encode(), v.encode()) for k, v in fixed]
                await outer_send(message)
                return

            if message["type"] == "http.response.body" and is_html:
                chunks.append(message.get("body", b""))
                if message.get("more_body", False):
                    return
                out = rewrite_html(b"".join(chunks), self.base)
                assert buffered_start is not None
                buffered_start["headers"].append(
                    (b"content-length", str(len(out)).encode())
                )
                await outer_send(buffered_start)
                await outer_send({"type": "http.response.body", "body": out})
                return

            await outer_send(message)

        await self.app(scope, receive, _send)


__all__ = ["SubsiteMiddleware", "rewrite_html"]
