"""Database backup and restore utilities for Lexigram Framework"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime
import gzip
from pathlib import Path
import re
from typing import Any

from lexigram.contracts import ConnectionPoolProtocol
from lexigram.contracts.data.identifiers import Column, Table
from lexigram.logging import get_logger
from lexigram.primitives import clock as ambient_clock
from lexigram.serialization import JSONDecodeError, dumps_str, loads
from lexigram.sql.abstractions.connection import DatabaseConnection

logger = get_logger(__name__)


def _validate_table_name(table_name: str) -> None:
    """Validate table name matches strict SQL identifier pattern.

    Table names used in f-string interpolation must be explicitly validated
    before use, even though they may come from a Table() object that already
    validates them. This ensures no SQL injection through identifier position.

    Args:
        table_name: The table name to validate.

    Raises:
        ValueError: If the table name doesn't match [a-zA-Z_][a-zA-Z0-9_]*
    """
    pattern = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    if not pattern.match(table_name):
        msg = (
            f"Invalid table name: {table_name!r}. "
            "Table names must match pattern [a-zA-Z_][a-zA-Z0-9_]*"
        )
        raise ValueError(msg)


@dataclass
class BackupMetadata:
    """Metadata for a database backup"""

    database_type: str
    tables: list[str]
    record_counts: dict[str, int]
    created_at: datetime
    version: str = "1.0"
    compressed: bool = False
    checksum: str | None = None


@dataclass
class TableData:
    """Data for a single table"""

    name: str
    columns: list[str]
    rows: list[list[Any]]
    primary_key: str | None = None


class BackupStrategy(ABC):
    """Abstract base class for backup strategies"""

    @abstractmethod
    async def backup_table(
        self,
        conn: DatabaseConnection,
        table_name: str,
        batch_size: int = 1000,
    ) -> TableData:
        """Backup a single table"""
        ...

    @abstractmethod
    async def get_table_list(self, conn: DatabaseConnection) -> list[str]:
        """Get list of tables to backup"""
        ...

    @abstractmethod
    async def get_table_info(
        self,
        conn: DatabaseConnection,
        table_name: str,
    ) -> dict[str, Any]:
        """Get table metadata"""


class SQLBackupStrategy(BackupStrategy):
    """Backup strategy for SQL databases"""

    async def backup_table(
        self,
        conn: DatabaseConnection,
        table_name: str,
        batch_size: int = 1000,
    ) -> TableData:
        """Backup a single table"""
        _validate_table_name(table_name)
        table = Table(table_name)
        # Get column information
        columns_query = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = ? AND table_schema = DATABASE()
        ORDER BY ordinal_position
        """
        columns_result = await conn.fetch_all(columns_query, (table_name,))
        columns = [row["column_name"] for row in columns_result]

        # Get primary key
        pk_query = """
        SELECT column_name
        FROM information_schema.key_column_usage
        WHERE table_name = ? AND constraint_name = 'PRIMARY'
        """
        pk_result = await conn.fetch_one(pk_query, (table_name,))
        primary_key = pk_result["column_name"] if pk_result else None

        # Get all data
        select_query = f"SELECT * FROM {table}"  # noqa: S608 -- table passes _validate_table_name() and is a Table() quoted identifier
        rows = await conn.fetch_all(select_query)

        # Convert rows to lists
        row_data = []
        for row in rows:
            try:
                # Prefer mapping access by column order
                row_data.append([row[col] for col in columns])
            except (KeyError, TypeError, IndexError):
                # Fallback for sequence-like rows
                row_data.append(list(row))

        return TableData(
            name=table_name,
            columns=columns,
            rows=row_data,
            primary_key=primary_key,
        )

    async def get_table_list(self, conn: DatabaseConnection) -> list[str]:
        """Get list of user tables"""
        query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'
        AND table_name NOT IN ('schema_migrations', 'migrations')
        """
        result = await conn.fetch_all(query)
        table_names = []
        for row in result:
            table_names.append(row["table_name"])
        return table_names

    async def get_table_info(
        self,
        conn: DatabaseConnection,
        table_name: str,
    ) -> dict[str, Any]:
        """Get table metadata"""
        _validate_table_name(table_name)
        table = Table(table_name)
        count_query = f"SELECT COUNT(*) as count FROM {table}"  # noqa: S608 -- table passes _validate_table_name() and is a Table() quoted identifier
        result = await conn.fetch_one(count_query)
        return {
            "record_count": result["count"] if result else 0,
            "table_name": table_name,
        }


class BackupManager:
    """Manages database backups and restores"""

    def __init__(
        self,
        connection_pool: ConnectionPoolProtocol,
        strategy: BackupStrategy | None = None,
    ):
        self.connection_pool = connection_pool
        self.strategy = strategy or SQLBackupStrategy()

    @property
    def _clock_now(self) -> datetime:
        """Return current UTC time using ambient clock."""
        return ambient_clock.now()

    async def create_backup(
        self,
        output_path: Path,
        tables: list[str] | None = None,
        compress: bool = True,
    ) -> BackupMetadata:
        """Create a database backup"""
        async with self.connection_pool.get_connection() as conn:
            # Get tables to backup
            if tables is None:
                tables = await self.strategy.get_table_list(conn)

            # Backup each table
            table_data = []
            record_counts = {}

            for table_name in tables:
                logger.info("Backing up table: %s", table_name)
                table_info = await self.strategy.get_table_info(conn, table_name)
                record_counts[table_name] = table_info["record_count"]

                if record_counts[table_name] > 0:
                    data = await self.strategy.backup_table(conn, table_name)
                    table_data.append(data)

            # Create metadata
            metadata = BackupMetadata(
                database_type="sql",
                tables=tables,
                record_counts=record_counts,
                created_at=self._clock_now,
                compressed=compress,
            )

            # Write backup
            backup_data = {
                "metadata": {
                    "database_type": metadata.database_type,
                    "tables": metadata.tables,
                    "record_counts": metadata.record_counts,
                    "created_at": metadata.created_at.isoformat(),
                    "version": metadata.version,
                    "compressed": metadata.compressed,
                },
                "tables": [
                    {
                        "name": table.name,
                        "columns": table.columns,
                        "rows": table.rows,
                        "primary_key": table.primary_key,
                    }
                    for table in table_data
                ],
            }

            # Write to file
            if compress:
                output_path = output_path.with_suffix(".json.gz")
                with gzip.open(output_path, "wt", encoding="utf-8") as f:
                    f.write(dumps_str(backup_data, indent=2, default=str))
            else:
                output_path = output_path.with_suffix(".json")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(dumps_str(backup_data, indent=2, default=str))

            return metadata

    async def restore_backup(
        self,
        backup_path: Path,
        tables: list[str] | None = None,
    ) -> None:
        """Restore from a database backup"""
        # Read backup file
        if backup_path.suffix == ".gz":
            with gzip.open(backup_path, "rt", encoding="utf-8") as f:
                backup_data = loads(f.read())
        else:
            with open(backup_path, encoding="utf-8") as f:
                backup_data = loads(f.read())

        tables_data = backup_data["tables"]

        async with self.connection_pool.get_connection() as conn:
            # Filter tables if specified
            if tables:
                tables_data = list(filter(lambda t: t["name"] in tables, tables_data))

            for table_data in tables_data:
                await self._restore_table(conn, table_data)

    async def _restore_table(
        self,
        conn: DatabaseConnection,
        table_data: dict[str, Any],
    ) -> None:
        """Restore a single table"""
        table_name = table_data["name"]
        _validate_table_name(table_name)
        table = Table(table_name)
        columns = table_data["columns"]
        rows = table_data["rows"]

        logger.info("Restoring table: %s (%d records)", table_name, len(rows))

        if not rows:
            return

        # Clear existing data
        await conn.execute(f"DELETE FROM {table}")  # noqa: S608 -- table passes _validate_table_name() and is a Table() quoted identifier

        # Insert data in batches
        batch_size = 1000
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]

            # Create placeholders
            # Validate column names from backup data before SQL interpolation
            safe_columns = [str(Column(c)) for c in columns]
            placeholders = ", ".join(["?"] * len(columns))
            query = f"INSERT INTO {table} ({', '.join(safe_columns)}) VALUES ({placeholders})"  # noqa: S608 -- table _validate_table_name()-checked; safe_columns are Column() quoted identifiers

            # Execute batch
            await conn.execute_many(query, batch)

    async def list_backups(self, backup_dir: Path) -> list[dict[str, Any]]:
        """List available backups"""
        backups = []

        for backup_file in backup_dir.glob("*.json*"):
            try:
                # Read metadata
                if backup_file.suffix == ".gz":
                    with gzip.open(backup_file, "rt", encoding="utf-8") as f:
                        data = loads(f.read())
                else:
                    with open(backup_file, encoding="utf-8") as f:
                        data = loads(f.read())

                metadata = data["metadata"]
                backups.append(
                    {
                        "filename": backup_file.name,
                        "path": str(backup_file),
                        "created_at": metadata["created_at"],
                        "tables": metadata["tables"],
                        "total_records": sum(metadata["record_counts"].values()),
                        "compressed": metadata.get("compressed", False),
                    },
                )

            except (OSError, JSONDecodeError, KeyError, ValueError):
                logger.exception("Error reading backup %s", backup_file)

        # Sort by creation date
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        return backups

    async def validate_backup(self, backup_path: Path) -> dict[str, Any]:
        """Validate a backup file"""
        try:
            # Read backup file
            if backup_path.suffix == ".gz":
                with gzip.open(backup_path, "rt", encoding="utf-8") as f:
                    backup_data = loads(f.read())
            else:
                with open(backup_path, encoding="utf-8") as f:
                    backup_data = loads(f.read())

            # Validate structure
            issues = []

            if "metadata" not in backup_data:
                issues.append("Missing metadata section")

            if "tables" not in backup_data:
                issues.append("Missing tables section")

            # Only proceed if basic structure is present
            if "metadata" in backup_data and "tables" in backup_data:
                metadata = backup_data["metadata"]
                tables_data = backup_data["tables"]

                # Validate each table
                for table in tables_data:
                    if "name" not in table:
                        issues.append(f"Table missing name: {table}")
                    if "columns" not in table:
                        issues.append(
                            f"Table {table.get('name', 'unknown')} missing columns",
                        )
                    if "rows" not in table:
                        issues.append(
                            f"Table {table.get('name', 'unknown')} missing rows",
                        )

                total_records = sum(len(table["rows"]) for table in tables_data)
                metadata_out = metadata
                table_count = len(tables_data)
            else:
                metadata_out = backup_data.get("metadata")
                table_count = 0
                total_records = 0

            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "table_count": table_count,
                "total_records": total_records,
                "metadata": metadata_out,
            }

        except (OSError, JSONDecodeError, KeyError, ValueError) as e:
            return {
                "valid": False,
                "issues": [f"Error reading backup: {e!s}"],
                "table_count": 0,
                "total_records": 0,
                "metadata": None,
            }

    async def backup_table_streaming(
        self,
        table_name: str,
        batch_size: int = 1000,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        """Stream table rows in batches to avoid loading all data into memory.

        Unlike :meth:`create_backup`, which reads every row of a table into a
        single list before writing, this method yields successive batches of
        rows using LIMIT/OFFSET so that memory usage is bounded by ``batch_size``
        regardless of the total row count.

        Args:
            table_name: The table to stream.
            batch_size: Number of rows to fetch per batch.  Defaults to 1000.

        Yields:
            Each batch as a list of row dicts (column → value).

        Example::

            async for batch in manager.backup_table_streaming("users", batch_size=500):
                for row in batch:
                    writer.write_row(row)
        """
        _validate_table_name(table_name)
        table = Table(table_name)
        offset = 0
        async with self.connection_pool.get_connection() as conn:
            while True:
                rows = await conn.fetch_all(
                    f"SELECT * FROM {table} LIMIT {batch_size} OFFSET {offset}",  # noqa: S608 -- table _validate_table_name()-checked; batch_size/offset are ints
                )
                if not rows:
                    break
                yield [dict(row) for row in rows]
                if len(rows) < batch_size:
                    # Last partial batch — no more rows remain
                    break
                offset += batch_size


class DatabaseMaintenance:
    """Database maintenance utilities"""

    def __init__(self, connection_pool: ConnectionPoolProtocol):
        self.connection_pool = connection_pool

    async def vacuum(self, table_name: str | None = None) -> None:
        """Reclaim storage and update statistics"""
        async with self.connection_pool.get_connection() as conn:
            if table_name:
                _validate_table_name(table_name)
                safe_table = Table(table_name)  # validates identifier
                await conn.execute(f"VACUUM {safe_table}")
            else:
                await conn.execute("VACUUM")

    async def analyze(self, table_name: str | None = None) -> None:
        """Update table statistics for query optimization"""
        async with self.connection_pool.get_connection() as conn:
            if table_name:
                _validate_table_name(table_name)
                safe_table = Table(table_name)  # validates identifier
                await conn.execute(f"ANALYZE TABLE {safe_table}")
            else:
                await conn.execute("ANALYZE TABLE")

    async def get_table_sizes(self) -> dict[str, dict[str, Any]]:
        """Get size information for all tables"""
        async with self.connection_pool.get_connection() as conn:
            query = """
            SELECT
                table_name,
                data_length,
                index_length,
                data_length + index_length as total_size
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            ORDER BY total_size DESC
            """
            results = await conn.fetch_all(query)

            sizes = {}
            for row in results:
                sizes[row["table_name"]] = {
                    "data_size": row["data_length"],
                    "index_size": row["index_length"],
                    "total_size": row["total_size"],
                }

            return sizes

    async def get_database_stats(self) -> dict[str, Any]:
        """Get comprehensive database statistics"""
        async with self.connection_pool.get_connection() as conn:
            # Table count
            table_query = "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_schema = DATABASE()"
            table_result = await conn.fetch_one(table_query)

            # Total records
            record_query = """
            SELECT SUM(table_rows) as total_records
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            """
            record_result = await conn.fetch_one(record_query)

            # Database size
            size_query = """
            SELECT
                SUM(data_length + index_length) as total_size,
                SUM(data_length) as data_size,
                SUM(index_length) as index_size
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
            """
            size_result = await conn.fetch_one(size_query)

            return {
                "table_count": table_result["count"] if table_result else 0,
                "total_records": record_result["total_records"] if record_result else 0,
                "database_size": {
                    "total": size_result["total_size"] if size_result else 0,
                    "data": size_result["data_size"] if size_result else 0,
                    "index": size_result["index_size"] if size_result else 0,
                },
            }
