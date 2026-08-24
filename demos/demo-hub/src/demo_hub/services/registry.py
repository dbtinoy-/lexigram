"""Catalog of every live demo service the hub monitors."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoService:
    """One monitorable demo entry.

    Attributes:
        slug: URL-safe identifier, also the tunnel subdomain prefix.
        name: Display name.
        port: Local port the service binds on this host.
        kind: ``web`` for live servers, ``cli`` for offline entries.
        blurb: One-line description for the card grid.
        check_path: Path used for the health GET.
    """

    slug: str
    name: str
    port: int
    kind: str
    blurb: str
    check_path: str = "/"


class ServiceRegistry:
    """Static catalog plus async health probing of all live services."""

    def __init__(self) -> None:
        self.services: list[DemoService] = [
            DemoService(
                "realtime-monitor",
                "Realtime Monitor",
                7071,
                "web",
                "SSE replay + WebSocket operator channel",
            ),
            DemoService(
                "resilient-rates",
                "Resilient Rates",
                7073,
                "web",
                "Retry, circuit breaker, stale fallback desk",
            ),
            DemoService(
                "event-driven-orders",
                "Event-Driven Orders",
                7074,
                "web",
                "CQRS lifecycle with transactional outbox",
            ),
            DemoService(
                "rag-docs",
                "RAG Docs",
                7075,
                "web",
                "Cited answers over framework documentation",
            ),
            DemoService(
                "support-agent",
                "Support Agent",
                8082,
                "web",
                "ReAct agent with scripted LLM + tools",
            ),
            DemoService(
                "memory-chat",
                "Memory Chat",
                8083,
                "web",
                "Episodic + semantic memory, owner isolation",
            ),
            DemoService(
                "ai-guardrails",
                "AI Guardrails",
                8084,
                "web",
                "Injection blocking, PII redaction, budgets",
            ),
            DemoService(
                "prompt-lab",
                "Prompt Lab",
                8085,
                "web",
                "Prompt versioning with deterministic A/B",
            ),
            DemoService(
                "feedback-loop",
                "Feedback Loop",
                8086,
                "web",
                "Ratings promoted into regression suites",
            ),
            DemoService(
                "auth-web",
                "Auth Web",
                8081,
                "web",
                "Cookie sessions, JWT claims, lockout",
            ),
            DemoService(
                "auth-rbac",
                "Auth RBAC",
                8090,
                "web",
                "Permission matrix with live authorize()",
            ),
            DemoService(
                "auth-apikeys",
                "Auth API Keys",
                8091,
                "web",
                "Scoped machine keys, instant revocation",
            ),
            DemoService(
                "auth-mfa",
                "Auth MFA",
                8092,
                "web",
                "TOTP challenge flow with backup codes",
            ),
            DemoService(
                "llm-reproducibility",
                "LLM Reproducibility",
                0,
                "cli",
                "Seeded digest-pinned experiment (CLI/notebook)",
            ),
        ]

    async def statuses(self) -> list[dict[str, object]]:
        """Probe every web service concurrently; CLI entries pass through."""
        import asyncio
        import time

        import httpx

        async def probe(svc: DemoService) -> dict[str, object]:
            if svc.kind != "web":
                return {
                    "slug": svc.slug,
                    "name": svc.name,
                    "port": svc.port,
                    "kind": svc.kind,
                    "blurb": svc.blurb,
                    "status": "cli",
                    "latency_ms": None,
                }
            started = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=1.5) as client:
                    resp = await client.get(
                        f"http://127.0.0.1:{svc.port}{svc.check_path}"
                    )
                ok = resp.status_code < 500
            except Exception:  # noqa: BLE001 - probe must never raise
                ok = False
            latency = round((time.perf_counter() - started) * 1000, 1)
            return {
                "slug": svc.slug,
                "name": svc.name,
                "port": svc.port,
                "kind": svc.kind,
                "blurb": svc.blurb,
                "status": "up" if ok else "down",
                "latency_ms": latency,
            }

        return list(await asyncio.gather(*(probe(s) for s in self.services)))
