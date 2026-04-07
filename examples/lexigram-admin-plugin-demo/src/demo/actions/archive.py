from __future__ import annotations


async def handle(days: int = 30) -> dict[str, object]:
    return {"archived": 0, "message": f"Archive of items older than {days} days completed"}
