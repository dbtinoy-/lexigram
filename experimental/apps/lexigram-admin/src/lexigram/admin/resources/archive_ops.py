"""Archive lifecycle operations for Admin Resources.

Clone/duplicate, soft-delete restore, and hard purge flows with their
``before_*`` / ``after_*`` extension hooks. Composed into
:class:`~lexigram.admin.resources.base.Resource` via inheritance so the
methods remain part of every resource's public surface:

    class MyResource(ArchiveOperationsMixin): ...

Subclasses override the hook pairs to customise behaviour; the orchestrators
(``duplicate`` / ``restore`` / ``purge``) handle data-source plumbing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.admin.data.data_source import IDataSource


class ArchiveOperationsMixin:
    """Clone / restore / purge operations plus their lifecycle hooks.

    Requires the composing class to provide an attached ``_data_source``
    (set by :class:`~lexigram.admin.resources.base.Resource.__init__`).
    """

    _data_source: IDataSource | None

    async def before_clone(self, data: dict) -> dict:
        """Hook called before a record is cloned.

        Strips the ``id`` field (so a new ID is assigned) and
        appends `` (Copy)`` to the ``name`` field.  Override
        to customise clone behaviour.

        Args:
            data: Record data dict fetched from the data source.

        Returns:
            Modified data dict to be passed to ``create``.
        """
        data.pop("id", None)
        if "name" in data:
            data["name"] = f"{data['name']} (Copy)"
        return data

    async def after_clone(self, record: Any) -> None:
        """Hook called after a record has been cloned.

        Args:
            record: The newly created record returned by the data source.
        """

    async def duplicate(self, item_id: Any) -> Any:
        """Duplicate (clone) a record by its identifier.

        Fetches the existing record via the attached data source,
        calls :meth:`before_clone` to prepare the data, creates
        a new record, and calls :meth:`after_clone` with the result.

        Args:
            item_id: Identifier of the record to clone.

        Returns:
            The newly created record.

        Raises:
            RuntimeError: If no data source is attached.
        """
        from lexigram.admin.resources.data_access import get_resource_data_source

        data_source = get_resource_data_source(self)
        if data_source is None:
            raise RuntimeError("No data source attached to this resource")

        original = await data_source.find_one(item_id)
        if original is None:
            raise LookupError(f"Record {item_id} not found")
        data: dict = dict(original) if isinstance(original, dict) else {}
        if not data and hasattr(original, "__dict__"):
            data = dict(original.__dict__)
        data = await self.before_clone(data)
        new_record = await data_source.create(data)
        await self.after_clone(new_record)
        return new_record

    async def before_restore(self, data: dict) -> dict:
        """Hook called before a soft-deleted record is restored.

        Sets ``deleted_at`` to ``None`` by default.  Override to
        customise restore behaviour.

        Args:
            data: Record data dict fetched from the data source.

        Returns:
            Modified data dict to be passed to ``update``.
        """
        return {"deleted_at": None}

    async def after_restore(self, record: Any) -> None:
        """Hook called after a record has been restored.

        Args:
            record: The restored record returned by the data source.
        """

    async def restore(self, item_id: Any) -> Any:
        """Restore a soft-deleted record.

        Fetches the existing record, calls :meth:`before_restore` to
        prepare the data, updates the record via the data source, and
        calls :meth:`after_restore` with the result.

        Args:
            item_id: Identifier of the record to restore.

        Returns:
            The restored record.

        Raises:
            RuntimeError: If no data source is attached.
        """
        from lexigram.admin.resources.data_access import get_resource_data_source

        data_source = get_resource_data_source(self)
        if data_source is None:
            raise RuntimeError("No data source attached to this resource")

        original = await data_source.find_one(item_id)
        if original is None:
            raise LookupError(f"Record {item_id} not found")
        data: dict = dict(original) if isinstance(original, dict) else {}
        if not data and hasattr(original, "__dict__"):
            data = dict(original.__dict__)
        data = await self.before_restore(data)
        new_record = await data_source.update(item_id, data)
        if new_record is None:
            raise LookupError(f"Record {item_id} not found")
        await self.after_restore(new_record)
        return new_record

    async def before_purge(self, data: dict) -> dict:
        """Hook called before a record is permanently purged.

        Args:
            data: Record data dict fetched from the data source.

        Returns:
            Modified data dict (default: unchanged).
        """
        return data

    async def after_purge(self, item_id: Any) -> None:
        """Hook called after a record has been permanently purged.

        Args:
            item_id: Identifier of the purged record.
        """

    async def purge(self, item_id: Any) -> None:
        """Permanently delete (purge) a record.

        Fetches the existing record, calls :meth:`before_purge` to
        prepare the data, hard-deletes via the data source, and calls
        :meth:`after_purge` with the item id.

        Args:
            item_id: Identifier of the record to purge.

        Raises:
            RuntimeError: If no data source is attached.
        """
        from lexigram.admin.resources.data_access import get_resource_data_source

        data_source = get_resource_data_source(self)
        if data_source is None:
            raise RuntimeError("No data source attached to this resource")

        original = await data_source.find_one(item_id)
        if original is None:
            raise LookupError(f"Record {item_id} not found")
        data: dict = dict(original) if isinstance(original, dict) else {}
        if not data and hasattr(original, "__dict__"):
            data = dict(original.__dict__)
        await self.before_purge(data)
        deleted = await data_source.delete(item_id)
        if not deleted:
            raise LookupError(f"Record {item_id} not found")
        await self.after_purge(item_id)


__all__ = ["ArchiveOperationsMixin"]
