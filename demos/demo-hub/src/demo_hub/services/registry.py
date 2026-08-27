"""Catalog of every demo the hub can host and monitor."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

_DEMOS_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


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
        readme_path: Path to the demo's README.md relative to the demos root.
    """

    slug: str
    name: str
    port: int
    kind: str
    blurb: str
    demo_dir: str = ""
    app_path: str = ""
    readme_path: str = ""
    check_path: str = "/"
    errors: list[str] = field(default_factory=list)

    @property
    def is_hostable(self) -> bool:
        """Whether the fleet can boot and embed this entry."""
        return self.kind == "web"

    def read_readme(self) -> str | None:
        """Return the README.md content, or ``None`` if not found."""
        if not self.readme_path:
            return None
        full = _DEMOS_ROOT / self.readme_path
        if full.is_file():
            return full.read_text(encoding="utf-8")
        return None


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
                "realtime-monitor/README.md",
            ),
            DemoService(
                "resilient-rates",
                "Resilient Rates",
                7073,
                "web",
                "Cache-aside + resilience pipeline with stale fallback",
                "resilient-rates",
                "rates.app",
                "resilient-rates/README.md",
            ),
            DemoService(
                "event-driven-orders",
                "Event-Driven Orders",
                7074,
                "web",
                "CQRS lifecycle with transactional outbox",
                "event-driven-orders",
                "orders.app",
                "event-driven-orders/README.md",
            ),
            DemoService(
                "rag-docs",
                "RAG Docs",
                7075,
                "web",
                "Cited answers over framework documentation",
                "rag-docs",
                "rag_docs.app",
                "rag-docs/README.md",
            ),
            DemoService(
                "support-agent",
                "Support Agent",
                8082,
                "web",
                "ReAct agent with scripted LLM + tools",
                "support-agent",
                "support_agent.app",
                "support-agent/README.md",
            ),
            DemoService(
                "memory-chat",
                "Memory Chat",
                8083,
                "web",
                "Episodic + semantic memory, owner isolation",
                "memory-chat",
                "memory_chat.app",
                "memory-chat/README.md",
            ),
            DemoService(
                "ai-guardrails",
                "AI Guardrails",
                8084,
                "web",
                "Injection blocking, PII redaction, governance gates",
                "ai-guardrails",
                "guard_gate.app",
                "ai-guardrails/README.md",
            ),
            DemoService(
                "prompt-lab",
                "Prompt Lab",
                8085,
                "web",
                "Prompt versioning with deterministic A/B",
                "prompt-lab",
                "prompt_lab.app",
                "prompt-lab/README.md",
            ),
            DemoService(
                "feedback-loop",
                "Feedback Loop",
                8086,
                "web",
                "Ratings promoted into regression suites",
                "feedback-loop",
                "feedback_loop.app",
                "feedback-loop/README.md",
            ),
            DemoService(
                "auth-web",
                "Auth Web",
                8081,
                "web",
                "Cookie sessions, JWT claims, lockout",
                "auth-web",
                "auth_web.app",
                "auth-web/README.md",
            ),
            DemoService(
                "auth-rbac",
                "Auth RBAC",
                8090,
                "web",
                "Permission matrix with live authorize()",
                "auth-rbac",
                "rbac_console.app",
                "auth-rbac/README.md",
            ),
            DemoService(
                "auth-apikeys",
                "Auth API Keys",
                8091,
                "web",
                "Scoped machine keys, instant revocation",
                "auth-apikeys",
                "apikey_console.app",
                "auth-apikeys/README.md",
            ),
            DemoService(
                "auth-mfa",
                "Auth MFA",
                8092,
                "web",
                "TOTP challenge flow with backup codes",
                "auth-mfa",
                "mfa_console.app",
                "auth-mfa/README.md",
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
