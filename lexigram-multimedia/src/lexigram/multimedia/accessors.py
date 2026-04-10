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
        cache_backend: Any = None,
        event_bus: Any = None,
        media_type: str = "",
    ) -> None:
        self._backend = backend
        self._task_manager = task_manager
        self._task_name = task_name
        self._storage = storage
        self._path_prefix = path_prefix
        self._idempotency_manager = idempotency_manager
        self._cache_backend = cache_backend
        self._event_bus = event_bus
        self._media_type = media_type

    async def generate(self, request: _Req) -> Result[MediaAsset, MultimediaError]:
        from typing import cast

        if self._cache_backend is not None:
            from dataclasses import asdict
            import hashlib

            from lexigram.serialization import dumps_str

            # hash(frozenset(...)) would crash — dict values (e.g. an `extra`
            # field) aren't hashable. Canonical-JSON + sha256 mirrors the
            # approach IdempotencyManager.generate_key() already uses elsewhere
            # in the framework for the same problem.
            digest = hashlib.sha256(
                dumps_str(asdict(request), sort_keys=True, separators=(",", ":")).encode()  # type: ignore[call-overload]
            ).hexdigest()
            cache_key = f"multimedia:{self._task_name}:{digest}"
            cached = await self._cache_backend.get(cache_key)
            if cached.is_ok() and cached.unwrap() is not None:
                return cast("Result[MediaAsset, MultimediaError]", cached)
            result = await self._backend.generate(request)
            if result.is_ok():
                await self._cache_backend.set(cache_key, result.unwrap())
        else:
            result = await self._backend.generate(request)

        await self._publish_generation_event(result)
        return cast("Result[MediaAsset, MultimediaError]", result)

    async def _publish_generation_event(
        self, result: Result[MediaAsset, MultimediaError]
    ) -> None:
        if self._event_bus is None or not result.is_ok():
            return

        from lexigram.multimedia.events import MultimediaGenerationEvent

        asset = result.unwrap()
        await self._event_bus.publish(
            MultimediaGenerationEvent(
                media_type=self._media_type,
                provider=asset.provider,
                size_bytes=len(asset.bytes_data) if asset.bytes_data is not None else None,
                duration_seconds=asset.metadata.get("duration_seconds"),
            )
        )

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
