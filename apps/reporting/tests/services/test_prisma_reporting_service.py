"""
Tests for PrismaReportingService.

Tests PRISMA-compliant report generation.
"""

from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.reporting.services.prisma_reporting_service import PrismaReportingService
from apps.results_manager.models import ProcessedResult
from apps.review_manager.models import SearchSession
from apps.review_results.models import ReviewTag, ReviewTagAssignment
from apps.search_strategy.models import SearchQuery
from apps.serp_execution.models import RawSearchResult, SearchExecution

User = get_user_model()


class TestPrismaReportingService(TestCase):
    """Test cases for PrismaReportingService."""

    def setUp(self):
        """Set up test data."""
        self.service = PrismaReportingService()

        # Create test user
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Create test session
        self.session = SearchSession.objects.create(
            title="Test Systematic Review",
            description="Test PRISMA review",
            owner=self.user,
            status="completed",
        )

        # Create search queries
        self.query1 = SearchQuery.objects.create(
            session=self.session,
            query_string="systematic review query",
            search_type="standard",
        )

        # Create executions and results
        self.execution = SearchExecution.objects.create(
            query=self.query1,
            search_engine="google",
            status="completed",
            results_count=100,
        )

        # Create raw results
        for i in range(100):
            RawSearchResult.objects.create(
                execution=self.execution,
                title=f"Result {i}",
                link=f"https://example.com/{i}",
                snippet=f"Snippet {i}",
                position=i + 1,
            )

        # Create processed results (80 after deduplication)
        self.processed_results = []
        for i in range(80):
            result = ProcessedResult.objects.create(
                session=self.session,
                title=f"Processed Result {i}",
                url=f"https://example.com/{i}",
                snippet=f"Processed snippet {i}",
                is_pdf=i % 2 == 0,
                publication_year=datetime.now().year - (i % 5),
            )
            self.processed_results.append(result)

        # Create tags
        self.tag_include = ReviewTag.objects.create(name="Include")
        self.tag_exclude = ReviewTag.objects.create(name="Exclude")

        # Tag some results (30 included, 40 excluded, 10 unreviewed)
        for i in range(30):
            ReviewTagAssignment.objects.create(
                result=self.processed_results[i],
                tag=self.tag_include,
                assigned_by=self.user,
            )

        for i in range(30, 70):
            ReviewTagAssignment.objects.create(
                result=self.processed_results[i],
                tag=self.tag_exclude,
                assigned_by=self.user,
                notes="Excluded due to relevance",
            )

    def test_generate_prisma_flow_diagram(self):
        """Test generation of PRISMA flow diagram data."""
        flow_data = self.service.generate_prisma_flow_diagram(str(self.session.id))

        self.assertIsInstance(flow_data, dict)

        # Check identification phase
        self.assertIn("identification", flow_data)
        identification = flow_data["identification"]
        self.assertIn("records_identified", identification)
        self.assertIn("duplicate_records", identification)
        self.assertEqual(identification["records_identified"], 100)
        self.assertEqual(identification["duplicate_records"], 20)

        # Check screening phase
        self.assertIn("screening", flow_data)
        screening = flow_data["screening"]
        self.assertIn("records_screened", screening)
        self.assertIn("records_excluded", screening)
        self.assertEqual(screening["records_screened"], 80)
        self.assertEqual(screening["records_excluded"], 40)

        # Check included phase
        self.assertIn("included", flow_data)
        included = flow_data["included"]
        self.assertIn("studies_included", included)
        self.assertEqual(included["studies_included"], 30)

    def test_generate_prisma_checklist(self):
        """Test generation of PRISMA checklist."""
        checklist = self.service.generate_prisma_checklist(str(self.session.id))

        self.assertIsInstance(checklist, list)
        self.assertTrue(len(checklist) > 0)

        # Check checklist item structure
        for item in checklist:
            self.assertIn("section", item)
            self.assertIn("item_number", item)
            self.assertIn("description", item)
            self.assertIn("completed", item)
            self.assertIn("page_number", item)
            self.assertIsInstance(item["completed"], bool)

        # Check key sections are present
        sections = {item["section"] for item in checklist}
        self.assertIn("Title", sections)
        self.assertIn("Abstract", sections)
        self.assertIn("Methods", sections)
        self.assertIn("Results", sections)
        self.assertIn("Discussion", sections)

    def test_generate_full_prisma_report(self):
        """Test generation of full PRISMA report."""
        report = self.service.generate_full_prisma_report(str(self.session.id))

        self.assertIsInstance(report, dict)

        # Check report sections
        self.assertIn("title", report)
        self.assertIn("abstract", report)
        self.assertIn("introduction", report)
        self.assertIn("methods", report)
        self.assertIn("results", report)
        self.assertIn("discussion", report)
        self.assertIn("conclusions", report)
        self.assertIn("flow_diagram", report)
        self.assertIn("checklist", report)
        self.assertIn("appendices", report)

        # Check methods section
        methods = report["methods"]
        self.assertIn("search_strategy", methods)
        self.assertIn("eligibility_criteria", methods)
        self.assertIn("information_sources", methods)
        self.assertIn("selection_process", methods)

        # Check results section
        results = report["results"]
        self.assertIn("search_results", results)
        self.assertIn("study_characteristics", results)
        self.assertIn("synthesis_results", results)

    def test_calculate_exclusion_reasons(self):
        """Test calculation of exclusion reasons."""
        reasons = self.service.calculate_exclusion_reasons(str(self.session.id))

        self.assertIsInstance(reasons, dict)
        self.assertIn("total_excluded", reasons)
        self.assertIn("reasons", reasons)

        self.assertEqual(reasons["total_excluded"], 40)

        # Check reason breakdown
        reason_list = reasons["reasons"]
        self.assertIsInstance(reason_list, list)

        for reason in reason_list:
            self.assertIn("reason", reason)
            self.assertIn("count", reason)
            self.assertIn("percentage", reason)

    def test_generate_search_strategy_description(self):
        """Test generation of search strategy description."""
        description = self.service.generate_search_strategy_description(
            str(self.session.id)
        )

        self.assertIsInstance(description, dict)
        self.assertIn("databases_searched", description)
        self.assertIn("search_terms", description)
        self.assertIn("search_dates", description)
        self.assertIn("restrictions", description)
        self.assertIn("search_strings", description)

        # Check search strings
        search_strings = description["search_strings"]
        self.assertIsInstance(search_strings, list)
        self.assertTrue(len(search_strings) > 0)

    def test_generate_study_characteristics_table(self):
        """Test generation of study characteristics table."""
        table = self.service.generate_study_characteristics_table(str(self.session.id))

        self.assertIsInstance(table, list)
        self.assertEqual(len(table), 30)  # Only included studies

        for row in table:
            self.assertIn("study_id", row)
            self.assertIn("title", row)
            self.assertIn("url", row)
            self.assertIn("publication_year", row)
            self.assertIn("document_type", row)
            self.assertIn("key_findings", row)

    def test_generate_quality_assessment_summary(self):
        """Test generation of quality assessment summary."""
        summary = self.service.generate_quality_assessment_summary(str(self.session.id))

        self.assertIsInstance(summary, dict)
        self.assertIn("total_assessed", summary)
        self.assertIn("quality_scores", summary)
        self.assertIn("risk_of_bias", summary)
        self.assertIn("confidence_assessment", summary)

    def test_format_report_for_export(self):
        """Test formatting report for different export formats."""
        report = self.service.generate_full_prisma_report(str(self.session.id))

        # Test Word format
        word_format = self.service.format_report_for_export(report, "docx")
        self.assertIn("formatted_content", word_format)
        self.assertIn("export_type", word_format)
        self.assertEqual(word_format["export_type"], "docx")

        # Test PDF format
        pdf_format = self.service.format_report_for_export(report, "pdf")
        self.assertIn("formatted_content", pdf_format)
        self.assertEqual(pdf_format["export_type"], "pdf")

        # Test HTML format
        html_format = self.service.format_report_for_export(report, "html")
        self.assertIn("formatted_content", html_format)
        self.assertEqual(html_format["export_type"], "html")

    def test_validate_prisma_compliance(self):
        """Test validation of PRISMA compliance."""
        compliance = self.service.validate_prisma_compliance(str(self.session.id))

        self.assertIsInstance(compliance, dict)
        self.assertIn("is_compliant", compliance)
        self.assertIn("compliance_score", compliance)
        self.assertIn("missing_elements", compliance)
        self.assertIn("recommendations", compliance)

        # Check compliance score is percentage
        self.assertGreaterEqual(compliance["compliance_score"], 0)
        self.assertLessEqual(compliance["compliance_score"], 100)

        # Check missing elements
        missing = compliance["missing_elements"]
        self.assertIsInstance(missing, list)

        for element in missing:
            self.assertIn("element", element)
            self.assertIn("importance", element)
            self.assertIn("description", element)

    def test_generate_prisma_abstract(self):
        """Test generation of PRISMA-compliant abstract."""
        abstract = self.service.generate_prisma_abstract(str(self.session.id))

        self.assertIsInstance(abstract, dict)
        self.assertIn("background", abstract)
        self.assertIn("objectives", abstract)
        self.assertIn("methods", abstract)
        self.assertIn("results", abstract)
        self.assertIn("conclusions", abstract)
        self.assertIn("registration", abstract)

        # Check word counts
        for section in abstract.values():
            self.assertIsInstance(section, str)
            self.assertTrue(len(section) > 0)

    def test_report_with_incomplete_review(self):
        """Test report generation with incomplete review."""
        # Create session still under review
        incomplete_session = SearchSession.objects.create(
            title="Incomplete Review",
            description="Still in progress",
            owner=self.user,
            status="under_review",
        )

        report = self.service.generate_full_prisma_report(str(incomplete_session.id))

        self.assertIn("warnings", report)
        warnings = report["warnings"]
        self.assertTrue(any("incomplete" in w.lower() for w in warnings))

    def test_logging_in_report_generation(self):
        """Test that report generation is properly logged."""
        with self.assertLogs(
            "apps.reporting.services.prisma_reporting_service", level="INFO"
        ) as cm:
            self.service.generate_full_prisma_report(str(self.session.id))

        self.assertTrue(any("Generating PRISMA report" in msg for msg in cm.output))
        self.assertTrue(any("PRISMA report generated" in msg for msg in cm.output))
