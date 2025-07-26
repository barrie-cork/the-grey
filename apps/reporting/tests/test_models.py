"""
Tests for reporting models.

Tests for ExportReport and related models including
report generation and export functionality.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.review_manager.models import SearchSession

from ..models import ExportReport

User = get_user_model()


class ExportReportModelTests(TestCase):
    """Test cases for ExportReport model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com", password="testpass123"
        )
        self.session = SearchSession.objects.create(
            title="Test Session", owner=self.user
        )

    def test_export_report_creation(self):
        """Test creating an export report."""
        report = ExportReport.objects.create(
            session=self.session,
            generated_by=self.user,
            report_type="prisma_flow",
            export_format="pdf",
            title="PRISMA Flow Diagram",
        )

        self.assertEqual(report.session, self.session)
        self.assertEqual(report.generated_by, self.user)
        self.assertEqual(report.report_type, "prisma_flow")
        self.assertEqual(report.export_format, "pdf")
