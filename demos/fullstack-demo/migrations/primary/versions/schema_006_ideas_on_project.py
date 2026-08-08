"""migrate ideas from runs to projects

Revision ID: schema_006
Revises: schema_005
Create Date: 2026-07-30
"""
from typing import Sequence
from alembic import op
import sqlalchemy as sa
import json
import uuid

revision: str = "schema_006"
down_revision: str | None = "schema_005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _assign_ids(ideas: list) -> list:
    for idea in ideas:
        if "id" not in idea or not idea.get("id"):
            idea["id"] = str(uuid.uuid4())
    return ideas


def upgrade() -> None:
    conn = op.get_bind()

    op.add_column("runs", sa.Column("selected_idea_id", sa.VARCHAR(36), nullable=True))

    rows = conn.execute(
        sa.text("SELECT id, project_id, idea_json, script_json, created_at FROM runs WHERE idea_json IS NOT NULL ORDER BY created_at ASC")
    ).fetchall()

    project_ideas: dict[str, list] = {}
    project_scripts: dict[str, dict[str, dict]] = {}

    for row in rows:
        rid, pid, idea_json, script_json, _ = row
        if pid not in project_ideas:
            project_ideas[pid] = []
            project_scripts[pid] = {}

        if idea_json:
            try:
                ideas = json.loads(idea_json)
                if isinstance(ideas, list):
                    known_titles = {i.get("title") for i in project_ideas[pid]}
                    for idea in ideas:
                        if idea.get("title") not in known_titles:
                            idea = _assign_ids([idea])[0]
                            project_ideas[pid].append(idea)
                            known_titles.add(idea.get("title"))
                elif isinstance(ideas, dict):
                    ideas = _assign_ids([ideas])
                    project_ideas[pid].extend(ideas)
            except (json.JSONDecodeError, TypeError):
                pass

        if script_json:
            try:
                scripts = json.loads(script_json)
                if isinstance(scripts, dict):
                    for k, v in scripts.items():
                        project_scripts[pid][k] = v
            except (json.JSONDecodeError, TypeError):
                pass

    for pid, scripts in project_scripts.items():
        ideas = project_ideas.get(pid, [])
        for idx_str, script in scripts.items():
            try:
                idx = int(idx_str)
                if 0 <= idx < len(ideas):
                    if "script_json" not in ideas[idx] or not ideas[idx]["script_json"]:
                        ideas[idx]["script_json"] = json.dumps(script)
            except (ValueError, IndexError):
                pass

    for pid, ideas in project_ideas.items():
        conn.execute(
            sa.text("UPDATE projects SET idea_json = :json WHERE id = :pid"),
            {"json": json.dumps(ideas), "pid": pid},
        )

    conn.execute(
        sa.text("UPDATE runs SET idea_json = NULL, script_json = NULL")
    )


def downgrade() -> None:
    conn = op.get_bind()

    rows = conn.execute(
        sa.text("SELECT id, project_id FROM runs ORDER BY created_at ASC")
    ).fetchall()
    project_first_run: dict[str, str] = {}
    for rid, pid in rows:
        if pid not in project_first_run:
            project_first_run[pid] = rid

    projects = conn.execute(
        sa.text("SELECT id, idea_json FROM projects WHERE idea_json IS NOT NULL")
    ).fetchall()

    for pid, idea_json in projects:
        if pid in project_first_run:
            rid = project_first_run[pid]
            conn.execute(
                sa.text("UPDATE runs SET idea_json = :json WHERE id = :rid"),
                {"json": idea_json, "rid": rid},
            )

    op.drop_column("runs", "selected_idea_id")
