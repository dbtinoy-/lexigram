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
from lexigram.ui.molecules.alert import Alert
from lexigram.ui.molecules.card import Card
from lexigram.ui.molecules.dropdown import Dropdown
from lexigram.ui.molecules.modal import Modal
from lexigram.ui.molecules.pagination import Pagination
from lexigram.ui.molecules.tabs import Tabs
from lexigram.ui.molecules.toast import InlineToast
from lexigram.ui.organisms.forms import Form
from lexigram.ui.organisms.slide_over import SlideOver
from lexigram.ui.styles.theme import shadcn_css


def build_gallery() -> dict[str, str]:
    """Return {component_name: full HTML page} for every component."""
    panels: list[tuple[str, object]] = [
        ("Alert", Alert("Operation complete")),
        ("Badge", Badge("New")),
        ("Button", Button("Save")),
        ("Card", Card(title="Card title", content="Card body content")),
        ("Checkbox", Checkbox(name="agree", label="Agree")),
        ("Divider", Divider()),
        ("Dropdown", Dropdown("Menu", items=["Item 1", "Item 2"])),
        ("Fieldset", Fieldset(TextInput(name="username"), legend="Account")),
        ("Form", Form(children=[TextInput(name="field")], action_url="/save")),
        ("Icon", Icon(name="check")),
        ("InlineToast", InlineToast("Saved successfully")),
        ("Label", Label("Name")),
        ("Layout", Row(Col("Cell A"), Col("Cell B"))),
        ("Link", Link("Home", href="/")),
        ("Modal", Modal(title="Dialog", trigger="Open", is_open=True, footer=[Button("Close", size="sm")])),
        ("NumberInput", NumberInput(name="count")),
        ("Pagination", Pagination(page=1, total=45, per_page=20)),
        ("PasswordInput", PasswordInput(name="pw")),
        ("ProgressBar", ProgressBar(value=60)),
        ("Radio", Radio(name="r", choices=[("a", "Alpha"), ("b", "Beta")])),
        ("Select", Select(name="s", choices=[("a", "Alpha"), ("b", "Beta")])),
        ("Skeleton", Skeleton()),
        ("SlideOver", SlideOver(title="Panel", trigger="Open", is_open=True)),
        ("Spinner", Spinner()),
        ("Switch", Switch("Toggle setting", name="toggle")),
        ("Tabs", Tabs([("Overview", "overview"), ("Details", "details")], active_tab="overview")),
        ("TextArea", TextArea(name="notes")),
        ("TextInput", TextInput(name="name")),
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
<script defer src="https://cdn.jsdelivr.net/npm/@alpinejs/focus@3.14.0/dist/cdn.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.0/dist/cdn.min.js"></script>
<style>
{shadcn_css()}
body {{ font-family: var(--font-sans); margin: 2rem; background: var(--background); color: var(--foreground); }}
</style>
</head>
<body>
{render_to_string(component)}
</body>
</html>"""