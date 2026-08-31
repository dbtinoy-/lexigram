"""UI components for the configuration dashboard."""

from __future__ import annotations

import re
from typing import Any

from lexigram.admin.settings.panel.nodes import ConfigSpec
from lexigram.ui import (
    Badge,
    Card,
    Component,
    FieldSchema,
    Form,
    FormActions,
    NumberInput,
    Select,
    Stack,
    TextArea,
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
        disabled: bool = False,
        required: bool = False,
        error: str | None = None,
    ) -> None:
        super().__init__()
        self.name = name
        self.value = value
        self.label = label
        self.disabled = disabled
        self.required = required
        self.error = error

    def render(self) -> Any:
        return el(
            "div",
            Toggle(
                name=self.name,
                value="true",
                checked=self.value,
                label=self.label,
                disabled=self.disabled,
                required=self.required,
                error=self.error,
            ),
            # Disabled controls are not submitted. The controller also
            # normalizes missing booleans, but keep the fallback for normal
            # editable toggles where it is useful.
            el("input", type="hidden", name=self.name, value="false")
            if not self.disabled
            else "",
            class_="flex flex-col",
            id=f"{self.name}-field",
        )


class ConfigDashboardUI:
    """UI helper for the registry-backed configuration dashboard."""

    @staticmethod
    def _form_id(namespace: str) -> str:
        """Return a stable, safe DOM id for a settings form."""
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", namespace).strip("-") or "settings"
        return f"settings-form-{slug}"

    @staticmethod
    def _source_label(store_name: str) -> str:
        """Return a human-readable persistence source label."""
        return {
            "env": "Environment",
            "db": "Database",
            "default": "Application memory",
        }.get(store_name, store_name.replace("_", " ").title())

    def render_dashboard(
        self,
        category: str,
        specs: list[ConfigSpec],
        active_ns: str | None,
        active_spec: dict[str, Any] | None,
        values: dict[str, Any],
        state: Any = None,
        action: str | None = None,
        csrf_token: str | None = None,
    ) -> Any:
        """Render the legacy complete dashboard content.

        The spec-route controller uses :meth:`render_config_form` directly.
        This compatibility helper remains available for older integrations,
        but delegates its active form to the same renderer so it cannot drift
        into a second field, CSRF, or action-bar contract. Callers rendering a
        writable dashboard should provide the request-aware ``action`` and
        ``csrf_token`` values.
        """
        return Stack(
            gap=6,
            children=[
                self.render_header(category),
                el(
                    "div",
                    self.render_sidebar(specs, active_ns, category),
                    (
                        self.render_main_content(
                            active_spec,
                            values,
                            active_ns,
                            action=action,
                            csrf_token=csrf_token,
                        )
                        if active_spec and active_ns
                        else self.render_empty_state()
                    ),
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
        """Render specs navigation for the legacy dashboard."""
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
                    aria_current="page" if is_active else None,
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
            el(
                "nav",
                nav_items,
                aria_label="Configuration namespaces",
                class_="space-y-1",
            ),
            class_="w-full lg:w-64 flex-shrink-0",
        )

    def render_main_content(
        self,
        spec: dict[str, Any],
        values: dict[str, Any],
        namespace: str,
        *,
        action: str | None = None,
        csrf_token: str | None = None,
    ) -> Any:
        """Render the legacy dashboard form through the canonical renderer.

        ``render_config_form`` is intentionally generic: settings share field,
        validation, and action semantics with resource forms, but do not need
        a resource model or CRUD assumptions. Keeping this adapter thin also
        makes the legacy dashboard safe to remove once downstream users have
        migrated to the spec-route controller.
        """
        spec_data = spec.to_dict() if hasattr(spec, "to_dict") else dict(spec)
        spec_data.setdefault("namespace", namespace)
        return self.render_config_form(
            spec=spec_data,
            values=values,
            action=action or f"?ns={namespace}",
            csrf_token=csrf_token,
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
        errors: dict[str, str] | None = None,
        value_metadata: dict[str, dict[str, Any]] | None = None,
        revision: str | None = None,
    ) -> Any:
        """Render a standalone configuration form.

        ``values`` may contain the submitted values after a validation error;
        this is deliberate so the form never replaces a user's typo with a
        default before they have had a chance to correct it.
        """
        errors = errors or {}
        value_metadata = value_metadata or {}
        nodes = spec.get("nodes", [])
        namespace = spec.get("namespace", "")
        can_edit = bool(spec.get("can_edit", True))
        fields = [
            self.render_field(
                {**node, "readonly": node.get("readonly", False) or not can_edit},
                values,
                errors,
                value_metadata=value_metadata.get(node.get("name", "")),
            )
            for node in nodes
        ]
        editable = can_edit and any(not node.get("readonly", False) for node in nodes)

        scope_label = "Tenant scoped" if spec.get("scope") == "tenant" else "Global"
        source_label = self._source_label(spec.get("store_name", "default"))
        runtime_status = spec.get("runtime_status", "active")
        runtime_labels = {
            "active": "Active at runtime",
            "restart_required": "Restart required",
            "dormant": "Stored, not active",
        }
        runtime_label = runtime_labels.get(runtime_status, "Runtime status unknown")
        metadata = el(
            "div",
            Badge(scope_label, variant="gray"),
            Badge(f"Source: {source_label}", variant="gray"),
            # The runtime badge reports live state, so it is the one chip
            # here that should be announced when it changes.
            Badge(
                runtime_label,
                variant="gray" if runtime_status == "active" else "warning",
                live=True,
            ),
            class_="flex flex-wrap gap-2 mb-5",
        )

        form_level_error = errors.get("__all__")
        body: list[Any] = [
            el(
                "p",
                spec.get("description", ""),
                class_="mb-5 text-sm text-muted-foreground",
            )
            if spec.get("description")
            else "",
            metadata,
            (
                el(
                    "div",
                    form_level_error,
                    role="alert",
                    # Machine-readable marker so the shared form behavior
                    # layer can tell a recoverable 200 error fragment from a
                    # successful save and avoid announcing "Form saved."
                    **{"data-admin-form-error": "true"},
                    class_="mb-5 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive",
                )
                if form_level_error
                else ""
            ),
        ]
        runtime_messages = {
            "restart_required": (
                "Changes require a service restart before they take effect."
            ),
            "dormant": (
                "These values are stored for future use but are not currently applied."
            ),
        }
        if runtime_status in runtime_messages:
            body.append(
                el(
                    "div",
                    el("strong", f"{runtime_label}. "),
                    runtime_messages[runtime_status],
                    role="status",
                    class_="mb-5 rounded-lg border border-warning/30 bg-warning/10 px-4 py-3 text-sm text-warning",
                )
            )

        hidden = []
        if csrf_token:
            hidden.append(
                el("input", type="hidden", name="csrf_token", value=csrf_token)
            )
        if revision:
            hidden.append(
                el(
                    "input",
                    type="hidden",
                    name="settings_revision",
                    value=revision,
                )
            )
        hidden.append(el("input", type="hidden", name="_ns", value=namespace))

        if editable:
            form_id = self._form_id(namespace)
            actions = el(
                "div",
                el(
                    "button",
                    "Reset form",
                    type="reset",
                    class_="inline-flex items-center rounded-md border border-border bg-card px-4 py-2 text-sm font-medium text-foreground shadow-sm hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                ),
                FormActions(primary_text="Save changes", secondary_text=None),
                **{"data-admin-form-actions": "true"},
                class_="sticky bottom-3 z-10 mt-6 flex items-center justify-between gap-3 rounded-lg border border-border bg-card/95 p-2 shadow-lg backdrop-blur",
            )
            body.append(
                Form(
                    action_url=action,
                    method="POST",
                    submit_label="",
                    form_id=form_id,
                    form_attrs={
                        "data-admin-form": "true",
                        # Keep the settings marker for consumers that still
                        # target settings-specific forms during migration.
                        "data-settings-form": "true",
                        "data-settings-namespace": namespace,
                    },
                    hx_target="#config-card",
                    hx_swap="outerHTML",
                    children=[
                        *hidden,
                        el("div", *fields, class_="space-y-4"),
                        el(
                            "p",
                            "",
                            id=f"{form_id}-status",
                            # Emit explicit "true" values so the marker
                            # contract matches data-admin-form and the
                            # documented [data-admin-form-status="true"]
                            # selector, not just attribute presence.
                            **{
                                "data-admin-form-status": "true",
                                "data-settings-status": "true",
                            },
                            aria_live="polite",
                            class_="sr-only",
                        ),
                        actions,
                    ],
                )
            )
        else:
            body.extend(
                [
                    el("div", *fields, class_="space-y-4"),
                    el(
                        "p",
                        (
                            "You have view-only access to these settings."
                            if not can_edit
                            else "These values are read-only and managed by the deployment environment."
                        ),
                        role="status",
                        class_="mt-6 rounded-lg bg-muted px-4 py-3 text-sm text-muted-foreground",
                    ),
                ]
            )

        return Card(
            title=spec.get("label", "Configuration"),
            children=body,
            class_="w-full",
            id="config-card",
        )

    def render_field(
        self,
        node: dict[str, Any],
        values: dict[str, Any],
        errors: dict[str, str] | None = None,
        *,
        value_metadata: dict[str, Any] | None = None,
    ) -> Any:
        """Render a single configuration field based on its type."""
        errors = errors or {}
        name = node["name"]
        value = values.get(name, node.get("default"))
        label = node.get("label") or name.replace("_", " ").title()
        help_text = node.get("help_text")
        node_type = node.get("type", "string")
        readonly = bool(node.get("readonly", False))
        required = bool(node.get("required", False))
        options = node.get("options", [])

        if readonly:
            readonly_note = "Read-only value."
            help_text = f"{help_text} {readonly_note}" if help_text else readonly_note

        if node_type == "boolean":
            input_comp: Any = BooleanField(
                name=name,
                value=bool(value),
                label=label,
                disabled=readonly,
                required=required,
                error=errors.get(name),
            )
        elif node_type == "int":
            input_comp = NumberInput(
                name=name,
                value=value,
                min_value=node.get("min"),
                max_value=node.get("max"),
                step=1,
                disabled=readonly,
                required=required,
            )
        elif node_type == "enum":
            choices = (
                list(options.items())
                if isinstance(options, dict)
                else [(str(option), str(option)) for option in options]
            )
            input_comp = Select(
                name=name,
                choices=choices,
                value=str(value) if value is not None else "",
                disabled=readonly,
                required=required,
            )
        elif node_type == "secret":
            has_value = bool(value)
            presence_note = (
                "(currently set; leave blank to keep it)" if has_value else "(not set)"
            )
            help_text = f"{help_text} {presence_note}" if help_text else presence_note
            input_comp = TextInput(
                name=name,
                value="",
                input_type="password",
                placeholder="••••••••" if has_value else "",
                disabled=readonly,
                required=required and not has_value,
                autocomplete="new-password",
            )
        elif node_type == "color":
            input_comp = TextInput(
                name=name,
                value=str(value) if value is not None else "",
                input_type="color",
                disabled=readonly,
                required=required,
            )
        elif node.get("extra", {}).get("multiline") or name in {"csp", "description"}:
            input_comp = TextArea(
                name=name,
                value=str(value) if value is not None else "",
                rows=7 if name == "csp" else 4,
                disabled=readonly,
                required=required,
            )
        else:
            input_type = "url" if name.endswith("_url") else "text"
            input_comp = TextInput(
                name=name,
                value=str(value) if value is not None else "",
                input_type=input_type,
                disabled=readonly,
                required=required,
            )

        origin_label = (value_metadata or {}).get("source_label")
        hint_parts = ["Read only"] if readonly else []
        if origin_label:
            hint_parts.append(str(origin_label))

        return FieldSchema(
            input_component=input_comp,
            label=label if node_type != "boolean" else None,
            help_text=help_text,
            error=errors.get(name),
            required=required,
            hint=" · ".join(hint_parts) if hint_parts else None,
            class_="mb-0",
        )
