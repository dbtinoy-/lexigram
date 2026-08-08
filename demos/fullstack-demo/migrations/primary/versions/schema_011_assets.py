"""create assets table and per-project asset reference columns

Asset system persists reusable assets (music, fonts, images, clips,
watermarks) and lets a project reference its chosen assets.

Revision ID: schema_011
Revises: schema_010
Create Date: 2026-08-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "schema_011"
down_revision: str | None = "schema_010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "assets",
        sa.Column("id", sa.VARCHAR(36), primary_key=True),
        sa.Column("created_at", sa.TEXT, nullable=False),
        sa.Column("updated_at", sa.TEXT, nullable=False),
        sa.Column("type", sa.VARCHAR(20), nullable=False),
        sa.Column("name", sa.VARCHAR(255), nullable=False),
        sa.Column("description", sa.TEXT, nullable=False, server_default=""),
        sa.Column("tags", sa.TEXT, nullable=False, server_default="[]"),
        sa.Column("role", sa.VARCHAR(20), nullable=True),
        sa.Column("meta", sa.TEXT, nullable=False, server_default="{}"),
        sa.Column("file_path", sa.TEXT, nullable=True),
    )
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("asset_music_id", sa.VARCHAR(36), nullable=True))
        batch_op.add_column(sa.Column("asset_font_id", sa.VARCHAR(36), nullable=True))
        batch_op.add_column(sa.Column("asset_watermark_id", sa.VARCHAR(36), nullable=True))
        batch_op.add_column(sa.Column("asset_bg_clip_id", sa.VARCHAR(36), nullable=True))
        batch_op.add_column(sa.Column("asset_outro_clip_id", sa.VARCHAR(36), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("asset_outro_clip_id")
        batch_op.drop_column("asset_bg_clip_id")
        batch_op.drop_column("asset_watermark_id")
        batch_op.drop_column("asset_font_id")
        batch_op.drop_column("asset_music_id")
    op.drop_table("assets")
