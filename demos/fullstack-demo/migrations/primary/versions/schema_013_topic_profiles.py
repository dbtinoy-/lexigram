"""rename video_type_profiles to topic_profiles

The per-topic override store is no longer tied to the retired "video type"
concept: each row names a topic from the skills registry. Renaming the table
keeps the schema aligned with the code (TopicProfileService).

Revision ID: schema_013
Revises: schema_012
Create Date: 2026-08-09
"""

from collections.abc import Sequence

from alembic import op

revision: str = "schema_013"
down_revision: str | None = "schema_012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.rename_table("video_type_profiles", "topic_profiles")


def downgrade() -> None:
    op.rename_table("topic_profiles", "video_type_profiles")
