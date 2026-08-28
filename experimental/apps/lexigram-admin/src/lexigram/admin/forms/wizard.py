"""Unified Wizard Component.
Combines wizard logic, persistence, and rendering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from lexigram.admin.schema import SchemaField
from lexigram.ui import Component, el

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class WizardDraft:
    """Wizard draft data for persistence."""

    wizard_id: str
    current_step: int
    form_data: dict[str, Any]
    step_errors: dict[int, dict[str, str]] = field(default_factory=dict)
    completed_steps: list[int] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WizardDraft:
        return cls(
            wizard_id=data["wizard_id"],
            current_step=data["current_step"],
            form_data=data["form_data"],
            step_errors={int(k): v for k, v in data.get("step_errors", {}).items()},
            completed_steps=data.get("completed_steps", []),
            created_at=data.get("created_at", datetime.now(UTC).isoformat()),
            updated_at=data.get("updated_at", datetime.now(UTC).isoformat()),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "wizard_id": self.wizard_id,
            "current_step": self.current_step,
            "form_data": self.form_data,
            "step_errors": self.step_errors,
            "completed_steps": self.completed_steps,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class WizardStep:
    """A single step in a multi-step form wizard."""

    def __init__(
        self,
        name: str,
        title: str,
        fields: list[SchemaField],
        description: str | None = None,
        is_conditional: bool = False,
        condition_func: Callable[[dict[str, Any]], bool] | None = None,
        can_skip: bool = False,
    ):
        self.name = name
        self.title = title
        self.fields = fields
        self.description = description
        self.is_conditional = is_conditional
        self.condition_func = condition_func
        self.can_skip = can_skip

    def is_visible(self, data: dict[str, Any]) -> bool:
        if not self.is_conditional or not self.condition_func:
            return True
        return self.condition_func(data)

    def validate(self, data: dict[str, Any]) -> tuple[bool, dict[str, str]]:
        errors = {}
        for form_field in self.fields:
            value = data.get(form_field.name)
            raw = value if value is None or isinstance(value, str) else str(value)
            result = form_field.from_form(raw)
            if result.is_err():
                errors[form_field.name] = str(result.unwrap_err())
                continue
            cleaned = result.unwrap()
            if form_field.required and (
                cleaned is None or (isinstance(cleaned, str) and not cleaned)
            ):
                errors[form_field.name] = "This field is required."
        return len(errors) == 0, errors


class FormWizard:
    """Stateful logic for multi-step forms."""

    def __init__(
        self,
        wizard_id: str,
        steps: list[WizardStep],
        draft_storage: Callable[[str], WizardDraft | None] | None = None,
        draft_saver: Callable[[WizardDraft], None] | None = None,
    ):
        self.wizard_id = wizard_id
        self.steps = steps
        self.current_step = 0
        self.form_data: dict[str, Any] = {}
        self.step_errors: dict[int, dict[str, str]] = {}
        self.completed_steps: set[int] = set()
        self.draft_storage = draft_storage
        self.draft_saver = draft_saver
        if self.draft_storage:
            self._load_draft()

    def get_current_step(self) -> WizardStep:
        return self.steps[self.current_step]

    def get_visible_steps(self) -> list[WizardStep]:
        return list(filter(lambda s: s.is_visible(self.form_data), self.steps))

    def get_progress(self) -> float:
        visible = self.get_visible_steps()
        if not visible:
            return 100.0
        current_step_obj = self.get_current_step()
        try:
            current_visible_idx = visible.index(current_step_obj)
        except ValueError:
            current_visible_idx = 0
        return ((current_visible_idx + 1) / len(visible)) * 100

    def jump_to_step(self, step_idx: int) -> bool:
        if not self.can_proceed_to_step(step_idx):
            return False
        self.current_step = step_idx
        return True

    def can_proceed_to_step(self, step_idx: int) -> bool:
        if step_idx == 0:
            return True
        # Simplified: can proceed if all visible steps before this one are completed
        visible = self.get_visible_steps()
        if step_idx < 0 or step_idx >= len(self.steps):
            return False

        target_step = self.steps[step_idx]
        if target_step not in visible:
            return False

        target_visible_idx = visible.index(target_step)
        for i in range(target_visible_idx):
            actual_idx = self.steps.index(visible[i])
            if actual_idx not in self.completed_steps:
                return False
        return True

    def next_step(self, data: dict[str, Any]) -> tuple[bool, dict[str, str]]:
        current = self.get_current_step()
        success, errors = current.validate(data)

        self.form_data.update(data)
        if success:
            self.completed_steps.add(self.current_step)
            self.step_errors.pop(self.current_step, None)

            visible = self.get_visible_steps()
            try:
                current_visible_idx = visible.index(current)
                if current_visible_idx < len(visible) - 1:
                    next_step_obj = visible[current_visible_idx + 1]
                    self.current_step = self.steps.index(next_step_obj)
            except ValueError:
                pass
        else:
            self.step_errors[self.current_step] = errors

        self._save_draft()
        return success, errors

    def previous_step(self) -> bool:
        visible = self.get_visible_steps()
        current = self.get_current_step()
        try:
            current_visible_idx = visible.index(current)
            if current_visible_idx > 0:
                prev_step_obj = visible[current_visible_idx - 1]
                self.current_step = self.steps.index(prev_step_obj)
                return True
        except ValueError:
            pass
        return False

    def skip_step(self) -> bool:
        current = self.get_current_step()
        if not current.can_skip:
            return False

        self.completed_steps.add(self.current_step)
        # Clear any errors for this step since we are skipping
        self.step_errors.pop(self.current_step, None)

        visible = self.get_visible_steps()
        try:
            current_visible_idx = visible.index(current)
            if current_visible_idx < len(visible) - 1:
                next_step_obj = visible[current_visible_idx + 1]
                self.current_step = self.steps.index(next_step_obj)
        except ValueError:
            pass

        self._save_draft()
        return True

    def add_review_step(
        self,
        title: str = "Review",
        description: str = "",
        name: str = "review",
    ) -> Any:
        """Add a review step at the end."""
        review_step = WizardStep(
            name=name,
            title=title,
            fields=[],
            description=description,
        )
        self.steps.append(review_step)

    def get_step_validation_summary(self, step_idx: int) -> dict[str, Any]:
        step = self.steps[step_idx]
        errors = self.step_errors.get(step_idx, {})
        return {
            "valid": len(errors) == 0,
            "error_count": len(errors),
            "step_title": step.title,
            "errors": errors,
        }

    def reset(self) -> Any:
        self.current_step = 0
        self.form_data = {}
        self.step_errors = {}
        self.completed_steps = set()
        self._save_draft()

    def _load_draft(self) -> Any:
        if not self.draft_storage:
            return
        draft = self.draft_storage(self.wizard_id)
        if draft:
            self.current_step = draft.current_step
            self.form_data = draft.form_data
            self.step_errors = draft.step_errors
            self.completed_steps = set(draft.completed_steps)

    def _save_draft(self) -> Any:
        if self.draft_saver:
            draft = WizardDraft(
                wizard_id=self.wizard_id,
                current_step=self.current_step,
                form_data=self.form_data,
                step_errors=dict(self.step_errors.items()),
                completed_steps=list(self.completed_steps),
                updated_at=datetime.now(UTC).isoformat(),
            )
            self.draft_saver(draft)

    def save_draft(self) -> Any:
        self._save_draft()


class WizardRenderer(Component):
    """UI Renderer for FormWizard."""

    def __init__(self, wizard: FormWizard, **props: Any) -> None:
        super().__init__(**props)
        self.wizard = wizard

    def render(self) -> Any:
        return el(
            "div",
            self.render_progress_bar(),
            self.render_step_navigation(),
            self.render_current_step(),
            class_="wizard-container p-6 bg-card rounded-xl shadow-lg",
        )

    def render_progress_bar(self) -> Any:
        progress = self.wizard.get_progress()
        return el(
            "div",
            el(
                "div",
                class_="h-2 bg-primary-600 transition-all duration-500",
                style=f"width: {progress}%",
            ),
            class_="w-full h-2 bg-muted rounded-full overflow-hidden mb-8",
        )

    def render_step_navigation(self) -> Any:
        steps = self.wizard.get_visible_steps()
        current = self.wizard.get_current_step()
        nav_items = []
        for _i, step in enumerate(steps):
            is_active = step == current
            nav_items.append(
                el(
                    "div",
                    step.title,
                    class_=f"text-sm font-medium {'text-primary-600' if is_active else 'text-muted-foreground'}",
                ),
            )
        return el("div", *nav_items, class_="flex justify-between mb-6")

    def render_current_step(self) -> Any:
        step = self.wizard.get_current_step()
        values = self.wizard.form_data
        fields_html = [f.render_form(values.get(f.name)) for f in step.fields]
        return el(
            "div",
            el("h2", step.title, class_="text-xl font-bold mb-2"),
            el("p", step.description or "", class_="text-muted-foreground mb-6"),
            el("div", *fields_html, class_="space-y-4"),
            class_="step-content",
        )
