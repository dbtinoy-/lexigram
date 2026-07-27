"""drop cta_enabled, cta_lead_in, cta_display from projects

The CTA system (visual tail + settings) was removed; the outro clip
replaces it. Columns are dropped since no code path references them.

Revision ID: schema_010
Revises: schema_009
Create Date: 2026-08-06
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "schema_010"
down_revision: str | None = "schema_009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("cta_enabled")
        batch_op.drop_column("cta_lead_in")
        batch_op.drop_column("cta_display")


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("cta_enabled", sa.BOOLEAN, nullable=True))
        batch_op.add_column(sa.Column("cta_lead_in", sa.FLOAT, nullable=True))
        batch_op.add_column(sa.Column("cta_display", sa.FLOAT, nullable=True))