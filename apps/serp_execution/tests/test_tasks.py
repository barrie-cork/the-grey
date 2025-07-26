"""
Tests for SERP execution Celery tasks.

Tests for search execution tasks, session monitoring, and error recovery.
"""

from decimal import Decimal
from unittest.mock import Mock, patch

from celery.exceptions import Retry
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, TransactionTestCase

from apps.review_manager.models import SearchSession
from apps.search_strategy.models import SearchQuery
from apps.serp_execution.models import ExecutionMetrics, SearchExecution
from apps.serp_execution.services.serper_client import (
    SerperQuotaError,
    SerperRateLimitError,
)
from apps.serp_execution.tasks import (
    _send_execution_notification,
    _send_session_notification,
    initiate_search_session_execution_task,
    monitor_session_completion_task,
    perform_serp_query_task,
    retry_failed_execution_task,
)

User = get_user_model()


class TestInitiateSearchSessionExecutionTask(TestCase):
    """Test cases for initiate_search_session_execution_task."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.session = SearchSession.objects.create(
            title="Test Session", owner=self.user, status="ready_to_execute"
        )
        self.query1 = SearchQuery.objects.create(
            session=self.session,
            population="developers",
            interest="testing",
            context="agile",
            search_engines=["google"],
            is_active=True,
            order=1,
        )
        self.query2 = SearchQuery.objects.create(
            session=self.session,
            population="managers",
            interest="metrics",
            context="software",
            search_engines=["google"],
            is_active=True,
            order=2,
        )

    @patch("apps.serp_execution.tasks.perform_serp_query_task.si")
    @patch("apps.serp_execution.tasks.monitor_session_completion_task.si")
    @patch("apps.serp_execution.tasks.group")
    def test_successful_execution_initiation(
        self, mock_group, mock_monitor, mock_perform
    ):
        """Test successful initiation of search session execution."""
        # Setup mocks
        mock_perform_task = Mock()
        mock_perform.return_value = mock_perform_task
        mock_monitor_task = Mock()
        mock_monitor.return_value = mock_monitor_task
        mock_job = Mock()
        mock_group.return_value.__or__ = Mock(return_value=mock_job)

        # Execute task
        result = initiate_search_session_execution_task(str(self.session.id))

        # Verify result
        self.assertTrue(result["success"])
        self.assertEqual(result["session_id"], str(self.session.id))
        self.assertEqual(result["queries_count"], 2)
        self.assertEqual(result["status"], "executing")

        # Verify session status updated
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "executing")
        self.assertIsNotNone(self.session.started_at)

        # Verify executions created
        executions = SearchExecution.objects.filter(query__session=self.session)
        self.assertEqual(executions.count(), 2)

        # Verify tasks created
        self.assertEqual(mock_perform.call_count, 2)
        mock_monitor.assert_called_once_with(str(self.session.id))
        mock_job.apply_async.assert_called_once()

    def test_invalid_session_status(self):
        """Test initiation with invalid session status."""
        self.session.status = "draft"
        self.session.save()

        result = initiate_search_session_execution_task(str(self.session.id))

        self.assertFalse(result["success"])
        self.assertIn("not ready", result["error"])

    def test_no_active_queries(self):
        """Test initiation with no active queries."""
        SearchQuery.objects.filter(session=self.session).update(is_active=False)

        result = initiate_search_session_execution_task(str(self.session.id))

        self.assertFalse(result["success"])
        self.assertIn("No active queries", result["error"])

        # Session status should revert
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "ready_to_execute")

    def test_session_not_found(self):
        """Test initiation with non-existent session."""
        result = initiate_search_session_execution_task("non-existent-id")

        self.assertFalse(result["success"])
        self.assertIn("not found", result["error"])

    @patch("apps.serp_execution.tasks.initiate_search_session_execution_task.retry")
    def test_error_handling_with_retry(self, mock_retry):
        """Test error handling and retry logic."""
        # Simulate an error during execution
        with patch(
            "apps.serp_execution.tasks.SearchQuery.objects.filter"
        ) as mock_filter:
            mock_filter.side_effect = Exception("Database error")

            # Execute task (should trigger retry)
            initiate_search_session_execution_task(str(self.session.id))

            # Verify retry was called
            mock_retry.assert_called_once()

            # Verify session status reverted
            self.session.refresh_from_db()
            self.assertEqual(self.session.status, "ready_to_execute")


class TestPerformSerpQueryTask(TransactionTestCase):
    """Test cases for perform_serp_query_task."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.session = SearchSession.objects.create(
            title="Test Session", owner=self.user, status="executing"
        )
        self.query = SearchQuery.objects.create(
            session=self.session,
            population="developers",
            interest="best practices",
            context="python",
            search_engines=["google"],
            include_keywords=["testing", "documentation"],
            exclude_keywords=["deprecated"],
            document_types=["pdf"],
            max_results=50,
            is_active=True,
        )
        self.execution = SearchExecution.objects.create(
            query=self.query, initiated_by=self.user, status="pending"
        )

    @patch("apps.serp_execution.tasks.ResultProcessor")
    @patch("apps.serp_execution.tasks.UsageTracker")
    @patch("apps.serp_execution.tasks.QueryBuilder")
    @patch("apps.serp_execution.tasks.SerperClient")
    def test_successful_query_execution(
        self, mock_serper, mock_builder, mock_tracker, mock_processor
    ):
        """Test successful SERP query execution."""
        # Setup mocks
        mock_serper_instance = Mock()
        mock_serper.return_value = mock_serper_instance

        mock_builder_instance = Mock()
        mock_builder_instance.build_query.return_value = "optimized query string"
        mock_builder.return_value = mock_builder_instance

        mock_results = {
            "organic": [
                {
                    "position": 1,
                    "title": "Python Best Practices",
                    "link": "https://example.com/python-practices.pdf",
                    "snippet": "A comprehensive guide to Python best practices",
                },
                {
                    "position": 2,
                    "title": "Testing in Python",
                    "link": "https://example.edu/testing-python",
                    "snippet": "Learn about testing methodologies in Python",
                },
            ]
        }
        mock_metadata = {
            "credits_used": 1,
            "cache_hit": False,
            "total_results": "1000",
            "time_taken": 0.5,
            "request_id": "test-request-123",
        }
        mock_serper_instance.search.return_value = (mock_results, mock_metadata)
        mock_serper_instance.estimate_cost.return_value = Decimal("0.001")

        mock_processor_instance = Mock()
        mock_processor_instance.process_search_results.return_value = (2, 0, [])
        mock_processor.return_value = mock_processor_instance

        mock_tracker_instance = Mock()
        mock_tracker.return_value = mock_tracker_instance

        # Execute task
        result = perform_serp_query_task(str(self.execution.id), str(self.query.id))

        # Verify result
        self.assertTrue(result["success"])
        self.assertEqual(result["execution_id"], str(self.execution.id))
        self.assertEqual(result["results_count"], 2)
        self.assertEqual(result["duplicates_count"], 0)
        self.assertEqual(result["credits_used"], 1)
        self.assertEqual(len(result["errors"]), 0)

        # Verify execution updated
        self.execution.refresh_from_db()
        self.assertEqual(self.execution.status, "completed")
        self.assertEqual(self.execution.results_count, 2)
        self.assertEqual(self.execution.api_credits_used, 1)
        self.assertEqual(self.execution.estimated_cost, Decimal("0.001"))
        self.assertIsNotNone(self.execution.started_at)
        self.assertIsNotNone(self.execution.completed_at)

        # Verify query updated
        self.query.refresh_from_db()
        self.assertIsNotNone(self.query.last_executed)
        self.assertEqual(self.query.execution_count, 1)

        # Verify service calls
        mock_builder_instance.build_query.assert_called_once()
        mock_serper_instance.search.assert_called_once()
        mock_processor_instance.process_search_results.assert_called_once_with(
            execution_id=str(self.execution.id),
            raw_results=mock_results["organic"],
            batch_size=50,
        )
        mock_tracker_instance.track_search.assert_called_once()

    @patch("apps.serp_execution.tasks.recovery_manager")
    @patch("apps.serp_execution.tasks.SerperClient")
    def test_api_error_with_recovery(self, mock_serper, mock_recovery):
        """Test handling API errors with recovery strategy."""
        # Setup mocks
        mock_serper_instance = Mock()
        mock_serper_instance.search.side_effect = SerperRateLimitError(
            "Rate limit exceeded"
        )
        mock_serper.return_value = mock_serper_instance

        # Setup recovery strategy
        mock_strategy = Mock()
        mock_strategy.should_retry.return_value = True
        mock_strategy.get_delay.return_value = 60
        mock_strategy.modify_request.return_value = {}
        mock_recovery.get_recovery_strategy.return_value = mock_strategy

        # Execute task with mock retry
        with patch.object(perform_serp_query_task, "retry") as mock_retry:
            mock_retry.side_effect = Retry()

            with self.assertRaises(Retry):
                perform_serp_query_task(str(self.execution.id), str(self.query.id))

            # Verify retry was called with correct parameters
            mock_retry.assert_called_once()
            retry_kwargs = mock_retry.call_args[1]
            self.assertEqual(retry_kwargs["countdown"], 60)

    @patch("apps.serp_execution.tasks._send_execution_notification")
    @patch("apps.serp_execution.tasks.recovery_manager")
    @patch("apps.serp_execution.tasks.SerperClient")
    def test_api_error_without_retry(self, mock_serper, mock_recovery, mock_notify):
        """Test handling API errors when retry is not recommended."""
        # Setup mocks
        mock_serper_instance = Mock()
        mock_serper_instance.search.side_effect = SerperQuotaError("Quota exceeded")
        mock_serper.return_value = mock_serper_instance

        # Setup recovery strategy
        mock_strategy = Mock()
        mock_strategy.should_retry.return_value = False
        mock_strategy.get_notification_message.return_value = (
            "Quota exceeded, manual intervention required"
        )
        mock_recovery.get_recovery_strategy.return_value = mock_strategy
        mock_recovery.get_manual_intervention_required.return_value = True

        # Execute task
        result = perform_serp_query_task(str(self.execution.id), str(self.query.id))

        # Verify result
        self.assertFalse(result["success"])
        self.assertIn("Quota exceeded", result["error"])
        self.assertTrue(result["manual_intervention_required"])

        # Verify execution marked as failed
        self.execution.refresh_from_db()
        self.assertEqual(self.execution.status, "failed")
        self.assertIn("Quota exceeded", self.execution.error_message)

        # Verify notification sent
        mock_notify.assert_called_once()

    @patch("apps.serp_execution.tasks.SerperClient")
    def test_no_results_returned(self, mock_serper):
        """Test handling when no results are returned."""
        # Setup mocks
        mock_serper_instance = Mock()
        mock_serper_instance.search.return_value = (
            {"organic": []},  # No results
            {"credits_used": 1, "cache_hit": False},
        )
        mock_serper.return_value = mock_serper_instance

        # Execute task
        result = perform_serp_query_task(str(self.execution.id), str(self.query.id))

        # Verify result
        self.assertTrue(result["success"])
        self.assertEqual(result["results_count"], 0)

        # Verify execution marked as completed
        self.execution.refresh_from_db()
        self.assertEqual(self.execution.status, "completed")
        self.assertEqual(self.execution.results_count, 0)

    @patch("apps.serp_execution.tasks.recovery_manager")
    @patch("apps.serp_execution.tasks.ResultProcessor")
    @patch("apps.serp_execution.tasks.SerperClient")
    def test_successful_retry_tracking(
        self, mock_serper, mock_processor, mock_recovery
    ):
        """Test tracking successful execution after retries."""
        # Setup execution with previous retry
        self.execution.retry_count = 2
        self.execution.save()

        # Setup mocks for successful execution
        mock_serper_instance = Mock()
        mock_serper_instance.search.return_value = (
            {
                "organic": [
                    {"position": 1, "title": "Test", "link": "https://example.com"}
                ]
            },
            {"credits_used": 1, "cache_hit": False},
        )
        mock_serper_instance.estimate_cost.return_value = Decimal("0.001")
        mock_serper.return_value = mock_serper_instance

        mock_processor_instance = Mock()
        mock_processor_instance.process_search_results.return_value = (1, 0, [])
        mock_processor.return_value = mock_processor_instance

        # Execute task
        result = perform_serp_query_task(str(self.execution.id), str(self.query.id))

        # Verify successful recovery was recorded
        mock_recovery.record_successful_recovery.assert_called_once_with(
            str(self.execution.id)
        )


class TestMonitorSessionCompletionTask(TestCase):
    """Test cases for monitor_session_completion_task."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.session = SearchSession.objects.create(
            title="Test Session", owner=self.user, status="executing"
        )
        self.query1 = SearchQuery.objects.create(
            session=self.session,
            population="developers",
            interest="testing",
            context="agile",
            search_engines=["google"],
            is_active=True,
        )
        self.query2 = SearchQuery.objects.create(
            session=self.session,
            population="managers",
            interest="metrics",
            context="software",
            search_engines=["google"],
            is_active=True,
        )

    @patch("apps.serp_execution.tasks.monitor_session_completion_task.apply_async")
    def test_monitor_incomplete_session(self, mock_apply_async):
        """Test monitoring when not all executions are complete."""
        # Create executions with mixed statuses
        SearchExecution.objects.create(
            query=self.query1,
            initiated_by=self.user,
            status="completed",
            results_count=50,
            api_credits_used=100,
            estimated_cost=Decimal("0.10"),
        )
        SearchExecution.objects.create(
            query=self.query2, initiated_by=self.user, status="running"  # Still running
        )

        # Execute task
        result = monitor_session_completion_task(str(self.session.id))

        # Verify result
        self.assertEqual(result["status"], "executing")
        self.assertEqual(result["progress"], "1/2")

        # Verify rescheduled
        mock_apply_async.assert_called_once_with(
            args=[str(self.session.id)], countdown=30
        )

        # Session status should not change
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "executing")

    @patch("apps.serp_execution.tasks._send_session_notification")
    @patch("apps.results_manager.tasks.process_session_results_task")
    def test_monitor_all_successful(self, mock_process_task, mock_notify):
        """Test monitoring when all executions completed successfully."""
        # Create successful executions
        exec1 = SearchExecution.objects.create(
            query=self.query1,
            initiated_by=self.user,
            status="completed",
            results_count=50,
            api_credits_used=100,
            estimated_cost=Decimal("0.10"),
        )
        exec2 = SearchExecution.objects.create(
            query=self.query2,
            initiated_by=self.user,
            status="completed",
            results_count=30,
            api_credits_used=100,
            estimated_cost=Decimal("0.10"),
        )

        # Execute task
        result = monitor_session_completion_task(str(self.session.id))

        # Verify result
        self.assertEqual(result["status"], "processing_results")
        self.assertEqual(result["successful"], 2)
        self.assertEqual(result["failed"], 0)
        self.assertEqual(result["total_results"], 80)
        self.assertEqual(result["total_credits"], 200)
        self.assertEqual(result["total_cost"], 0.20)

        # Verify session updated
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "processing_results")
        self.assertIsNotNone(self.session.completed_at)
        self.assertEqual(self.session.total_results, 80)

        # Verify metrics created/updated
        metrics = ExecutionMetrics.objects.get(session=self.session)
        self.assertEqual(metrics.total_executions, 2)
        self.assertEqual(metrics.successful_executions, 2)
        self.assertEqual(metrics.failed_executions, 0)
        self.assertEqual(metrics.total_results_retrieved, 80)
        self.assertEqual(metrics.total_api_credits, 200)
        self.assertEqual(metrics.total_estimated_cost, Decimal("0.20"))

        # Verify next task triggered
        mock_process_task.delay.assert_called_once_with(str(self.session.id))

        # Verify notification sent
        mock_notify.assert_called_once()
        notification_call = mock_notify.call_args[0]
        self.assertIn("completed", notification_call[1])
        self.assertIn("80", notification_call[1])

    @patch("apps.serp_execution.tasks._send_session_notification")
    def test_monitor_all_failed(self, mock_notify):
        """Test monitoring when all executions failed."""
        # Create failed executions
        SearchExecution.objects.create(
            query=self.query1,
            initiated_by=self.user,
            status="failed",
            error_message="API error",
        )
        SearchExecution.objects.create(
            query=self.query2,
            initiated_by=self.user,
            status="failed",
            error_message="Rate limit exceeded",
        )

        # Execute task
        result = monitor_session_completion_task(str(self.session.id))

        # Verify result
        self.assertEqual(result["status"], "all_failed")
        self.assertEqual(result["successful"], 0)
        self.assertEqual(result["failed"], 2)

        # Verify session reverted to allow retry
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "ready_to_execute")
        self.assertIsNotNone(self.session.completed_at)

        # Verify notification sent
        mock_notify.assert_called_once()
        notification_call = mock_notify.call_args[0]
        self.assertIn("failed", notification_call[1])

    @patch("apps.serp_execution.tasks.monitor_session_completion_task.apply_async")
    def test_monitor_error_handling(self, mock_apply_async):
        """Test error handling in session monitoring."""
        # Simulate database error
        with patch(
            "apps.serp_execution.tasks.SearchExecution.objects.filter"
        ) as mock_filter:
            mock_filter.side_effect = Exception("Database connection error")

            # Execute task
            result = monitor_session_completion_task(str(self.session.id))

            # Verify error result
            self.assertEqual(result["status"], "error")
            self.assertIn("Database connection error", result["error"])

            # Verify rescheduled with longer delay
            mock_apply_async.assert_called_once_with(
                args=[str(self.session.id)], countdown=60
            )


class TestRetryFailedExecutionTask(TestCase):
    """Test cases for retry_failed_execution_task."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.session = SearchSession.objects.create(
            title="Test Session", owner=self.user, status="executing"
        )
        self.query = SearchQuery.objects.create(
            session=self.session,
            population="developers",
            interest="testing",
            context="agile",
            search_engines=["google"],
            is_active=True,
        )
        self.execution = SearchExecution.objects.create(
            query=self.query,
            initiated_by=self.user,
            status="failed",
            error_message="Rate limit exceeded",
            retry_count=1,
        )

    @patch("apps.serp_execution.tasks.perform_serp_query_task.delay")
    def test_retry_immediate(self, mock_perform):
        """Test immediate retry of failed execution."""
        mock_perform.return_value = Mock(id="new-task-id")

        # Execute task
        result = retry_failed_execution_task(str(self.execution.id), delay_seconds=0)

        # Verify result
        self.assertTrue(result["success"])
        self.assertEqual(result["execution_id"], str(self.execution.id))
        self.assertEqual(result["task_id"], "new-task-id")
        self.assertIn("immediately", result["message"])

        # Verify execution updated
        self.execution.refresh_from_db()
        self.assertEqual(self.execution.status, "pending")
        self.assertEqual(self.execution.error_message, "")

        # Verify task called
        mock_perform.assert_called_once_with(str(self.execution.id), str(self.query.id))

    @patch("apps.serp_execution.tasks.perform_serp_query_task.apply_async")
    def test_retry_with_delay(self, mock_apply_async):
        """Test retry with delay."""
        # Execute task with delay
        result = retry_failed_execution_task(str(self.execution.id), delay_seconds=120)

        # Verify result
        self.assertTrue(result["success"])
        self.assertEqual(result["scheduled_delay"], 120)
        self.assertIn("120 seconds", result["message"])

        # Verify execution updated
        self.execution.refresh_from_db()
        self.assertEqual(self.execution.status, "pending")

        # Verify task scheduled with delay
        mock_apply_async.assert_called_once_with(
            args=[str(self.execution.id), str(self.query.id)], countdown=120
        )

    def test_retry_validation(self):
        """Test retry validation for eligibility."""
        # Set retry count to max
        self.execution.retry_count = 3
        self.execution.save()

        # Execute task
        result = retry_failed_execution_task(str(self.execution.id))

        # Verify result
        self.assertFalse(result["success"])
        self.assertIn("cannot be retried", result["error"])

        # Execution should not be modified
        self.execution.refresh_from_db()
        self.assertEqual(self.execution.status, "failed")
        self.assertEqual(self.execution.retry_count, 3)

    def test_retry_execution_not_found(self):
        """Test retry with non-existent execution."""
        result = retry_failed_execution_task("non-existent-id")

        self.assertFalse(result["success"])
        self.assertIn("not found", result["error"])


class TestNotificationFunctions(TestCase):
    """Test cases for notification functions."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.session = SearchSession.objects.create(
            title="Test Research Session", owner=self.user
        )
        self.query = SearchQuery.objects.create(
            session=self.session,
            population="researchers",
            interest="climate change",
            context="policy",
            query_string="researchers climate change policy",
        )
        self.execution = SearchExecution.objects.create(
            query=self.query,
            initiated_by=self.user,
            status="failed",
            error_message="API quota exceeded",
            retry_count=2,
        )

    def test_send_execution_notification(self):
        """Test sending execution failure notification."""
        with self.settings(
            DEFAULT_FROM_EMAIL="noreply@example.com", SITE_URL="https://example.com"
        ):
            _send_execution_notification(
                self.execution, "Search execution failed after multiple attempts."
            )

            # Check email sent
            self.assertEqual(len(mail.outbox), 1)
            email = mail.outbox[0]

            self.assertIn("Search Execution Alert", email.subject)
            self.assertIn("Test Research Session", email.subject)
            self.assertIn("failed after multiple attempts", email.body)
            self.assertIn("researchers climate change policy", email.body)
            self.assertIn("API quota exceeded", email.body)
            self.assertIn("Attempts: 3", email.body)
            self.assertIn("https://example.com/review/", email.body)
            self.assertEqual(email.to, ["test@example.com"])

    def test_send_session_notification(self):
        """Test sending session completion notification."""
        with self.settings(
            DEFAULT_FROM_EMAIL="noreply@example.com", SITE_URL="https://example.com"
        ):
            _send_session_notification(
                self.session,
                "Search execution completed successfully. Found 150 results.",
            )

            # Check email sent
            self.assertEqual(len(mail.outbox), 1)
            email = mail.outbox[0]

            self.assertIn("Search Session Update", email.subject)
            self.assertIn("Test Research Session", email.subject)
            self.assertIn("completed successfully", email.body)
            self.assertIn("150 results", email.body)
            self.assertIn("https://example.com/review/", email.body)
            self.assertEqual(email.to, ["test@example.com"])

    def test_notification_without_email(self):
        """Test notification handling when user has no email."""
        self.user.email = ""
        self.user.save()

        # Should not raise error
        _send_execution_notification(self.execution, "Test message")
        _send_session_notification(self.session, "Test message")

        # No emails sent
        self.assertEqual(len(mail.outbox), 0)

    @patch("apps.serp_execution.tasks.logger")
    def test_notification_email_error(self, mock_logger):
        """Test handling email sending errors."""
        with patch("django.core.mail.send_mail") as mock_send:
            mock_send.side_effect = Exception("SMTP error")

            # Should not raise error
            _send_execution_notification(self.execution, "Test message")

            # Error should be logged
            mock_logger.error.assert_called()
            error_call = mock_logger.error.call_args[0][0]
            self.assertIn("Failed to send notification", error_call)
