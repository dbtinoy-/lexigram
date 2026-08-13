"""Content-addressed saga orchestration.

Extends ``AbstractSaga`` with content-addressed checkpoint caching so that
stages keyed by ``sha256(stage_id || tenant_id || inputs)`` can skip
already-completed work on resume or re-run.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from lexigram.contracts.infra.storage.protocols import BlobStoreProtocol
from lexigram.contracts.workflow.content_checkpoint import (
    ContentCheckpointEntry,
    ContentCheckpointKey,
    ContentCheckpointStoreProtocol,
)
from lexigram.result import Err, Ok, Result
from lexigram.saga.base import AbstractSaga, SagaError, SagaState
from lexigram.saga.canonical_json import canonical_json_bytes
from lexigram.serialization import loads

if TYPE_CHECKING:
    from lexigram.contracts.workflow.protocols import SagaStoreProtocol

__all__ = [
    "ContentAddressedSaga",
    "ContentAddressedStage",
]


@dataclass
class ContentAddressedStage:
    """Descriptor for a single content-addressed saga stage.

    Unlike ``SagaStep`` (which uses a generic ``action`` callable), this stage
    is designed for content addressing: its inputs, handler version, and
    config-affecting-output are all hashed into ``ContentCheckpointKey``.
    """

    stage_id: str
    handler: Callable[[dict[str, Any]], Awaitable[Any]]
    handler_version: str
    config_affecting_output: dict[str, Any] = field(default_factory=dict)
    compensation: Callable[[Any], Awaitable[None]] | None = None


class ContentAddressedSaga(AbstractSaga[None]):
    """Saga where every stage handler is content-addressed.

    Subclass and register stages via ``add_stage()``; the framework computes the
    input hash, checks the checkpoint store, returns cached output, or runs the
    handler and caches the result.

    Args:
        saga_id: Stable identifier for this saga instance.
        checkpoint_store: Persistence backend for checkpoint entries.
        store: Optional saga state store (passed to ``AbstractSaga``).
        blob_store: Optional blob store for offloading large outputs.
        tenant_id: Optional tenant identifier (included in content-address key).
        inline_threshold_bytes: Max bytes to store inline; beyond this threshold
            the output is offloaded to ``blob_store``.
    """

    def __init__(
        self,
        saga_id: str,
        checkpoint_store: ContentCheckpointStoreProtocol,
        *,
        store: SagaStoreProtocol | None = None,
        blob_store: BlobStoreProtocol | None = None,
        tenant_id: str | None = None,
        inline_threshold_bytes: int = 1_048_576,
    ) -> None:
        super().__init__(store=store)
        self._saga_id = saga_id
        self._checkpoint_store = checkpoint_store
        self._blob_store = blob_store
        self._tenant_id = tenant_id
        self._inline_threshold_bytes = inline_threshold_bytes
        self._stages: list[ContentAddressedStage] = []

    # ------------------------------------------------------------------
    # AbstractSaga overrides
    # ------------------------------------------------------------------

    def get_id(self) -> str:
        return self._saga_id

    def is_completed(self) -> bool:
        return self.state == SagaState.COMPLETED

    # ------------------------------------------------------------------
    # Stage registration
    # ------------------------------------------------------------------

    def add_stage(self, stage: ContentAddressedStage) -> None:
        self._stages.append(stage)

    # ------------------------------------------------------------------
    # Content-addressed execution
    # ------------------------------------------------------------------

    async def execute(self) -> Result[None, SagaError]:
        self.state = SagaState.RUNNING
        self._completed_steps = []
        await self._persist_state()

        for stage in self._stages:
            try:
                await self.run_stage(stage, {})
            except (RuntimeError, ValueError, OSError) as exc:
                await self._run_compensation()
                return Err(SagaError(stage.stage_id, exc))

        self.state = SagaState.COMPLETED
        await self._persist_state()
        return Ok(None)

    async def run_stage(
        self,
        stage: ContentAddressedStage,
        inputs: dict[str, Any],
    ) -> Any:
        key = ContentCheckpointKey.compute(
            stage_id=stage.stage_id,
            tenant_id=self._tenant_id,
            inputs=inputs,
            stage_handler_version=stage.handler_version,
            config_affecting_output=stage.config_affecting_output,
        )
        cached = await self._checkpoint_store.get(key)
        if cached is not None:
            return await self._load_output(cached)

        output = await stage.handler(inputs)
        await self._persist_checkpoint(key, output, stage)
        return output

    async def _load_output(self, entry: ContentCheckpointEntry) -> Any:
        if entry.output is not None:
            return entry.output
        if entry.output_blob_ref is None:
            return None
        if self._blob_store is None:
            raise RuntimeError(
                f"Cached entry references blob '{entry.output_blob_ref}' "
                "but no blob_store is configured"
            )
        data = await self._blob_store.download(entry.output_blob_ref)
        return loads(data)

    async def _persist_checkpoint(
        self,
        key: ContentCheckpointKey,
        output: Any,
        stage: ContentAddressedStage,
    ) -> None:
        serialized = canonical_json_bytes(output)
        output_blob_ref: str | None = None
        actual_output: Any = output

        if (
            len(serialized) > self._inline_threshold_bytes
            and self._blob_store is not None
        ):
            blob_path = (
                f"checkpoints/{stage.stage_id}/"
                f"{self._tenant_id or '_global'}/"
                f"{key.input_hash.hex()}.json"
            )
            await self._blob_store.upload(
                path=blob_path,
                data=serialized,
                content_type="application/json",
            )
            output_blob_ref = blob_path
            actual_output = None

        entry = ContentCheckpointEntry(
            output=actual_output,
            output_blob_ref=output_blob_ref,
            completed_at=datetime.now(UTC),
            stage_handler_version=stage.handler_version,
            output_size_bytes=len(serialized),
        )
        await self._checkpoint_store.set(key, entry)

    # ------------------------------------------------------------------
    # Compensation
    # ------------------------------------------------------------------

    async def compensate(self) -> None:
        await self._run_compensation()

    async def _run_compensation(self) -> None:
        self.state = SagaState.COMPENSATING
        await self._persist_state()

        for stage in reversed(self._stages):
            if stage.compensation is None:
                continue
            try:
                await stage.compensation(None)
            except (RuntimeError, TypeError, ValueError, OSError):
                pass

        self.state = SagaState.FAILED
        await self._persist_state()
