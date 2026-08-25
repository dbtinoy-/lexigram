"""Catalog of every demo the hub can host and monitor."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DemoService:
    """One hostable demo entry.

    Attributes:
        slug: URL-safe identifier; the demo is mounted at ``/demos/<slug>/``.
        name: Display name.
        port: Port used when the demo runs standalone (informational only —
            embedded mode serves everything from the hub's own port).
        kind: ``web`` for live consoles, ``cli`` for offline entries.
        blurb: One-line description for the card grid.
        demo_dir: Directory under ``demos/`` containing this demo.
        app_path: Dotted path of the demo's ``app`` module exposing
            ``create_app()`` — the composition root (starter pattern).
    """

    slug: str
    name: str
    port: int
    kind: str
    blurb: str
    demo_dir: str = ""
    app_path: str = ""
    check_path: str = "/"
    errors: list[str] = field(default_factory=list)

    @property
    def is_hostable(self) -> bool:
        """Whether the fleet can boot and embed this entry."""
        return self.kind == "web"


class ServiceRegistry:
    """Static catalog of all demos; fleet state is tracked by ``Fleet``."""

    def __init__(self) -> None:
        self.services: list[DemoService] = [
            DemoService(
                "realtime-monitor",
                "Realtime Monitor",
                7071,
                "web",
                "SSE replay + WebSocket operator channel",
                "realtime-monitor",
                "ops_console.app",
            ),
            DemoService(
                "resilient-rates",
                "Resilient Rates",
                7073,
                "web",
                "Retry, circuit breaker, stale fallback desk",
                "resilient-rates",
                "rates.app",
            ),
            DemoService(
                "event-driven-orders",
                "Event-Driven Orders",
                7074,
                "web",
                "CQRS lifecycle with transactional outbox",
                "event-driven-orders",
                "orders.app",
            ),
            DemoService(
                "rag-docs",
                "RAG Docs",
                7075,
                "web",
                "Cited answers over framework documentation",
                "rag-docs",
                "rag_docs.app",
            ),
            DemoService(
                "support-agent",
                "Support Agent",
                8082,
                "web",
                "ReAct agent with scripted LLM + tools",
                "support-agent",
                "support_agent.app",
            ),
            DemoService(
                "memory-chat",
                "Memory Chat",
                8083,
                "web",
                "Episodic + semantic memory, owner isolation",
                "memory-chat",
                "memory_chat.app",
            ),
            DemoService(
                "ai-guardrails",
                "AI Guardrails",
                8084,
                "web",
                "Injection blocking, PII redaction, budgets",
                "ai-guardrails",
                "guard_gate.app",
            ),
            DemoService(
                "prompt-lab",
                "Prompt Lab",
                8085,
                "web",
                "Prompt versioning with deterministic A/B",
                "prompt-lab",
                "prompt_lab.app",
            ),
            DemoService(
                "feedback-loop",
                "Feedback Loop",
                8086,
                "web",
                "Ratings promoted into regression suites",
                "feedback-loop",
                "feedback_loop.app",
            ),
            DemoService(
                "auth-web",
                "Auth Web",
                8081,
                "web",
                "Cookie sessions, JWT claims, lockout",
                "auth-web",
                "auth_web.app",
            ),
            DemoService(
                "auth-rbac",
                "Auth RBAC",
                8090,
                "web",
                "Permission matrix with live authorize()",
                "auth-rbac",
                "rbac_console.app",
            ),
            DemoService(
                "auth-apikeys",
                "Auth API Keys",
                8091,
                "web",
                "Scoped machine keys, instant revocation",
                "auth-apikeys",
                "apikey_console.app",
            ),
            DemoService(
                "auth-mfa",
                "Auth MFA",
                8092,
                "web",
                "TOTP challenge flow with backup codes",
                "auth-mfa",
                "mfa_console.app",
            ),
            DemoService(
                "llm-reproducibility",
                "LLM Reproducibility",
                0,
                "cli",
                "Seeded digest-pinned experiment (CLI/notebook)",
                "llm-reproducibility",
            ),
        ]

    def web_services(self) -> list[DemoService]:
        """Return entries that the fleet can boot and embed."""
        return [s for s in self.services if s.is_hostable]

    def snapshot(
        self,
        mounted: dict[str, bool],
        failures: dict[str, str],
    ) -> list[dict[str, object]]:
        """Compose the status payload consumed by the hub console.

        Args:
            mounted: Slug → whether the demo booted and is mounted.
            failures: Slug → error text for demos that failed to boot.

        Returns:
            One dict per service with a ``status`` of ``up``, ``down``
            or ``cli``.
        """
        payload: list[dict[str, object]] = []
        for svc in self.services:
            if svc.kind != "web":
                status = "cli"
            elif mounted.get(svc.slug):
                status = "up"
            else:
                status = "down"
            payload.append(
                {
                    "slug": svc.slug,
                    "name": svc.name,
                    "port": svc.port,
                    "kind": svc.kind,
                    "blurb": svc.blurb,
                    "status": status,
                    "error": failures.get(svc.slug),
                }
            )
        return payload


__all__ = ["DemoService", "ServiceRegistry"]
