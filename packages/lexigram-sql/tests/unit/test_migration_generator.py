from dataclasses import dataclass
from pathlib import Path

from lexigram.validation import Field
from lexigram.domain import DomainModel

from lexigram.sql.migrations.generator import (
    MigrationGenerator,
    ModelAnalyzer,
)


def test_camel_to_snake_and_table_name():
    analyzer = ModelAnalyzer()
    assert analyzer._camel_to_snake("TestModelName") == "test_model_name"


def test_format_default_value_and_sql_type():
    analyzer = ModelAnalyzer()
    assert analyzer._format_default_value("x") == "'x'"
    assert analyzer._format_default_value(True) == "TRUE"
    assert analyzer._format_default_value(5) == "5"
    assert analyzer._format_default_value(None) == "NULL"

    assert analyzer._get_sql_type(str) == "VARCHAR"
    assert analyzer._get_sql_type(int) == "INTEGER"


def test_analyze_model_and_column_properties():
    @dataclass
    class User(DomainModel):
        id: int
        name: str = Field(
            ...,
            description="user name",
            json_schema_extra={"unique": True, "index": True},
        )

        class Meta:
            table_name = "users_table"

    analyzer = ModelAnalyzer()
    table_def = analyzer.analyze_model(User)

    assert table_def.name == "users_table"
    assert any(col.name == "id" and col.primary_key for col in table_def.columns)
    name_col = next(c for c in table_def.columns if c.name == "name")
    assert name_col.unique is True
    assert name_col.index is True
    assert name_col.comment == "user name"


def test_generate_migration_file(tmp_path: Path):
    @dataclass
    class Item(DomainModel):
        id: int
        title: str = Field(..., json_schema_extra={"index": True})

    mg = MigrationGenerator(str(tmp_path))
    path = mg.generate_migration_from_models(
        [Item], message="Create Items", revision="rev1",
    )

    assert Path(path).exists()
    content = Path(path).read_text()
    assert "op.create_table" in content
    # title column should appear in the table definition
    assert "'title'" in content

    # cleanup created file and directory
    versions_dir = tmp_path / "versions"
    for f in versions_dir.iterdir():
        f.unlink()
    versions_dir.rmdir()