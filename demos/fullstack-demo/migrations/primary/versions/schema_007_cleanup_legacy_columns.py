"""drop legacy columns from projects and runs tables

Columns on projects that were never mapped in the Pydantic model:
  - script_json, stage_progress, status, output_path, duration_s, error
  These were superseded by the runs table (schema_003) or idea_json repurposing.

Columns on runs that were migrated to projects in schema_006:
  - idea_json, script_json (already nulled by schema_006)

Revision ID: schema_007
Revises: schema_006
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "schema_007"
down_revision: str | None = "schema_006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_index("ix_projects_status")
        batch_op.drop_column("script_json")
        batch_op.drop_column("stage_progress")
        batch_op.drop_column("status")
        batch_op.drop_column("output_path")
        batch_op.drop_column("duration_s")
        batch_op.drop_column("error")

    with op.batch_alter_table("runs") as batch_op:
        batch_op.drop_column("idea_json")
        batch_op.drop_column("script_json")


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("script_json", sa.TEXT, nullable=True))
        batch_op.add_column(
            sa.Column("stage_progress", sa.TEXT, nullable=False, server_default="{}")
        )
        batch_op.add_column(
            sa.Column("status", sa.VARCHAR(20), nullable=False, server_default="draft")
        )
        batch_op.add_column(sa.Column("output_path", sa.TEXT, nullable=True))
        batch_op.add_column(sa.Column("duration_s", sa.FLOAT, nullable=True))
        batch_op.add_column(sa.Column("error", sa.TEXT, nullable=True))
        batch_op.create_index("ix_projects_status", "projects", ["status"])

    with op.batch_alter_table("runs") as batch_op:
        batch_op.add_column(sa.Column("idea_json", sa.TEXT, nullable=True))
        batch_op.add_column(sa.Column("script_json", sa.TEXT, nullable=True))
