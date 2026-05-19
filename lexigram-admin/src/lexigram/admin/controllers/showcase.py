"""Showcase controller for demonstrating stateful components."""

from __future__ import annotations

from typing import Any

from lexigram.admin.ui.examples.stateful_components import (  # type: ignore[import-untyped]
    CounterComponent,
    FormWizard,
)
from lexigram.admin.ui.templates.page import (  # type: ignore[import-untyped]
    PageRenderer,
)
from lexigram.contracts.web import get
from lexigram.di.decorators import inject


@inject
class ShowcaseController:
    """Controller for showcasing stateful components and features."""

    def __init__(self, renderer: PageRenderer):
        self.renderer = renderer

    @get("/showcase/counter")
    async def counter_example(self) -> Any:
        """Display counter component example."""
        counter = CounterComponent(initial_value=10)

        return self.renderer.render_page(counter, title="Counter Component Example")

    @get("/showcase/wizard")
    async def wizard_example(self) -> Any:
        """Display form wizard example."""
        wizard = FormWizard()

        return self.renderer.render_page(wizard, title="Form Wizard Example")

    @get("/showcase")
    async def index(self) -> Any:
        """Showcase index with links to all examples."""
        from lexigram.ui.core.base import el

        content = el(
            "div",
            el(
                "h1",
                "Component Showcase",
                class_="text-3xl font-bold text-foreground mb-8",
            ),
            el(
                "div",
                el(
                    "div",
                    el(
                        "h2",
                        "Stateful Components",
                        class_="text-xl font-semibold text-foreground mb-4",
                    ),
                    el(
                        "ul",
                        el(
                            "li",
                            el(
                                "a",
                                "Counter Component",
                                href="/showcase/counter",
                                class_="text-primary-600 dark:text-primary-400 hover:underline",
                            ),
                            " - Simple counter with lifecycle hooks",
                            class_="mb-2",
                        ),
                        el(
                            "li",
                            el(
                                "a",
                                "Form Wizard",
                                href="/showcase/wizard",
                                class_="text-primary-600 dark:text-primary-400 hover:underline",
                            ),
                            " - Multi-step form with state management",
                            class_="mb-2",
                        ),
                        class_="space-y-2 list-disc list-inside",
                    ),
                    class_="p-6 bg-card rounded-lg shadow-md border border-border",
                ),
                class_="max-w-4xl",
            ),
            class_="container mx-auto px-4 py-8",
        )

        return self.renderer.render_page(content, title="Component Showcase")
