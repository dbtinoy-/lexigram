"""add project override columns for tri-tier settings

Revision ID: schema_005
Revises: schema_004
Create Date: 2026-07-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "schema_005"
down_revision: str | None = "schema_004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("default_duration", sa.INTEGER, nullable=True))
    op.add_column("projects", sa.Column("cta_enabled", sa.BOOLEAN, nullable=True))
    op.add_column("projects", sa.Column("cta_lead_in", sa.REAL, nullable=True))
    op.add_column("projects", sa.Column("cta_display", sa.REAL, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("default_duration")
        batch_op.drop_column("cta_enabled")
        batch_op.drop_column("cta_lead_in")
        batch_op.drop_column("cta_display")
