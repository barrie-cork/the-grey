import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError

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
        'review_manager.SearchSession',
        on_delete=models.CASCADE,
        related_name='processed_results',
        help_text="The search session this result belongs to"
    )
    raw_result = models.ForeignKey(
        'serp_execution.RawSearchResult',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='processed_version',
        help_text="The original raw result this was processed from"
    )
    duplicate_group = models.ForeignKey(
        'DuplicateGroup',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='results',
        help_text="Group of duplicate results"
    )
    
    # Core fields (normalized)
    title = models.TextField(
        help_text="Cleaned and normalized title"
    )
    url = models.URLField(
        max_length=2048,
        help_text="Canonical URL"
    )
    snippet = models.TextField(
        blank=True,
        help_text="Cleaned snippet or abstract"
    )
    
    # Extracted metadata
    authors = models.JSONField(
        default=list,
        blank=True,
        help_text="List of author names"
    )
    publication_date = models.DateField(
        null=True,
        blank=True,
        help_text="Extracted publication date"
    )
    publication_year = models.IntegerField(
        null=True,
        blank=True,
        help_text="Publication year for easier filtering"
    )
    
    # Document metadata
    document_type = models.CharField(
        max_length=50,
        blank=True,
        help_text="Type of document (report, thesis, etc.)"
    )
    language = models.CharField(
        max_length=10,
        default='en',
        help_text="Document language code"
    )
    source_organization = models.CharField(
        max_length=255,
        blank=True,
        help_text="Publishing organization"
    )
    
    # Content indicators
    has_full_text = models.BooleanField(
        default=False,
        help_text="Whether full text is available"
    )
    full_text_url = models.URLField(
        max_length=2048,
        blank=True,
        help_text="Direct link to full text (PDF, etc.)"
    )
    is_pdf = models.BooleanField(
        default=False,
        help_text="Whether the result is a PDF"
    )
    file_size_bytes = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="File size if known"
    )
    
    # Quality scoring
    relevance_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Calculated relevance score (0-1)"
    )
    quality_indicators = models.JSONField(
        default=dict,
        blank=True,
        help_text="Quality indicators (e.g., peer_reviewed, has_doi)"
    )
    
    # Processing metadata
    processed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this result was processed"
    )
    processing_version = models.CharField(
        max_length=20,
        default='1.0',
        help_text="Version of processing algorithm used"
    )
    
    # Review status
    is_reviewed = models.BooleanField(
        default=False,
        help_text="Whether this result has been reviewed"
    )
    review_priority = models.IntegerField(
        default=0,
        help_text="Priority for review (higher = more important)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'processed_results'
        ordering = ['-relevance_score', '-publication_date']
        indexes = [
            models.Index(fields=['session', 'is_reviewed']),
            models.Index(fields=['url']),
            models.Index(fields=['publication_year']),
            models.Index(fields=['document_type']),
            models.Index(fields=['relevance_score']),
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


class DuplicateGroup(models.Model):
    """
    Groups duplicate results together for deduplication.
    """
    
    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationship
    session = models.ForeignKey(
        'review_manager.SearchSession',
        on_delete=models.CASCADE,
        related_name='duplicate_groups',
        help_text="The search session these duplicates belong to"
    )
    
    # Group metadata
    canonical_url = models.URLField(
        max_length=2048,
        help_text="The primary URL for this group"
    )
    similarity_type = models.CharField(
        max_length=50,
        choices=[
            ('exact_url', 'Exact URL Match'),
            ('normalized_url', 'Normalized URL Match'),
            ('title_match', 'Title Match'),
            ('content_hash', 'Content Hash Match'),
            ('fuzzy_match', 'Fuzzy Match'),
        ],
        help_text="How duplicates were identified"
    )
    
    # Statistics
    result_count = models.IntegerField(
        default=0,
        help_text="Number of results in this group"
    )
    sources = models.JSONField(
        default=list,
        help_text="List of search engines that found this"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'duplicate_groups'
        ordering = ['-result_count']
        indexes = [
            models.Index(fields=['session', 'canonical_url']),
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
            if result.has_full_text:
                score += 3
            if result.relevance_score:
                score += result.relevance_score
            
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
                    if result.raw_result and result.raw_result.execution.search_engine not in self.sources:
                        self.sources.append(result.raw_result.execution.search_engine)
            
            best_result.save()
            self.save()


class ResultMetadata(models.Model):
    """
    Additional metadata extracted from results.
    Stores structured data that doesn't fit in the main model.
    """
    
    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationship
    result = models.OneToOneField(
        ProcessedResult,
        on_delete=models.CASCADE,
        related_name='metadata',
        help_text="The result this metadata belongs to"
    )
    
    # Identifiers
    doi = models.CharField(
        max_length=255,
        blank=True,
        help_text="Digital Object Identifier"
    )
    isbn = models.CharField(
        max_length=20,
        blank=True,
        help_text="ISBN for books"
    )
    issn = models.CharField(
        max_length=20,
        blank=True,
        help_text="ISSN for journals"
    )
    
    # Additional metadata
    keywords = models.JSONField(
        default=list,
        blank=True,
        help_text="Extracted keywords"
    )
    abstract = models.TextField(
        blank=True,
        help_text="Full abstract if available"
    )
    funding_info = models.TextField(
        blank=True,
        help_text="Funding information"
    )
    
    # Geographic information
    country = models.CharField(
        max_length=100,
        blank=True,
        help_text="Country of origin"
    )
    region = models.CharField(
        max_length=100,
        blank=True,
        help_text="Geographic region"
    )
    
    # Classification
    subject_areas = models.JSONField(
        default=list,
        blank=True,
        help_text="Subject classification"
    )
    methodology = models.CharField(
        max_length=100,
        blank=True,
        help_text="Research methodology if identified"
    )
    
    # Access information
    access_type = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('open_access', 'Open Access'),
            ('restricted', 'Restricted Access'),
            ('subscription', 'Subscription Required'),
            ('unknown', 'Unknown'),
        ],
        default='unknown',
        help_text="Access restrictions"
    )
    license = models.CharField(
        max_length=100,
        blank=True,
        help_text="License information"
    )
    
    # Extraction metadata
    extraction_confidence = models.JSONField(
        default=dict,
        blank=True,
        help_text="Confidence scores for extracted fields"
    )
    extraction_method = models.CharField(
        max_length=50,
        blank=True,
        help_text="Method used for metadata extraction"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'result_metadata'
        verbose_name_plural = 'Result metadata'
    
    def __str__(self) -> str:
        return f"Metadata for: {self.result.title[:50]}..."


class ProcessingSession(models.Model):
    """
    Tracks the progress of results processing for a search session.
    This provides real-time status updates and error tracking.
    """
    
    # Status choices
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('partial', 'Partial'),
    ]
    
    # Processing stages
    STAGE_CHOICES = [
        ('initialization', 'Initialization'),
        ('url_normalization', 'URL Normalization'),
        ('metadata_extraction', 'Metadata Extraction'),
        ('deduplication', 'Deduplication'),
        ('quality_scoring', 'Quality Scoring'),
        ('finalization', 'Finalization'),
    ]
    
    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationship
    search_session = models.OneToOneField(
        'review_manager.SearchSession',
        on_delete=models.CASCADE,
        related_name='processing_session',
        help_text="The search session being processed"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Current processing status"
    )
    current_stage = models.CharField(
        max_length=30,
        choices=STAGE_CHOICES,
        blank=True,
        help_text="Current processing stage"
    )
    stage_progress = models.IntegerField(
        default=0,
        help_text="Progress within current stage (0-100)"
    )
    
    # Progress metrics
    total_raw_results = models.IntegerField(
        default=0,
        help_text="Total number of raw results to process"
    )
    processed_count = models.IntegerField(
        default=0,
        help_text="Number of results processed so far"
    )
    error_count = models.IntegerField(
        default=0,
        help_text="Number of processing errors encountered"
    )
    duplicate_count = models.IntegerField(
        default=0,
        help_text="Number of duplicates found"
    )
    
    # Timing information
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When processing started"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When processing completed"
    )
    last_heartbeat = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last progress update timestamp"
    )
    
    # Error tracking
    error_details = models.JSONField(
        default=list,
        blank=True,
        help_text="List of processing errors with details"
    )
    retry_count = models.IntegerField(
        default=0,
        help_text="Number of retry attempts"
    )
    
    # Configuration and metadata
    processing_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Processing configuration parameters"
    )
    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="Associated Celery task ID"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'processing_sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['search_session', 'status']),
            models.Index(fields=['status', 'started_at']),
        ]
    
    def __str__(self) -> str:
        return f"Processing: {self.search_session.title} ({self.status})"
    
    @property
    def progress_percentage(self) -> int:
        """Calculate overall progress percentage."""
        if self.total_raw_results == 0:
            return 0
        return min(100, int((self.processed_count / self.total_raw_results) * 100))
    
    @property
    def duration_seconds(self) -> Optional[int]:
        """Get processing duration in seconds."""
        if not self.started_at:
            return None
        
        end_time = self.completed_at or timezone.now()
        duration = end_time - self.started_at
        return int(duration.total_seconds())
    
    @property
    def estimated_completion(self) -> Optional[timezone.datetime]:
        """Estimate completion time based on current progress."""
        if not self.started_at or self.processed_count == 0:
            return None
        
        elapsed = timezone.now() - self.started_at
        rate = self.processed_count / elapsed.total_seconds()  # results per second
        
        remaining = self.total_raw_results - self.processed_count
        if remaining <= 0 or rate <= 0:
            return None
        
        estimated_seconds = remaining / rate
        return timezone.now() + timezone.timedelta(seconds=estimated_seconds)
    
    def update_progress(
        self,
        stage: str,
        stage_progress: int,
        processed_count: Optional[int] = None,
        error_count: Optional[int] = None,
        duplicate_count: Optional[int] = None
    ) -> None:
        """
        Update processing progress.
        
        Args:
            stage: Current processing stage
            stage_progress: Progress within stage (0-100)
            processed_count: Total processed count (optional)
            error_count: Total error count (optional)
            duplicate_count: Total duplicate count (optional)
        """
        self.current_stage = stage
        self.stage_progress = stage_progress
        self.last_heartbeat = timezone.now()
        
        if processed_count is not None:
            self.processed_count = processed_count
        if error_count is not None:
            self.error_count = error_count
        if duplicate_count is not None:
            self.duplicate_count = duplicate_count
        
        self.save(update_fields=[
            'current_stage', 'stage_progress', 'last_heartbeat',
            'processed_count', 'error_count', 'duplicate_count', 'updated_at'
        ])
    
    def add_error(self, error_message: str, error_details: Optional[Dict[str, Any]] = None) -> None:
        """
        Add an error to the processing session.
        
        Args:
            error_message: Error message
            error_details: Additional error details
        """
        error_entry = {
            'timestamp': timezone.now().isoformat(),
            'message': error_message,
            'details': error_details or {}
        }
        
        self.error_details.append(error_entry)
        self.error_count += 1
        self.save(update_fields=['error_details', 'error_count', 'updated_at'])
    
    def start_processing(self, total_raw_results: int, celery_task_id: str = '') -> None:
        """
        Mark processing as started.
        
        Args:
            total_raw_results: Total number of results to process
            celery_task_id: Associated Celery task ID
        """
        self.status = 'in_progress'
        self.total_raw_results = total_raw_results
        self.started_at = timezone.now()
        self.celery_task_id = celery_task_id
        self.current_stage = 'initialization'
        self.stage_progress = 0
        
        self.save(update_fields=[
            'status', 'total_raw_results', 'started_at', 'celery_task_id',
            'current_stage', 'stage_progress', 'updated_at'
        ])
    
    def complete_processing(self) -> None:
        """Mark processing as completed."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.current_stage = 'finalization'
        self.stage_progress = 100
        
        self.save(update_fields=[
            'status', 'completed_at', 'current_stage', 'stage_progress', 'updated_at'
        ])
    
    def fail_processing(self, error_message: str, error_details: Optional[Dict[str, Any]] = None) -> None:
        """
        Mark processing as failed.
        
        Args:
            error_message: Failure reason
            error_details: Additional error details
        """
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.add_error(error_message, error_details)
        
        self.save(update_fields=['status', 'completed_at', 'updated_at'])