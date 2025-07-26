"""
Tests for additional SERP execution services.

Tests for ContentAnalysisService, CostService, ExecutionService, and MonitoringService.
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.review_manager.models import SearchSession
from apps.search_strategy.models import SearchQuery
from apps.serp_execution.models import RawSearchResult, SearchExecution
from apps.serp_execution.services.content_analysis_service import ContentAnalysisService
from apps.serp_execution.services.cost_service import CostService
from apps.serp_execution.services.execution_service import ExecutionService
from apps.serp_execution.services.monitoring_service import MonitoringService

User = get_user_model()


class TestContentAnalysisService(TestCase):
    """Test cases for ContentAnalysisService."""

    def setUp(self):
        """Set up test data."""
        self.service = ContentAnalysisService()

    def test_detect_content_type(self):
        """Test content type detection."""
        test_cases = [
            # (url, title, snippet, expected_results)
            (
                "https://example.com/document.pdf",
                "Research Paper PDF",
                "This is a PDF document",
                {"is_pdf": True, "is_academic": True, "is_news": False},
            ),
            (
                "https://news.site.com/article/breaking",
                "Breaking News: Latest Updates",
                "Today in breaking news...",
                {"is_pdf": False, "is_academic": False, "is_news": True},
            ),
            (
                "https://journal.academic.edu/paper",
                "Systematic Review of AI Applications",
                "This systematic review examines...",
                {"is_pdf": False, "is_academic": True, "is_news": False},
            ),
            (
                "https://blog.com/post",
                "My thoughts on technology",
                "In this blog post I discuss...",
                {"is_pdf": False, "is_academic": False, "is_news": False},
            ),
        ]

        for url, title, snippet, expected in test_cases:
            result = self.service.detect_content_type(url, title, snippet)

            self.assertEqual(result["is_pdf"], expected["is_pdf"])
            self.assertEqual(result["is_academic"], expected["is_academic"])
            self.assertEqual(result["is_news"], expected["is_news"])

    def test_extract_key_information(self):
        """Test extraction of key information from content."""
        title = "Effects of Climate Change on Marine Ecosystems: A 10-Year Study"
        snippet = """This comprehensive study examines the impact of climate change on marine 
        ecosystems over a 10-year period from 2014 to 2024. Results show significant 
        changes in species distribution and ocean acidification levels."""

        info = self.service.extract_key_information(title, snippet)

        self.assertIsInstance(info, dict)
        self.assertIn("topics", info)
        self.assertIn("time_period", info)
        self.assertIn("key_findings", info)
        self.assertIn("research_type", info)

        # Check extracted information
        self.assertIn("climate change", info["topics"])
        self.assertIn("marine ecosystems", info["topics"])
        self.assertIn("10-year", info["time_period"])

    def test_calculate_content_quality_score(self):
        """Test content quality scoring."""
        test_cases = [
            # High quality
            (
                "Comprehensive Analysis of Machine Learning in Healthcare: A Systematic Review",
                "This systematic review analyzes 500 peer-reviewed studies on machine learning applications in healthcare, following PRISMA guidelines. We found significant improvements in diagnostic accuracy.",
                0.8,  # Expected minimum score
            ),
            # Low quality
            ("AI stuff", "Some info about AI", 0.3),  # Expected maximum score
        ]

        for title, snippet, expected_threshold in test_cases:
            score = self.service.calculate_content_quality_score(title, snippet)

            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 1)

            if expected_threshold > 0.5:
                self.assertGreater(score, expected_threshold)
            else:
                self.assertLess(score, expected_threshold)

    def test_detect_language(self):
        """Test language detection."""
        test_cases = [
            ("This is an English text about research", "en"),
            ("Ceci est un texte en français", "fr"),
            ("Este es un texto en español", "es"),
            ("", "unknown"),
        ]

        for text, expected_lang in test_cases:
            detected = self.service.detect_language(text)
            if expected_lang != "unknown":
                self.assertEqual(detected, expected_lang)

    def test_extract_publication_info(self):
        """Test extraction of publication information."""
        snippets = [
            "Published in Nature Journal, Volume 123, Issue 4, Pages 234-256",
            "Conference Proceedings of ICML 2024",
            "Technical Report TR-2024-001 from MIT",
            "Blog post with no publication info",
        ]

        for snippet in snippets:
            pub_info = self.service.extract_publication_info(snippet)

            self.assertIsInstance(pub_info, dict)
            self.assertIn("journal_name", pub_info)
            self.assertIn("volume", pub_info)
            self.assertIn("issue", pub_info)
            self.assertIn("pages", pub_info)
            self.assertIn("publication_type", pub_info)


class TestCostService(TestCase):
    """Test cases for CostService."""

    def setUp(self):
        """Set up test data."""
        self.service = CostService()

        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.session = SearchSession.objects.create(
            title="Test Session", owner=self.user
        )

        self.query = SearchQuery.objects.create(
            session=self.session, query_string="test query", target_results=100
        )

    def test_calculate_execution_cost(self):
        """Test calculation of execution cost."""
        execution = SearchExecution.objects.create(
            query=self.query,
            search_engine="google",
            results_count=50,
            status="completed",
        )

        cost = self.service.calculate_execution_cost(execution)

        self.assertIsInstance(cost, Decimal)
        self.assertGreater(cost, 0)
        # Default cost should be 50 * 0.01 = 0.50
        self.assertEqual(cost, Decimal("0.50"))

    def test_calculate_session_cost(self):
        """Test calculation of total session cost."""
        # Create multiple executions
        for i in range(3):
            SearchExecution.objects.create(
                query=self.query,
                search_engine="google",
                results_count=30 + (i * 10),
                estimated_cost=Decimal("0.30") + (i * Decimal("0.10")),
                status="completed",
            )

        total_cost = self.service.calculate_session_cost(str(self.session.id))

        self.assertEqual(total_cost, Decimal("1.20"))  # 0.30 + 0.40 + 0.50

    def test_estimate_remaining_cost(self):
        """Test estimation of remaining cost."""
        # Create pending queries
        for i in range(2):
            SearchQuery.objects.create(
                session=self.session,
                query_string=f"pending query {i}",
                target_results=50,
            )

        estimate = self.service.estimate_remaining_cost(str(self.session.id))

        self.assertIsInstance(estimate, dict)
        self.assertIn("estimated_cost", estimate)
        self.assertIn("pending_queries", estimate)
        self.assertIn("average_cost_per_query", estimate)

        self.assertEqual(estimate["pending_queries"], 2)
        self.assertGreater(estimate["estimated_cost"], 0)

    def test_get_cost_breakdown(self):
        """Test detailed cost breakdown."""
        # Create executions with different engines
        engines = ["google", "bing", "google"]
        for i, engine in enumerate(engines):
            SearchExecution.objects.create(
                query=self.query,
                search_engine=engine,
                results_count=40,
                estimated_cost=Decimal("0.40"),
                status="completed",
            )

        breakdown = self.service.get_cost_breakdown(str(self.session.id))

        self.assertIn("by_engine", breakdown)
        self.assertIn("by_query", breakdown)
        self.assertIn("by_date", breakdown)
        self.assertIn("total", breakdown)

        # Check engine breakdown
        self.assertEqual(breakdown["by_engine"]["google"], Decimal("0.80"))
        self.assertEqual(breakdown["by_engine"]["bing"], Decimal("0.40"))
        self.assertEqual(breakdown["total"], Decimal("1.20"))

    def test_cost_alerts(self):
        """Test cost threshold alerts."""
        # Set high costs
        for i in range(10):
            SearchExecution.objects.create(
                query=self.query,
                search_engine="google",
                results_count=100,
                estimated_cost=Decimal("1.00"),
                status="completed",
            )

        alerts = self.service.check_cost_alerts(
            str(self.session.id), threshold=Decimal("5.00")
        )

        self.assertIsInstance(alerts, list)
        self.assertTrue(len(alerts) > 0)

        for alert in alerts:
            self.assertIn("type", alert)
            self.assertIn("message", alert)
            self.assertIn("severity", alert)


class TestExecutionService(TestCase):
    """Test cases for ExecutionService."""

    def setUp(self):
        """Set up test data."""
        self.service = ExecutionService()

        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.session = SearchSession.objects.create(
            title="Test Session", owner=self.user, status="executing"
        )

        self.query = SearchQuery.objects.create(
            session=self.session,
            query_string="machine learning healthcare",
            target_results=50,
        )

    @patch("apps.serp_execution.services.execution_service.SerperClient")
    def test_execute_query(self, mock_serper_client):
        """Test query execution."""
        # Mock Serper response
        mock_client = MagicMock()
        mock_serper_client.return_value = mock_client
        mock_client.search.return_value = {
            "organic": [
                {
                    "title": "ML in Healthcare Study",
                    "link": "https://example.com/study",
                    "snippet": "Study about ML in healthcare",
                    "position": 1,
                }
            ],
            "searchParameters": {"q": "machine learning healthcare", "num": 50},
        }

        execution = self.service.execute_query(self.query)

        self.assertIsInstance(execution, SearchExecution)
        self.assertEqual(execution.status, "completed")
        self.assertEqual(execution.results_count, 1)

        # Check that raw results were created
        raw_results = RawSearchResult.objects.filter(execution=execution)
        self.assertEqual(raw_results.count(), 1)

    @patch("apps.serp_execution.services.execution_service.SerperClient")
    def test_execute_query_with_error(self, mock_serper_client):
        """Test query execution with API error."""
        mock_client = MagicMock()
        mock_serper_client.return_value = mock_client
        mock_client.search.side_effect = Exception("API Error")

        execution = self.service.execute_query(self.query)

        self.assertEqual(execution.status, "failed")
        self.assertIn("API Error", execution.error_message)

    def test_retry_failed_execution(self):
        """Test retrying failed executions."""
        # Create failed execution
        failed_execution = SearchExecution.objects.create(
            query=self.query,
            search_engine="google",
            status="failed",
            error_message="Temporary error",
            retry_count=0,
        )

        with patch.object(self.service, "execute_query") as mock_execute:
            mock_execute.return_value = SearchExecution.objects.create(
                query=self.query,
                search_engine="google",
                status="completed",
                results_count=10,
            )

            result = self.service.retry_failed_execution(failed_execution)

            self.assertTrue(result)
            failed_execution.refresh_from_db()
            self.assertEqual(failed_execution.retry_count, 1)

    def test_bulk_execution(self):
        """Test bulk query execution."""
        # Create multiple queries
        queries = []
        for i in range(3):
            query = SearchQuery.objects.create(
                session=self.session, query_string=f"test query {i}", target_results=20
            )
            queries.append(query)

        with patch.object(self.service, "execute_query") as mock_execute:
            mock_execute.return_value = MagicMock(status="completed")

            results = self.service.execute_bulk_queries(queries)

            self.assertEqual(len(results), 3)
            self.assertEqual(mock_execute.call_count, 3)

    def test_execution_validation(self):
        """Test execution validation before running."""
        # Query with invalid session status
        invalid_session = SearchSession.objects.create(
            title="Invalid Session",
            owner=self.user,
            status="completed",  # Can't execute on completed session
        )

        invalid_query = SearchQuery.objects.create(
            session=invalid_session, query_string="test"
        )

        is_valid, errors = self.service.validate_execution(invalid_query)

        self.assertFalse(is_valid)
        self.assertTrue(len(errors) > 0)


class TestMonitoringService(TestCase):
    """Test cases for MonitoringService (already tested in previous implementation)."""

    def setUp(self):
        """Set up test data."""
        self.service = MonitoringService()

        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        self.session = SearchSession.objects.create(
            title="Test Session", owner=self.user
        )

        self.query = SearchQuery.objects.create(
            session=self.session, query_string="test query"
        )

        # Create test executions
        self.execution1 = SearchExecution.objects.create(
            query=self.query,
            search_engine="google",
            status="completed",
            results_count=50,
            duration_seconds=2.5,
            estimated_cost=Decimal("0.50"),
        )

        self.execution2 = SearchExecution.objects.create(
            query=self.query,
            search_engine="google",
            status="failed",
            error_message="Rate limit exceeded",
        )

    def test_get_execution_statistics(self):
        """Test basic execution statistics."""
        stats = self.service.get_execution_statistics(str(self.session.id))

        self.assertEqual(stats["total_executions"], 2)
        self.assertEqual(stats["successful_executions"], 1)
        self.assertEqual(stats["failed_executions"], 1)
        self.assertEqual(stats["success_rate"], 50.0)
        self.assertEqual(stats["total_results"], 50)

    def test_get_failed_executions_with_analysis(self):
        """Test failed execution analysis."""
        failures = self.service.get_failed_executions_with_analysis(
            str(self.session.id)
        )

        self.assertEqual(len(failures), 1)

        failure = failures[0]
        self.assertEqual(failure["execution_id"], str(self.execution2.id))
        self.assertEqual(failure["failure_category"], "rate_limit")
        self.assertIn("retry", failure["suggested_action"].lower())

    def test_categorize_failure(self):
        """Test failure categorization."""
        test_cases = [
            ("Rate limit exceeded", "rate_limit"),
            ("Connection timeout", "timeout"),
            ("Network error", "network"),
            ("Invalid API key", "authentication"),
            ("Quota exceeded", "quota_exceeded"),
            ("Unknown error", "api_error"),
        ]

        for error_msg, expected_category in test_cases:
            category = self.service.categorize_failure(error_msg)
            self.assertEqual(category, expected_category)

    def test_optimize_retry_strategy(self):
        """Test retry strategy optimization."""
        strategy = self.service.optimize_retry_strategy(self.execution2)

        self.assertIn("should_retry", strategy)
        self.assertIn("delay_seconds", strategy)
        self.assertIn("modifications", strategy)
        self.assertIn("priority", strategy)

        # Rate limit should suggest retry
        self.assertTrue(strategy["should_retry"])
        self.assertGreater(strategy["delay_seconds"], 0)
