from dataclasses import dataclass
"""Unit tests for migration generator components"""

from datetime import datetime
from pathlib import Path
import tempfile

import pytest

from lexigram.domain import DomainModel
from lexigram.validation import Field

from lexigram.sql.migrations.generator import (
    ColumnDefinition,
    MigrationError,
    MigrationGenerator,
    ModelAnalyzer,
    SchemaDiff,
    TableDefinition,
)


class TestColumnDefinition:
    """Test ColumnDefinition dataclass"""

    def test_column_definition_creation(self):
        """Test creating a column definition"""
        col = ColumnDefinition(
            name="id",
            type_sql="INTEGER",
            nullable=False,
            primary_key=True,
            unique=True,
            index=True,
            foreign_key="users.id",
            comment="Primary key",
        )

        assert col.name == "id"
        assert col.type_sql == "INTEGER"
        assert col.nullable is False
        assert col.primary_key is True
        assert col.unique is True
        assert col.index is True
        assert col.foreign_key == "users.id"
        assert col.comment == "Primary key"
        assert col.default is None

    def test_column_definition_defaults(self):
        """Test column definition default values"""
        col = ColumnDefinition(name="name", type_sql="VARCHAR")

        assert col.name == "name"
        assert col.type_sql == "VARCHAR"
        assert col.nullable is True
        assert col.primary_key is False
        assert col.unique is False
        assert col.index is False
        assert col.foreign_key is None
        assert col.comment is None
        assert col.default is None


class TestTableDefinition:
    """Test TableDefinition dataclass"""

    def test_table_definition_creation(self):
        """Test creating a table definition"""
        columns = [
            ColumnDefinition(name="id", type_sql="INTEGER", primary_key=True),
            ColumnDefinition(name="name", type_sql="VARCHAR"),
        ]

        table = TableDefinition(
            name="users",
            columns=columns,
            indexes=[{"name": "ix_users_name", "columns": ["name"]}],
            constraints=[
                {
                    "name": "ck_name_length",
                    "type": "check",
                    "expression": "length(name) > 0",
                },
            ],
        )

        assert table.name == "users"
        assert len(table.columns) == 2
        assert len(table.indexes) == 1
        assert len(table.constraints) == 1

    def test_table_definition_post_init_defaults(self):
        """Test table definition post init sets defaults"""
        table = TableDefinition(name="users", columns=[])

        assert table.indexes == []
        assert table.constraints == []


class TestSchemaDiff:
    """Test SchemaDiff dataclass"""

    def test_schema_diff_creation(self):
        """Test creating a schema diff"""
        diff = SchemaDiff(
            tables_to_create=[TableDefinition(name="users", columns=[])],
            tables_to_drop=["old_table"],
            columns_to_add={
                "users": [ColumnDefinition(name="email", type_sql="VARCHAR")],
            },
            columns_to_drop={"users": ["old_column"]},
            columns_to_modify={"users": [{"name": "name", "type_sql": "VARCHAR(255)"}]},
            indexes_to_add={
                "users": [{"name": "ix_users_email", "columns": ["email"]}],
            },
            indexes_to_drop={"users": ["ix_users_old"]},
            constraints_to_add={
                "users": [{"name": "ck_email_format", "type": "check"}],
            },
            constraints_to_drop={"users": ["ck_old_constraint"]},
        )

        assert len(diff.tables_to_create) == 1
        assert diff.tables_to_drop == ["old_table"]
        assert "users" in diff.columns_to_add
        assert "users" in diff.columns_to_drop
        assert "users" in diff.columns_to_modify
        assert "users" in diff.indexes_to_add
        assert "users" in diff.indexes_to_drop
        assert "users" in diff.constraints_to_add
        assert "users" in diff.constraints_to_drop


class TestModelAnalyzer:
    """Test ModelAnalyzer functionality"""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance"""
        return ModelAnalyzer()

    def test_analyzer_creation(self, analyzer):
        """Test analyzer can be created"""
        assert isinstance(analyzer, ModelAnalyzer)
        assert analyzer.TYPE_MAPPING[str] == "VARCHAR"
        assert analyzer.TYPE_MAPPING[int] == "INTEGER"
        assert analyzer.TYPE_MAPPING[bool] == "BOOLEAN"

    def test_analyze_model_basic(self, analyzer):
        """Test analyzing a basic DomainModel."""

        @dataclass
        class User(DomainModel):
            id: int
            name: str
            email: str | None = None
            active: bool = True

        table_def = analyzer.analyze_model(User)

        assert table_def.name == "user"  # snake_case conversion
        assert len(table_def.columns) == 4

        # Check id column
        id_col = next(col for col in table_def.columns if col.name == "id")
        assert id_col.type_sql == "INTEGER"
        assert id_col.primary_key is True  # id field is auto primary key
        assert id_col.nullable is False

        # Check name column
        name_col = next(col for col in table_def.columns if col.name == "name")
        assert name_col.type_sql == "VARCHAR"
        assert name_col.nullable is False

        # Check email column (optional)
        email_col = next(col for col in table_def.columns if col.name == "email")
        assert email_col.type_sql == "VARCHAR"
        assert email_col.nullable is True

        # Check active column
        active_col = next(col for col in table_def.columns if col.name == "active")
        assert active_col.type_sql == "BOOLEAN"
        assert active_col.nullable is False
        assert active_col.default == "TRUE"

    def test_analyze_model_with_meta_table_name(self, analyzer):
        """Test analyzing model with custom table name in Meta"""

        @dataclass
        class CustomUser(DomainModel):
            id: int
            name: str

            class Meta:
                table_name = "custom_users"

        table_def = analyzer.analyze_model(CustomUser)
        assert table_def.name == "custom_users"

    def test_analyze_model_with_constraints(self, analyzer):
        """Test analyzing model with field constraints"""

        @dataclass
        class User(DomainModel):
            id: int = Field(json_schema_extra={"primary_key": True})
            email: str = Field(json_schema_extra={"unique": True, "index": True})
            name: str = Field(description="User's full name")

        table_def = analyzer.analyze_model(User)

        id_col = next(col for col in table_def.columns if col.name == "id")
        assert id_col.primary_key is True

        email_col = next(col for col in table_def.columns if col.name == "email")
        assert email_col.unique is True
        assert email_col.index is True

        name_col = next(col for col in table_def.columns if col.name == "name")
        assert name_col.comment == "User's full name"

    def test_analyze_model_foreign_key(self, analyzer):
        """Test analyzing model with foreign key"""

        @dataclass
        class Post(DomainModel):
            id: int
            user_id: int = Field(json_schema_extra={"foreign_key": "users.id"})
            title: str

        table_def = analyzer.analyze_model(Post)

        user_id_col = next(col for col in table_def.columns if col.name == "user_id")
        assert user_id_col.foreign_key == "users.id"

    def test_analyze_model_list_relationship(self, analyzer):
        """Test analyzing model with list relationship"""

        @dataclass
        class Comment(DomainModel):
            id: int
            post_id: int
            content: str

        @dataclass
        class Post(DomainModel):
            id: int
            title: str
            comments: list[Comment]  # This should be handled as relationship

        table_def = analyzer.analyze_model(Post)

        # comments field should be treated as array or ignored for now
        # (full relationship handling would be more complex)
        comments_col = next(
            (col for col in table_def.columns if col.name == "comments"), None,
        )
        if comments_col:
            # Depending on implementation, might be INTEGER[] or ignored
            pass

    def test_analyze_non_domain_model(self, analyzer):
        """Test analyzing non-DomainModel class raises error."""

        class NotADomainModel:
            id: int
            name: str

        with pytest.raises(MigrationError, match="must inherit from DomainModel"):
            analyzer.analyze_model(NotADomainModel)

    def test_camel_to_snake_conversion(self, analyzer):
        """Test camelCase to snake_case conversion"""

        @dataclass
        class UserProfile(DomainModel):
            userId: int
            fullName: str
            isActive: bool

        table_def = analyzer.analyze_model(UserProfile)
        assert table_def.name == "user_profile"

        column_names = list(map(lambda col: col.name, table_def.columns))
        assert "user_id" in column_names
        assert "full_name" in column_names
        assert "is_active" in column_names

    def test_type_mapping(self, analyzer):
        """Test type mapping functionality"""

        # Test direct mappings
        assert analyzer._get_sql_type(str) == "VARCHAR"
        assert analyzer._get_sql_type(int) == "INTEGER"
        assert analyzer._get_sql_type(float) == "FLOAT"
        assert analyzer._get_sql_type(bool) == "BOOLEAN"
        assert analyzer._get_sql_type(datetime) == "TIMESTAMP"
        assert analyzer._get_sql_type(bytes) == "BYTEA"

        # Test string forward reference
        assert analyzer._get_sql_type("SomeClass") == "VARCHAR"

        # Test unknown type defaults to VARCHAR
        class UnknownType:
            pass

        assert analyzer._get_sql_type(UnknownType) == "VARCHAR"

    def test_format_default_value(self, analyzer):
        """Test default value formatting"""

        assert analyzer._format_default_value("test") == "'test'"
        assert analyzer._format_default_value(42) == "42"
        assert analyzer._format_default_value(3.14) == "3.14"
        assert analyzer._format_default_value(True) == "TRUE"
        assert analyzer._format_default_value(False) == "FALSE"
        assert analyzer._format_default_value(None) == "NULL"
        assert analyzer._format_default_value([1, 2, 3]) == "[1, 2, 3]"

    def test_optional_type_detection(self, analyzer):
        """Test optional type detection"""

        # Test Optional[T] detection
        optional_str = str | None
        assert analyzer._is_optional_type(optional_str)
        assert analyzer._get_optional_inner_type(optional_str) is str

        # Test Union with None
        union_str = str | None
        assert analyzer._is_optional_type(union_str)
        assert analyzer._get_optional_inner_type(union_str) is str

        # Test non-optional
        assert not analyzer._is_optional_type(str)

    def test_list_type_detection(self, analyzer):
        """Test list type detection"""

        # Test List[T] detection
        list_str = list[str]
        assert analyzer._is_list_type(list_str)
        assert analyzer._get_list_inner_type(list_str) is str

        # Test non-list
        assert not analyzer._is_list_type(str)

    def test_add_indexes_and_constraints(self, analyzer):
        """Test adding indexes and constraints from Meta"""

        @dataclass
        class User(DomainModel):
            id: int
            email: str
            name: str

            class Meta:
                indexes = [
                    {"name": "ix_users_email", "columns": ["email"]},
                    {"name": "ix_users_name", "columns": ["name"], "unique": True},
                ]
                constraints = [
                    {
                        "name": "ck_email_format",
                        "type": "check",
                        "expression": "email LIKE '%@%'",
                    },
                ]

        table_def = analyzer.analyze_model(User)

        assert len(table_def.indexes) == 2
        assert len(table_def.constraints) == 1

        # Check index details
        email_index = next(
            idx for idx in table_def.indexes if idx["name"] == "ix_users_email"
        )
        assert email_index["columns"] == ["email"]
        assert email_index.get("unique", False) is False

        name_index = next(
            idx for idx in table_def.indexes if idx["name"] == "ix_users_name"
        )
        assert name_index["columns"] == ["name"]
        assert name_index.get("unique", False) is True


class TestMigrationGenerator:
    """Test MigrationGenerator functionality"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def generator(self, temp_dir):
        """Create migration generator"""
        return MigrationGenerator(temp_dir)

    def test_generator_creation(self, generator):
        """Test generator can be created"""
        assert isinstance(generator, MigrationGenerator)
        assert isinstance(generator.analyzer, ModelAnalyzer)

    def test_generate_migration_from_models(self, generator, temp_dir):
        """Test generating migration from models"""

        @dataclass
        class User(DomainModel):
            id: int
            name: str
            email: str

        @dataclass
        class Post(DomainModel):
            id: int
            title: str
            user_id: int

        migration_file = generator.generate_migration_from_models(
            [User, Post], message="Create users and posts tables",
        )

        # Check that file was created
        assert Path(migration_file).exists()

        # Check file content
        content = Path(migration_file).read_text()
        assert "Create users and posts tables" in content
        assert "create_table('user'" in content
        assert "create_table('post'" in content
        assert "op.create_table" in content

    def test_generate_migration_content(self, generator):
        """Test generating migration content"""

        # Create test schema diff
        user_columns = [
            ColumnDefinition(
                name="id", type_sql="INTEGER", primary_key=True, nullable=False,
            ),
            ColumnDefinition(name="name", type_sql="VARCHAR", nullable=False),
        ]
        user_table = TableDefinition(name="users", columns=user_columns)

        schema_diff = SchemaDiff(
            tables_to_create=[user_table],
            tables_to_drop=[],
            columns_to_add={},
            columns_to_drop={},
            columns_to_modify={},
            indexes_to_add={},
            indexes_to_drop={},
            constraints_to_add={},
            constraints_to_drop={},
        )

        content = generator._generate_migration_content(
            schema_diff, "Test migration", "test_rev",
        )

        assert "Test migration" in content
        assert 'revision: str = "test_rev"' in content
        assert "create_table('users'" in content
        assert "def upgrade() -> None:" in content
        assert "def downgrade() -> None:" in content

    def test_generate_create_table_sql(self, generator):
        """Test generating CREATE TABLE SQL"""

        columns = [
            ColumnDefinition(
                name="id", type_sql="INTEGER", primary_key=True, nullable=False,
            ),
            ColumnDefinition(
                name="name", type_sql="VARCHAR", nullable=False, default="'Anonymous'",
            ),
            ColumnDefinition(
                name="email", type_sql="VARCHAR", nullable=True, unique=True, index=True,
            ),
            ColumnDefinition(
                name="user_id",
                type_sql="INTEGER",
                foreign_key="users.id",
                comment="Reference to user",
            ),
        ]

        table = TableDefinition(
            name="profiles",
            columns=columns,
            indexes=[{"name": "ix_profiles_name", "columns": ["name"]}],
        )

        sql = generator._generate_create_table_sql(table)

        assert "op.create_table('profiles'" in sql
        assert "sa.Column('id', INTEGER" in sql
        assert "primary_key=True" in sql
        assert "nullable=False" in sql
        assert "default='Anonymous'" in sql
        assert "unique=True" in sql
        assert "sa.ForeignKey('users.id')" in sql
        assert ".comment('Reference to user')" in sql
        assert "sa.Index('ix_profiles_name', 'name')" in sql

    def test_generate_add_column_sql(self, generator):
        """Test generating ADD COLUMN SQL"""

        column = ColumnDefinition(
            name="age", type_sql="INTEGER", nullable=True, default="18",
        )

        sql = generator._generate_add_column_sql("users", column)
        assert "op.add_column('users', sa.Column('age', INTEGER" in sql
        assert "default=18" in sql

    def test_generate_drop_column_sql(self, generator):
        """Test generating DROP COLUMN SQL"""

        column = ColumnDefinition(name="old_field", type_sql="VARCHAR")
        sql = generator._generate_drop_column_sql("users", column)
        assert sql == "op.drop_column('users', 'old_field')"

    def test_generate_create_index_sql(self, generator):
        """Test generating CREATE INDEX SQL"""

        index_def = {"name": "ix_users_email", "columns": ["email"], "unique": True}
        sql = generator._generate_create_index_sql("users", index_def)
        assert (
            "op.create_index('ix_users_email', 'users', ['email'], unique=True)" in sql
        )

        # Test without unique
        index_def = {"name": "ix_users_name", "columns": ["name"]}
        sql = generator._generate_create_index_sql("users", index_def)
        assert "op.create_index('ix_users_name', 'users', ['name'])" in sql

    def test_generate_drop_index_sql(self, generator):
        """Test generating DROP INDEX SQL"""

        index_def = {"name": "ix_users_email", "columns": ["email"]}
        sql = generator._generate_drop_index_sql("users", index_def)
        assert sql == "op.drop_index('ix_users_email')"

    def test_generate_drop_table_sql(self, generator):
        """Test generating DROP TABLE SQL"""

        sql = generator._generate_drop_table_sql("users")
        assert sql == "op.drop_table('users')"

    def test_generate_index_definition(self, generator):
        """Test generating index definition for table args"""

        index_def = {"name": "ix_users_email", "columns": ["email"], "unique": True}
        sql = generator._generate_index_definition("users", index_def)
        assert "sa.Index('ix_users_email', 'email', unique=True)" in sql

    def test_format_migration_template(self, generator):
        """Test formatting migration template"""

        upgrade_ops = [
            "op.create_table('users', sa.Column('id', sa.INTEGER(), primary_key=True))",
        ]
        downgrade_ops = ["op.drop_table('users')"]

        content = generator._format_migration_template(
            "Test migration", "test_rev", upgrade_ops, downgrade_ops,
        )

        assert "Test migration" in content
        assert 'revision: str = "test_rev"' in content
        assert "op.create_table('users'" in content
        assert "op.drop_table('users')" in content
        assert "def upgrade() -> None:" in content
        assert "def downgrade() -> None:" in content

    def test_format_migration_template_empty_ops(self, generator):
        """Test formatting migration template with empty operations"""

        content = generator._format_migration_template("Empty migration", None, [], [])

        assert "def upgrade() -> None:" in content
        assert "pass" in content
        assert "def downgrade() -> None:" in content

    def test_create_migration_file(self, generator, temp_dir):
        """Test creating migration file"""

        content = "# Test migration content"
        message = "Test migration file"

        migration_file = generator._create_migration_file(content, message)

        assert migration_file.exists()
        assert migration_file.parent.name == "versions"
        assert migration_file.name.endswith(".py")
        assert "test_migration_file" in migration_file.name

        file_content = migration_file.read_text()
        assert file_content == content

    def test_migration_file_timestamp_format(self, generator, temp_dir):
        """Test migration file has proper timestamp format"""

        content = "# Test"
        migration_file = generator._create_migration_file(content, "Test")

        # Filename should start with YYYYMMDD_HHMMSS
        filename = migration_file.name
        # Split on '_' and take first two parts (date and time), then join them back
        parts = filename.split("_")
        timestamp_part = "_".join(parts[:2])  # YYYYMMDD_HHMMSS
        # Should be YYYYMMDD_HHMMSS format (15 digits with underscore)
        assert len(timestamp_part) == 15
        assert timestamp_part.replace("_", "").isdigit()
        # Should contain underscore in filename
        assert "_" in filename

    def test_migration_with_revision(self, generator, temp_dir):
        """Test generating migration with custom revision"""

        @dataclass
        class User(DomainModel):
            id: int
            name: str

        migration_file = generator.generate_migration_from_models(
            [User], message="Test with revision", revision="custom_rev_123",
        )

        content = Path(migration_file).read_text()
        assert 'revision: str = "custom_rev_123"' in content