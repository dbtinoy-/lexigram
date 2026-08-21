import types

from lexigram.admin.layout import LayoutType
from lexigram.admin.resources.layouts import apply_layout_config


class DummyManager:
    def __init__(self):
        self.calls = []

    def add_grid_layout(self, **kwargs):
        self.calls.append(("grid", kwargs))

    def add_calendar_layout(self, **kwargs):
        self.calls.append(("calendar", kwargs))

    def add_map_layout(self, **kwargs):
        self.calls.append(("map", kwargs))

    def add_list_layout(self, **kwargs):
        self.calls.append(("list", kwargs))


def make_cfg(layout_type, **kwargs):
    cfg = types.SimpleNamespace()
    cfg.type = layout_type
    cfg.columns = kwargs.get("columns", 3)
    cfg.card_template = kwargs.get("card_template", "card")
    cfg.enabled = kwargs.get("enabled", True)
    cfg.date_field = kwargs.get("date_field", "date")
    cfg.title_field = kwargs.get("title_field", "title")
    cfg.latitude_field = kwargs.get("latitude_field", "lat")
    cfg.longitude_field = kwargs.get("longitude_field", "lon")
    cfg.marker_template = kwargs.get("marker_template", "marker")
    return cfg


def test_apply_grid_layout_uses_registry():
    mgr = DummyManager()
    cfg = make_cfg(LayoutType.GRID)

    apply_layout_config(mgr, cfg)

    assert mgr.calls == [
        (
            "grid",
            {
                "columns": cfg.columns,
                "card_template": cfg.card_template,
                "enabled": cfg.enabled,
            },
        )
    ]


def test_apply_calendar_layout_uses_registry():
    mgr = DummyManager()
    cfg = make_cfg(LayoutType.CALENDAR)

    apply_layout_config(mgr, cfg)

    assert mgr.calls == [
        (
            "calendar",
            {
                "date_field": cfg.date_field,
                "title_field": cfg.title_field,
                "enabled": cfg.enabled,
            },
        )
    ]


def test_apply_map_layout_uses_registry():
    mgr = DummyManager()
    cfg = make_cfg(LayoutType.MAP)

    apply_layout_config(mgr, cfg)

    assert mgr.calls == [
        (
            "map",
            {
                "latitude_field": cfg.latitude_field,
                "longitude_field": cfg.longitude_field,
                "marker_template": cfg.marker_template,
                "enabled": cfg.enabled,
            },
        )
    ]


def test_apply_list_layout_uses_registry():
    mgr = DummyManager()
    cfg = make_cfg(LayoutType.LIST)

    apply_layout_config(mgr, cfg)

    assert mgr.calls == [("list", {"enabled": cfg.enabled})]
