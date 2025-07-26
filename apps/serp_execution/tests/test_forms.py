"""
Tests for SERP execution forms.

Tests for ExecutionConfirmationForm and ErrorRecoveryForm.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.review_manager.models import SearchSession
from apps.search_strategy.models import SearchQuery
from apps.serp_execution.forms import ErrorRecoveryForm, ExecutionConfirmationForm
from apps.serp_execution.models import SearchExecution

User = get_user_model()


class TestExecutionConfirmationForm(TestCase):
    """Test cases for ExecutionConfirmationForm."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.session = SearchSession.objects.create(
            title="Test Session", owner=self.user, status="ready_to_execute"
        )
        self.query = SearchQuery.objects.create(
            session=self.session,
            population="developers",
            interest="testing",
            context="python",
            search_engines=["google"],
            is_active=True,
        )

    def test_form_valid_data(self):
        """Test form with valid data."""
        form_data = {"confirm_execution": True, "acknowledge_cost": True}

        form = ExecutionConfirmationForm(data=form_data, session=self.session)
        self.assertTrue(form.is_valid())

    def test_form_requires_confirmation(self):
        """Test form requires execution confirmation."""
        form_data = {"confirm_execution": False, "acknowledge_cost": True}

        form = ExecutionConfirmationForm(data=form_data, session=self.session)
        self.assertFalse(form.is_valid())
        self.assertIn("confirm_execution", form.errors)
        self.assertIn("must confirm", str(form.errors["confirm_execution"]))

    def test_form_requires_cost_acknowledgment(self):
        """Test form requires cost acknowledgment."""
        form_data = {"confirm_execution": True, "acknowledge_cost": False}

        form = ExecutionConfirmationForm(data=form_data, session=self.session)
        self.assertFalse(form.is_valid())
        self.assertIn("acknowledge_cost", form.errors)
        self.assertIn("must acknowledge", str(form.errors["acknowledge_cost"]))

    def test_form_validates_session_has_queries(self):
        """Test form validates session has active queries."""
        # Deactivate all queries
        SearchQuery.objects.filter(session=self.session).update(is_active=False)

        form_data = {"confirm_execution": True, "acknowledge_cost": True}

        form = ExecutionConfirmationForm(data=form_data, session=self.session)
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)
        self.assertIn("No active queries", str(form.errors))

    def test_form_validates_session_status(self):
        """Test form validates session is in correct status."""
        self.session.status = "executing"
        self.session.save()

        form_data = {"confirm_execution": True, "acknowledge_cost": True}

        form = ExecutionConfirmationForm(data=form_data, session=self.session)
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)
        self.assertIn("already executing", str(form.errors))

    def test_form_fields_attributes(self):
        """Test form fields have correct attributes."""
        form = ExecutionConfirmationForm(session=self.session)

        # Check confirm_execution field
        confirm_field = form.fields["confirm_execution"]
        self.assertTrue(confirm_field.required)
        self.assertIn("I confirm", confirm_field.label)

        # Check acknowledge_cost field
        cost_field = form.fields["acknowledge_cost"]
        self.assertTrue(cost_field.required)
        self.assertIn("acknowledge", cost_field.label)

        # Check widget attributes
        self.assertEqual(
            form.fields["confirm_execution"].widget.attrs.get("class"),
            "form-check-input",
        )


class TestErrorRecoveryForm(TestCase):
    """Test cases for ErrorRecoveryForm."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.session = SearchSession.objects.create(
            title="Test Session", owner=self.user
        )
        self.query = SearchQuery.objects.create(
            session=self.session,
            population="developers",
            interest="testing",
            context="python",
            search_engines=["google"],
        )
        self.execution = SearchExecution.objects.create(
            query=self.query,
            initiated_by=self.user,
            status="failed",
            error_message="Rate limit exceeded",
            retry_count=0,
        )

    def test_form_valid_retry(self):
        """Test form with valid retry action."""
        form_data = {
            "recovery_action": "retry",
            "retry_delay": 60,
            "notes": "Retrying after rate limit",
        }

        form = ErrorRecoveryForm(data=form_data, execution=self.execution)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["recovery_action"], "retry")
        self.assertEqual(form.cleaned_data["retry_delay"], 60)

    def test_form_valid_skip(self):
        """Test form with skip action."""
        form_data = {"recovery_action": "skip", "notes": "Skipping problematic query"}

        form = ErrorRecoveryForm(data=form_data, execution=self.execution)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["recovery_action"], "skip")

    def test_form_valid_manual(self):
        """Test form with manual intervention action."""
        form_data = {
            "recovery_action": "manual",
            "notes": "Need to check API credentials",
        }

        form = ErrorRecoveryForm(data=form_data, execution=self.execution)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["recovery_action"], "manual")

    def test_form_retry_requires_delay(self):
        """Test retry action requires delay when specified."""
        form_data = {
            "recovery_action": "retry",
            "retry_delay": 0,  # Invalid delay
            "notes": "Test",
        }

        form = ErrorRecoveryForm(data=form_data, execution=self.execution)
        self.assertFalse(form.is_valid())
        self.assertIn("retry_delay", form.errors)

    def test_form_validates_max_retries(self):
        """Test form validates execution hasn't exceeded max retries."""
        self.execution.retry_count = 3  # Max retries
        self.execution.save()

        form_data = {"recovery_action": "retry", "retry_delay": 60, "notes": "Test"}

        form = ErrorRecoveryForm(data=form_data, execution=self.execution)
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)
        self.assertIn("maximum retry attempts", str(form.errors))

    def test_form_delay_choices(self):
        """Test retry delay choices."""
        form = ErrorRecoveryForm(execution=self.execution)
        delay_field = form.fields["retry_delay"]

        # Check choices include expected delays
        choice_values = [choice[0] for choice in delay_field.choices]
        self.assertIn(60, choice_values)  # 1 minute
        self.assertIn(300, choice_values)  # 5 minutes
        self.assertIn(900, choice_values)  # 15 minutes
        self.assertIn(3600, choice_values)  # 1 hour

    def test_form_initial_values_based_on_error(self):
        """Test form sets initial values based on error type."""
        # Rate limit error
        self.execution.error_message = "Rate limit exceeded. Retry after 300 seconds"
        form = ErrorRecoveryForm(execution=self.execution)

        # Should suggest retry with appropriate delay
        self.assertEqual(form.initial.get("recovery_action"), "retry")
        self.assertGreaterEqual(form.initial.get("retry_delay", 0), 300)

        # Quota error
        self.execution.error_message = "API quota exceeded"
        form = ErrorRecoveryForm(execution=self.execution)

        # Should suggest manual intervention
        self.assertEqual(form.initial.get("recovery_action"), "manual")

    def test_form_notes_field(self):
        """Test notes field configuration."""
        form = ErrorRecoveryForm(execution=self.execution)
        notes_field = form.fields["notes"]

        self.assertFalse(notes_field.required)
        self.assertIsInstance(notes_field.widget.attrs.get("rows"), int)
        self.assertIn("form-control", notes_field.widget.attrs.get("class", ""))

    def test_form_action_field_help_text(self):
        """Test recovery action field has appropriate help text."""
        form = ErrorRecoveryForm(execution=self.execution)
        action_field = form.fields["recovery_action"]

        # Check each choice has descriptive help
        for choice_value, choice_label in action_field.choices:
            if choice_value == "retry":
                self.assertIn("Retry", choice_label)
            elif choice_value == "skip":
                self.assertIn("Skip", choice_label)
            elif choice_value == "manual":
                self.assertIn("Manual", choice_label)

    def test_form_clean_validates_execution_status(self):
        """Test form validates execution is in failed status."""
        self.execution.status = "completed"
        self.execution.save()

        form_data = {"recovery_action": "retry", "retry_delay": 60, "notes": "Test"}

        form = ErrorRecoveryForm(data=form_data, execution=self.execution)
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)
        self.assertIn("not in failed status", str(form.errors))
