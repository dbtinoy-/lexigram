"""Fleet: boot every demo Application in-process and mount it on the hub.

Each child is a complete Lexigram ``Application`` (own DI container, own
providers) whose Starlette app is mounted under ``/demos/<slug>/``. Demos
keep working standalone — embedding simply reuses their module factories.
"""

from __future__ import annotations

import importlib
from pathlib import Path
import sys
from typing import TYPE_CHECKING

from starlette.applications import Starlette

from demo_hub.services.registry import ServiceRegistry
from demo_hub.subsite import SubsiteMiddleware
from lexigram.logging import get_logger
from lexigram.web.di.provider import WebProvider

if TYPE_CHECKING:
    from lexigram.app import Application

logger = get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[4]


class Fleet:
    """Boot, mount and track the embedded demo applications."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self._registry = registry
        self._apps: dict[str, Application] = {}
        self._failures: dict[str, str] = {}

    @property
    def mounted(self) -> dict[str, bool]:
        """Slug → whether the demo booted and is serving."""
        return dict.fromkeys(self._apps, True)

    @property
    def failures(self) -> dict[str, str]:
        """Slug → error text for demos that failed to boot."""
        return dict(self._failures)

    def snapshot(self) -> list[dict[str, object]]:
        """Status payload for ``/api/status`` (see ServiceRegistry.snapshot)."""
        return self._registry.snapshot(self.mounted, self.failures)

    def _ensure_import_paths(self) -> None:
        for svc in self._registry.web_services():
            src = REPO_ROOT / "demos" / svc.demo_dir / "src"
            if not src.is_dir():
                raise FileNotFoundError(f"missing demo sources: {src}")
            if str(src) not in sys.path:
                sys.path.append(str(src))

    async def mount_all(self, parent: Starlette) -> None:
        """Boot every web demo and mount it under ``/demos/<slug>/``.

        A failing demo is logged and surfaced via :attr:`failures`; it never
        prevents the remaining demos or the hub itself from serving.
        """
        self._ensure_import_paths()
        for svc in self._registry.web_services():
            try:
                module = importlib.import_module(svc.app_path)
                child_app = module.create_app()
                await child_app.start()
                web = await child_app.container.resolve(WebProvider)
                if web.starlette is None:
                    raise RuntimeError("child starlette app missing")
                base = f"/demos/{svc.slug}"
                parent.mount(
                    base,
                    app=SubsiteMiddleware(web.starlette, base=base),
                )
                self._apps[svc.slug] = child_app
                logger.info("fleet_child_mounted", slug=svc.slug)
            except Exception as exc:  # noqa: BLE001 - isolate child faults
                self._failures[svc.slug] = f"{type(exc).__name__}: {exc}"
                logger.error("fleet_child_failed", slug=svc.slug, error=str(exc))

    async def aclose(self) -> None:
        """Shut down every booted child application."""
        for slug, app in reversed(list(self._apps.items())):
            try:
                await app.stop()
            except Exception as exc:  # noqa: BLE001 - best-effort teardown
                logger.warning("fleet_child_shutdown_failed", slug=slug, error=str(exc))
        self._apps.clear()


__all__ = ["Fleet"]
