import uuid
from typing import Any, Optional

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone

User = get_user_model()


class ProcessedResult(models.Model):
    """
    Normalized and processed search result.
    This is the cleaned, deduplicated version of raw results.
    """

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationships
    session = models.ForeignKey(
        "review_manager.SearchSession",
        on_delete=models.CASCADE,
        related_name="processed_results",
        help_text="The search session this result belongs to",
    )
    raw_result = models.ForeignKey(
        "serp_execution.RawSearchResult",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="processed_version",
        help_text="The original raw result this was processed from",
    )
    duplicate_group = models.ForeignKey(
        "DuplicateGroup",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="results",
        help_text="Group of duplicate results",
    )

    # Core fields (normalized)
    title = models.TextField(help_text="Cleaned and normalized title")
    url = models.URLField(max_length=2048, help_text="Canonical URL")
    snippet = models.TextField(blank=True, help_text="Cleaned snippet or abstract")

    # Extracted metadata
    authors = models.JSONField(
        default=list, blank=True, help_text="List of author names"
    )
    publication_date = models.DateField(
        null=True, blank=True, help_text="Extracted publication date"
    )
    publication_year = models.IntegerField(
        null=True, blank=True, help_text="Publication year for easier filtering"
    )

    # Document metadata
    document_type = models.CharField(
        max_length=50, blank=True, help_text="Type of document (report, thesis, etc.)"
    )
    language = models.CharField(
        max_length=10, default="en", help_text="Document language code"
    )
    source_organization = models.CharField(
        max_length=255, blank=True, help_text="Publishing organization"
    )

    # Content indicators
    full_text_url = models.URLField(
        max_length=2048, blank=True, help_text="Direct link to full text (PDF, etc.)"
    )
    is_pdf = models.BooleanField(default=False, help_text="Whether the result is a PDF")

    # Processing metadata
    processed_at = models.DateTimeField(
        auto_now_add=True, help_text="When this result was processed"
    )

    # Review status
    is_reviewed = models.BooleanField(
        default=False, help_text="Whether this result has been reviewed"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "processed_results"
        ordering = ["-processed_at"]  # Most recently processed first
        indexes = [
            models.Index(fields=["session", "is_reviewed"]),
            models.Index(fields=["url"]),
            models.Index(fields=["publication_year"]),
            models.Index(fields=["document_type"]),
            models.Index(fields=["-processed_at"]),  # For ordering by processing time
        ]

    def __str__(self) -> str:
        return f"{self.title[:50]}... ({self.publication_year or 'Unknown'})"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Extract year from date if available."""
        if self.publication_date and not self.publication_year:
            self.publication_year = self.publication_date.year
        super().save(*args, **kwargs)

    def get_display_url(self) -> str:
        """Get a shortened display version of the URL."""
        from urllib.parse import urlparse

        parsed = urlparse(self.url)
        return parsed.netloc

    @property
    def has_full_text(self) -> bool:
        """Check if full text is available based on PDF status or full_text_url."""
        return bool(self.is_pdf or self.full_text_url)


class DuplicateGroup(models.Model):
    """
    Groups duplicate results together for deduplication.
    """

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationship
    session = models.ForeignKey(
        "review_manager.SearchSession",
        on_delete=models.CASCADE,
        related_name="duplicate_groups",
        help_text="The search session these duplicates belong to",
    )

    # Group metadata
    canonical_url = models.URLField(
        max_length=2048, help_text="The primary URL for this group"
    )
    similarity_type = models.CharField(
        max_length=50,
        choices=[
            ("exact_url", "Exact URL Match"),
            ("normalized_url", "Normalized URL Match"),
            ("title_match", "Title Match"),
            ("content_hash", "Content Hash Match"),
            ("fuzzy_match", "Fuzzy Match"),
        ],
        help_text="How duplicates were identified",
    )

    # Statistics
    result_count = models.IntegerField(
        default=0, help_text="Number of results in this group"
    )
    sources = models.JSONField(
        default=list, help_text="List of search engines that found this"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "duplicate_groups"
        ordering = ["-result_count"]
        indexes = [
            models.Index(fields=["session", "canonical_url"]),
        ]

    def __str__(self) -> str:
        return f"Duplicate group: {self.canonical_url} ({self.result_count} results)"

    def merge_results(self) -> None:
        """
        Merge duplicate results, keeping the best version.
        This would typically keep the result with the most metadata.
        """
        results = self.results.all()
        if results.count() <= 1:
            return

        # Find the best result (most complete metadata)
        # Optimize queries by prefetching related objects
        results = results.select_related("raw_result__execution")
        
        best_result: Optional[ProcessedResult] = None
        best_score: float = 0

        for result in results:
            score = 0
            if result.snippet:
                score += 1
            if result.authors:
                score += 2
            if result.publication_date:
                score += 2
            if result.is_pdf:
                score += 2

            if score > best_score:
                best_score = score
                best_result = result

        # Update the canonical result with merged data
        if best_result:
            for result in results:
                if result != best_result:
                    # Merge any missing data
                    if not best_result.snippet and result.snippet:
                        best_result.snippet = result.snippet
                    if not best_result.authors and result.authors:
                        best_result.authors = result.authors
                    # Add to sources
                    if (
                        result.raw_result
                        and result.raw_result.execution.search_engine
                        not in self.sources
                    ):
                        self.sources.append(result.raw_result.execution.search_engine)

            best_result.save()
            self.save()


class ProcessingSession(models.Model):
    """
    Tracks the processing status for a search session.
    Shows progress through various stages of result processing.
    """

    PROCESSING_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("partial", "Partial"),
    ]

    PROCESSING_STAGES = [
        ("initialization", "Initialization"),
        ("url_normalization", "URL Normalization"),
        ("deduplication", "Deduplication"),
        ("quality_scoring", "Quality Scoring"),
        ("finalization", "Finalization"),
    ]

    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relationship
    search_session = models.OneToOneField(
        "review_manager.SearchSession",
        on_delete=models.CASCADE,
        related_name="processing_session",
        help_text="The search session being processed",
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=PROCESSING_STATUS_CHOICES,
        default="pending",
        help_text="Current processing status",
    )
    current_stage = models.CharField(
        max_length=30,
        choices=PROCESSING_STAGES,
        blank=True,
        help_text="Current processing stage",
    )
    stage_progress = models.IntegerField(
        default=0, help_text="Progress within current stage (0-100)"
    )

    # Counts
    total_raw_results = models.IntegerField(
        default=0, help_text="Total number of raw results to process"
    )
    processed_count = models.IntegerField(
        default=0, help_text="Number of results processed so far"
    )
    error_count = models.IntegerField(
        default=0, help_text="Number of processing errors encountered"
    )
    duplicate_count = models.IntegerField(
        default=0, help_text="Number of duplicates found"
    )

    # Timing
    started_at = models.DateTimeField(
        null=True, blank=True, help_text="When processing started"
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, help_text="When processing completed"
    )
    last_heartbeat = models.DateTimeField(
        null=True, blank=True, help_text="Last progress update timestamp"
    )

    # Error tracking
    error_details = models.JSONField(
        default=list, blank=True, help_text="List of processing errors with details"
    )
    retry_count = models.IntegerField(default=0, help_text="Number of retry attempts")

    # Configuration
    processing_config = models.JSONField(
        default=dict, blank=True, help_text="Processing configuration parameters"
    )
    celery_task_id = models.CharField(
        max_length=255, blank=True, help_text="Associated Celery task ID"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "processing_sessions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["search_session", "status"]),
            models.Index(fields=["status", "started_at"]),
        ]

    def __str__(self) -> str:
        return f"Processing {self.search_session.title} - {self.get_status_display()}"

    @property
    def progress_percentage(self) -> int:
        """Calculate overall progress percentage."""
        if self.total_raw_results == 0:
            return 0
        return min(100, int((self.processed_count / self.total_raw_results) * 100))

    def update_heartbeat(self) -> None:
        """Update the last heartbeat timestamp."""
        self.last_heartbeat = timezone.now()
        self.save(update_fields=["last_heartbeat"])
