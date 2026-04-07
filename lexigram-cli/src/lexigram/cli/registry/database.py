"""Database backend registry with pluggable drivers.

This module provides a registry pattern for supporting multiple database backends.
Each backend is implemented as a separate class that handles connection, query,
and shell operations for that specific database type.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
import re
import shutil
import subprocess
from typing import TYPE_CHECKING, Any, ClassVar, Self

if TYPE_CHECKING:
    from pathlib import Path

    from lexigram.contracts.data.sql.database import DatabaseProviderProtocol


@dataclass
class QueryResult:
    """Result of a database query."""

    rows: list[dict[str, Any]]
    rowcount: int


class DatabaseBackend(abc.ABC):
    """Abstract base class for database backends."""

    name: ClassVar[str]
    aliases: ClassVar[list[str]] = []

    @abc.abstractmethod
    def parse_url(self, url: str) -> dict[str, Any]:
        """Parse a database URL into connection parameters."""

    @abc.abstractmethod
    def get_client_binary(self) -> str | None:
        """Get the path to the native client binary."""

    @abc.abstractmethod
    def build_shell_command(self, params: dict[str, Any]) -> list[str]:
        """Build the command to launch the interactive shell."""

    @abc.abstractmethod
    async def get_tables(self, provider: DatabaseProviderProtocol) -> list[str]:
        """Get list of tables in the database."""

    @abc.abstractmethod
    async def get_columns(
        self, provider: DatabaseProviderProtocol, table: str
    ) -> list[dict[str, Any]]:
        """Get column information for a table."""

    @abc.abstractmethod
    def build_backup_command(
        self,
        params: dict[str, Any],
        output_path: str,
    ) -> list[str]:
        """Build command to backup the database."""

    @abc.abstractmethod
    def build_restore_command(
        self,
        params: dict[str, Any],
        input_path: str,
    ) -> list[str]:
        """Build command to restore the database."""

    def supports_backup(self) -> bool:
        """Check if backup is supported."""
        return self.get_client_binary() is not None

    def supports_restore(self) -> bool:
        """Check if restore is supported."""
        return self.get_client_binary() is not None

    def uses_shell(self) -> bool:
        """Check if the backend requires shell=True for subprocess calls."""
        return False


class SQLiteBackend(DatabaseBackend):
    """SQLite database backend."""

    name = "sqlite"
    aliases = []

    def parse_url(self, url: str) -> dict[str, Any]:
        path = url.replace("sqlite:///", "")
        return {"backend": "sqlite", "path": path}

    def get_client_binary(self) -> str | None:
        return shutil.which("sqlite3")

    def build_shell_command(self, params: dict[str, Any]) -> list[str]:
        binary = self.get_client_binary()
        if not binary:
            raise RuntimeError("sqlite3 client not found")
        db_path = params.get("path", "dev.db")
        return [binary, db_path]

    async def get_tables(self, provider: DatabaseProviderProtocol) -> list[str]:
        result = await provider.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
        )
        return [row["name"] for row in result.rows]

    async def get_columns(
        self, provider: DatabaseProviderProtocol, table: str
    ) -> list[dict[str, Any]]:
        result = await provider.execute_query(f"PRAGMA table_info({table})")
        return [
            {
                "name": row.get("name", ""),
                "type": row.get("type", ""),
                "nullable": not row.get("notnull", False),
                "default": row.get("dflt_value"),
                "primary_key": bool(row.get("pk", 0)),
            }
            for row in result.rows
        ]

    def build_backup_command(
        self,
        params: dict[str, Any],
        output_path: str,
    ) -> list[str]:
        """Build SQLite backup command."""
        binary = self.get_client_binary()
        if not binary:
            raise RuntimeError("sqlite3 client not found")
        db_path = params.get("path", "dev.db")
        return [binary, db_path, f".output {output_path}", ".dump"]

    def build_restore_command(
        self,
        params: dict[str, Any],
        input_path: str,
    ) -> list[str]:
        """Build SQLite restore command."""
        binary = self.get_client_binary()
        if not binary:
            raise RuntimeError("sqlite3 client not found")
        db_path = params.get("path", "dev.db")
        return [binary, db_path]


class PostgreSQLBackend(DatabaseBackend):
    """PostgreSQL database backend."""

    name = "postgresql"
    aliases = ["postgres", "pg"]

    URL_PATTERN = re.compile(
        r"^(?P<backend>\w+)://(?:(?P<user>[^:@]+)(?::(?P<password>[^@]+))?@)?"
        r"(?P<host>[^:/]+)(?::(?P<port>\d+))?/(?P<database>.*)$",
    )

    def parse_url(self, url: str) -> dict[str, Any]:
        match = self.URL_PATTERN.match(url)
        if not match:
            return {"backend": "postgresql", "error": "Invalid URL format"}
        return {
            "backend": "postgresql",
            "user": match.group("user"),
            "password": match.group("password"),
            "host": match.group("host"),
            "port": match.group("port") or "5432",
            "database": match.group("database"),
        }

    def get_client_binary(self) -> str | None:
        return shutil.which("psql")

    def build_shell_command(self, params: dict[str, Any]) -> list[str]:
        binary = self.get_client_binary()
        if not binary:
            raise RuntimeError("psql client not found")

        cmd = [binary]
        if params.get("user"):
            cmd.extend(["-U", params["user"]])
        if params.get("host"):
            cmd.extend(["-h", params["host"]])
        if params.get("port"):
            cmd.extend(["-p", params["port"]])
        cmd.append(params.get("database", "postgres"))
        return cmd

    async def get_tables(self, provider: DatabaseProviderProtocol) -> list[str]:
        result = await provider.execute_query("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        return [row["table_name"] for row in result.rows]

    async def get_columns(
        self, provider: DatabaseProviderProtocol, table: str
    ) -> list[dict[str, Any]]:
        result = await provider.execute_query(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = $1
            ORDER BY ordinal_position
        """,
            [table],
        )
        return [
            {
                "name": row["column_name"],
                "type": row["data_type"],
                "nullable": row["is_nullable"] == "YES",
                "default": row["column_default"],
                "primary_key": False,
            }
            for row in result.rows
        ]

    def build_backup_command(
        self,
        params: dict[str, Any],
        output_path: str,
    ) -> list[str]:
        """Build PostgreSQL backup command."""
        binary = shutil.which("pg_dump")
        if not binary:
            raise RuntimeError("pg_dump client not found")
        cmd = ["pg_dump"]
        if params.get("user"):
            cmd.extend(["-U", params["user"]])
        if params.get("host"):
            cmd.extend(["-h", params["host"]])
        if params.get("port"):
            cmd.extend(["-p", params["port"]])
        cmd.extend(["-f", output_path, params.get("database", "postgres")])
        return cmd

    def build_restore_command(
        self,
        params: dict[str, Any],
        input_path: str,
    ) -> list[str]:
        """Build PostgreSQL restore command."""
        binary = shutil.which("psql")
        if not binary:
            raise RuntimeError("psql client not found")
        cmd = ["psql"]
        if params.get("user"):
            cmd.extend(["-U", params["user"]])
        if params.get("host"):
            cmd.extend(["-h", params["host"]])
        if params.get("port"):
            cmd.extend(["-p", params["port"]])
        cmd.extend(["-d", params.get("database", "postgres"), "-f", input_path])
        return cmd


class MySQLBackend(DatabaseBackend):
    """MySQL database backend."""

    name = "mysql"
    aliases = []

    URL_PATTERN = re.compile(
        r"^(?P<backend>\w+)://(?:(?P<user>[^:@]+)(?::(?P<password>[^@]+))?@)?"
        r"(?P<host>[^:/]+)(?::(?P<port>\d+))?/(?P<database>.*)$",
    )

    def parse_url(self, url: str) -> dict[str, Any]:
        match = self.URL_PATTERN.match(url)
        if not match:
            return {"backend": "mysql", "error": "Invalid URL format"}
        return {
            "backend": "mysql",
            "user": match.group("user"),
            "password": match.group("password"),
            "host": match.group("host"),
            "port": match.group("port") or "3306",
            "database": match.group("database"),
        }

    def get_client_binary(self) -> str | None:
        return shutil.which("mysql")

    def build_shell_command(self, params: dict[str, Any]) -> list[str]:
        binary = self.get_client_binary()
        if not binary:
            raise RuntimeError("mysql client not found")

        cmd = [binary]
        if params.get("user"):
            cmd.extend(["-u", params["user"]])
        if params.get("password"):
            cmd.extend(["-p" + params["password"]])
        if params.get("host"):
            cmd.extend(["-h", params["host"]])
        if params.get("port"):
            cmd.extend(["-P", params["port"]])
        cmd.append(params.get("database", "mysql"))
        return cmd

    async def get_tables(self, provider: DatabaseProviderProtocol) -> list[str]:
        result = await provider.execute_query("SHOW TABLES")
        if result.rows:
            key = next(iter(result.rows[0].keys()))
            return [row[key] for row in result.rows]
        return []

    async def get_columns(
        self, provider: DatabaseProviderProtocol, table: str
    ) -> list[dict[str, Any]]:
        result = await provider.execute_query(f"DESCRIBE `{table}`")
        return [
            {
                "name": row.get("Field", ""),
                "type": row.get("Type", ""),
                "nullable": row.get("Null", "") == "YES",
                "default": row.get("Default"),
                "primary_key": row.get("Key", "") == "PRI",
            }
            for row in result.rows
        ]

    def build_backup_command(
        self,
        params: dict[str, Any],
        output_path: str,
    ) -> list[str]:
        """Build MySQL backup command."""
        binary = shutil.which("mysqldump")
        if not binary:
            raise RuntimeError("mysqldump client not found")
        cmd = ["mysqldump"]
        if params.get("user"):
            cmd.extend(["-u", params["user"]])
        if params.get("password"):
            cmd.extend(["-p" + params["password"]])
        if params.get("host"):
            cmd.extend(["-h", params["host"]])
        cmd.append(params.get("database", "mysql"))
        # Redirect output to file
        cmd.extend([">", output_path])
        return cmd

    def build_restore_command(
        self,
        params: dict[str, Any],
        input_path: str,
    ) -> list[str]:
        """Build MySQL restore command."""
        binary = shutil.which("mysql")
        if not binary:
            raise RuntimeError("mysql client not found")
        cmd = ["mysql"]
        if params.get("user"):
            cmd.extend(["-u", params["user"]])
        if params.get("password"):
            cmd.extend(["-p" + params["password"]])
        if params.get("host"):
            cmd.extend(["-h", params["host"]])
        cmd.append(params.get("database", "mysql"))
        cmd.extend(["<", input_path])
        return cmd

    def uses_shell(self) -> bool:
        """MySQL uses shell=True for redirect operators."""
        return True


class DatabaseRegistry:
    """Registry for database backends.

    Provides a pluggable way to add support for new database types.
    """

    _backends: dict[str, DatabaseBackend] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, backend: type[DatabaseBackend]) -> None:
        """Register a database backend."""
        instance = backend()
        cls._backends[backend.name] = instance
        for alias in backend.aliases:
            cls._backends[alias] = instance

    @classmethod
    def get(cls, name: str) -> DatabaseBackend | None:
        """Get a backend by name."""
        cls.register_defaults()
        return cls._backends.get(name)

    @classmethod
    def get_all(cls) -> dict[str, DatabaseBackend]:
        """Get all registered backends."""
        return cls._backends.copy()

    @classmethod
    def register_defaults(cls) -> None:
        """Initialize default backends if not already done."""
        if not cls._initialized:
            cls.register(SQLiteBackend)
            cls.register(PostgreSQLBackend)
            cls.register(MySQLBackend)
            cls._initialized = True

    @classmethod
    def detect_from_url(cls, url: str) -> DatabaseBackend:
        """Detect and return the appropriate backend from a database URL."""
        cls.register_defaults()

        if url.startswith("sqlite"):
            return cls._backends["sqlite"]

        match = re.match(r"^(\w+):", url)
        if match:
            backend_name = match.group(1).lower()
            if backend_name in cls._backends:
                return cls._backends[backend_name]

        for backend in cls._backends.values():
            if backend.get_client_binary():
                return backend

        return cls._backends["sqlite"]


class DatabaseConnection:
    """Database connection manager using the registry pattern."""

    def __init__(self, url: str | None = None, config_path: Path | None = None):
        self.url = url or self._get_url_from_env_or_config(config_path)
        self.backend = DatabaseRegistry.detect_from_url(self.url)
        self.params = self.backend.parse_url(self.url)
        self._provider = None
        self._provider_async = None

    @staticmethod
    def _get_url_from_env_or_config(config_path: Path | None = None) -> str:
        import os

        db_url = os.environ.get("DATABASE_URL")
        if db_url:
            return db_url

        if config_path and config_path.exists():
            import yaml

            with open(config_path) as f:
                config = yaml.safe_load(f) or {}

            db_url = config.get("database", {}).get("url")
            if db_url:
                return db_url

        return "sqlite:///./dev.db"

    async def connect(self) -> Any:
        """Connect to the database and return a provider."""
        try:
            import importlib

            db_providers = importlib.import_module("lexigram.sql.providers")
            DatabaseService = db_providers.DatabaseService
            self._provider = DatabaseService(config=self.url)
            if self._provider is not None:
                await self._provider.boot()
            return self._provider
        except ImportError as e:
            raise RuntimeError(f"lexigram-sql not installed: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from the database."""
        if self._provider:
            await self._provider.shutdown()
            self._provider = None

    async def __aenter__(self) -> Self:
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.disconnect()

    def open_shell(self) -> None:
        """Open the native database shell."""
        cmd = self.backend.build_shell_command(self.params)
        try:
            subprocess.run(cmd, check=False)
        except OSError as e:
            raise RuntimeError(f"Failed to open shell: {e}") from e

    async def get_tables(self) -> list[str]:
        """Get list of tables."""
        if not self._provider:
            await self.connect()
        if self._provider:
            return await self.backend.get_tables(self._provider)
        return []

    async def get_columns(self, table: str) -> list[dict[str, Any]]:
        """Get columns for a table."""
        if not self._provider:
            await self.connect()
        if self._provider:
            return await self.backend.get_columns(self._provider, table)
        return []


def create_database_connection(
    url: str | None = None,
    config_path: Path | None = None,
) -> DatabaseConnection:
    """Factory function to create a database connection."""
    return DatabaseConnection(url=url, config_path=config_path)


__all__ = [
    "DatabaseBackend",
    "DatabaseConnection",
    "DatabaseRegistry",
    "MySQLBackend",
    "PostgreSQLBackend",
    "QueryResult",
    "SQLiteBackend",
    "create_database_connection",
]
