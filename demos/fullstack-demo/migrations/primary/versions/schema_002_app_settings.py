"""create app_settings table

Revision ID: schema_002
Revises: schema_001
Create Date: 2026-07-26
"""
from typing import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = "schema_002"
down_revision: str | None = "schema_001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.VARCHAR(100), primary_key=True),
        sa.Column("value", sa.TEXT, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
