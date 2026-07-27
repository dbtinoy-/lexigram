"""add updated_at column to app_settings

Revision ID: schema_004
Revises: schema_003
Create Date: 2026-07-29
"""
from typing import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "schema_004"
down_revision: str | None = "schema_003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("app_settings", sa.Column("updated_at", sa.TEXT, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("app_settings") as batch_op:
        batch_op.drop_column("updated_at")
