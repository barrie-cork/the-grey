import uuid
from typing import Any

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class SearchExecution(models.Model):
    """
    Tracks the execution of a search query via the Serper API.
    Records API calls and status.
    """

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
        ("rate_limited", "Rate Limited"),
    ]

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    query = models.ForeignKey(
        "search_strategy.SearchQuery",
        on_delete=models.CASCADE,
        related_name="executions",
        help_text="The search query being executed",
    )
    initiated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text="User who initiated this execution",
    )

    # Execution details
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        help_text="Current status of the execution",
    )
    search_engine = models.CharField(
        max_length=50,
        default="google",
        help_text="Search engine used (e.g., google, bing)",
    )

    # API details
    api_request_id = models.CharField(
        max_length=255, blank=True, help_text="External API request ID for tracking"
    )
    api_parameters = models.JSONField(
        default=dict, help_text="Parameters sent to the API"
    )

    # Timing
    started_at = models.DateTimeField(
        null=True, blank=True, help_text="When execution started"
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, help_text="When execution completed"
    )
    duration_seconds = models.FloatField(
        null=True, blank=True, help_text="Execution duration in seconds"
    )

    # Results metadata
    results_count = models.IntegerField(
        default=0, help_text="Number of results returned"
    )
    results_offset = models.IntegerField(
        default=0, help_text="Offset for paginated results"
    )


    # Error handling
    error_message = models.TextField(
        blank=True, help_text="Error message if execution failed"
    )
    retry_count = models.IntegerField(default=0, help_text="Number of retry attempts")

    # Celery integration
    celery_task_id = models.CharField(
        max_length=255, blank=True, help_text="Celery task ID for async execution"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "search_executions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["query", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["celery_task_id"]),
        ]

    def __str__(self) -> str:
        return f"Execution {self.id} - {self.status} ({self.search_engine})"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Calculate duration when completing."""
        if self.status == "completed" and self.started_at and not self.duration_seconds:
            self.completed_at = self.completed_at or timezone.now()
            duration = self.completed_at - self.started_at
            self.duration_seconds = duration.total_seconds()

        super().save(*args, **kwargs)

    def can_retry(self) -> bool:
        """Check if execution can be retried."""
        return self.status in ["failed", "rate_limited"] and self.retry_count < 3


class RawSearchResult(models.Model):
    """
    Stores raw search results from the Serper API.
    This is the unprocessed data before normalization.
    """

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    execution = models.ForeignKey(
        SearchExecution,
        on_delete=models.CASCADE,
        related_name="raw_results",
        help_text="The execution that produced this result",
    )

    # Result data
    position = models.IntegerField(help_text="Position in search results (1-based)")
    title = models.TextField(help_text="Title of the search result")
    link = models.URLField(max_length=2048, help_text="URL of the result")
    snippet = models.TextField(blank=True, help_text="Text snippet from the result")

    # Additional metadata
    display_link = models.CharField(
        max_length=255, blank=True, help_text="Display version of the URL"
    )
    source = models.CharField(
        max_length=255, blank=True, help_text="Source website or platform"
    )

    # Raw API response
    raw_data = models.JSONField(
        default=dict, help_text="Complete raw response from API"
    )

    # Content indicators
    has_pdf = models.BooleanField(
        default=False, help_text="Whether result links to a PDF"
    )
    has_date = models.BooleanField(
        default=False, help_text="Whether a publication date was detected"
    )
    detected_date = models.DateField(
        null=True, blank=True, help_text="Extracted publication date if available"
    )

    # Content indicators
    language_code = models.CharField(
        max_length=10, blank=True, help_text="Detected language code"
    )

    # Processing status
    is_processed = models.BooleanField(
        default=False, help_text="Whether this result has been processed"
    )
    processing_error = models.TextField(
        blank=True, help_text="Error message if processing failed"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "raw_search_results"
        ordering = ["execution", "position"]
        indexes = [
            models.Index(fields=["execution", "position"]),
            models.Index(fields=["is_processed"]),
            models.Index(fields=["link"]),
        ]
        unique_together = [["execution", "position"]]

    def __str__(self) -> str:
        return f"{self.title[:50]}... (Position {self.position})"

    def get_domain(self) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse

        parsed = urlparse(self.link)
        return parsed.netloc


