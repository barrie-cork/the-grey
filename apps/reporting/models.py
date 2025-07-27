import uuid

from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class ExportReport(models.Model):
    """
    Tracks generated reports and exports for PRISMA compliance.
    """

    REPORT_TYPES = [
        ("prisma_flow", "PRISMA Flow Diagram"),
        ("full_report", "Full PRISMA Report"),
        ("included_results", "Included Results List"),
        ("excluded_results", "Excluded Results with Reasons"),
        ("search_strategy", "Search Strategy Documentation"),
        ("data_export", "Raw Data Export"),
    ]

    EXPORT_FORMATS = [
        ("pdf", "PDF"),
        ("docx", "Word Document"),
        ("xlsx", "Excel Spreadsheet"),
        ("csv", "CSV"),
        ("json", "JSON"),
        ("bibtex", "BibTeX"),
    ]

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    session = models.ForeignKey(
        "review_manager.SearchSession",
        on_delete=models.CASCADE,
        related_name="export_reports",
        help_text="The search session this report is for",
    )
    generated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text="User who generated this report",
    )

    # Report details
    report_type = models.CharField(
        max_length=20, choices=REPORT_TYPES, help_text="Type of report"
    )
    export_format = models.CharField(
        max_length=10, choices=EXPORT_FORMATS, help_text="Export file format"
    )

    # File information
    file_name = models.CharField(max_length=255, help_text="Generated file name")
    file_path = models.FileField(
        upload_to="reports/%Y/%m/", help_text="Path to generated file"
    )
    file_size_bytes = models.BigIntegerField(help_text="File size in bytes")

    # Report metadata
    title = models.CharField(max_length=255, help_text="Report title")
    description = models.TextField(blank=True, help_text="Report description or notes")

    # Report parameters
    parameters = models.JSONField(
        default=dict, help_text="Parameters used to generate report"
    )

    # Statistics included
    total_results = models.IntegerField(default=0, help_text="Total results in report")
    included_results = models.IntegerField(
        default=0, help_text="Number of included results"
    )
    excluded_results = models.IntegerField(
        default=0, help_text="Number of excluded results"
    )

    # Timestamps
    generated_at = models.DateTimeField(
        auto_now_add=True, help_text="When report was generated"
    )
    expires_at = models.DateTimeField(
        null=True, blank=True, help_text="When report file will be deleted"
    )

    class Meta:
        db_table = "export_reports"
        ordering = ["-generated_at"]
        indexes = [
            models.Index(fields=["session", "report_type"]),
            models.Index(fields=["generated_by", "-generated_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.get_report_type_display()})"
