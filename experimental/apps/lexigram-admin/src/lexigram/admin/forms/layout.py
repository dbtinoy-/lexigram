"""Unified Form Layout System.
Combines schema definitions with rendering logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from lexigram.ui import Col as AtomCol
from lexigram.ui import Row as AtomRow
from lexigram.ui import el

if TYPE_CHECKING:
    from lexigram.admin.forms.components import FormBase


@dataclass
class AbstractLayoutNode(ABC):
    """Base class for all layout elements."""

    id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    visible_when: str | None = None

    @abstractmethod
    def render(self, form: FormBase) -> Any:
        """Render the node given a bound form instance."""


@dataclass
class FieldNode(AbstractLayoutNode):
    """Represents a single field in the layout."""

    field_name: str = ""
    props: dict[str, Any] = field(default_factory=dict)

    def render(self, form: FormBase) -> Any:
        try:
            field = form.fields[self.field_name]
            value = self.props.get("value")
            if value is None and hasattr(form, "values"):
                value = form.values.get(self.field_name)
            errors = self.props.get("errors")
            if errors is None and hasattr(form, "errors"):
                errors = form.errors.get(self.field_name)
            rendered = field.render_form(value, errors=errors)
            if self.visible_when:
                return el(
                    "div", rendered, **{"x-show": self.visible_when, "x-cloak": True}
                )
            return rendered
        except KeyError:
            return el(
                "div",
                f"Error: Field '{self.field_name}' not found",
                class_="text-destructive",
            )


@dataclass
class Section(AbstractLayoutNode):
    """A visual grouping of fields with a title and description."""

    title: str | None = None
    description: str | None = None
    children: list[Section | FieldNode | Grid | Tabs | Column] = field(
        default_factory=list,
    )
    columns: int = 1

    def render(self, form: FormBase) -> Any:
        content = [child.render(form) for child in self.children]
        header = []
        if self.title:
            header.append(
                el(
                    "h3",
                    self.title,
                    class_="text-lg font-medium text-foreground",
                ),
            )
        if self.description:
            header.append(
                el(
                    "p",
                    self.description,
                    class_="mt-1 text-sm text-muted-foreground",
                ),
            )

        header_el = (
            el(
                "div",
                *header,
                class_="mb-4 pb-2 border-b border-border",
            )
            if header
            else ""
        )

        return_el = el(
            "div",
            header_el,
            el(
                "div",
                *content,
                class_=f"grid grid-cols-1 md:grid-cols-{self.columns} gap-4",
            ),
            class_="bg-muted dark:bg-card/50 p-4 rounded-lg border border-border",
        )
        if self.visible_when:
            return el(
                "div", return_el, **{"x-show": self.visible_when, "x-cloak": True}
            )
        return return_el


@dataclass
class Grid(AbstractLayoutNode):
    """A multi-column layout container (Row)."""

    columns: int = 2
    children: list[Section | FieldNode | Grid | Tabs | Column] = field(
        default_factory=list,
    )

    def render(self, form: FormBase) -> Any:
        rendered_children = [child.render(form) for child in self.children]
        return AtomRow(*rendered_children, cols=self.columns, gap=4)


@dataclass
class Column(AbstractLayoutNode):
    """A vertical column (Col) in a Grid/Row."""

    span: int | None = None
    children: list[Section | FieldNode | Grid | Tabs] = field(default_factory=list)

    def render(self, form: FormBase) -> Any:
        rendered_children = [child.render(form) for child in self.children]
        return AtomCol(*rendered_children, span=self.span, gap=4)


@dataclass
class Tab(AbstractLayoutNode):
    """A single tab in a Tabs container."""

    label: str = ""
    icon: str | None = None
    children: list[Section | FieldNode | Grid | Tabs | Column] = field(
        default_factory=list,
    )

    def render(self, form: FormBase) -> Any:
        content = [child.render(form) for child in self.children]
        return el("div", *content, class_="space-y-4")


@dataclass
class Tabs(AbstractLayoutNode):
    """A container for multiple tabs."""

    tabs: list[Tab] = field(default_factory=list)

    def render(self, form: FormBase) -> Any:
        tab_headers = [
            el("button", tab.label, class_="px-4 py-2 border-b-2") for tab in self.tabs
        ]
        tab_contents = [tab.render(form) for tab in self.tabs]
        return el(
            "div",
            el("div", *tab_headers, class_="flex space-x-4 border-b"),
            *tab_contents,
        )


class FormLayoutBuilder:
    """Fluent API for building form layouts."""

    def __init__(self) -> None:
        self._children: list[Any] = []

    @classmethod
    def create(cls) -> FormLayoutBuilder:
        return cls()

    def section(
        self,
        title: str,
        fields: list[str],
        description: str | None = None,
        columns: int = 1,
    ) -> FormLayoutBuilder:
        child_nodes = [FieldNode(field_name=f) for f in fields]
        self._children.append(
            Section(
                title=title,
                description=description,
                children=child_nodes,  # type: ignore[arg-type]
                columns=columns,
            ),
        )
        return self

    def grid(self, columns: int, children: list[Any]) -> FormLayoutBuilder:
        nodes = [FieldNode(field_name=c) if isinstance(c, str) else c for c in children]
        self._children.append(Grid(columns=columns, children=nodes))
        return self

    def tabs(self, tabs_config: dict[str, list[str]]) -> FormLayoutBuilder:
        """Add a tabs section."""
        tab_nodes = []
        for label, fields in tabs_config.items():
            children = [FieldNode(field_name=f) for f in fields]
            tab_nodes.append(Tab(label=label, children=children))  # type: ignore[arg-type]
        self._children.append(Tabs(tabs=tab_nodes))
        return self

    def build(self) -> list[AbstractLayoutNode]:
        return self._children


@dataclass
class FormLayout:
    """Schema definition for form layout."""

    sections: list[dict[str, Any]] = field(default_factory=list)
