"""Tests for enhanced wizard functionality."""

from lexigram.admin.forms import (
    FormWizard,
    WizardDraft,
    WizardStep,
)
from lexigram.admin.schema import IntegerField, TextField


class TestWizardDraft:
    """Test WizardDraft functionality."""

    def test_draft_creation(self):
        """Test creating a wizard draft."""
        draft = WizardDraft(
            wizard_id="test-wizard",
            current_step=1,
            form_data={"name": "John", "age": 30},
            step_errors={0: {"name": "Required"}},
        )

        assert draft.wizard_id == "test-wizard"
        assert draft.current_step == 1
        assert draft.form_data == {"name": "John", "age": 30}
        assert draft.step_errors == {0: {"name": "Required"}}

    def test_draft_to_dict(self):
        """Test converting draft to dictionary."""
        draft = WizardDraft(
            wizard_id="test-wizard",
            current_step=1,
            form_data={"name": "John"},
        )

        data = draft.to_dict()
        assert data["wizard_id"] == "test-wizard"
        assert data["current_step"] == 1
        assert data["form_data"] == {"name": "John"}
        assert "created_at" in data
        assert "updated_at" in data

    def test_draft_from_dict(self):
        """Test creating draft from dictionary."""
        data = {
            "wizard_id": "test-wizard",
            "current_step": 2,
            "form_data": {"email": "test@example.com"},
            "step_errors": {},
            "created_at": "2024-01-01T10:00:00",
            "updated_at": "2024-01-01T10:30:00",
        }

        draft = WizardDraft.from_dict(data)
        assert draft.wizard_id == "test-wizard"
        assert draft.current_step == 2
        assert draft.form_data == {"email": "test@example.com"}


class TestEnhancedWizard:
    """Test enhanced wizard functionality."""

    def create_test_wizard(self):
        """Create a test wizard with multiple steps."""
        steps = [
            WizardStep(
                name="personal",
                title="Personal Information",
                fields=[
                    TextField(name="first_name", label="First Name", required=True),
                    TextField(name="last_name", label="Last Name", required=True),
                ],
                description="Please enter your personal information.",
            ),
            WizardStep(
                name="contact",
                title="Contact Information",
                fields=[
                    TextField(name="email", label="Email", required=True),
                    TextField(name="phone", label="Phone", required=False),
                ],
                description="Please enter your contact information.",
                can_skip=False,
            ),
            WizardStep(
                name="preferences",
                title="Preferences",
                fields=[
                    IntegerField(name="age", label="Age"),
                ],
                description="Please enter your preferences.",
                can_skip=True,
            ),
        ]

        return FormWizard("test-wizard", steps)

    def test_wizard_initialization(self):
        """Test wizard initialization."""
        wizard = self.create_test_wizard()

        assert wizard.wizard_id == "test-wizard"
        assert wizard.current_step == 0
        assert wizard.form_data == {}
        assert wizard.step_errors == {}
        assert wizard.completed_steps == set()

    def test_get_visible_steps(self):
        """Test getting visible steps."""
        wizard = self.create_test_wizard()
        visible_steps = wizard.get_visible_steps()

        assert len(visible_steps) == 3
        assert all(
            step.name in ["personal", "contact", "preferences"]
            for step in visible_steps
        )

    def test_jump_to_step(self):
        """Test jumping to a specific step."""
        wizard = self.create_test_wizard()

        # Should not be able to jump forward initially
        assert not wizard.jump_to_step(1)

        # Complete first step
        success, _errors = wizard.next_step({"first_name": "John", "last_name": "Doe"})
        assert success

        # Now should be able to jump to second step
        assert wizard.jump_to_step(1)
        assert wizard.current_step == 1

    def test_previous_step(self):
        """Test moving to previous step."""
        wizard = self.create_test_wizard()

        # Move forward
        wizard.next_step({"first_name": "John", "last_name": "Doe"})
        assert wizard.current_step == 1

        # Move back
        assert wizard.previous_step()
        assert wizard.current_step == 0

        # Can't go back from first step
        assert not wizard.previous_step()

    def test_progress_calculation(self):
        """Test progress percentage calculation."""
        wizard = self.create_test_wizard()

        # Initially at step 1 of 3
        assert abs(wizard.get_progress() - 33.333333333333336) < 0.001

        # Complete first step
        wizard.next_step({"first_name": "John", "last_name": "Doe"})
        assert abs(wizard.get_progress() - 66.66666666666667) < 0.001

        # Complete second step
        wizard.next_step({"email": "john@example.com"})
        assert abs(wizard.get_progress() - 100.0) < 0.001

    def test_step_validation_summary(self):
        """Test step validation summary."""
        wizard = self.create_test_wizard()

        # Try to proceed with invalid data
        success, errors = wizard.next_step({})
        assert not success
        assert "first_name" in errors
        assert "last_name" in errors

        # Check validation summary
        summary = wizard.get_step_validation_summary(0)
        assert not summary["valid"]
        assert summary["error_count"] == 2
        assert summary["step_title"] == "Personal Information"

    def test_can_proceed_to_step(self):
        """Test checking if user can proceed to a step."""
        wizard = self.create_test_wizard()

        # Can always proceed to first step
        assert wizard.can_proceed_to_step(0)

        # Cannot proceed to later steps initially
        assert not wizard.can_proceed_to_step(1)
        assert not wizard.can_proceed_to_step(2)

        # Complete first step
        wizard.next_step({"first_name": "John", "last_name": "Doe"})

        # Now can proceed to second step
        assert wizard.can_proceed_to_step(1)
        assert not wizard.can_proceed_to_step(2)

    def test_conditional_steps(self):
        """Test conditional steps functionality."""
        # Create wizard with conditional step
        steps = [
            WizardStep(
                name="basic",
                title="Basic Info",
                fields=[TextField(name="user_type", label="User Type", required=True)],
            ),
            WizardStep(
                name="advanced",
                title="Advanced Settings",
                fields=[TextField(name="api_key", label="API Key")],
                is_conditional=True,
                condition_func=lambda data: data.get("user_type") == "admin",
            ),
        ]

        wizard = FormWizard("conditional-wizard", steps)

        # Initially, advanced step should not be visible
        visible_steps = wizard.get_visible_steps()
        assert len(visible_steps) == 1
        assert visible_steps[0].name == "basic"

        # Complete basic step with regular user
        wizard.next_step({"user_type": "regular"})
        visible_steps = wizard.get_visible_steps()
        assert len(visible_steps) == 1  # Still only basic step

        # Reset and try with admin user
        wizard.reset()
        wizard.next_step({"user_type": "admin"})
        visible_steps = wizard.get_visible_steps()
        assert len(visible_steps) == 2  # Now includes advanced step

    def test_draft_save_load(self):
        """Test draft saving and loading."""
        drafts = {}

        def save_draft(draft):
            drafts[draft.wizard_id] = draft

        def load_draft(wizard_id):
            return drafts.get(wizard_id)

        wizard = self.create_test_wizard()
        wizard.draft_saver = save_draft
        wizard.draft_storage = load_draft

        # Complete first step
        wizard.next_step({"first_name": "John", "last_name": "Doe"})
        wizard._save_draft()

        # Create new wizard instance
        new_wizard = FormWizard("test-wizard", wizard.steps, load_draft, save_draft)

        # Should load the draft
        assert new_wizard.current_step == 1
        assert new_wizard.form_data == {"first_name": "John", "last_name": "Doe"}

    def test_add_review_step(self):
        """Test adding a review step."""
        wizard = self.create_test_wizard()
        wizard.add_review_step("Review Information", "Please review your information")

        assert len(wizard.steps) == 4
        review_step = wizard.steps[-1]
        assert review_step.name == "review"
        assert review_step.title == "Review Information"
        assert review_step.description == "Please review your information"

    def test_skip_step(self):
        """Test skipping a step."""
        wizard = self.create_test_wizard()

        # Complete first step
        wizard.next_step({"first_name": "John", "last_name": "Doe"})

        # Skip the contact step (which cannot be skipped)
        # This should not work since contact step has can_skip=False
        assert wizard.current_step == 1  # Still on contact step

        # Move to preferences step
        wizard.next_step({"email": "john@example.com"})

        # Skip preferences step (which can be skipped)
        # Since it's the last step, skipping should work but stay on the same step
        assert wizard.skip_step()
        assert wizard.current_step == 2  # Still on preferences step

    def test_reset_wizard(self):
        """Test resetting wizard."""
        wizard = self.create_test_wizard()

        # Make some progress
        wizard.next_step({"first_name": "John", "last_name": "Doe"})
        wizard.next_step({"email": "john@example.com"})
        wizard.form_data["extra"] = "data"
        wizard.completed_steps.add(0)
        wizard.completed_steps.add(1)

        # Reset
        wizard.reset()

        assert wizard.current_step == 0
        assert wizard.form_data == {}
        assert wizard.step_errors == {}
        assert wizard.completed_steps == set()
