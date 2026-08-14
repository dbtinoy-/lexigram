"""Component gallery: renders every lexigram-ui component as HTML pages.

The gallery is the substrate for axe-core accessibility scans (Phase 1 of
the professional-grade plan). Each component is rendered through
``render_to_string`` and wrapped in a full document with the real design
tokens injected via ``shadcn_css`` so axe can measure computed contrast,
focus styles, and semantic structure.
"""

from __future__ import annotations

from lexigram.ui.atoms.badge import Badge
from lexigram.ui.atoms.button import Button
from lexigram.ui.atoms.divider import Divider
from lexigram.ui.atoms.fieldset import Fieldset
from lexigram.ui.atoms.icon import Icon
from lexigram.ui.atoms.inputs import (
    Checkbox,
    NumberInput,
    PasswordInput,
    Radio,
    Select,
    TextArea,
    TextInput,
)
from lexigram.ui.atoms.label import Label
from lexigram.ui.atoms.layout import Col, Row
from lexigram.ui.atoms.link import Link
from lexigram.ui.atoms.progress_bar import ProgressBar
from lexigram.ui.atoms.skeleton import Skeleton
from lexigram.ui.atoms.spinner import Spinner
from lexigram.ui.atoms.switch import Switch
from lexigram.ui.atoms.tooltip import Tooltip
from lexigram.ui.charts import BarChart, LineChart, MiniBar, PieChart, Sparkline
from lexigram.ui.charts.types import ChartDataPoint
from lexigram.ui.molecules.alert import Alert
from lexigram.ui.molecules.card import Card
from lexigram.ui.molecules.dropdown import Dropdown
from lexigram.ui.molecules.modal import Modal
from lexigram.ui.molecules.pagination import Pagination
from lexigram.ui.molecules.tabs import TabPanel, Tabs
from lexigram.ui.molecules.toast import InlineToast
from lexigram.ui.organisms.forms import Form
from lexigram.ui.organisms.slide_over import SlideOver
from lexigram.ui.styles.theme import shadcn_css


def build_gallery() -> dict[str, str]:
    """Return {component_name: full HTML page} for every component."""
    panels: list[tuple[str, object]] = [
        ("Alert", Alert("Operation complete")),
        ("Badge", Badge("New")),
        (
            "BarChart",
            BarChart(
                [
                    ChartDataPoint("Jan", 42, "chart-1"),
                    ChartDataPoint("Feb", 68, "chart-2"),
                    ChartDataPoint("Mar", 33, "chart-3"),
                ]
            ),
        ),
        ("Button", Button("Save")),
        ("Card", Card(title="Card title", content="Card body content")),
        ("Checkbox", Checkbox(name="agree", label="Agree")),
        ("Divider", Divider()),
        ("Dropdown", Dropdown("Menu", items=["Item 1", "Item 2"])),
        (
            "Fieldset",
            Fieldset(TextInput(name="username", label="Username"), legend="Account"),
        ),
        (
            "Form",
            Form(children=[TextInput(name="field", label="Field")], action_url="/save"),
        ),
        ("Icon", Icon(name="check")),
        ("InlineToast", InlineToast("Saved successfully")),
        ("Label", Label("Name")),
        ("Layout", Row(Col("Cell A"), Col("Cell B"))),
        (
            "LineChart",
            LineChart(
                [
                    ChartDataPoint("Jan", 42, "chart-1"),
                    ChartDataPoint("Feb", 68, "chart-2"),
                    ChartDataPoint("Mar", 33, "chart-3"),
                ]
            ),
        ),
        ("Link", Link("Home", href="/")),
        (
            "Modal",
            Modal(
                title="Dialog",
                trigger="Open",
                is_open=True,
                footer=[Button("Close", size="sm")],
            ),
        ),
        ("NumberInput", NumberInput(name="count", label="Count")),
        ("Pagination", Pagination(page=1, total=45, per_page=20)),
        ("PasswordInput", PasswordInput(name="pw", label="Password")),
        (
            "PieChart",
            PieChart(
                [
                    ChartDataPoint("Alpha", 30, "chart-1"),
                    ChartDataPoint("Beta", 50, "chart-2"),
                    ChartDataPoint("Gamma", 20, "chart-3"),
                ]
            ),
        ),
        ("ProgressBar", ProgressBar(value=60)),
        ("Radio", Radio(name="r", choices=[("a", "Alpha"), ("b", "Beta")])),
        (
            "Select",
            Select(
                name="s", label="Choose one", choices=[("a", "Alpha"), ("b", "Beta")]
            ),
        ),
        ("Skeleton", Skeleton()),
        ("SlideOver", SlideOver(title="Panel", trigger="Open", is_open=True)),
        (
            "Sparkline",
            Sparkline(
                [
                    ChartDataPoint("P1", 10, "chart-1"),
                    ChartDataPoint("P2", 25, "chart-2"),
                    ChartDataPoint("P3", 18, "chart-3"),
                ]
            ),
        ),
        ("Spinner", Spinner()),
        ("Switch", Switch("Toggle setting", name="toggle")),
        (
            "Tabs",
            Tabs(
                [("Overview", "overview"), ("Details", "details")],
                active_tab="overview",
                children=[
                    TabPanel("overview", "Overview content"),
                    TabPanel("details", "Details content"),
                ],
            ),
        ),
        ("TextArea", TextArea(name="notes", label="Notes")),
        ("TextInput", TextInput(name="name", label="Name")),
        ("Tooltip", Tooltip("More info here")),
    ]

    pages: dict[str, str] = {}
    for name, component in panels:
        pages[name] = render_page(component)
    return pages


def render_page(component: object) -> str:
    """Wrap a rendered component in a full HTML document with design tokens."""
    from lexigram.ui.core.base import render_to_string

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Component: {type(component).__name__}</title>
<script src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.4/dist/htmx.min.js"></script>
<script src="https://cdn.tailwindcss.com"></script>
<script>tailwind.config = {{ darkMode: 'class' }}</script>
<script defer src="https://cdn.jsdelivr.net/npm/@alpinejs/focus@3.14.0/dist/cdn.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.0/dist/cdn.min.js"></script>
<style>
{shadcn_css()}
:root {{ color-scheme: light; }}
.dark {{ color-scheme: dark; }}
[x-cloak] {{ display: none !important; }}
body {{ font-family: var(--font-sans); margin: 2rem; background: var(--background); color: var(--foreground); }}
</style>
</head>
<body>
{render_to_string(component)}
</body>
</html>"""
