"""Per-subsystem accessor exposing .generate() (sync) and .submit() (queued)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

if TYPE_CHECKING:
    from lexigram.contracts.core.result import Result
    from lexigram.contracts.multimedia.exceptions import MultimediaError
    from lexigram.contracts.multimedia.types import MediaAsset
    from lexigram.multimedia.jobs import JobHandle

_Req = TypeVar("_Req")


class SubsystemAccessor(Generic[_Req]):
    """Wraps one sub-provider's backend + task manager + storage normalizer."""

    def __init__(
        self,
        *,
        backend: Any,
        task_manager: Any,
        task_name: str,
        storage: Any,
        path_prefix: str,
        idempotency_manager: Any = None,
    ) -> None:
        self._backend = backend
        self._task_manager = task_manager
        self._task_name = task_name
        self._storage = storage
        self._path_prefix = path_prefix
        self._idempotency_manager = idempotency_manager

    async def generate(self, request: _Req) -> Result[MediaAsset, MultimediaError]:
        from typing import cast

        from lexigram.contracts.core.result import Result
        from lexigram.contracts.multimedia.exceptions import MultimediaError

        result = await self._backend.generate(request)
        return cast(Result[MediaAsset, MultimediaError], result)

    async def submit(self, request: _Req, idempotency_key: str | None = None) -> JobHandle:
        from dataclasses import asdict

        from lexigram.multimedia.jobs import JobHandle

        params = asdict(request)  # type: ignore[call-overload]

        # IdempotentTaskManager.submit_task()'s return value alone can't
        # tell us whether this was a fresh submission or a duplicate of a
        # still-in-flight one (both come back with status="submitted") — see
        # JobHandle.from_idempotency_result. We own the IdempotencyManager
        # instance (constructed in MultimediaProvider._wire_task_manager()),
        # so pre-check directly for an accurate signal. This opens a narrow
        # race window against submit_task()'s own internal per-key lock, but
        # that only affects the informational is_duplicate flag — task
        # submission itself stays correctly deduplicated either way.
        is_duplicate = False
        if self._idempotency_manager is not None:
            key = self._idempotency_manager.generate_key(
                self._task_name, params, idempotency_key
            )
            is_duplicate = await self._idempotency_manager.check_duplicate(key) is not None

        result = await self._task_manager.submit_task(
            self._task_name, params, idempotency_key=idempotency_key
        )
        return JobHandle.from_idempotency_result(result, is_duplicate=is_duplicate)


__all__ = ["SubsystemAccessor"]
