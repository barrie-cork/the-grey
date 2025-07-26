"""
Tests for QualityAssessmentService.

Tests result quality assessment and scoring functionality.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.results_manager.models import ProcessedResult
from apps.results_manager.services.quality_assessment_service import (
    QualityAssessmentService,
)
from apps.review_manager.models import SearchSession

User = get_user_model()


class TestQualityAssessmentService(TestCase):
    """Test cases for QualityAssessmentService."""

    def setUp(self):
        """Set up test data."""
        self.service = QualityAssessmentService()

        # Create test user
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Create test session
        self.session = SearchSession.objects.create(
            title="Test Quality Assessment",
            description="Testing quality assessment",
            owner=self.user,
            status="ready_for_review",
        )

        # Create test results with varying quality
        self.results = []

        # High quality result
        self.results.append(
            ProcessedResult.objects.create(
                session=self.session,
                title="Comprehensive Systematic Review of AI in Healthcare: A Multi-Center Study",
                url="https://journal.medical.edu/systematic-review-ai-healthcare.pdf",
                snippet="This systematic review analyzes 500 studies across 50 medical centers examining the impact of artificial intelligence on patient outcomes, diagnostic accuracy, and healthcare efficiency. Methods include meta-analysis and rigorous quality assessment.",
                publication_year=2024,
                document_type="journal_article",
                is_pdf=True,
            )
        )

        # Medium quality result
        self.results.append(
            ProcessedResult.objects.create(
                session=self.session,
                title="AI Healthcare Report",
                url="https://blog.tech.com/ai-healthcare",
                snippet="Brief overview of AI in healthcare with some statistics.",
                publication_year=2023,
                document_type="blog_post",
                is_pdf=False,
            )
        )

        # Low quality result
        self.results.append(
            ProcessedResult.objects.create(
                session=self.session,
                title="Healthcare AI",
                url="https://example.com/page",
                snippet="AI healthcare stuff",
                publication_year=None,
                document_type="unknown",
                is_pdf=False,
            )
        )

    def test_assess_result_quality(self):
        """Test quality assessment for individual results."""
        for result in self.results:
            quality = self.service.assess_result_quality(result)

            self.assertIsInstance(quality, dict)
            self.assertIn("overall_score", quality)
            self.assertIn("dimensions", quality)
            self.assertIn("flags", quality)
            self.assertIn("recommendations", quality)

            # Check score range
            self.assertGreaterEqual(quality["overall_score"], 0)
            self.assertLessEqual(quality["overall_score"], 1)

            # Check dimensions
            dimensions = quality["dimensions"]
            expected_dims = [
                "title_quality",
                "snippet_quality",
                "metadata_completeness",
                "source_reliability",
                "relevance",
            ]

            for dim in expected_dims:
                self.assertIn(dim, dimensions)
                self.assertGreaterEqual(dimensions[dim], 0)
                self.assertLessEqual(dimensions[dim], 1)

    def test_calculate_title_quality(self):
        """Test title quality calculation."""
        test_titles = [
            ("Comprehensive Study: Effects of X on Y in Z Population", 0.9),  # High
            ("Study of Healthcare AI", 0.6),  # Medium
            ("healthcare", 0.2),  # Low
            ("", 0.0),  # Empty
        ]

        for title, expected_min_score in test_titles:
            score = self.service.calculate_title_quality(title)
            self.assertGreaterEqual(
                score,
                expected_min_score,
                f"Title '{title}' scored {score}, expected >= {expected_min_score}",
            )

    def test_calculate_snippet_quality(self):
        """Test snippet quality calculation."""
        test_snippets = [
            (
                "This comprehensive systematic review examines the impact of artificial intelligence on clinical outcomes. We analyzed 200 peer-reviewed studies using PRISMA guidelines. Results show significant improvements in diagnostic accuracy (p<0.001).",
                0.8,  # High quality
            ),
            ("Brief overview of AI in healthcare.", 0.4),  # Low quality
            ("AI stuff", 0.1),  # Very low quality
        ]

        for snippet, expected_min_score in test_snippets:
            score = self.service.calculate_snippet_quality(snippet)
            self.assertGreaterEqual(
                score,
                expected_min_score,
                f"Snippet scored {score}, expected >= {expected_min_score}",
            )

    def test_assess_metadata_completeness(self):
        """Test metadata completeness assessment."""
        # Complete metadata
        complete_result = ProcessedResult.objects.create(
            session=self.session,
            title="Complete Metadata Result",
            url="https://example.com/complete",
            snippet="Full snippet",
            publication_year=2024,
            document_type="journal_article",
            is_pdf=True,
            authors=["Smith, J.", "Doe, A."],
            source_organization="Medical AI Journal",
        )

        completeness = self.service.assess_metadata_completeness(complete_result)
        self.assertGreater(completeness, 0.8)

        # Incomplete metadata
        incomplete_result = ProcessedResult.objects.create(
            session=self.session,
            title="Incomplete",
            url="https://example.com/incomplete",
            snippet="Brief",
            is_pdf=False,
        )

        completeness = self.service.assess_metadata_completeness(incomplete_result)
        self.assertLess(completeness, 0.5)

    def test_evaluate_source_reliability(self):
        """Test source reliability evaluation."""
        test_sources = [
            ("https://journal.nature.com/article", 0.9),  # High reliability
            ("https://university.edu/research/paper", 0.8),  # Academic
            ("https://www.who.int/report", 0.85),  # Government/org
            ("https://blog.personal.com/post", 0.3),  # Low reliability
            ("https://unknown-site.xyz/page", 0.2),  # Unknown
        ]

        for url, expected_min_score in test_sources:
            result = ProcessedResult.objects.create(
                session=self.session,
                title="Test",
                url=url,
                snippet="Test snippet",
                is_pdf=False,
            )

            reliability = self.service.evaluate_source_reliability(result)
            self.assertGreaterEqual(
                reliability,
                expected_min_score,
                f"URL {url} reliability {reliability}, expected >= {expected_min_score}",
            )

    def test_batch_quality_assessment(self):
        """Test batch quality assessment for multiple results."""
        assessments = self.service.batch_quality_assessment(self.results)

        self.assertIsInstance(assessments, list)
        self.assertEqual(len(assessments), len(self.results))

        # Check that results are ordered by quality
        scores = [a["overall_score"] for a in assessments]
        self.assertEqual(scores, sorted(scores, reverse=True))

        # High quality result should score highest
        self.assertGreater(assessments[0]["overall_score"], 0.8)
        # Low quality result should score lowest
        self.assertLess(assessments[-1]["overall_score"], 0.4)

    def test_generate_quality_report(self):
        """Test generation of quality report for session."""
        report = self.service.generate_quality_report(str(self.session.id))

        self.assertIsInstance(report, dict)
        self.assertIn("summary", report)
        self.assertIn("distribution", report)
        self.assertIn("dimension_analysis", report)
        self.assertIn("recommendations", report)

        # Check summary statistics
        summary = report["summary"]
        self.assertIn("total_results", summary)
        self.assertIn("average_quality_score", summary)
        self.assertIn("high_quality_count", summary)
        self.assertIn("low_quality_count", summary)

        self.assertEqual(summary["total_results"], 3)

    def test_identify_quality_issues(self):
        """Test identification of specific quality issues."""
        for result in self.results:
            issues = self.service.identify_quality_issues(result)

            self.assertIsInstance(issues, list)

            for issue in issues:
                self.assertIn("issue_type", issue)
                self.assertIn("severity", issue)
                self.assertIn("description", issue)
                self.assertIn("impact", issue)
                self.assertIn(["critical", "major", "minor"], issue["severity"])

    def test_calculate_quality_distribution(self):
        """Test calculation of quality score distribution."""
        distribution = self.service.calculate_quality_distribution(self.results)

        self.assertIsInstance(distribution, dict)
        self.assertIn("bins", distribution)
        self.assertIn("counts", distribution)
        self.assertIn("percentiles", distribution)
        self.assertIn("statistics", distribution)

        # Check statistics
        stats = distribution["statistics"]
        self.assertIn("mean", stats)
        self.assertIn("median", stats)
        self.assertIn("std_dev", stats)
        self.assertIn("min", stats)
        self.assertIn("max", stats)

    def test_flag_outliers(self):
        """Test flagging of quality outliers."""
        # Add more results to create distribution
        for i in range(10):
            ProcessedResult.objects.create(
                session=self.session,
                title=f"Normal Quality Result {i}",
                url=f"https://journal.com/article{i}",
                snippet=f"Standard research article about topic {i}",
                publication_year=2023,
                is_pdf=True,
            )

        all_results = ProcessedResult.objects.filter(session=self.session)
        outliers = self.service.flag_quality_outliers(list(all_results))

        self.assertIsInstance(outliers, dict)
        self.assertIn("high_outliers", outliers)
        self.assertIn("low_outliers", outliers)

        # The very low quality result should be flagged
        low_outlier_ids = [r.id for r in outliers["low_outliers"]]
        self.assertIn(self.results[2].id, low_outlier_ids)

    def test_generate_improvement_suggestions(self):
        """Test generation of quality improvement suggestions."""
        for result in self.results:
            suggestions = self.service.generate_improvement_suggestions(result)

            self.assertIsInstance(suggestions, list)

            for suggestion in suggestions:
                self.assertIn("field", suggestion)
                self.assertIn("current_quality", suggestion)
                self.assertIn("suggestion", suggestion)
                self.assertIn("priority", suggestion)
                self.assertIn("potential_improvement", suggestion)

    def test_compare_quality_across_sources(self):
        """Test quality comparison across different sources."""
        # Add results from different sources
        sources = ["journal.medical.edu", "blog.tech.com", "news.site.com"]

        for source in sources:
            for i in range(3):
                ProcessedResult.objects.create(
                    session=self.session,
                    title=f"Article from {source} #{i}",
                    url=f"https://{source}/article{i}",
                    snippet=f"Content from {source}",
                    is_pdf=i % 2 == 0,
                )

        comparison = self.service.compare_quality_across_sources(str(self.session.id))

        self.assertIsInstance(comparison, dict)

        for source in sources:
            self.assertIn(source, comparison)
            source_data = comparison[source]
            self.assertIn("average_quality", source_data)
            self.assertIn("result_count", source_data)
            self.assertIn("quality_range", source_data)

    def test_quality_threshold_filtering(self):
        """Test filtering results by quality threshold."""
        threshold = 0.7

        high_quality = self.service.filter_by_quality_threshold(self.results, threshold)

        self.assertIsInstance(high_quality, list)
        # Only the first result should pass the threshold
        self.assertEqual(len(high_quality), 1)
        self.assertEqual(high_quality[0].id, self.results[0].id)

        # Test with lower threshold
        low_threshold = 0.3
        more_results = self.service.filter_by_quality_threshold(
            self.results, low_threshold
        )

        self.assertGreater(len(more_results), len(high_quality))

    def test_temporal_quality_analysis(self):
        """Test quality analysis over time."""
        # Add results with different years
        for year in range(2020, 2025):
            for i in range(3):
                ProcessedResult.objects.create(
                    session=self.session,
                    title=f"Study from {year}",
                    url=f"https://journal.com/{year}/study{i}",
                    snippet=f"Research conducted in {year}",
                    publication_year=year,
                    is_pdf=year >= 2022,
                )

        temporal_analysis = self.service.analyze_quality_by_time(str(self.session.id))

        self.assertIsInstance(temporal_analysis, dict)
        self.assertIn("yearly_quality", temporal_analysis)
        self.assertIn("quality_trend", temporal_analysis)
        self.assertIn("recent_vs_older", temporal_analysis)

    def test_logging_in_quality_assessment(self):
        """Test that quality assessment operations are properly logged."""
        with self.assertLogs(
            "apps.results_manager.services.quality_assessment_service", level="INFO"
        ) as cm:
            self.service.assess_result_quality(self.results[0])

        self.assertTrue(any("Assessing quality" in msg for msg in cm.output))
        self.assertTrue(any("Quality assessment completed" in msg for msg in cm.output))
