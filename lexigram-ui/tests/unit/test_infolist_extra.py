"""Focused tests for InfolistWidget."""

from __future__ import annotations

from datetime import date, datetime

from lexigram.ui.molecules.infolist import InfolistEntry, InfolistEntryType, InfolistWidget


def _text(name: str, value: object = "v") -> InfolistEntry:
    return InfolistEntry(name=name, label=name.capitalize(), value=value)


class TestEntryType:
    def test_members(self) -> None:
        assert InfolistEntryType.TEXT.value == "text"
        assert InfolistEntryType.BOOLEAN.value == "boolean"
        assert InfolistEntryType.BADGE.value == "badge"
        assert InfolistEntryType.DATE.value == "date"
        assert InfolistEntryType.IMAGE.value == "image"
        assert InfolistEntryType.MONEY.value == "money"
        assert InfolistEntryType.URL.value == "url"
        assert InfolistEntryType.EMAIL.value == "email"

    def test_entry_defaults(self) -> None:
        e = InfolistEntry(name="n", label="N")
        assert e.value is None
        assert e.type is InfolistEntryType.TEXT
        assert e.icon is None
        assert e.badge_type == "default"
        assert e.image_url is None
        assert e.currency == "USD"
        assert e.url is None
        assert e.section is None

    def test_entry_frozen(self) -> None:
        e = InfolistEntry(name="n", label="N")
        try:
            e.value = 1
        except Exception as exc:  # noqa: BLE001
            assert isinstance(exc, Exception)
        else:
            raise AssertionError("expected frozen dataclass to raise")


class TestInit:
    def test_columns_clamped_low(self) -> None:
        assert InfolistWidget(entries=[]).columns == 2
        assert InfolistWidget(entries=[], columns=0).columns == 1

    def test_columns_clamped_high(self) -> None:
        assert InfolistWidget(entries=[], columns=9).columns == 4


class TestEmptyState:
    def test_empty_entries(self) -> None:
        html = str(InfolistWidget(entries=[]).render())
        assert "No information available." in html
        assert "p-6 text-center" in html

    def test_empty_entries_italic(self) -> None:
        html = str(InfolistWidget(entries=[]).render())
        assert "italic" in html


class TestRender:
    def test_single_text_entry(self) -> None:
        html = str(InfolistWidget(entries=[_text("name", "Alice")]).render())
        assert "Name" in html
        assert "Alice" in html

    def test_two_column_grid_class(self) -> None:
        html = str(InfolistWidget(entries=[_text("a"), _text("b")]).render())
        assert "grid-cols-1 sm:grid-cols-2" in html

    def test_one_column_grid_class(self) -> None:
        html = str(InfolistWidget(entries=[_text("a")], columns=1).render())
        assert "grid-cols-1" in html
        assert "sm:grid-cols-2" not in html

    def test_three_column_grid_class(self) -> None:
        html = str(InfolistWidget(entries=[_text("a")], columns=3).render())
        assert "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3" in html

    def test_four_column_grid_class(self) -> None:
        html = str(InfolistWidget(entries=[_text("a")], columns=4).render())
        assert "grid-cols-1 sm:grid-cols-2 lg:grid-cols-4" in html

    def test_entry_card_structure(self) -> None:
        el = InfolistWidget(entries=[_text("role", "admin")]).render()
        card = el.children[0].children[0]
        assert card.tag == "div"
        assert "p-3 rounded-lg border" in card.attrs["class_"]
        dt, dd = card.children
        assert dt.tag == "dt"
        assert dd.tag == "dd"
        assert "Owner" in str(dd) or "admin" in str(dd)

    def test_icon_rendered_when_set(self) -> None:
        entry = InfolistEntry(name="email", label="Email", value="a@b.c", icon="mail")
        html = str(InfolistWidget(entries=[entry]).render())
        assert "mail" in html

    def test_no_icon_when_unset(self) -> None:
        html = str(InfolistWidget(entries=[_text("a")]).render())
        assert "w-4 h-4" not in html


class TestSections:
    def test_sectioned_rendering(self) -> None:
        entries = [
            _text("a"),
            _text("b"),
            InfolistEntry(name="c", label="C", value=1, section="Identity"),
        ]
        html = str(InfolistWidget(entries=entries).render())
        assert "<h3" in html
        assert "Identity" in html
        assert "border-b border-border" in html

    def test_no_section_headings(self) -> None:
        html = str(InfolistWidget(entries=[_text("a"), _text("b")]).render())
        assert "<h3" not in html

    def test_grouping_order_first_appearance(self) -> None:
        entries = [
            InfolistEntry(name="z", label="Z", value=1, section="Second"),
            _text("a"),
            InfolistEntry(name="y", label="Y", value=2, section="First"),
        ]
        groups = InfolistWidget(entries=entries)._group_by_section()
        titles = [t for t, _ in groups]
        assert titles == ["Second", None, "First"]

    def test_grouping_keeps_entry_order(self) -> None:
        entries = [
            InfolistEntry(name="a", label="A", value=1, section="S"),
            InfolistEntry(name="b", label="B", value=2, section="S"),
        ]
        groups = InfolistWidget(entries=entries)._group_by_section()
        assert [e.name for _, es in groups for e in es] == ["a", "b"]


class TestValues:
    def test_none_value_dash(self) -> None:
        html = str(InfolistWidget(entries=[_text("a", None)]).render())
        assert "\u2014" in html

    def test_boolean_true(self) -> None:
        entry = InfolistEntry(name="ok", label="Ok", value=True, type=InfolistEntryType.BOOLEAN)
        html = str(InfolistWidget(entries=[entry]).render())
        assert "\u2713 Yes" in html
        assert "text-success" in html

    def test_boolean_false(self) -> None:
        entry = InfolistEntry(name="ok", label="Ok", value=False, type=InfolistEntryType.BOOLEAN)
        html = str(InfolistWidget(entries=[entry]).render())
        assert "\u2717 No" in html
        assert "text-destructive" in html

    def test_boolean_truthy_value(self) -> None:
        entry = InfolistEntry(name="n", label="N", value="x", type=InfolistEntryType.BOOLEAN)
        html = str(InfolistWidget(entries=[entry]).render())
        assert "Yes" in html

    def test_badge_types(self) -> None:
        for badge_type, token in [
            ("success", "bg-success/10"),
            ("warning", "bg-warning/10"),
            ("danger", "bg-destructive/10"),
            ("info", "bg-info/10"),
            ("default", "bg-muted"),
        ]:
            entry = InfolistEntry(
                name="s", label="S", value="x", type=InfolistEntryType.BADGE, badge_type=badge_type
            )
            html = str(InfolistWidget(entries=[entry]).render())
            assert token in html

    def test_badge_unknown_type_falls_back(self) -> None:
        entry = InfolistEntry(
            name="s", label="S", value="x", type=InfolistEntryType.BADGE, badge_type="mystery"
        )
        html = str(InfolistWidget(entries=[entry]).render())
        assert "bg-muted" in html

    def test_date_datetime(self) -> None:
        entry = InfolistEntry(name="d", label="D", value=datetime(2025, 1, 2, 13, 30), type=InfolistEntryType.DATE)
        html = str(InfolistWidget(entries=[entry]).render())
        assert "2025-01-02 13:30" in html

    def test_date_plain_date(self) -> None:
        entry = InfolistEntry(name="d", label="D", value=date(2025, 1, 2), type=InfolistEntryType.DATE)
        html = str(InfolistWidget(entries=[entry]).render())
        assert "2025-01-02" in html

    def test_date_string_passthrough(self) -> None:
        entry = InfolistEntry(name="d", label="D", value="soon", type=InfolistEntryType.DATE)
        html = str(InfolistWidget(entries=[entry]).render())
        assert "soon" in html

    def test_image_with_url(self) -> None:
        entry = InfolistEntry(
            name="i", label="I", value="avatar_id", type=InfolistEntryType.IMAGE,
            image_url="/media/a.png",
        )
        el = InfolistWidget(entries=[entry]).render()
        html = str(el)
        assert 'src="/media/a.png"' in html
        assert 'alt="avatar_id"' in html

    def test_image_value_as_src(self) -> None:
        entry = InfolistEntry(name="i", label="I", value="/media/b.png", type=InfolistEntryType.IMAGE)
        html = str(InfolistWidget(entries=[entry]).render())
        assert 'src="/media/b.png"' in html
        assert "max-h-20 rounded" in html

    def test_money_usd(self) -> None:
        entry = InfolistEntry(name="m", label="M", value=1234.5, type=InfolistEntryType.MONEY)
        html = str(InfolistWidget(entries=[entry]).render())
        assert "$1,234.50" in html

    def test_money_euro_and_pound(self) -> None:
        eur = InfolistEntry(name="m", label="M", value=10.5, type=InfolistEntryType.MONEY, currency="EUR")
        gbp = InfolistEntry(name="m", label="M", value=10.5, type=InfolistEntryType.MONEY, currency="GBP")
        assert "\u20ac10.50" in str(InfolistWidget(entries=[eur]).render())
        assert "\u00a310.50" in str(InfolistWidget(entries=[gbp]).render())

    def test_money_unknown_currency(self) -> None:
        entry = InfolistEntry(name="m", label="M", value=5.0, type=InfolistEntryType.MONEY, currency="JPY")
        html = str(InfolistWidget(entries=[entry]).render())
        assert "JPY 5.00" in html

    def test_money_invalid_value_passthrough(self) -> None:
        entry = InfolistEntry(name="m", label="M", value="expensive", type=InfolistEntryType.MONEY)
        html = str(InfolistWidget(entries=[entry]).render())
        assert "expensive" in html

    def test_url_with_override(self) -> None:
        entry = InfolistEntry(name="u", label="U", value="repo", type=InfolistEntryType.URL, url="/repo/1")
        el = InfolistWidget(entries=[entry]).render()
        html = str(el)
        assert 'href="/repo/1"' in html
        assert 'target="_blank"' in html
        assert "underline" in html

    def test_url_value_as_href(self) -> None:
        entry = InfolistEntry(name="u", label="U", value="https://x.dev", type=InfolistEntryType.URL)
        html = str(InfolistWidget(entries=[entry]).render())
        assert 'href="https://x.dev"' in html

    def test_email(self) -> None:
        entry = InfolistEntry(name="e", label="E", value="a@b.c", type=InfolistEntryType.EMAIL)
        html = str(InfolistWidget(entries=[entry]).render())
        assert 'href="mailto:a@b.c"' in html

    def test_text_wraps_non_string(self) -> None:
        html = str(InfolistWidget(entries=[_text("n", 42)]).render())
        assert "42" in html