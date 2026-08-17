"""Form Renderer Service for Lexigram Admin.

Provides a unified interface for rendering schema-driven forms with
built-in RBAC enforcement.
"""

from __future__ import annotations

from dataclasses import replace as dc_replace
from typing import Any

from lexigram.admin.forms.components import FormSchema, FormSchemaGenerator
from lexigram.admin.rbac.service import PermissionService
from lexigram.admin.ui.organisms.dynamic_form import DynamicForm
from lexigram.di.decorators import inject


@inject
class FormRenderer:
    """Service for rendering forms with RBAC integration.

    Orchestrates schema generation, permission filtering, and
    component instantiation.
    """

    def __init__(
        self,
        generator: FormSchemaGenerator,
        permission_service: PermissionService | None = None,
    ) -> None:
        self.generator = generator
        self.permission_service = permission_service

    async def render_form(
        self,
        model: type | None = None,
        schema: FormSchema | None = None,
        user: Any = None,
        resource_name: str = "unknown",
        action: str = "",
        method: str = "POST",
        initial_data: dict[str, Any] | None = None,
        submit_text: str = "Submit",
        hx_post: str | None = None,
        hx_target: str | None = None,
        hx_swap: str = "outerHTML",
    ) -> DynamicForm:
        """Render a form for the given model/schema and user context.

        Args:
            model: Pydantic model class to generate schema from.
            schema: Explicit FormSchema (overrides model).
            user: Current user for RBAC filtering.
            resource_name: Name of the resource for RBAC checks.
            action: Form action URL.
            method: HTTP method.
            initial_data: Initial values for the form.
            submit_text: Text for the submit button.
            hx_post: HTMX post URL.
            hx_target: HTMX target selector.
            hx_swap: HTMX swap strategy.

        Returns:
            A DynamicForm component instance ready for rendering.
        """
        # 1. Resolve base schema
        if schema:
            base_schema = schema
        elif model:
            base_schema = self.generator.from_pydantic(model)
        else:
            base_schema = FormSchema()

        # Update resource name in schema if provided
        if resource_name != "unknown":
            base_schema.resource_name = resource_name

        # 2. Apply RBAC filtering if user is provided
        if user:
            form_schema = await base_schema.filter_for_user(
                user,
                resource_name,
                self.permission_service,
            )
        else:
            form_schema = base_schema

        # 3. Apply initial data as defaults if provided
        if initial_data:
            for idx, field in enumerate(form_schema.fields):
                if field.name in initial_data:
                    form_schema.fields[idx] = dc_replace(
                        field, default=initial_data[field.name]
                    )

        # 4. Create and return the DynamicForm
        return DynamicForm(
            schema=form_schema,
            action=action,
            method=method,
            submit_text=submit_text,
            hx_post=hx_post,
            hx_target=hx_target,
            hx_swap=hx_swap,
        )
