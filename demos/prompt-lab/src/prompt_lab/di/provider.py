"""DI wiring for the prompt-lab demo (internal)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.contracts.core.health import (
    HealthCheckResult,
)
from lexigram.di.provider import Provider

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

from prompt_lab.repository.templates import TEMPLATES
from prompt_lab.services.ab_runner import ABRunner
from prompt_lab.services.versioning import LabVersions


class LabProvider(Provider):
    """Binds seeded versions and assembles the runner at boot."""

    name = "prompt-lab"

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Report component readiness with live counters."""
        return HealthCheckResult(
            component=self.name,
            details={"variants_seeded": len(self._versions.history("v2"))},
        )

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

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Assemble the runner over the seeded store."""
        self._runner = ABRunner(versions=self._versions)


__all__ = ["LabProvider"]
