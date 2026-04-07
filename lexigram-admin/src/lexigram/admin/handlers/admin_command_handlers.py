"""Command handlers for lexigram-admin.

Handlers process commands and emit corresponding events.
They integrate with lexigram-events CommandBusProtocol.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.events import (
    BulkOperationCompleted,
    ExportCompleted,
    ExportStarted,
    ResourceCreated,
    ResourceDeleted,
    ResourceUpdated,
)
from lexigram.contracts.events import CommandHandlerProtocol as BaseCommandHandler
from lexigram.contracts.events import EventBusProtocol
from lexigram.di.decorators import inject
from lexigram.logging import get_logger
from lexigram.result import Err, Ok, Result

logger = get_logger(__name__)

if TYPE_CHECKING:
    from lexigram.admin.cqrs.commands import (
        BulkDeleteResources,
        CreateResource,
        DeleteResource,
        ExportResources,
        UpdateResource,
    )
    from lexigram.contracts.data.data_source import DataSourceProtocol


@inject
class ResourceCommandHandler(BaseCommandHandler):
    """Handler for resource CRUD commands."""

    def __init__(
        self,
        data_sources: dict[str, DataSourceProtocol],
        event_bus: EventBusProtocol | None = None,
    ):
        self.data_sources = data_sources
        self.event_bus = event_bus

    def get_data_source(self, resource_type: str) -> DataSourceProtocol:
        """Get data source for resource type."""
        if resource_type not in self.data_sources:
            raise ValueError(f"Unknown resource type: {resource_type}")
        return self.data_sources[resource_type]

    async def handle_create(self, command: CreateResource) -> Result[Any, str]:
        """Handle CreateResource command."""
        try:
            data_source = self.get_data_source(command.resource_type)

            result = await data_source.create(command.data)
            resource_id = getattr(result, "id", None)

            if self.event_bus:
                event = ResourceCreated(
                    resource_type=command.resource_type,
                    resource_id=resource_id,
                    data=command.data,
                    actor_id=command.user_id,
                    correlation_id=command.correlation_id,
                )
                await self.event_bus.publish(event)

            logger.info(
                "Created %s: %s",
                command.resource_type,
                resource_id,
            )

            return Ok(result)

        except (ValueError, ConnectionError, TimeoutError, OSError, KeyError) as e:
            logger.exception("Failed to create %s", command.resource_type)
            return Err(str(e))

    async def handle_update(self, command: UpdateResource) -> Result[Any, str]:
        """Handle UpdateResource command."""
        try:
            data_source = self.get_data_source(command.resource_type)

            old_item = await data_source.find_one(command.resource_id)
            if old_item is None:
                return Err(f"{command.resource_type} not found")

            result = await data_source.update(command.resource_id, command.data)

            changes = {}
            for key, new_val in command.data.items():
                old_val = getattr(old_item, key, None)
                if old_val != new_val:
                    changes[key] = (old_val, new_val)

            if self.event_bus and changes:
                event = ResourceUpdated(
                    resource_type=command.resource_type,
                    resource_id=command.resource_id,
                    changes=changes,
                    actor_id=command.user_id,
                    correlation_id=command.correlation_id,
                )
                await self.event_bus.publish(event)

            logger.info(
                "Updated %s: %s",
                command.resource_type,
                command.resource_id,
            )

            return Ok(result)

        except (ValueError, ConnectionError, TimeoutError, OSError, KeyError) as e:
            logger.exception("Failed to update %s", command.resource_type)
            return Err(str(e))

    async def handle_delete(self, command: DeleteResource) -> Result[Any, str]:
        """Handle DeleteResource command."""
        try:
            data_source = self.get_data_source(command.resource_type)

            success = await data_source.delete(command.resource_id)

            if not success:
                return Err(f"{command.resource_type} not found")

            if self.event_bus:
                event = ResourceDeleted(
                    resource_type=command.resource_type,
                    resource_id=command.resource_id,
                    soft_delete=command.soft_delete,
                    actor_id=command.user_id,
                    correlation_id=command.correlation_id,
                )
                await self.event_bus.publish(event)

            logger.info(
                "Deleted %s: %s",
                command.resource_type,
                command.resource_id,
            )

            return Ok(None)

        except (ValueError, ConnectionError, TimeoutError, OSError, KeyError) as e:
            logger.exception("Failed to delete %s", command.resource_type)
            return Err(str(e))

    async def handle_bulk_delete(
        self, command: BulkDeleteResources
    ) -> Result[Any, str]:
        """Handle BulkDeleteResources command."""
        try:
            data_source = self.get_data_source(command.resource_type)

            count = await data_source.bulk_delete(command.resource_ids)  # type: ignore[arg-type]

            if self.event_bus:
                event = BulkOperationCompleted(
                    operation="delete",
                    resource_type=command.resource_type,
                    resource_ids=command.resource_ids,
                    success_count=count,
                    failure_count=len(command.resource_ids) - count,
                    actor_id=command.user_id,
                    correlation_id=command.correlation_id,
                )
                await self.event_bus.publish(event)

            logger.info(
                "Bulk deleted %d %s",
                count,
                command.resource_type,
            )

            return Ok({"deleted": count})

        except (ValueError, ConnectionError, TimeoutError, OSError, KeyError) as e:
            logger.exception("Failed to bulk delete %s", command.resource_type)
            return Err(str(e))


@inject
class ExportCommandHandler(BaseCommandHandler):
    """Handler for export commands."""

    def __init__(
        self,
        data_sources: dict[str, DataSourceProtocol],
        event_bus: EventBusProtocol | None = None,
        export_dir: str | None = None,
    ):
        self.data_sources = data_sources
        self.event_bus = event_bus
        if export_dir:
            self.export_dir = export_dir
        else:
            from pathlib import Path
            import tempfile

            temp_dir = Path(tempfile.gettempdir()) / "lexigram_exports"
            temp_dir.mkdir(parents=True, exist_ok=True)
            self.export_dir = str(temp_dir)

    async def handle_export(self, command: ExportResources) -> Result[Any, str]:
        """Handle ExportResources command."""
        import csv
        from pathlib import Path
        from uuid import uuid4

        from lexigram import serialization as json

        export_id = str(uuid4())

        try:
            if command.resource_type not in self.data_sources:
                return Err(
                    f"Unknown resource type: {command.resource_type}",
                )

            data_source = self.data_sources[command.resource_type]

            from lexigram.admin.data.query import QuerySpec

            qs = QuerySpec()
            for field, value in command.query.items():
                qs = qs.with_where_eq(field, value)
            if self.event_bus:
                await self.event_bus.publish(
                    ExportStarted(
                        export_id=export_id,
                        resource_type=command.resource_type,
                        format=command.format,
                        actor_id=command.user_id,
                    ),
                )

            result = await data_source.find_many(qs)  # type: ignore[arg-type]

            import aiofiles

            export_path = Path(self.export_dir) / f"{export_id}.{command.format}"
            export_path.parent.mkdir(parents=True, exist_ok=True)

            if command.format == "json":
                items = [
                    {k: v for k, v in vars(item).items() if not k.startswith("_")}
                    for item in result.items  # type: ignore[attr-defined]
                ]
                import asyncio

                content = await asyncio.to_thread(
                    json.dumps_str,
                    items,
                    default=str,
                    indent=2,
                )
                async with aiofiles.open(export_path, "w") as f:
                    await f.write(content)

            elif command.format == "csv":
                import io

                output = io.StringIO()
                if result.items:  # type: ignore[attr-defined]
                    first_item = result.items[0]  # type: ignore[attr-defined]
                    fieldnames = command.columns or [
                        k for k in vars(first_item) if not k.startswith("_")
                    ]
                    writer = csv.DictWriter(output, fieldnames=fieldnames)
                    writer.writeheader()
                    for item in result.items:  # type: ignore[attr-defined]
                        row = {k: getattr(item, k, "") for k in fieldnames}
                        writer.writerow(row)

                async with aiofiles.open(export_path, "w") as f:
                    await f.write(output.getvalue())

            file_size = export_path.stat().st_size

            total_records = (
                result.total
                if hasattr(result, "total")
                else len(result.items)
                if hasattr(result, "items")
                else 0
            )

            if self.event_bus:
                await self.event_bus.publish(
                    ExportCompleted(
                        export_id=export_id,
                        resource_type=command.resource_type,
                        format=command.format,
                        total_records=total_records,
                        file_path=str(export_path),
                        file_size=file_size,
                        actor_id=command.user_id,
                    ),
                )

            logger.info(
                "Exported %d %s to %s",
                total_records,
                command.resource_type,
                export_path,
            )

            return Ok(
                {
                    "export_id": export_id,
                    "file_path": str(export_path),
                    "total_records": total_records,
                },
            )

        except (ValueError, ConnectionError, TimeoutError, OSError) as e:
            logger.exception("Export failed")
            return Err(str(e))
