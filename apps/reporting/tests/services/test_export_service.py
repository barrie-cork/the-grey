"""
Tests for ExportService.

Tests data export functionality in various formats (CSV, JSON, Excel).
"""

import csv
import json
from datetime import datetime
from io import StringIO
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.reporting.services.export_service import ExportService
from apps.results_manager.models import ProcessedResult
from apps.review_manager.models import SearchSession
from apps.review_results.models import ReviewTag, ReviewTagAssignment

User = get_user_model()


class TestExportService(TestCase):
    """Test cases for ExportService."""

    def setUp(self):
        """Set up test data."""
        self.service = ExportService()

        # Create test user
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

        # Create test session
        self.session = SearchSession.objects.create(
            title="Test Session",
            description="Test description",
            owner=self.user,
            status="completed",
        )

        # Create test results
        self.result1 = ProcessedResult.objects.create(
            session=self.session,
            title="Test Result 1",
            url="https://example.com/1",
            snippet="Test snippet 1",
            is_pdf=True,
            publication_year=datetime.now().year,
        )

        self.result2 = ProcessedResult.objects.create(
            session=self.session,
            title="Test Result 2",
            url="https://example.com/2",
            snippet="Test snippet 2",
            is_pdf=False,
            publication_year=datetime.now().year - 1,
        )

        # Create test tags
        self.tag_include = ReviewTag.objects.create(
            name="Include", description="Include in review"
        )

        self.tag_exclude = ReviewTag.objects.create(
            name="Exclude", description="Exclude from review"
        )

        # Create tag assignments
        ReviewTagAssignment.objects.create(
            result=self.result1,
            tag=self.tag_include,
            assigned_by=self.user,
            notes="Good quality result",
        )

    def test_export_to_csv_success(self):
        """Test successful CSV export."""
        result = self.service.export_to_csv(str(self.session.id))

        self.assertIsInstance(result, dict)
        self.assertIn("content", result)
        self.assertIn("filename", result)
        self.assertIn("content_type", result)
        self.assertEqual(result["content_type"], "text/csv")

        # Parse CSV content
        csv_content = StringIO(result["content"])
        reader = csv.DictReader(csv_content)
        rows = list(reader)

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["title"], "Test Result 1")
        self.assertEqual(rows[0]["tags"], "Include")

    def test_export_to_json_success(self):
        """Test successful JSON export."""
        result = self.service.export_to_json(str(self.session.id))

        self.assertIsInstance(result, dict)
        self.assertIn("content", result)
        self.assertIn("filename", result)
        self.assertIn("content_type", result)
        self.assertEqual(result["content_type"], "application/json")

        # Parse JSON content
        json_data = json.loads(result["content"])

        self.assertIn("session", json_data)
        self.assertIn("results", json_data)
        self.assertIn("export_metadata", json_data)
        self.assertEqual(len(json_data["results"]), 2)
        self.assertEqual(json_data["results"][0]["title"], "Test Result 1")

    @patch("apps.reporting.services.export_service.xlsxwriter")
    def test_export_to_excel_success(self, mock_xlsxwriter):
        """Test successful Excel export."""
        # Mock Excel writer
        mock_workbook = MagicMock()
        mock_worksheet = MagicMock()
        mock_xlsxwriter.Workbook.return_value = mock_workbook
        mock_workbook.add_worksheet.return_value = mock_worksheet

        result = self.service.export_to_excel(str(self.session.id))

        self.assertIsInstance(result, dict)
        self.assertIn("content", result)
        self.assertIn("filename", result)
        self.assertIn("content_type", result)
        self.assertEqual(
            result["content_type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        # Verify Excel methods were called
        mock_workbook.add_worksheet.assert_called()
        mock_worksheet.write_row.assert_called()
        mock_workbook.close.assert_called()

    def test_export_with_invalid_session_id(self):
        """Test export with invalid session ID."""
        with self.assertRaises(ValueError):
            self.service.export_to_csv("invalid-uuid")

    def test_export_with_nonexistent_session(self):
        """Test export with non-existent session."""
        from uuid import uuid4

        fake_id = str(uuid4())

        with self.assertRaises(SearchSession.DoesNotExist):
            self.service.export_to_csv(fake_id)

    def test_export_empty_session(self):
        """Test export of session with no results."""
        empty_session = SearchSession.objects.create(
            title="Empty Session",
            description="No results",
            owner=self.user,
            status="completed",
        )

        result = self.service.export_to_csv(str(empty_session.id))

        csv_content = StringIO(result["content"])
        reader = csv.DictReader(csv_content)
        rows = list(reader)

        self.assertEqual(len(rows), 0)

    def test_export_with_complex_tags(self):
        """Test export with multiple tags per result."""
        # Add another tag to result1
        tag_maybe = ReviewTag.objects.create(name="Maybe", description="Uncertain")

        ReviewTagAssignment.objects.create(
            result=self.result1,
            tag=tag_maybe,
            assigned_by=self.user,
            notes="Need further review",
        )

        result = self.service.export_to_csv(str(self.session.id))

        csv_content = StringIO(result["content"])
        reader = csv.DictReader(csv_content)
        rows = list(reader)

        # Check that multiple tags are properly formatted
        self.assertIn("Include", rows[0]["tags"])
        self.assertIn("Maybe", rows[0]["tags"])

    def test_export_preserves_special_characters(self):
        """Test that export properly handles special characters."""
        special_result = ProcessedResult.objects.create(
            session=self.session,
            title='Test with "quotes" & special <chars>',
            url="https://example.com/special",
            snippet="Contains newline\nand tab\tcharacters",
            relevance_score=0.90,
        )

        result = self.service.export_to_csv(str(self.session.id))

        # Verify special characters are properly escaped
        self.assertIn("quotes", result["content"])
        self.assertIn("special", result["content"])

    @patch("apps.reporting.services.export_service.datetime")
    def test_export_filename_generation(self, mock_datetime):
        """Test that export filenames are generated correctly."""
        mock_datetime.now.return_value.strftime.return_value = "20250126_120000"

        csv_result = self.service.export_to_csv(str(self.session.id))
        json_result = self.service.export_to_json(str(self.session.id))
        excel_result = self.service.export_to_excel(str(self.session.id))

        self.assertIn("test_session", csv_result["filename"].lower())
        self.assertIn("20250126_120000", csv_result["filename"])
        self.assertIn(".csv", csv_result["filename"])

        self.assertIn(".json", json_result["filename"])
        self.assertIn(".xlsx", excel_result["filename"])

    def test_export_includes_metadata(self):
        """Test that exports include proper metadata."""
        result = self.service.export_to_json(str(self.session.id))
        json_data = json.loads(result["content"])

        self.assertIn("export_metadata", json_data)
        metadata = json_data["export_metadata"]

        self.assertIn("export_date", metadata)
        self.assertIn("total_results", metadata)
        self.assertIn("reviewed_results", metadata)
        self.assertIn("session_status", metadata)

        self.assertEqual(metadata["total_results"], 2)
        self.assertEqual(metadata["reviewed_results"], 1)
        self.assertEqual(metadata["session_status"], "completed")

    def test_logging_on_export(self):
        """Test that exports are properly logged."""
        with self.assertLogs(
            "apps.reporting.services.export_service", level="INFO"
        ) as cm:
            self.service.export_to_csv(str(self.session.id))

        self.assertTrue(any("Starting CSV export" in msg for msg in cm.output))
        self.assertTrue(any("CSV export completed" in msg for msg in cm.output))
