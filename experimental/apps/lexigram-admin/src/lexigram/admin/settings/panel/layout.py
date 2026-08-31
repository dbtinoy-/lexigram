"""Configuration Center layout component.

This is a nested layout that renders inside the admin shell's #main-content.
It provides a secondary sidebar for configuration categories while the main
admin chrome (topbar, primary sidebar) remains intact.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ui import Card, Component, el, raw

if TYPE_CHECKING:
    from lexigram.admin.settings.panel.types import ConfigCategory

__all__ = ["ConfigLayout"]


class ConfigLayout(Component):
    """Two-column layout for Configuration Center.

    Renders a secondary sidebar with category groups and a main content area
    for the active configuration form. Designed to be placed inside the admin
    shell's main content area.

    Example:
        ```python
        layout = ConfigLayout(
            categories=categories,
            active_category="env",
            active_namespace="system.core",
            content=form_component,
        )
        return await self.render_admin(request, layout, title="Configuration")
        ```
    """

    def __init__(
        self,
        categories: list[ConfigCategory],
        active_category: str | None = None,
        active_namespace: str | None = None,
        content: Any = None,
        title: str = "Configuration",
        admin_prefix: str = "/admin",
        **props,
    ) -> None:
        super().__init__(**props)
        self.categories = categories
        self.active_category = active_category
        self.active_namespace = active_namespace
        self.content = content
        self.title = title
        self.admin_prefix = admin_prefix.rstrip("/") or "/admin"

    def render(self) -> Any:
        """Render the full two-column configuration layout."""
        return el(
            "div",
            self._render_header(),
            el(
                "div",
                self._render_sidebar(),
                self._render_main(),
                class_="flex flex-col md:flex-row gap-6",
            ),
            raw(self._settings_form_script()),
        )

    def _render_header(self) -> Any:
        """Render page header with title and description."""
        return el(
            "div",
            el(
                "h1",
                self.title,
                class_="text-2xl font-bold text-foreground",
            ),
            el(
                "p",
                "Manage system configuration, environment variables, and application settings.",
                class_="text-muted-foreground mt-1",
            ),
            class_="mb-2",
        )

    def _render_sidebar(self) -> Any:
        """Render the category navigation sidebar."""
        groups = []

        for category in sorted(self.categories, key=lambda c: c.order):
            is_active_category = category.name == self.active_category

            # Category header
            header = el(
                "div",
                self._render_icon(category.icon),
                el("span", category.label, class_="font-medium"),
                class_=f"flex items-center gap-2 px-3 py-2 text-sm {'text-primary-700 dark:text-primary-400' if is_active_category else 'text-muted-foreground dark:text-muted-foreground'}",
            )

            # Spec links within category
            spec_links = []
            for spec in category.specs:
                is_active_spec = spec.namespace == self.active_namespace

                spec_links.append(
                    el(
                        "a",
                        el("span", spec.label or spec.namespace, class_="truncate"),
                        href=f"{self.admin_prefix}/settings/{spec.namespace}",
                        hx_get=f"{self.admin_prefix}/settings/{spec.namespace}",
                        hx_target="#main-content",
                        hx_swap="innerHTML",
                        hx_push_url="true",
                        data_settings_nav=True,
                        aria_current="page" if is_active_spec else None,
                        class_=f"block px-3 py-2 pl-9 text-sm rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring {'bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400 font-medium' if is_active_spec else 'text-muted-foreground hover:bg-muted dark:text-muted-foreground dark:hover:bg-card'}",
                    ),
                )

            # Category group
            groups.append(
                el(
                    "div",
                    header,
                    el("div", *spec_links, class_="space-y-1")
                    if spec_links
                    else el(
                        "div",
                        "No configurations",
                        class_="px-3 py-2 pl-9 text-xs text-muted-foreground italic",
                    ),
                    class_="mb-4",
                ),
            )

        return el(
            "nav",
            *groups,
            class_="w-full md:w-64 flex-shrink-0",
            aria_label="Configuration categories",
        )

    def _render_main(self) -> Any:
        """Render the main content area."""
        if self.content:
            return el(
                "div",
                el("div", self.content, class_="p-6"),
                class_="flex-1 min-w-0",
            )

        # Empty state
        return Card(
            children=[
                el(
                    "div",
                    el("div", "⚙️", class_="text-5xl mb-4"),
                    el(
                        "h3",
                        "Select a Configuration",
                        class_="text-lg font-semibold text-foreground",
                    ),
                    el(
                        "p",
                        "Choose a configuration from the sidebar to view and edit settings.",
                        class_="text-muted-foreground mt-2 max-w-sm",
                    ),
                    class_="text-center py-16",
                ),
            ],
            class_="flex-1",
        )

    @staticmethod
    def _settings_form_script() -> str:
        """Return delegated UX behavior for settings forms and navigation."""
        return """
        <script>
        (function () {
            if (window.__lexigramSettingsFormInit) return;
            window.__lexigramSettingsFormInit = true;

            function settingsForm(target) {
                return target && target.closest
                    ? target.closest('form[data-settings-form]')
                    : null;
            }

            function hasDirtySettingsForm() {
                return Array.prototype.some.call(
                    document.querySelectorAll('form[data-settings-form]'),
                    function (form) { return form.dataset.dirty === 'true'; }
                );
            }

            function setFormStatus(form, message) {
                var status = form.querySelector('[data-settings-status]');
                if (status) status.textContent = message;
            }

            document.addEventListener('input', function (event) {
                var form = settingsForm(event.target);
                if (form) form.dataset.dirty = 'true';
            });

            document.addEventListener('change', function (event) {
                var form = settingsForm(event.target);
                if (form) form.dataset.dirty = 'true';
            });

            document.addEventListener('submit', function (event) {
                var form = settingsForm(event.target);
                if (!form) return;
                if (form.dataset.submitting === 'true') {
                    event.preventDefault();
                    return;
                }
                form.dataset.submitting = 'true';
                form.dataset.dirty = 'false';
                var button = form.querySelector('button[type="submit"]');
                if (button) {
                    button.dataset.settingsOriginalText = button.textContent;
                    button.disabled = true;
                    button.setAttribute('aria-disabled', 'true');
                    button.textContent = 'Saving…';
                }
                setFormStatus(form, 'Saving settings.');
            }, true);

            document.body.addEventListener('htmx:afterRequest', function (event) {
                var form = settingsForm(event.detail && event.detail.elt);
                if (!form || event.detail.successful) return;
                form.dataset.submitting = 'false';
                form.dataset.dirty = 'true';
                var button = form.querySelector('button[type="submit"]');
                if (button) {
                    button.disabled = false;
                    button.removeAttribute('aria-disabled');
                    button.textContent = button.dataset.settingsOriginalText || 'Save changes';
                }
                setFormStatus(form, 'Settings were not saved. Review the errors and try again.');
            });

            document.addEventListener('click', function (event) {
                var link = event.target instanceof Element
                    ? event.target.closest('[data-settings-nav]')
                    : null;
                if (!link || !hasDirtySettingsForm()) return;
                if (!window.confirm('You have unsaved settings changes. Leave without saving?')) {
                    event.preventDefault();
                    event.stopImmediatePropagation();
                }
            }, true);

            window.addEventListener('beforeunload', function (event) {
                if (!hasDirtySettingsForm()) return;
                event.preventDefault();
                event.returnValue = '';
            });
        }());
        </script>
        """

    def _render_icon(self, icon_name: str) -> Any:
        """Render an icon by name."""
        try:
            from lexigram.ui import get_icon

            return get_icon(icon_name, class_name="w-5 h-5 opacity-70")
        except (ImportError, ModuleNotFoundError, AttributeError):
            return el("span", "●", class_="text-muted-foreground")
