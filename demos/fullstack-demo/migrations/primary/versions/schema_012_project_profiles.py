"""persist project overrides, video-type profiles, and run snapshots

Introduces single-source JSON storage for per-project creative overrides
(profile_overrides_json), a video_type_profiles table for per-video-type
overrides, and a nullable settings_snapshot_json on runs. Legacy per-column
override values are backfilled into the JSON blob and the duplicate columns
are dropped.

Revision ID: schema_012
Revises: schema_011
Create Date: 2026-08-08
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "schema_012"
down_revision: str | None = "schema_011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LEGACY_COLUMNS = (
    "default_duration",
    "format",
    "caption_style",
    "asset_music_id",
    "asset_font_id",
    "asset_watermark_id",
    "asset_bg_clip_id",
    "asset_outro_clip_id",
)

_ASSET_COLUMNS = (
    "asset_music_id",
    "asset_font_id",
    "asset_watermark_id",
    "asset_bg_clip_id",
    "asset_outro_clip_id",
)

_SELECT_LEGACY = sa.text(
    "SELECT id, default_duration, format, caption_style, "
    "asset_music_id, asset_font_id, asset_watermark_id, "
    "asset_bg_clip_id, asset_outro_clip_id FROM projects"
)


def _profile_values(row) -> dict:
    """Serialize one legacy project row into profile override values.

    Non-null legacy values are mapped onto their profile JSON keys;
    unparseable numbers and empty strings are omitted rather than
    blocking boot.
    """
    values = {}
    raw_duration = row.default_duration
    if raw_duration is not None:
        try:
            values["duration_seconds"] = int(raw_duration)
        except (TypeError, ValueError):
            pass
    if row.format:
        values["format_name"] = row.format
    if row.caption_style:
        values["caption_style"] = row.caption_style
    for column in _ASSET_COLUMNS:
        if getattr(row, column):
            values[column] = getattr(row, column)
    return values


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("profile_overrides_json", sa.TEXT, nullable=False, server_default="{}"),
    )
    op.add_column("runs", sa.Column("settings_snapshot_json", sa.TEXT, nullable=True))
    op.create_table(
        "video_type_profiles",
        sa.Column("name", sa.TEXT, primary_key=True),
        sa.Column("overrides_json", sa.TEXT, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.TEXT, nullable=False),
        sa.Column("updated_at", sa.TEXT, nullable=False),
    )

    connection = op.get_bind()
    for row in connection.execute(_SELECT_LEGACY):
        values = _profile_values(row)
        if not values:
            continue
        connection.execute(
            sa.text("UPDATE projects SET profile_overrides_json = :payload WHERE id = :id"),
            {"payload": json.dumps(values, separators=(",", ":")), "id": row.id},
        )

    with op.batch_alter_table("projects") as batch_op:
        for column in _LEGACY_COLUMNS:
            batch_op.drop_column(column)


def downgrade() -> None:
    connection = op.get_bind()
    with op.batch_alter_table("projects") as batch_op:
        batch_op.add_column(sa.Column("default_duration", sa.INTEGER, nullable=True))
        batch_op.add_column(
            sa.Column(
                "format",
                sa.VARCHAR(50),
                nullable=False,
                server_default="narration",
                default="narration",
            )
        )
        batch_op.add_column(
            sa.Column(
                "caption_style",
                sa.VARCHAR(20),
                nullable=False,
                server_default="highlight",
                default="highlight",
            )
        )
        for column in _ASSET_COLUMNS:
            batch_op.add_column(sa.Column(column, sa.VARCHAR(36), nullable=True))

    for row in connection.execute(sa.text("SELECT id, profile_overrides_json FROM projects")):
        try:
            values = json.loads(row.profile_overrides_json or "{}")
        except (TypeError, ValueError):
            values = {}
        if not isinstance(values, dict):
            continue
        updates = {}
        raw_duration = values.get("duration_seconds")
        if raw_duration is not None:
            try:
                updates["default_duration"] = int(raw_duration)
            except (TypeError, ValueError):
                pass
        for column, profile_key in (
            ("format", "format_name"),
            ("caption_style", "caption_style"),
        ):
            if values.get(profile_key):
                updates[column] = values[profile_key]
        for column in _ASSET_COLUMNS:
            if values.get(column):
                updates[column] = values[column]
        if not updates:
            continue
        connection.execute(
            sa.text(
                "UPDATE projects SET "
                + ", ".join(f"{column} = :{column}" for column in updates)
                + " WHERE id = :id"
            ),
            {**updates, "id": row.id},
        )

    with op.batch_alter_table("projects") as batch_op:
        batch_op.drop_column("profile_overrides_json")
    with op.batch_alter_table("runs") as batch_op:
        batch_op.drop_column("settings_snapshot_json")
    op.drop_table("video_type_profiles")
