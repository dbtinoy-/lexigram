"""rename projects.script_type to topic

Content framework renamed to topic as part of the topic/format system.
Also rewrites the script_type key inside stored idea_json rows.

Revision ID: schema_008
Revises: schema_007
Create Date: 2026-08-06
"""

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "schema_008"
down_revision: str | None = "schema_007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.alter_column("script_type", new_column_name="topic")

    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, idea_json FROM projects WHERE idea_json IS NOT NULL")
    ).fetchall()
    for pid, raw in rows:
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        changed = False
        for idea in items:
            if isinstance(idea, dict) and "script_type" in idea and "topic" not in idea:
                idea["topic"] = idea.pop("script_type")
                changed = True
        if changed:
            conn.execute(
                sa.text("UPDATE projects SET idea_json = :idea_json WHERE id = :id"),
                {"idea_json": json.dumps(items if isinstance(data, list) else items[0]), "id": pid},
            )


def downgrade() -> None:
    with op.batch_alter_table("projects") as batch_op:
        batch_op.alter_column("topic", new_column_name="script_type")

    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, idea_json FROM projects WHERE idea_json IS NOT NULL")
    ).fetchall()
    for pid, raw in rows:
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        items = data if isinstance(data, list) else [data]
        changed = False
        for idea in items:
            if isinstance(idea, dict) and "topic" in idea and "script_type" not in idea:
                idea["script_type"] = idea.pop("topic")
                changed = True
        if changed:
            conn.execute(
                sa.text("UPDATE projects SET idea_json = :idea_json WHERE id = :id"),
                {"idea_json": json.dumps(items if isinstance(data, list) else items[0]), "id": pid},
            )
