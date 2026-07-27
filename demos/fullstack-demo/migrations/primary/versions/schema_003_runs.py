"""create runs table

Revision ID: schema_003
Revises: schema_002
Create Date: 2026-07-27
"""
from typing import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "schema_003"
down_revision: str | None = "schema_002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", sa.VARCHAR(36), primary_key=True),
        sa.Column("project_id", sa.VARCHAR(36), nullable=False),
        sa.Column("title", sa.TEXT, nullable=False, server_default=""),
        sa.Column("status", sa.VARCHAR(20), nullable=False, server_default="draft"),
        sa.Column("idea_json", sa.TEXT, nullable=True),
        sa.Column("script_json", sa.TEXT, nullable=True),
        sa.Column("stage_progress", sa.TEXT, nullable=False, server_default="{}"),
        sa.Column("output_path", sa.TEXT, nullable=True),
        sa.Column("duration_s", sa.FLOAT, nullable=True),
        sa.Column("error", sa.TEXT, nullable=True),
        sa.Column("created_at", sa.DATETIME, nullable=False),
        sa.Column("updated_at", sa.DATETIME, nullable=False),
    )
    op.create_index("ix_runs_project_id", "runs", ["project_id"])
    op.create_index("ix_runs_status", "runs", ["status"])
    op.create_index("ix_runs_created_at", "runs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_runs_created_at", table_name="runs")
    op.drop_index("ix_runs_status", table_name="runs")
    op.drop_index("ix_runs_project_id", table_name="runs")
    op.drop_table("runs")
