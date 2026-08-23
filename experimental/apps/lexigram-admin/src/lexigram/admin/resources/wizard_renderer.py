"""Multi-step Alpine.js wizard form rendering for admin resources."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from starlette.responses import HTMLResponse

from lexigram.admin.exceptions import AdminValidationError
from lexigram.admin.state.context import wants_fragment
from lexigram.logging import get_logger
from lexigram.ui import el, render_to_string

logger = get_logger(__name__)

if TYPE_CHECKING:
    from lexigram.admin.config import AdminConfig
    from lexigram.admin.engine.renderer import AdminRenderer


class WizardRendererMixin:
    """Renders multi-step wizard forms; composed into ``FormRenderer``."""

    resource_name: str
    _config: AdminConfig
    _renderer: AdminRenderer
    _create_field_component: Any

    async def render_wizard(
        self,
        request: Any,
        resource: Any,
        steps: list[dict],
        action_url: str,
        submit_label: str = "Submit",
    ) -> HTMLResponse:
        """Render a multi-step wizard form driven by Alpine.js.

        Each step is defined by a dict with ``"title"`` and ``"fields"`` keys.
        Only the step whose index matches the Alpine ``currentStep`` variable
        is visible at any time.  Previous / Next buttons advance or retreat
        through the steps, and the final step shows a Submit button that POSTs
        the whole form to ``action_url``.  A step indicator line (e.g.
        "Step 2 of 4") is shown above the step body.

        Args:
            request: Incoming HTTP request.
            resource: Admin resource instance (used to build field components).
            steps: Step definitions.  Each item must be a dict with at minimum
                ``"title": str`` and ``"fields": list[str]`` keys.
            action_url: Form ``action`` / HTMX ``hx-post`` target URL.
            submit_label: Label for the submit button on the final step.

        Returns:
            ``HTMLResponse`` with the wizard form fragment or full page.
        """
        label = self.resource_name.replace("_", " ").title()
        total_steps = len(steps)

        # Build Alpine.js data initialiser - currentStep is 0-indexed.
        alpine_data = "{ currentStep: 0 }"

        step_els: list[Any] = []
        for idx, step_def in enumerate(steps):
            step_title = step_def.get("title", f"Step {idx + 1}")
            step_fields_names: list[str] = step_def.get("fields", [])

            # Attempt to render each named field via the field registry.
            field_html_parts: list[Any] = []
            if resource and resource.model:
                try:
                    from lexigram.admin.forms.components import FormSchemaGenerator

                    generator = FormSchemaGenerator()
                    schema = generator.from_pydantic(resource.model)
                    schema_map = {f.name: f for f in schema.fields}

                    for fname in step_fields_names:
                        field_schema = schema_map.get(fname)
                        if field_schema is None:
                            field_html_parts.append(
                                el(
                                    "p",
                                    f"Unknown field: {fname}",
                                    class_="text-xs text-destructive",
                                )
                            )
                            continue
                        field_component = self._create_field_component(
                            field_schema, field_schema.default
                        )
                        if field_component:
                            raw = field_component.render()
                            field_html_parts.append(
                                el("div", raw, class_="wizard-field mb-4")
                            )
                except AdminValidationError as exc:
                    logger.debug(
                        "render_wizard field generation failed resource=%s: %s",
                        self.resource_name,
                        exc,
                    )
                    field_html_parts.append(
                        el(
                            "p",
                            f"Error building fields: {exc}",
                            class_="text-destructive text-sm",
                        )
                    )
            else:
                for fname in step_fields_names:
                    field_html_parts.append(
                        el(
                            "div",
                            el(
                                "input",
                                type="text",
                                name=fname,
                                placeholder=fname.replace("_", " ").title(),
                                class_=(
                                    "block w-full rounded-md border border-border "
                                    "dark:border-border bg-muted "
                                    "text-foreground px-3 py-2 text-sm "
                                    "focus:outline-none focus:ring-2 focus:ring-primary-500"
                                ),
                            ),
                            class_="wizard-field mb-4",
                        )
                    )

            # Navigation buttons
            nav_buttons: list[Any] = []
            if idx > 0:
                nav_buttons.append(
                    el(
                        "button",
                        "← Previous",
                        type="button",
                        class_=(
                            "px-4 py-2 text-sm font-medium text-foreground "
                            "border border-border rounded-lg "
                            "hover:bg-muted dark:hover:bg-muted transition-colors"
                        ),
                        **{"@click": "currentStep--"},
                    )
                )

            if idx < total_steps - 1:
                nav_buttons.append(
                    el(
                        "button",
                        "Next →",
                        type="button",
                        class_=(
                            "px-4 py-2 text-sm font-medium text-white bg-primary-600 "
                            "hover:bg-primary-700 rounded-lg focus:outline-none "
                            "focus:ring-2 focus:ring-primary-500 transition-colors"
                        ),
                        **{"@click": "currentStep++"},
                    )
                )
            else:
                nav_buttons.append(
                    el(
                        "button",
                        submit_label,
                        type="submit",
                        class_=(
                            "px-4 py-2 text-sm font-medium text-white bg-success "
                            "hover:bg-success/90 rounded-lg focus:outline-none "
                            "focus:ring-2 focus:ring-ring transition-colors"
                        ),
                    )
                )

            step_indicator = el(
                "p",
                f"Step {idx + 1} of {total_steps}",
                class_="text-xs text-muted-foreground mb-1",
            )
            step_heading = el(
                "h3",
                step_title,
                class_="text-base font-semibold text-foreground mb-4",
            )
            step_els.append(
                el(
                    "div",
                    step_indicator,
                    step_heading,
                    *field_html_parts,
                    el(
                        "div",
                        *nav_buttons,
                        class_="flex items-center justify-between mt-6 gap-3",
                    ),
                    class_="wizard-step",
                    **{"x-show": f"currentStep === {idx}"},
                )
            )

        # Progress bar / step dots
        step_dots: list[Any] = [
            el(
                "span",
                str(i + 1),
                class_=(
                    f"wizard-dot inline-flex items-center justify-center w-7 h-7 "
                    f"rounded-full text-xs font-semibold transition-colors "
                    f"{'bg-primary-600 text-white' if i == 0 else 'bg-muted text-muted-foreground dark:text-muted-foreground'}"
                ),
                **{
                    ":class": (
                        f"currentStep === {i} "
                        f"? 'bg-primary-600 text-white' "
                        f": currentStep > {i} "
                        f"? 'bg-success text-success-foreground' "
                        f": 'bg-muted text-muted-foreground dark:text-muted-foreground'"
                    )
                },
            )
            for i in range(total_steps)
        ]
        progress_bar = el(
            "div",
            *step_dots,
            class_="wizard-progress flex items-center gap-2 mb-6",
        )

        form_el = el(
            "form",
            progress_bar,
            *step_els,
            action=action_url,
            method="post",
            class_="wizard-form",
            **{
                "x-data": alpine_data,
                "hx-post": action_url,
                "hx-target": "#main-content",
                "hx-swap": "innerHTML",
            },
        )

        is_htmx = wants_fragment(request)
        if is_htmx:
            return HTMLResponse(render_to_string(form_el))

        content = el(
            "div",
            el(
                "div",
                el(
                    "a",
                    f"← Back to {label}",
                    href=f"{self._config.prefix}/{self.resource_name}",
                    class_="text-primary-600 hover:text-primary-900",
                ),
                el(
                    "h1",
                    f"Create {label}",
                    class_="text-2xl font-bold text-foreground mt-2",
                ),
                class_="mb-6",
            ),
            el(
                "div",
                form_el,
                class_="bg-card shadow rounded-lg p-6",
            ),
            class_="resource-content",
        )

        return self._renderer.render_page(
            content,
            request=request,
            title=f"Create {label}",
            breadcrumbs=[
                {"label": "Dashboard", "url": self._config.prefix},
                {"label": label, "url": f"{self._config.prefix}/{self.resource_name}"},
                {
                    "label": "Create",
                    "url": f"{self._config.prefix}/{self.resource_name}/create",
                },
            ],
        )


__all__ = ["WizardRendererMixin"]
