"""Unit tests for all MigrationCopyStrategy implementations."""

from __future__ import annotations

import pytest

from lexigram.contracts.tenancy.migration import (
    CopyResult,
    MigrationContext,
    SnapshotResult,
)
from lexigram.tenancy.migration.copy.database_to_schema import DatabaseToSchemaCopy
from lexigram.tenancy.migration.copy.row_to_schema import RowToSchemaCopy
from lexigram.tenancy.migration.copy.schema_to_database import SchemaToDatabaseCopy
from lexigram.tenancy.migration.copy.schema_to_row import SchemaToRowCopy


_ROW_TO_SCHEMA_CTX = MigrationContext(
    source_tier="m1",
    target_tier="m5",
    source_strategy_name="row_level",
    target_strategy_name="schema",
)

_SCHEMA_TO_DB_CTX = MigrationContext(
    source_tier="m5",
    target_tier="m6",
    source_strategy_name="schema",
    target_strategy_name="database",
)

_SCHEMA_TO_ROW_CTX = MigrationContext(
    source_tier="m5",
    target_tier="m1",
    source_strategy_name="schema",
    target_strategy_name="row_level",
)

_DB_TO_SCHEMA_CTX = MigrationContext(
    source_tier="m6",
    target_tier="m5",
    source_strategy_name="database",
    target_strategy_name="schema",
)


class TestRowToSchemaCopy:
    """Suite for RowToSchemaCopy."""

    @pytest.fixture
    def strategy(self) -> RowToSchemaCopy:
        return RowToSchemaCopy()

    async def test_validate_succeeds_for_row_to_schema(
        self, strategy: RowToSchemaCopy
    ) -> None:
        await strategy.validate("tenant-abc", _ROW_TO_SCHEMA_CTX)

    async def test_validate_rejects_wrong_source(
        self, strategy: RowToSchemaCopy
    ) -> None:
        ctx = MigrationContext(
            source_tier="m5",
            target_tier="m6",
            source_strategy_name="schema",
            target_strategy_name="database",
        )
        with pytest.raises(ValueError, match="requires source 'row_level'"):
            await strategy.validate("tenant-abc", ctx)

    async def test_validate_rejects_wrong_target(
        self, strategy: RowToSchemaCopy
    ) -> None:
        ctx = MigrationContext(
            source_tier="m1",
            target_tier="m6",
            source_strategy_name="row_level",
            target_strategy_name="database",
        )
        with pytest.raises(ValueError, match="requires target 'schema'"):
            await strategy.validate("tenant-abc", ctx)

    async def test_copy_without_handler_returns_empty(
        self, strategy: RowToSchemaCopy
    ) -> None:
        result = await strategy.copy("tenant-abc", _ROW_TO_SCHEMA_CTX)
        assert isinstance(result, CopyResult)
        assert result.records_copied == 0
        assert result.records_failed == 0

    async def test_copy_with_handler(
        self, strategy: RowToSchemaCopy
    ) -> None:
        async def custom_copy(tid: str, ctx: MigrationContext) -> CopyResult:
            return CopyResult(
                records_copied=42,
                records_failed=0,
                source_snapshot=SnapshotResult(before_count=100, after_count=142),
                target_snapshot=SnapshotResult(before_count=0, after_count=42),
            )

        strategy_with_handler = RowToSchemaCopy(copy_handler=custom_copy)
        result = await strategy_with_handler.copy("tenant-abc", _ROW_TO_SCHEMA_CTX)
        assert result.records_copied == 42
        assert result.source_snapshot is not None
        assert result.source_snapshot.before_count == 100

    async def test_rollback_is_noop(
        self, strategy: RowToSchemaCopy
    ) -> None:
        result = CopyResult(records_copied=0, records_failed=0)
        await strategy.rollback("tenant-abc", result)


class TestSchemaToDatabaseCopy:
    """Suite for SchemaToDatabaseCopy."""

    @pytest.fixture
    def strategy(self) -> SchemaToDatabaseCopy:
        return SchemaToDatabaseCopy()

    async def test_validate_succeeds_for_schema_to_database(
        self, strategy: SchemaToDatabaseCopy
    ) -> None:
        await strategy.validate("tenant-abc", _SCHEMA_TO_DB_CTX)

    async def test_validate_rejects_wrong_source(
        self, strategy: SchemaToDatabaseCopy
    ) -> None:
        ctx = MigrationContext(
            source_tier="m1",
            target_tier="m5",
            source_strategy_name="row_level",
            target_strategy_name="schema",
        )
        with pytest.raises(ValueError, match="requires source 'schema'"):
            await strategy.validate("tenant-abc", ctx)

    async def test_validate_rejects_wrong_target(
        self, strategy: SchemaToDatabaseCopy
    ) -> None:
        ctx = MigrationContext(
            source_tier="m5",
            target_tier="m7",
            source_strategy_name="schema",
            target_strategy_name="schema",
        )
        with pytest.raises(ValueError, match="requires target 'database'"):
            await strategy.validate("tenant-abc", ctx)

    async def test_copy_without_handler_returns_empty(
        self, strategy: SchemaToDatabaseCopy
    ) -> None:
        result = await strategy.copy("tenant-abc", _SCHEMA_TO_DB_CTX)
        assert isinstance(result, CopyResult)
        assert result.records_copied == 0

    async def test_copy_with_handler(
        self, strategy: SchemaToDatabaseCopy
    ) -> None:
        async def custom_copy(tid: str, ctx: MigrationContext) -> CopyResult:
            return CopyResult(
                records_copied=99,
                records_failed=1,
                errors=["skipped row 5: constraint violation"],
            )

        strategy_with_handler = SchemaToDatabaseCopy(copy_handler=custom_copy)
        result = await strategy_with_handler.copy("tenant-abc", _SCHEMA_TO_DB_CTX)
        assert result.records_copied == 99
        assert len(result.errors) == 1

    async def test_rollback_is_noop(
        self, strategy: SchemaToDatabaseCopy
    ) -> None:
        result = CopyResult(records_copied=0, records_failed=0)
        await strategy.rollback("tenant-abc", result)


class TestSchemaToRowCopy:
    """Suite for SchemaToRowCopy."""

    @pytest.fixture
    def strategy(self) -> SchemaToRowCopy:
        return SchemaToRowCopy()

    async def test_validate_succeeds_for_schema_to_row(
        self, strategy: SchemaToRowCopy
    ) -> None:
        await strategy.validate("tenant-abc", _SCHEMA_TO_ROW_CTX)

    async def test_validate_rejects_wrong_source(
        self, strategy: SchemaToRowCopy
    ) -> None:
        ctx = MigrationContext(
            source_tier="m1",
            target_tier="m5",
            source_strategy_name="row_level",
            target_strategy_name="schema",
        )
        with pytest.raises(ValueError, match="requires source 'schema'"):
            await strategy.validate("tenant-abc", ctx)

    async def test_validate_rejects_wrong_target(
        self, strategy: SchemaToRowCopy
    ) -> None:
        ctx = MigrationContext(
            source_tier="m5",
            target_tier="m6",
            source_strategy_name="schema",
            target_strategy_name="database",
        )
        with pytest.raises(ValueError, match="requires target 'row_level'"):
            await strategy.validate("tenant-abc", ctx)

    async def test_copy_without_handler_returns_empty(
        self, strategy: SchemaToRowCopy
    ) -> None:
        result = await strategy.copy("tenant-abc", _SCHEMA_TO_ROW_CTX)
        assert isinstance(result, CopyResult)
        assert result.records_copied == 0

    async def test_copy_with_handler(
        self, strategy: SchemaToRowCopy
    ) -> None:
        async def custom_copy(tid: str, ctx: MigrationContext) -> CopyResult:
            return CopyResult(
                records_copied=15,
                records_failed=0,
                source_snapshot=SnapshotResult(before_count=50, after_count=35),
                target_snapshot=SnapshotResult(before_count=100, after_count=115),
            )

        strategy_with_handler = SchemaToRowCopy(copy_handler=custom_copy)
        result = await strategy_with_handler.copy("tenant-abc", _SCHEMA_TO_ROW_CTX)
        assert result.records_copied == 15
        assert result.source_snapshot is not None
        assert result.source_snapshot.after_count == 35

    async def test_rollback_is_noop(
        self, strategy: SchemaToRowCopy
    ) -> None:
        result = CopyResult(records_copied=0, records_failed=0)
        await strategy.rollback("tenant-abc", result)


class TestDatabaseToSchemaCopy:
    """Suite for DatabaseToSchemaCopy."""

    @pytest.fixture
    def strategy(self) -> DatabaseToSchemaCopy:
        return DatabaseToSchemaCopy()

    async def test_validate_succeeds_for_database_to_schema(
        self, strategy: DatabaseToSchemaCopy
    ) -> None:
        await strategy.validate("tenant-abc", _DB_TO_SCHEMA_CTX)

    async def test_validate_rejects_wrong_source(
        self, strategy: DatabaseToSchemaCopy
    ) -> None:
        ctx = MigrationContext(
            source_tier="m5",
            target_tier="m6",
            source_strategy_name="schema",
            target_strategy_name="database",
        )
        with pytest.raises(ValueError, match="requires source 'database'"):
            await strategy.validate("tenant-abc", ctx)

    async def test_validate_rejects_wrong_target(
        self, strategy: DatabaseToSchemaCopy
    ) -> None:
        ctx = MigrationContext(
            source_tier="m6",
            target_tier="m1",
            source_strategy_name="database",
            target_strategy_name="row_level",
        )
        with pytest.raises(ValueError, match="requires target 'schema'"):
            await strategy.validate("tenant-abc", ctx)

    async def test_copy_without_handler_returns_empty(
        self, strategy: DatabaseToSchemaCopy
    ) -> None:
        result = await strategy.copy("tenant-abc", _DB_TO_SCHEMA_CTX)
        assert isinstance(result, CopyResult)
        assert result.records_copied == 0

    async def test_copy_with_handler(
        self, strategy: DatabaseToSchemaCopy
    ) -> None:
        async def custom_copy(tid: str, ctx: MigrationContext) -> CopyResult:
            return CopyResult(
                records_copied=77,
                records_failed=3,
                errors=["row 42: null violation", "row 99: timeout"],
            )

        strategy_with_handler = DatabaseToSchemaCopy(copy_handler=custom_copy)
        result = await strategy_with_handler.copy("tenant-abc", _DB_TO_SCHEMA_CTX)
        assert result.records_copied == 77
        assert len(result.errors) == 2

    async def test_rollback_is_noop(
        self, strategy: DatabaseToSchemaCopy
    ) -> None:
        result = CopyResult(records_copied=0, records_failed=0)
        await strategy.rollback("tenant-abc", result)
