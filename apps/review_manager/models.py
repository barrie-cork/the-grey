import uuid
from typing import List, Optional, Dict, Any
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

User = get_user_model()


class SearchSession(models.Model):
    """
    Core model representing a grey literature search session.
    Implements a 9-state workflow for systematic literature review.
    """
    
    # Status choices representing the 9-state workflow
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('defining_search', 'Defining Search'),
        ('ready_to_execute', 'Ready to Execute'),
        ('executing', 'Executing'),
        ('processing_results', 'Processing Results'),
        ('ready_for_review', 'Ready for Review'),
        ('under_review', 'Under Review'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]
    
    # Allowed status transitions
    ALLOWED_TRANSITIONS = {
        'draft': ['defining_search', 'archived'],
        'defining_search': ['ready_to_execute', 'draft', 'archived'],
        'ready_to_execute': ['executing', 'defining_search', 'archived'],
        'executing': ['processing_results', 'ready_to_execute', 'archived'],
        'processing_results': ['ready_for_review', 'executing', 'archived'],
        'ready_for_review': ['under_review', 'processing_results', 'archived'],
        'under_review': ['completed', 'ready_for_review', 'archived'],
        'completed': ['archived', 'under_review'],
        'archived': ['draft'],  # Can only unarchive to draft
    }
    
    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Core fields
    title = models.CharField(max_length=255, help_text="Title of the search session")
    description = models.TextField(
        blank=True, 
        help_text="Detailed description of the search objectives"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='draft',
        help_text="Current status in the 9-state workflow"
    )
    
    # User relationship
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='search_sessions',
        help_text="User who created this search session"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When search execution started"
    )
    completed_at = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="When search was completed"
    )
    
    # Metadata
    notes = models.TextField(
        blank=True,
        help_text="Internal notes about the search session"
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Tags for categorizing sessions"
    )
    
    # Search statistics
    total_queries = models.IntegerField(
        default=0,
        help_text="Total number of search queries"
    )
    total_results = models.IntegerField(
        default=0,
        help_text="Total number of results found"
    )
    reviewed_results = models.IntegerField(
        default=0,
        help_text="Number of results reviewed"
    )
    included_results = models.IntegerField(
        default=0,
        help_text="Number of results included in final selection"
    )
    
    class Meta:
        db_table = 'search_sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['owner', '-created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.title} ({self.get_status_display()})"
    
    def clean(self) -> None:
        """Validate status transitions."""
        if self.pk:  # Only validate on updates
            try:
                old_instance = SearchSession.objects.get(pk=self.pk)
                old_status = old_instance.status
                if old_status != self.status:
                    if not self.can_transition_to(self.status):
                        raise ValidationError(
                            f"Cannot transition from '{old_status}' to '{self.status}'"
                        )
            except SearchSession.DoesNotExist:
                pass
    
    def save(self, *args: Any, **kwargs: Any) -> None:
        """Override save to handle status change timestamps."""
        self.full_clean()
        
        # Set started_at when moving to executing
        if self.status == 'executing' and not self.started_at:
            self.started_at = timezone.now()
        
        # Set completed_at when moving to completed
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def can_transition_to(self, new_status: str) -> bool:
        """Check if transition to new status is allowed."""
        if self.status == new_status:
            return True
        return new_status in self.ALLOWED_TRANSITIONS.get(self.status, [])
    
    def get_allowed_transitions(self) -> List[str]:
        """Get list of allowed status transitions from current status."""
        return self.ALLOWED_TRANSITIONS.get(self.status, [])
    
    @property
    def progress_percentage(self) -> float:
        """Calculate review progress as a percentage."""
        if self.total_results == 0:
            return 0
        return round((self.reviewed_results / self.total_results) * 100, 1)
    
    @property
    def inclusion_rate(self) -> float:
        """Calculate the rate of included results."""
        if self.reviewed_results == 0:
            return 0
        return round((self.included_results / self.reviewed_results) * 100, 1)


class SessionActivity(models.Model):
    """
    Audit trail for SearchSession activities.
    Tracks all significant events and changes in a search session.
    """
    
    ACTIVITY_TYPES = [
        ('created', 'Session Created'),
        ('status_changed', 'Status Changed'),
        ('search_defined', 'Search Defined'),
        ('search_executed', 'Search Executed'),
        ('results_processed', 'Results Processed'),
        ('review_started', 'Review Started'),
        ('review_completed', 'Review Completed'),
        ('exported', 'Data Exported'),
        ('shared', 'Session Shared'),
        ('note_added', 'Note Added'),
        ('settings_changed', 'Settings Changed'),
    ]
    
    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    session = models.ForeignKey(
        SearchSession,
        on_delete=models.CASCADE,
        related_name='activities',
        help_text="The search session this activity belongs to"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text="User who performed this activity"
    )
    
    # Activity details
    activity_type = models.CharField(
        max_length=20,
        choices=ACTIVITY_TYPES,
        help_text="Type of activity performed"
    )
    description = models.TextField(
        help_text="Detailed description of the activity"
    )
    
    # Additional data
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional activity metadata (e.g., old/new values)"
    )
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'session_activities'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['session', '-created_at']),
            models.Index(fields=['activity_type']),
            models.Index(fields=['created_at']),
        ]
        verbose_name_plural = 'Session activities'
    
    def __str__(self) -> str:
        return f"{self.get_activity_type_display()} - {self.session.title} ({self.created_at})"
    
    @classmethod
    def log_activity(cls, session: 'SearchSession', activity_type: str, description: str, 
                    user: Optional[User] = None, metadata: Optional[Dict[str, Any]] = None) -> 'SessionActivity':
        """
        Convenience method to log an activity.
        
        Args:
            session: The SearchSession instance
            activity_type: Type of activity (from ACTIVITY_TYPES)
            description: Description of the activity
            user: User who performed the activity (optional)
            metadata: Additional metadata dict (optional)
        
        Returns:
            SessionActivity instance
        """
        return cls.objects.create(
            session=session,
            activity_type=activity_type,
            description=description,
            user=user or session.owner,
            metadata=metadata or {}
        )
