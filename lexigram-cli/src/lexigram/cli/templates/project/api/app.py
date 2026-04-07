"""{{ project_name }} — minimal Lexigram API (Gear 1)."""
from __future__ import annotations

from lexigram.web import app, get  # noqa: F401


@get("/")
async def hello() -> dict:
    return {"hello": "{{ project_name }}", "status": "ok"}
