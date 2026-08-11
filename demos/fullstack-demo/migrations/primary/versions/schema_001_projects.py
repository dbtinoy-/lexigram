"""create projects table

Revision ID: schema_001
Revises: None
Create Date: 2026-07-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "schema_001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.VARCHAR(36), primary_key=True),
        sa.Column("created_at", sa.DATETIME, nullable=False),
        sa.Column("updated_at", sa.DATETIME, nullable=False),
        sa.Column("status", sa.VARCHAR(20), nullable=False, server_default="draft"),
        sa.Column("script_type", sa.VARCHAR(50), nullable=False),
        sa.Column("focus", sa.TEXT, nullable=False, server_default=""),
        sa.Column("title", sa.TEXT, nullable=False, server_default=""),
        sa.Column("idea_json", sa.TEXT, nullable=True),
        sa.Column("script_json", sa.TEXT, nullable=True),
        sa.Column("stage_progress", sa.TEXT, nullable=False, server_default="{}"),
        sa.Column("output_path", sa.TEXT, nullable=True),
        sa.Column("duration_s", sa.FLOAT, nullable=True),
        sa.Column("error", sa.TEXT, nullable=True),
    )
    op.create_index("ix_projects_status", "projects", ["status"])
    op.create_index("ix_projects_created_at", "projects", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_projects_created_at", table_name="projects")
    op.drop_index("ix_projects_status", table_name="projects")
    op.drop_table("projects")
