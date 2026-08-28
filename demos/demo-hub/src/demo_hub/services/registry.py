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
        kind: ``web`` for live browser consoles.
        group: Top-level grouping — ``standard`` (single-package) or
            ``multi-module`` (multi-package composition).
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
    group: str
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
                "standard",
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
                "standard",
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
                "standard",
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
                "standard",
                "Cited answers over docs — no LLM, BLAKE2b embedder",
                "rag-docs",
                "rag_docs.app",
                "rag-docs/README.md",
            ),
            DemoService(
                "support-agent",
                "Support Agent",
                8082,
                "web",
                "standard",
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
                "standard",
                "Episodic + semantic memory — zero LLM, template responder",
                "memory-chat",
                "memory_chat.app",
                "memory-chat/README.md",
            ),
            DemoService(
                "ai-guardrails",
                "AI Guardrails",
                8084,
                "web",
                "standard",
                "Guards, budgets, audit — canned replies, no LLM",
                "ai-guardrails",
                "guard_gate.app",
                "ai-guardrails/README.md",
            ),
            DemoService(
                "prompt-lab",
                "Prompt Lab",
                8085,
                "web",
                "standard",
                "Prompt versioning with deterministic A/B — zero LLM",
                "prompt-lab",
                "prompt_lab.app",
                "prompt-lab/README.md",
            ),
            DemoService(
                "feedback-loop",
                "Feedback Loop",
                8086,
                "web",
                "standard",
                "Ratings → regression — no model call, canned Q&A",
                "feedback-loop",
                "feedback_loop.app",
                "feedback-loop/README.md",
            ),
            DemoService(
                "auth-web",
                "Auth Web",
                8081,
                "web",
                "standard",
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
                "standard",
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
                "standard",
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
                "standard",
                "TOTP challenge flow with backup codes",
                "auth-mfa",
                "mfa_console.app",
                "auth-mfa/README.md",
            ),
            DemoService(
                "llm-router",
                "LLM Router",
                8093,
                "web",
                "standard",
                "Content generation with deterministic routing",
                "llm-router",
                "content_gen.app",
                "llm-router/README.md",
            ),
            DemoService(
                "monitor-stack",
                "Monitor Stack",
                8094,
                "web",
                "standard",
                "Tracing and observability dashboard",
                "monitor-stack",
                "monitorstack.app",
                "monitor-stack/README.md",
            ),
            DemoService(
                "queue-worker",
                "Queue Worker",
                8095,
                "web",
                "standard",
                "Background job processing with retry",
                "queue-worker",
                "queueworker.app",
                "queue-worker/README.md",
            ),
            DemoService(
                "rag-pipeline",
                "RAG Pipeline",
                8096,
                "web",
                "standard",
                "Retrieval-augmented generation pipeline",
                "rag-pipeline",
                "ragdocs.app",
                "rag-pipeline/README.md",
            ),
            DemoService(
                "sql-repository",
                "SQL Repository",
                8097,
                "web",
                "standard",
                "SQLAlchemy repository pattern with unit-of-work",
                "sql-repository",
                "taskapp.app",
                "sql-repository/README.md",
            ),
            DemoService(
                "webhook-relay",
                "Webhook Relay",
                8098,
                "web",
                "standard",
                "Inbound webhook processing and relay",
                "webhook-relay",
                "webhookrelay.app",
                "webhook-relay/README.md",
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
            One dict per service with a ``status`` of ``up`` or ``down``.
        """
        payload: list[dict[str, object]] = []
        for svc in self.services:
            status = "up" if mounted.get(svc.slug) else "down"
            payload.append(
                {
                    "slug": svc.slug,
                    "name": svc.name,
                    "port": svc.port,
                    "kind": svc.kind,
                    "group": svc.group,
                    "blurb": svc.blurb,
                    "status": status,
                    "error": failures.get(svc.slug),
                }
            )
        return payload


__all__ = ["DemoService", "ServiceRegistry"]
