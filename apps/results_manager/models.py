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
    
    # Basic quality indicators (simplified)
    quality_indicators = models.JSONField(
        default=dict,
        blank=True,
        help_text="Basic quality flags (e.g., has_doi, is_peer_reviewed)"
    )
    
    # Processing metadata
    processed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this result was processed"
    )
    
    # Review status
    is_reviewed = models.BooleanField(
        default=False,
        help_text="Whether this result has been reviewed"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'processed_results'
        ordering = ['-publication_date', '-processed_at']
        indexes = [
            models.Index(fields=['session', 'is_reviewed']),
            models.Index(fields=['url']),
            models.Index(fields=['publication_year']),
            models.Index(fields=['document_type']),
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


# Removed ResultMetadata and ProcessingSession models to simplify the system
# These added unnecessary complexity for the core requirement of simple Include/Exclude review