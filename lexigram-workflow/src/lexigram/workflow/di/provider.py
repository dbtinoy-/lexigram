"""WorkflowProvider — DI integration for the lexigram-workflow package.

Registers the workflow subsystem (pipelines, bulk operations, sagas)
into the Lexigram DI container with sensible defaults and optional
user-supplied overrides.

Example::

    from lexigram.app import Application
    from lexigram.workflow.di import WorkflowProvider
    from lexigram.workflow.config import BulkOperationConfig

    app = Application()
    app.use(WorkflowProvider(config=BulkOperationConfig(batch_size=200)))
    await app.start()
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Self, cast

from lexigram.contracts.core import HealthCheckResult, HealthStatus, ProviderPriority
from lexigram.contracts.workflow import (
    ContentCheckpointStoreProtocol,
    PipelineProtocol,
    SagaStoreProtocol,
    StateMachineProtocol,
    StatePersistenceProtocol,
)
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from lexigram.workflow.config import (
    BulkOperationConfig,
    ContentCheckpointConfig,
    GraphConfig,
)
from lexigram.workflow.pipeline import Pipeline

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )
    from lexigram.contracts.data import DatabaseProviderProtocol

_logger = get_logger(__name__)


class WorkflowProvider(Provider):
    """DI provider for the workflow subsystem.

    Registers pipeline, bulk-operation, and saga infrastructure into
    the container.  All registrations use ``singleton`` scope so that
    the same configured objects are shared across the application.

    Attributes:
        config: ``BulkOperationConfig`` controlling bulk and pipeline defaults.
        saga_store: Optional ``SagaStoreProtocol`` implementation for
            durable saga state.  When omitted, sagas operate in-memory
            only (suitable for development and single-process deployments).
    """

    name = "workflow"
    priority = ProviderPriority.DOMAIN
    config_key: str | None = "workflow"
    config_model: type | None = BulkOperationConfig

    def __init__(
        self,
        config: BulkOperationConfig | None = None,
        saga_store: SagaStoreProtocol | None = None,
        state_machine: StateMachineProtocol | None = None,
        db_provider: DatabaseProviderProtocol | None = None,
        state_table: str = "workflow_state_transitions",
        content_checkpoint_store: ContentCheckpointStoreProtocol | None = None,
        content_checkpoint_config: ContentCheckpointConfig | None = None,
    ) -> None:
        """Initialise the WorkflowProvider.

        Args:
            config: ``BulkOperationConfig`` for bulk and pipeline defaults.
                Defaults to ``BulkOperationConfig()`` (framework defaults).
            saga_store: Optional durable store for saga state.
                When ``None``, sagas run in-memory only.
            state_machine: Optional pre-configured :class:`~lexigram.workflow.state.StateMachine`
                instance to register under :class:`~lexigram.contracts.workflow.StateMachineProtocol`.
                When ``None``, no state machine singleton is registered.
            db_provider: Optional database provider for state transition
                persistence.
            state_table: SQL table name used by ``DatabaseStatePersistence``.
                Defaults to ``"workflow_state_transitions"``.
            content_checkpoint_store: Optional :class:`~lexigram.contracts.workflow.ContentCheckpointStoreProtocol`
                implementation for content-addressed saga checkpoints.
        """
        super().__init__()
        self._config = config or BulkOperationConfig()
        self._saga_store = saga_store
        self._state_machine = state_machine
        self._db_provider = db_provider
        self._state_table = state_table
        self._content_checkpoint_store = content_checkpoint_store
        self._content_checkpoint_config = (
            content_checkpoint_config or ContentCheckpointConfig()
        )

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_config(cls, config: BulkOperationConfig, **context: Any) -> Self:
        """Create provider from config object."""
        return cls(config=config)

    # ------------------------------------------------------------------
    # Provider lifecycle
    # ------------------------------------------------------------------

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register workflow services into the DI container.

        Bindings registered:
        - ``WorkflowProvider`` — self-reference for inspection.
        - ``BulkOperationConfig`` — pipeline/bulk defaults.
        - ``Pipeline`` / ``PipelineProtocol`` — default pipeline factory.
        - ``SagaStoreProtocol`` — optional durable saga store.

        Args:
            container: DI registrar provided by the framework.
        """
        config = self._config
        saga_store = self._saga_store

        container.singleton(WorkflowProvider, lambda: self)
        container.singleton(BulkOperationConfig, lambda: config)
        container.singleton(GraphConfig, GraphConfig)
        # Register the content-checkpoint config so downstream code
        # (ContentAddressedSaga and store backends) can resolve threshold +
        # TTL settings without each call site duplicating the values.
        cc_config = self._content_checkpoint_config
        container.singleton(ContentCheckpointConfig, lambda: cc_config)
        # Default pipeline — callers may request their own instances via
        # the Pipeline constructor; this singleton acts as a shared default.
        container.singleton(
            cast("type", PipelineProtocol),
            Pipeline,
        )
        container.singleton(Pipeline, Pipeline)

        if self._state_machine is not None:
            sm = self._state_machine
            container.singleton(
                cast("type", StateMachineProtocol),
                lambda: sm,
            )

        if self._db_provider is not None:
            from lexigram.workflow.state.persistence import DatabaseStatePersistence

            db = self._db_provider
            table = self._state_table
            container.singleton(
                cast("type", StatePersistenceProtocol),
                lambda: DatabaseStatePersistence(provider=db, table_name=table),
            )

        if saga_store is not None:
            container.singleton(
                cast("type", SagaStoreProtocol),
                lambda: saga_store,
            )

        if self._content_checkpoint_store is not None:
            container.singleton(
                cast("type", ContentCheckpointStoreProtocol),
                lambda: self._content_checkpoint_store,
            )

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Perform post-registration initialisation.

        Resolves ``BulkOperationConfig`` and logs the active configuration so
        that operators can confirm the expected settings on startup.

        Args:
            container: DI resolver provided by the framework.
        """
        try:
            resolved_config: BulkOperationConfig = await container.resolve(
                BulkOperationConfig
            )
            _logger.info(
                "workflow_provider_booted",
                bulk_batch_size=resolved_config.batch_size,
                bulk_concurrency=resolved_config.max_concurrency,
                bulk_timeout=resolved_config.timeout,
                pipeline_timeout=resolved_config.pipeline_timeout,
                graph_engine="available",
                saga_store=type(self._saga_store).__name__
                if self._saga_store
                else "none",
                state_persistence="database" if self._db_provider else "none",
                content_checkpoint=type(self._content_checkpoint_store).__name__
                if self._content_checkpoint_store
                else "none",
            )
        except (RuntimeError, OSError, LookupError, AttributeError) as exc:
            _logger.warning(
                "workflow_provider_boot_warning",
                error=str(exc),
            )

    async def shutdown(self) -> None:
        """Shut down the workflow provider and release any held resources."""
        _logger.info("workflow_provider_shutdown")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check provider health.

        Args:
            timeout: Maximum seconds to wait for health check response.

        Returns:
            HealthCheckResult with status and component details.
        """
        start = time.perf_counter()
        details: dict[str, Any] = {"components": {}}
        overall_status = HealthStatus.HEALTHY

        details["components"]["pipeline"] = {"status": "healthy"}

        if self._saga_store is not None:
            details["components"]["saga_store"] = {
                "status": "healthy",
                "driver": type(self._saga_store).__name__,
            }

        if self._state_machine is not None:
            details["components"]["state_machine"] = {
                "status": "healthy",
                "driver": type(self._state_machine).__name__,
            }

        if self._db_provider is not None:
            details["components"]["state_persistence"] = {
                "status": "healthy",
                "table": self._state_table,
            }

        return HealthCheckResult(
            component="workflow",
            status=overall_status,
            details=details,
            duration_ms=(time.perf_counter() - start) * 1000,
        )


__all__ = ["WorkflowProvider"]
