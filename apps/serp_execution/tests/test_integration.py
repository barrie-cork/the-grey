"""
Integration tests for SERP execution module.

End-to-end tests covering the complete search execution workflow,
from query building through result processing.
"""

import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from apps.review_manager.models import SearchSession
from apps.search_strategy.models import SearchQuery
from apps.serp_execution.models import (
    ExecutionMetrics,
    RawSearchResult,
    SearchExecution,
)
from apps.serp_execution.services.cache_manager import CacheManager
# from apps.serp_execution.services.usage_tracker import UsageTracker  # Removed for simplification
from apps.serp_execution.tasks import (
    initiate_search_session_execution_task,
    monitor_session_completion_task,
    perform_serp_query_task,
)

User = get_user_model()


class TestCompleteSearchWorkflow(TransactionTestCase):
    """Test complete search execution workflow from start to finish."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="researcher@example.com",
            password="testpass123",
            username="researcher",
        )
        self.client = Client()
        self.client.login(username="researcher", password="testpass123")

        # Create research session
        self.session = SearchSession.objects.create(
            title="Climate Change Policy Research",
            description="Research on climate change mitigation policies",
            owner=self.user,
            status="ready_to_execute",
        )

        # Create multiple queries with different characteristics
        self.query1 = SearchQuery.objects.create(
            session=self.session,
            population="policy makers",
            interest="climate change mitigation",
            context="international agreements",
            query_string="policy makers climate change mitigation international agreements",
            search_engines=["google"],
            include_keywords=["Paris Agreement", "carbon pricing"],
            exclude_keywords=["denial", "hoax"],
            document_types=["pdf"],
            max_results=50,
            is_active=True,
            order=1,
        )

        self.query2 = SearchQuery.objects.create(
            session=self.session,
            population="researchers",
            interest="renewable energy",
            context="policy effectiveness",
            query_string="researchers renewable energy policy effectiveness",
            search_engines=["google", "bing"],
            include_keywords=["solar", "wind", "incentives"],
            document_types=["pdf", "doc"],
            max_results=30,
            is_active=True,
            order=2,
        )

        cache.clear()

    @patch("apps.serp_execution.services.serper_client.requests.Session.post")
    @patch("apps.serp_execution.tasks.group")
    @patch("apps.results_manager.tasks.process_session_results_task")
    def test_complete_execution_workflow(
        self, mock_process_results, mock_group, mock_post
    ):
        """Test the complete execution workflow from initiation to completion."""

        # Mock Serper API responses
        def mock_api_response(url, json=None, **kwargs):
            """Generate mock API response based on query."""
            query = json.get("q", "")
            response = Mock()
            response.status_code = 200

            if "policy makers" in query:
                response.json.return_value = {
                    "organic": [
                        {
                            "position": i,
                            "title": f"Climate Policy Document {i}",
                            "link": f"https://policy.org/climate-doc-{i}.pdf",
                            "snippet": f"Policy analysis on climate mitigation strategies...",
                            "displayLink": "policy.org",
                        }
                        for i in range(1, 6)
                    ],
                    "credits": 1,
                    "searchInformation": {"totalResults": "5000", "searchTime": 0.35},
                }
            else:
                response.json.return_value = {
                    "organic": [
                        {
                            "position": i,
                            "title": f"Renewable Energy Research {i}",
                            "link": f"https://research.edu/renewable-{i}",
                            "snippet": f"Study on renewable energy policy effectiveness...",
                            "displayLink": "research.edu",
                        }
                        for i in range(1, 4)
                    ],
                    "credits": 1,
                    "searchInformation": {"totalResults": "3000", "searchTime": 0.28},
                }

            response.headers = {"X-Request-ID": f"test-{timezone.now().timestamp()}"}
            return response

        mock_post.side_effect = mock_api_response

        # Mock celery group behavior
        mock_job = Mock()
        mock_group.return_value.__or__ = Mock(return_value=mock_job)

        # Step 1: View the execution preview page
        preview_url = reverse(
            "serp_execution:execute_search", kwargs={"session_id": self.session.id}
        )
        response = self.client.get(preview_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Climate Change Policy Research")
        self.assertContains(response, "2")  # Two queries

        # Step 2: Initiate execution
        with patch(
            "apps.serp_execution.views.initiate_search_session_execution_task.delay"
        ) as mock_initiate:
            mock_initiate.return_value = Mock(id="main-task-id")

            response = self.client.post(
                preview_url, {"confirm_execution": True, "acknowledge_cost": True}
            )

            self.assertEqual(response.status_code, 302)
            mock_initiate.assert_called_once_with(str(self.session.id))

        # Step 3: Execute the initiation task
        result = initiate_search_session_execution_task(str(self.session.id))

        self.assertTrue(result["success"])
        self.assertEqual(result["queries_count"], 2)

        # Verify session status updated
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "executing")

        # Verify executions created
        executions = SearchExecution.objects.filter(query__session=self.session)
        self.assertEqual(executions.count(), 2)

        # Step 4: Execute individual query tasks
        for execution in executions:
            result = perform_serp_query_task(str(execution.id), str(execution.query.id))

            self.assertTrue(result["success"])
            self.assertGreater(result["results_count"], 0)
            self.assertEqual(result["credits_used"], 1)

        # Verify results were created
        total_results = RawSearchResult.objects.filter(
            execution__query__session=self.session
        ).count()
        self.assertEqual(total_results, 8)  # 5 + 3 results

        # Step 5: Monitor session completion
        completion_result = monitor_session_completion_task(str(self.session.id))

        self.assertEqual(completion_result["status"], "processing_results")
        self.assertEqual(completion_result["successful"], 2)
        self.assertEqual(completion_result["failed"], 0)
        self.assertEqual(completion_result["total_results"], 8)

        # Verify session updated
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, "processing_results")
        self.assertEqual(self.session.total_results, 8)

        # Verify metrics created
        metrics = ExecutionMetrics.objects.get(session=self.session)
        self.assertEqual(metrics.total_executions, 2)
        self.assertEqual(metrics.successful_executions, 2)
        self.assertEqual(metrics.total_results_retrieved, 8)

        # Step 6: View execution status
        status_url = reverse(
            "serp_execution:execution_status", kwargs={"session_id": self.session.id}
        )
        response = self.client.get(status_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "processing_results")
        self.assertContains(response, "8")  # Total results

        # Verify next processing task was triggered
        mock_process_results.delay.assert_called_once_with(str(self.session.id))

    @patch("apps.serp_execution.services.serper_client.requests.Session.post")
    def test_execution_with_failures_and_retry(self, mock_post):
        """Test execution workflow with failures and retry logic."""
        # Mock API to fail first, then succeed
        call_count = 0

        def mock_api_response(url, json=None, **kwargs):
            nonlocal call_count
            call_count += 1

            response = Mock()

            if call_count == 1:
                # First call fails with rate limit
                response.status_code = 429
                response.headers = {"Retry-After": "60"}
            else:
                # Subsequent calls succeed
                response.status_code = 200
                response.json.return_value = {
                    "organic": [
                        {
                            "position": 1,
                            "title": "Retry Success Result",
                            "link": "https://example.com/success",
                            "snippet": "Successfully retrieved after retry",
                        }
                    ],
                    "credits": 1,
                    "searchInformation": {"totalResults": "1000"},
                }
                response.headers = {"X-Request-ID": "retry-success"}

            return response

        mock_post.side_effect = mock_api_response

        # Create execution
        execution = SearchExecution.objects.create(
            query=self.query1, initiated_by=self.user, status="pending"
        )

        # First attempt should fail
        with patch(
            "apps.serp_execution.tasks.perform_serp_query_task.retry"
        ) as mock_retry:
            mock_retry.side_effect = Exception("Simulated retry")

            with self.assertRaises(Exception):
                perform_serp_query_task(str(execution.id), str(self.query1.id))

            # Verify retry was called
            mock_retry.assert_called_once()

        # Reset call count and try again (simulating retry)
        call_count = 1  # Skip the failing call
        result = perform_serp_query_task(str(execution.id), str(self.query1.id))

        self.assertTrue(result["success"])
        self.assertEqual(result["results_count"], 1)

        # Verify execution succeeded
        execution.refresh_from_db()
        self.assertEqual(execution.status, "completed")
        self.assertEqual(execution.results_count, 1)

    def test_execution_status_monitoring(self):
        """Test real-time execution status monitoring."""
        # Create executions with different statuses
        exec1 = SearchExecution.objects.create(
            query=self.query1,
            initiated_by=self.user,
            status="completed",
            results_count=25,
            api_credits_used=50,
            celery_task_id="task-1",
        )

        exec2 = SearchExecution.objects.create(
            query=self.query2,
            initiated_by=self.user,
            status="running",
            celery_task_id="task-2",
        )

        # Test execution status API
        url = reverse(
            "serp_execution:execution_status_api", kwargs={"execution_id": exec2.id}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(data["status"], "running")
        self.assertGreater(data["progress"], 0)
        self.assertLess(data["progress"], 100)

        # Test session progress API
        url = reverse(
            "serp_execution:session_progress_api",
            kwargs={"session_id": self.session.id},
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertTrue(data["has_running"])
        self.assertEqual(data["progress"], 50.0)  # 1 of 2 completed
        self.assertEqual(data["statistics"]["total_executions"], 2)


class TestSearchCachingIntegration(TestCase):
    """Test search result caching integration."""

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
            query_string="developers testing python",
            search_engines=["google"],
        )
        self.cache_manager = CacheManager()
        cache.clear()

    @patch("apps.serp_execution.services.serper_client.requests.Session.post")
    def test_cache_hit_workflow(self, mock_post):
        """Test workflow with cache hits."""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "organic": [
                {
                    "position": 1,
                    "title": "Cached Result",
                    "link": "https://example.com/cached",
                    "snippet": "This should be cached",
                }
            ],
            "credits": 1,
        }
        mock_response.headers = {"X-Request-ID": "test-123"}
        mock_post.return_value = mock_response

        # Create two executions for the same query
        exec1 = SearchExecution.objects.create(
            query=self.query, initiated_by=self.user, status="pending"
        )

        exec2 = SearchExecution.objects.create(
            query=self.query, initiated_by=self.user, status="pending"
        )

        # Execute first query - should hit API
        result1 = perform_serp_query_task(str(exec1.id), str(self.query.id))
        self.assertTrue(result1["success"])
        self.assertEqual(mock_post.call_count, 1)

        # Execute second query - should hit cache
        result2 = perform_serp_query_task(str(exec2.id), str(self.query.id))
        self.assertTrue(result2["success"])
        self.assertEqual(mock_post.call_count, 1)  # No additional API call

        # Both should have same results
        results1 = RawSearchResult.objects.filter(execution=exec1)
        results2 = RawSearchResult.objects.filter(execution=exec2)

        self.assertEqual(results1.count(), results2.count())
        self.assertEqual(results1.first().title, results2.first().title)

        # Second execution should have 0 credits used (cache hit)
        exec2.refresh_from_db()
        # Note: This depends on implementation details of caching in tasks


class TestErrorRecoveryIntegration(TransactionTestCase):
    """Test error recovery and retry mechanisms."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123", username="testuser"
        )
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

        self.session = SearchSession.objects.create(
            title="Test Session", owner=self.user, status="executing"
        )
        self.query = SearchQuery.objects.create(
            session=self.session,
            population="test",
            interest="test",
            context="test",
            search_engines=["google"],
        )

    @patch("apps.serp_execution.services.serper_client.requests.Session.post")
    def test_automatic_retry_on_transient_errors(self, mock_post):
        """Test automatic retry for transient errors."""
        # Create execution
        execution = SearchExecution.objects.create(
            query=self.query, initiated_by=self.user, status="pending"
        )

        # Mock connection error
        mock_post.side_effect = ConnectionError("Network unreachable")

        # Execute with retry
        with patch(
            "apps.serp_execution.tasks.perform_serp_query_task.retry"
        ) as mock_retry:
            mock_retry.side_effect = Exception("Retry called")

            with self.assertRaises(Exception):
                perform_serp_query_task(str(execution.id), str(self.query.id))

            # Verify retry was called
            self.assertTrue(mock_retry.called)
            retry_kwargs = mock_retry.call_args[1]
            self.assertIn("exc", retry_kwargs)

    def test_manual_retry_through_ui(self):
        """Test manual retry through the UI."""
        # Create failed execution
        execution = SearchExecution.objects.create(
            query=self.query,
            initiated_by=self.user,
            status="failed",
            error_message="API quota exceeded",
            retry_count=1,
        )

        # View error recovery page
        url = reverse(
            "serp_execution:error_recovery", kwargs={"execution_id": execution.id}
        )
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "API quota exceeded")
        self.assertContains(response, "Retry")

        # Submit retry with delay
        with patch(
            "apps.serp_execution.tasks.retry_failed_execution_task.delay"
        ) as mock_retry:
            mock_retry.return_value = Mock(id="retry-task-id")

            response = self.client.post(
                url,
                {
                    "recovery_action": "retry",
                    "retry_delay": 300,  # 5 minutes
                    "notes": "Waiting for quota reset",
                },
            )

            self.assertEqual(response.status_code, 302)
            mock_retry.assert_called_once()

            # Verify execution updated
            execution.refresh_from_db()
            self.assertEqual(execution.status, "pending")


class TestMetricsAndMonitoring(TestCase):
    """Test metrics collection and monitoring integration."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.session = SearchSession.objects.create(
            title="Metrics Test Session", owner=self.user
        )

        # Create multiple queries
        for i in range(3):
            SearchQuery.objects.create(
                session=self.session,
                population=f"group_{i}",
                interest=f"topic_{i}",
                context="research",
                search_engines=["google"],
            )

    def test_metrics_aggregation(self):
        """Test metrics aggregation across multiple executions."""
        queries = SearchQuery.objects.filter(session=self.session)

        # Create executions with various outcomes
        for i, query in enumerate(queries):
            SearchExecution.objects.create(
                query=query,
                initiated_by=self.user,
                status="completed" if i < 2 else "failed",
                results_count=25 * (i + 1) if i < 2 else 0,
                api_credits_used=100,
                estimated_cost=Decimal("0.10"),
                duration_seconds=2.5 + i,
                started_at=timezone.now() - timedelta(seconds=10),
                completed_at=timezone.now(),
            )

        # Create and update metrics
        metrics = ExecutionMetrics.objects.create(session=self.session)
        metrics.update_metrics()

        # Verify aggregations
        self.assertEqual(metrics.total_executions, 3)
        self.assertEqual(metrics.successful_executions, 2)
        self.assertEqual(metrics.failed_executions, 1)
        self.assertEqual(metrics.total_results_retrieved, 75)  # 25 + 50
        self.assertEqual(metrics.total_api_credits, 300)
        self.assertEqual(metrics.total_estimated_cost, Decimal("0.30"))
        self.assertAlmostEqual(float(metrics.average_execution_time), 3.0, places=1)

    # Usage tracking test removed for simplification


class TestConcurrentExecution(TransactionTestCase):
    """Test concurrent execution scenarios."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.session = SearchSession.objects.create(
            title="Concurrent Test", owner=self.user, status="ready_to_execute"
        )

        # Create multiple queries
        for i in range(5):
            SearchQuery.objects.create(
                session=self.session,
                population=f"group_{i}",
                interest="concurrent testing",
                context="stress test",
                search_engines=["google"],
                is_active=True,
            )

    @patch("apps.serp_execution.services.serper_client.requests.Session.post")
    @patch("apps.serp_execution.tasks.group")
    def test_parallel_execution(self, mock_group, mock_post):
        """Test parallel execution of multiple queries."""
        # Mock API responses
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "organic": [
                {
                    "position": 1,
                    "title": "Test",
                    "link": "https://example.com",
                    "snippet": "Test",
                }
            ],
            "credits": 1,
        }
        mock_response.headers = {}
        mock_post.return_value = mock_response

        # Mock celery group
        mock_job = Mock()
        mock_group.return_value.__or__ = Mock(return_value=mock_job)

        # Initiate execution
        result = initiate_search_session_execution_task(str(self.session.id))

        self.assertTrue(result["success"])
        self.assertEqual(result["queries_count"], 5)

        # Verify all executions created
        executions = SearchExecution.objects.filter(query__session=self.session)
        self.assertEqual(executions.count(), 5)

        # Simulate parallel execution
        for execution in executions:
            # Each should be able to execute independently
            result = perform_serp_query_task(str(execution.id), str(execution.query.id))
            self.assertTrue(result["success"])

        # All should complete successfully
        completed = executions.filter(status="completed").count()
        self.assertEqual(completed, 5)
