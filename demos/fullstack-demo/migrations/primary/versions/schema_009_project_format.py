"""add format and caption_style columns to projects

The format (e.g. narration) drives how a project's videos present their
script; caption_style (highlight|plain) is the presentation mode consumed
by the render pipeline.

Revision ID: schema_009
Revises: schema_008
Create Date: 2026-08-06
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "schema_009"
down_revision: str | None = "schema_008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("format", sa.VARCHAR(50), nullable=False, server_default="narration"))
        batch_op.add_column(sa.Column("caption_style", sa.VARCHAR(20), nullable=False, server_default="highlight"))


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("caption_style")
        batch_op.drop_column("format")
