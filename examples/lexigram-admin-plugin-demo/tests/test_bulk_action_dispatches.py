from __future__ import annotations

from demo.actions.archive import handle
from demo.contributor import DemoContributor


async def test_archive_handle_returns_expected_dict() -> None:
    result = await handle(days=30)
    assert isinstance(result, dict)
    assert "archived" in result
    assert "message" in result


async def test_archive_handle_includes_days_in_message() -> None:
    result = await handle(days=90)
    assert "90" in result["message"]


async def test_archive_handle_with_default_days() -> None:
    result = await handle()
    assert result["archived"] == 0
    assert "30" in result["message"]


async def test_archive_action_is_callable_via_contributor() -> None:
    c = DemoContributor()
    result = await c.execute_action("archive_old", {"days": 7})
    assert isinstance(result, dict)
    assert "archived" in result


async def test_contributor_execute_action_uses_correct_handler() -> None:
    c = DemoContributor()
    actions = c.get_actions()
    archive = next(a for a in actions if a.name == "archive_old")
    assert archive.handler == "demo.actions.archive:handle"
