"""UI components for configuration dashboard."""

from __future__ import annotations

from typing import Any

from lexigram.admin.settings.panel.nodes import ConfigSpec
from lexigram.ui import (
    Card,
    Component,
    FieldSchema,
    Form,
    FormActions,
    NumberInput,
    Select,
    Stack,
    TextInput,
    Toggle,
    el,
)

__all__ = ["ConfigDashboardUI"]


class BooleanField(Component):
    """Toggle with a hidden false input so unchecked states persist."""

    def __init__(
        self,
        name: str,
        value: bool,
        label: str | None = None,
    ) -> None:
        super().__init__()
        self.name = name
        self.value = value
        self.label = label

    def render(self) -> Any:
        return el(
            "div",
            Toggle(
                name=self.name,
                value="true",
                checked=self.value,
                label=self.label,
            ),
            el("input", type="hidden", name=self.name, value="false"),
            class_="flex flex-col",
            id=f"{self.name}-field",
        )


class ConfigDashboardUI:
    """UI helper for configuration dashboard."""

    def render_dashboard(
        self,
        category: str,
        specs: list[ConfigSpec],
        active_ns: str | None,
        active_spec: dict[str, Any] | None,
        values: dict[str, Any],
        state: Any = None,
    ) -> Any:
        """Render the complete dashboard content."""
        return Stack(
            gap=6,
            children=[
                self.render_header(category),
                el(
                    "div",
                    self.render_sidebar(specs, active_ns, category),
                    self.render_main_content(active_spec, values, active_ns)
                    if active_spec and active_ns
                    else self.render_empty_state(),
                    class_="flex flex-col lg:flex-row gap-6 items-start",
                ),
            ],
        )

    def render_header(self, category: str) -> Any:
        """Render dashboard header."""
        title_map = {
            "env": "Environment Variables",
            "admin": "Admin Settings",
            "app": "Application Config",
        }

        return el(
            "div",
            [
                el(
                    "h1",
                    title_map.get(category, "Configuration"),
                    class_="text-3xl font-bold text-foreground",
                ),
                el(
                    "p",
                    "Manage your system configuration and environment settings",
                    class_="text-muted-foreground mt-2",
                ),
            ],
        )

    def render_sidebar(
        self,
        specs: list[ConfigSpec],
        active_ns: str | None,
        category: str,
    ) -> Any:
        """Render specs navigation."""
        nav_items = []
        for spec in specs:
            is_active = spec.namespace == active_ns

            nav_items.append(
                el(
                    "a",
                    [
                        el("i", class_=f"fas fa-{spec.icon} w-5 mr-3 opacity-70")
                        if spec.icon
                        else "",
                        el("span", spec.label or spec.namespace.title()),
                    ],
                    href=f"?ns={spec.namespace}",
                    class_=f"flex items-center px-4 py-3 rounded-lg text-sm font-medium transition-colors {'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400' if is_active else 'text-muted-foreground hover:bg-muted dark:text-muted-foreground dark:hover:bg-card'}",
                ),
            )

        if not nav_items:
            nav_items.append(
                el(
                    "div",
                    "No configurations found.",
                    class_="text-sm text-muted-foreground italic p-4",
                ),
            )

        return el(
            "div",
            el(
                "h3",
                "Namespaces",
                class_="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3 px-2",
            ),
            el("nav", nav_items, class_="space-y-1"),
            class_="w-full lg:w-64 flex-shrink-0",
        )

    def render_main_content(
        self,
        spec: dict[str, Any],
        values: dict[str, Any],
        namespace: str,
    ) -> Any:
        """Render the configuration form."""
        nodes = spec.get("nodes", [])

        fields = []
        for node_data in nodes:
            fields.append(self.render_field(node_data, values))

        return Card(
            title=spec.get("label", "Configuration"),
            children=[
                Form(
                    action_url="?ns=" + namespace,
                    method="POST",
                    hx_target="#config-card",
                    hx_swap="outerHTML",
                    children=[
                        el("input", type="hidden", name="_ns", value=namespace),
                        Stack(gap=4, children=fields),
                        el("div", class_="h-4"),
                        FormActions(submit_label="Save Changes"),
                    ],
                ),
            ],
            class_="flex-1 w-full",
            id="config-card",
        )

    def render_empty_state(self) -> Any:
        """Render the empty state when no namespace is selected."""
        return Card(
            children=[
                el(
                    "div",
                    el("div", "⚙️", class_="text-4xl mb-4"),
                    el(
                        "h3",
                        "Select a Namespace",
                        class_="text-lg font-medium text-foreground",
                    ),
                    el(
                        "p",
                        "Choose a configuration namespace from the sidebar to edit settings.",
                        class_="text-muted-foreground mt-2",
                    ),
                    class_="text-center py-12",
                ),
            ],
            class_="flex-1 w-full",
        )

    def render_config_form(
        self,
        spec: dict[str, Any],
        values: dict[str, Any],
        action: str,
        csrf_token: str | None = None,
    ) -> Any:
        """Render a standalone configuration form for use within ConfigLayout.

        Args:
            spec: Configuration spec dictionary with nodes
            values: Current values for the spec
            action: Form action URL
            csrf_token: Optional CSRF token rendered as a hidden input

        Returns:
            Card component containing the configuration form
        """
        nodes = spec.get("nodes", [])
        namespace = spec.get("namespace", "")

        fields = []
        for node_data in nodes:
            fields.append(self.render_field(node_data, values))

        hidden = []
        if csrf_token:
            hidden.append(
                el("input", type="hidden", name="csrf_token", value=csrf_token)
            )
        hidden.append(el("input", type="hidden", name="_ns", value=namespace))

        return Card(
            title=spec.get("label", "Configuration"),
            subtitle=spec.get("description", ""),
            children=[
                Form(
                    action_url=action,
                    method="POST",
                    hx_target="#config-card",
                    hx_swap="outerHTML",
                    children=[
                        *hidden,
                        el("div", *fields, class_="space-y-4"),
                        el("div", class_="h-4"),
                        FormActions(submit_label="Save Changes"),
                    ],
                ),
            ],
            class_="w-full",
            id="config-card",
        )

    def render_field(self, node: dict[str, Any], values: dict[str, Any]) -> Any:
        """Render a single configuration field based on its type."""
        name = node["name"]
        value = values.get(name, node["default"])
        label = node["label"]
        help_text = node["help_text"]
        node_type = node["type"]
        readonly = node["readonly"]
        options = node.get("options", [])

        # Decide input component based on type
        input_comp: Any = None

        if node_type == "boolean":
            input_comp = BooleanField(
                name=name,
                value=bool(value),
                label=label,
            )
        elif node_type == "int":
            input_comp = NumberInput(name=name, value=value, disabled=readonly)
        elif node_type == "enum":
            # Normalize options to list of (value, label) tuples if needed
            choices = []
            if isinstance(options, dict):
                choices = list(options.items())
            else:
                choices = [(str(o), str(o)) for o in options]

            input_comp = Select(
                name=name,
                choices=choices,
                value=str(value) if value is not None else "",
                disabled=readonly,
            )
        elif node_type == "secret":
            has_value = bool(value)
            presence_note = "(currently set)" if has_value else "(not set)"
            help_text = f"{help_text} {presence_note}" if help_text else presence_note
            input_comp = TextInput(
                name=name,
                value="",
                input_type="password",
                placeholder="••••••••" if has_value else "",
                disabled=readonly,
            )
        elif node_type == "color":
            input_comp = TextInput(
                name=name,
                value=str(value) if value is not None else "",
                input_type="color",
                disabled=readonly,
            )
        else:  # string and others
            input_comp = TextInput(
                name=name,
                value=str(value) if value is not None else "",
                disabled=readonly,
            )

        return FieldSchema(
            input_component=input_comp,
            label=label if node_type != "boolean" else None,
            help_text=help_text,
            class_="mb-0",
        )
