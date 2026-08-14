"""Tests for UserDashboardService — per-user custom dashboard builder."""

from __future__ import annotations

import pytest

from lexigram.admin.services.user_dashboard import (
    UserDashboardLayout,
    UserDashboardService,
    WidgetPlacement,
)


# ---------------------------------------------------------------------------
# WidgetPlacement
# ---------------------------------------------------------------------------

class TestWidgetPlacement:
    def test_to_dict_roundtrip(self) -> None:
        p = WidgetPlacement(widget_id="w1", col=2, row=3, col_span=4, row_span=2)
        d = p.to_dict()
        p2 = WidgetPlacement.from_dict(d)
        assert p2.widget_id == "w1"
        assert p2.col == 2
        assert p2.row == 3
        assert p2.col_span == 4
        assert p2.row_span == 2


# ---------------------------------------------------------------------------
# UserDashboardLayout
# ---------------------------------------------------------------------------

class TestUserDashboardLayout:
    def test_to_dict_roundtrip(self) -> None:
        layout = UserDashboardLayout(
            user_id="u1",
            dashboard_id="main",
            placements=[WidgetPlacement("w1", col=0, row=0)],
            hidden_widgets=["w2"],
            cols=12,
        )
        d = layout.to_dict()
        restored = UserDashboardLayout.from_dict(d)
        assert restored.user_id == "u1"
        assert restored.dashboard_id == "main"
        assert len(restored.placements) == 1
        assert restored.hidden_widgets == ["w2"]
        assert restored.cols == 12


# ---------------------------------------------------------------------------
# UserDashboardService — get_or_create
# ---------------------------------------------------------------------------

class TestGetOrCreate:
    @pytest.mark.asyncio
    async def test_creates_layout_for_new_user(self) -> None:
        svc = UserDashboardService()
        layout = await svc.get_or_create("u1")
        assert layout.user_id == "u1"

    @pytest.mark.asyncio
    async def test_returns_same_layout_on_second_call(self) -> None:
        svc = UserDashboardService()
        layout1 = await svc.get_or_create("u1")
        layout2 = await svc.get_or_create("u1")
        assert layout1 is layout2

    @pytest.mark.asyncio
    async def test_get_layout_none_for_new_user(self) -> None:
        svc = UserDashboardService()
        assert svc.get_layout("newuser") is None

    @pytest.mark.asyncio
    async def test_get_layout_returns_after_create(self) -> None:
        svc = UserDashboardService()
        await svc.get_or_create("u1")
        assert svc.get_layout("u1") is not None


# ---------------------------------------------------------------------------
# Add / remove widgets
# ---------------------------------------------------------------------------

class TestAddRemoveWidgets:
    @pytest.mark.asyncio
    async def test_add_widget_creates_placement(self) -> None:
        svc = UserDashboardService()
        placement = await svc.add_widget("u1", "stat_card", col=0, row=0, widget_id="w1")
        assert placement.widget_id == "w1"
        assert placement.col == 0
        assert placement.row == 0

    @pytest.mark.asyncio
    async def test_add_widget_with_span(self) -> None:
        svc = UserDashboardService()
        p = await svc.add_widget("u1", "chart", col=0, row=0, col_span=6, row_span=2, widget_id="w1")
        assert p.col_span == 6
        assert p.row_span == 2

    @pytest.mark.asyncio
    async def test_add_multiple_widgets(self) -> None:
        svc = UserDashboardService()
        await svc.add_widget("u1", "stat_card", col=0, row=0, widget_id="w1")
        await svc.add_widget("u1", "stat_card", col=4, row=0, widget_id="w2")
        layout = svc.get_layout("u1")
        assert layout is not None
        assert len(layout.placements) == 2

    @pytest.mark.asyncio
    async def test_remove_widget(self) -> None:
        svc = UserDashboardService()
        await svc.add_widget("u1", "stat_card", widget_id="w1")
        removed = await svc.remove_widget("u1", "w1")
        assert removed is True
        layout = svc.get_layout("u1")
        assert layout is not None
        assert len(layout.placements) == 0

    @pytest.mark.asyncio
    async def test_remove_missing_returns_false(self) -> None:
        svc = UserDashboardService()
        result = await svc.remove_widget("u1", "ghost")
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_missing_user_returns_false(self) -> None:
        svc = UserDashboardService()
        assert await svc.remove_widget("nouser", "w1") is False


# ---------------------------------------------------------------------------
# Move / resize
# ---------------------------------------------------------------------------

class TestMoveResize:
    @pytest.mark.asyncio
    async def test_move_widget(self) -> None:
        svc = UserDashboardService()
        await svc.add_widget("u1", "stat_card", col=0, row=0, widget_id="w1")
        moved = await svc.move_widget("u1", "w1", col=3, row=2)
        assert moved is True
        layout = svc.get_layout("u1")
        assert layout is not None
        p = next(p for p in layout.placements if p.widget_id == "w1")
        assert p.col == 3
        assert p.row == 2

    @pytest.mark.asyncio
    async def test_move_missing_widget_returns_false(self) -> None:
        svc = UserDashboardService()
        await svc.get_or_create("u1")
        assert await svc.move_widget("u1", "ghost", col=1, row=1) is False

    @pytest.mark.asyncio
    async def test_resize_widget(self) -> None:
        svc = UserDashboardService()
        await svc.add_widget("u1", "chart", widget_id="w1")
        resized = await svc.resize_widget("u1", "w1", col_span=6, row_span=3)
        assert resized is True
        layout = svc.get_layout("u1")
        assert layout is not None
        p = next(p for p in layout.placements if p.widget_id == "w1")
        assert p.col_span == 6
        assert p.row_span == 3


# ---------------------------------------------------------------------------
# Hide / show
# ---------------------------------------------------------------------------

class TestHideShow:
    @pytest.mark.asyncio
    async def test_hide_widget(self) -> None:
        svc = UserDashboardService()
        await svc.hide_widget("u1", "w1")
        layout = svc.get_layout("u1")
        assert layout is not None
        assert "w1" in layout.hidden_widgets

    @pytest.mark.asyncio
    async def test_hide_idempotent(self) -> None:
        svc = UserDashboardService()
        await svc.hide_widget("u1", "w1")
        await svc.hide_widget("u1", "w1")
        layout = svc.get_layout("u1")
        assert layout is not None
        assert layout.hidden_widgets.count("w1") == 1

    @pytest.mark.asyncio
    async def test_show_widget(self) -> None:
        svc = UserDashboardService()
        await svc.hide_widget("u1", "w1")
        await svc.show_widget("u1", "w1")
        layout = svc.get_layout("u1")
        assert layout is not None
        assert "w1" not in layout.hidden_widgets


# ---------------------------------------------------------------------------
# Reset / export / import
# ---------------------------------------------------------------------------

class TestResetExportImport:
    @pytest.mark.asyncio
    async def test_reset_clears_layout(self) -> None:
        svc = UserDashboardService()
        await svc.add_widget("u1", "stat_card", widget_id="w1")
        await svc.reset("u1")
        assert svc.get_layout("u1") is None

    @pytest.mark.asyncio
    async def test_reset_then_get_or_create_returns_fresh(self) -> None:
        svc = UserDashboardService()
        await svc.add_widget("u1", "stat_card", widget_id="w1")
        await svc.reset("u1")
        layout = await svc.get_or_create("u1")
        assert len(layout.placements) == 0

    @pytest.mark.asyncio
    async def test_export_layout(self) -> None:
        svc = UserDashboardService()
        await svc.add_widget("u1", "stat_card", col=0, row=0, widget_id="w1")
        data = svc.export_layout("u1")
        assert data is not None
        assert data["user_id"] == "u1"
        assert len(data["placements"]) == 1

    def test_export_none_for_missing_user(self) -> None:
        svc = UserDashboardService()
        assert svc.export_layout("ghost") is None

    def test_import_layout(self) -> None:
        svc = UserDashboardService()
        data = {
            "user_id": "u2",
            "dashboard_id": "default",
            "placements": [{"widget_id": "w1", "col": 0, "row": 0, "col_span": 1, "row_span": 1}],
            "hidden_widgets": [],
            "cols": 12,
        }
        layout = svc.import_layout(data)
        assert layout.user_id == "u2"
        assert len(layout.placements) == 1
        assert svc.get_layout("u2") is layout

    @pytest.mark.asyncio
    async def test_export_import_roundtrip(self) -> None:
        svc = UserDashboardService()
        await svc.add_widget("u1", "chart", col=2, row=1, col_span=6, widget_id="w1")
        exported = svc.export_layout("u1")
        assert exported is not None

        svc2 = UserDashboardService()
        svc2.import_layout(exported)
        layout = svc2.get_layout("u1")
        assert layout is not None
        assert layout.placements[0].col == 2
        assert layout.placements[0].col_span == 6
