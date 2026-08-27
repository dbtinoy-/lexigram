"""DI wiring for the prompt-lab demo.

A Provider tells the DI container *what* exists and *how* to build it.
Two-phase lifecycle: ``register()`` binds, ``boot()`` initialises.

Simplest patterns for new users:

- ``container.singleton(Thing, instance=Thing())`` — already built, hand it over
- ``container.singleton(Thing, factory=lambda: ...)`` — build lazily on first resolve
- ``container.singleton(Thing, factory=self._build_thing)`` — async factory for complex wiring
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.core.health import HealthCheckResult
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from prompt_lab.repository.templates import TEMPLATES
from prompt_lab.services.ab_runner import ABRunner
from prompt_lab.services.versioning import LabVersions

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        BootContainerProtocol,
        ContainerRegistrarProtocol,
    )

logger = get_logger(__name__)

__all__ = ["LabProvider"]


class LabProvider(Provider):
    """Demo-specific DI registrations — your app replaces this.

    Provider lifecycle: register() → boot() → shutdown().
    register() binds services (no I/O); boot() initialises after freeze.
    """

    name = "prompt-lab"

    def __init__(self) -> None:
        super().__init__()
        self._versions = LabVersions(max_versions=10)
        self._runner: ABRunner | None = None

    def _get_runner(self) -> ABRunner:
        if self._runner is None:
            raise RuntimeError("LabProvider has not been booted yet")
        return self._runner

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Seed revisions eagerly; the runner resolves in boot()."""
        self._versions.seed(TEMPLATES)
        container.singleton(LabVersions, instance=self._versions)
        container.singleton(ABRunner, factory=self._get_runner)

    async def boot(self, container: BootContainerProtocol) -> None:
        """Assemble the runner over the seeded store."""
        self._runner = ABRunner(versions=self._versions)
        logger.info("lab_provider.booted", variants=len(TEMPLATES))

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report component readiness with live counters."""
        return HealthCheckResult(
            component=self.name,
            details={"variants_seeded": len(self._versions.history("v2"))},
        )
