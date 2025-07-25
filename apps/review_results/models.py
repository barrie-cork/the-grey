import uuid
from typing import Optional, List, Dict, Any
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class ReviewTag(models.Model):
    """
    Tags for categorizing and filtering reviewed results.
    Can be system-defined or user-created.
    """
    
    TAG_TYPES = [
        ('quality', 'Quality Indicator'),
        ('methodology', 'Methodology'),
        ('topic', 'Topic/Theme'),
        ('relevance', 'Relevance'),
        ('custom', 'Custom'),
    ]
    
    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Tag details
    name = models.CharField(
        max_length=50,
        unique=True,
        help_text="Tag name"
    )
    slug = models.SlugField(
        max_length=50,
        unique=True,
        help_text="URL-friendly version of the name"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of what this tag represents"
    )
    
    # Tag metadata
    tag_type = models.CharField(
        max_length=20,
        choices=TAG_TYPES,
        default='custom',
        help_text="Type of tag"
    )
    color = models.CharField(
        max_length=7,
        default='#6c757d',
        help_text="Hex color code for display"
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Icon class for display (e.g., 'fa-star')"
    )
    
    # Ownership
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text="User who created this tag"
    )
    is_system = models.BooleanField(
        default=False,
        help_text="Whether this is a system-defined tag"
    )
    
    # Usage tracking
    usage_count = models.IntegerField(
        default=0,
        help_text="Number of times this tag has been used"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'review_tags'
        ordering = ['tag_type', 'name']
        indexes = [
            models.Index(fields=['tag_type']),
            models.Index(fields=['slug']),
        ]
    
    def __str__(self) -> str:
        return f"{self.name} ({self.get_tag_type_display()})"
    
    def save(self, *args: Any, **kwargs: Any) -> None:
        """Auto-generate slug from name if not provided."""
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class ReviewDecision(models.Model):
    """
    Review decision for a processed result.
    Records include/exclude decisions with reasoning.
    """
    
    DECISION_CHOICES = [
        ('include', 'Include'),
        ('exclude', 'Exclude'),
        ('maybe', 'Maybe/Uncertain'),
        ('pending', 'Pending Review'),
    ]
    
    EXCLUSION_REASONS = [
        ('not_grey_lit', 'Not Grey Literature'),
        ('wrong_population', 'Wrong Population'),
        ('wrong_intervention', 'Wrong Intervention/Interest'),
        ('wrong_context', 'Wrong Context'),
        ('wrong_language', 'Wrong Language'),
        ('duplicate', 'Duplicate'),
        ('quality', 'Quality Concerns'),
        ('access', 'Cannot Access'),
        ('date_range', 'Outside Date Range'),
        ('other', 'Other'),
    ]
    
    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    result = models.OneToOneField(
        'results_manager.ProcessedResult',
        on_delete=models.CASCADE,
        related_name='review_decision',
        help_text="The result being reviewed"
    )
    reviewer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text="User who made this decision"
    )
    
    # Decision details
    decision = models.CharField(
        max_length=20,
        choices=DECISION_CHOICES,
        default='pending',
        help_text="Review decision"
    )
    exclusion_reason = models.CharField(
        max_length=20,
        choices=EXCLUSION_REASONS,
        blank=True,
        help_text="Reason for exclusion (if excluded)"
    )
    
    # Additional information
    confidence_score = models.IntegerField(
        default=3,
        help_text="Reviewer confidence (1-5)",
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ]
    )
    needs_second_review = models.BooleanField(
        default=False,
        help_text="Flag for second reviewer"
    )
    
    # Notes
    reviewer_notes = models.TextField(
        blank=True,
        help_text="Detailed notes about the decision"
    )
    
    # Timestamps
    reviewed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the review was completed"
    )
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'review_decisions'
        ordering = ['-reviewed_at']
        indexes = [
            models.Index(fields=['decision']),
            models.Index(fields=['reviewer', 'reviewed_at']),
            models.Index(fields=['needs_second_review']),
        ]
    
    def __str__(self) -> str:
        return f"{self.get_decision_display()} - {self.result.title[:50]}..."
    
    def clean(self) -> None:
        """Validate exclusion reason is provided when excluding."""
        if self.decision == 'exclude' and not self.exclusion_reason:
            raise ValidationError("Exclusion reason is required when excluding a result")
    
    def save(self, *args: Any, **kwargs: Any) -> None:
        """Update result review status."""
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Update the processed result's review status
        if self.result:
            self.result.is_reviewed = True
            self.result.save(update_fields=['is_reviewed'])


class ReviewTagAssignment(models.Model):
    """
    Assignment of tags to reviewed results.
    Many-to-many relationship between results and tags.
    """
    
    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    result = models.ForeignKey(
        'results_manager.ProcessedResult',
        on_delete=models.CASCADE,
        related_name='tag_assignments',
        help_text="The result being tagged"
    )
    tag = models.ForeignKey(
        ReviewTag,
        on_delete=models.CASCADE,
        related_name='assignments',
        help_text="The tag being assigned"
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text="User who assigned this tag"
    )
    
    # Assignment metadata
    confidence = models.FloatField(
        default=1.0,
        help_text="Confidence in tag assignment (0-1)"
    )
    notes = models.CharField(
        max_length=255,
        blank=True,
        help_text="Brief note about why tag was assigned"
    )
    
    # Timestamps
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'review_tag_assignments'
        ordering = ['-assigned_at']
        indexes = [
            models.Index(fields=['result', 'tag']),
            models.Index(fields=['tag']),
        ]
        unique_together = [['result', 'tag']]
    
    def __str__(self) -> str:
        return f"{self.tag.name} → {self.result.title[:30]}..."
    
    def save(self, *args: Any, **kwargs: Any) -> None:
        """Update tag usage count."""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new and self.tag:
            self.tag.usage_count += 1
            self.tag.save(update_fields=['usage_count'])


class ReviewComment(models.Model):
    """
    Comments on reviewed results for collaboration.
    Supports threaded discussions.
    """
    
    COMMENT_TYPES = [
        ('general', 'General Comment'),
        ('quality', 'Quality Assessment'),
        ('relevance', 'Relevance Discussion'),
        ('methodology', 'Methodology Note'),
        ('question', 'Question'),
        ('suggestion', 'Suggestion'),
    ]
    
    # Primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    result = models.ForeignKey(
        'results_manager.ProcessedResult',
        on_delete=models.CASCADE,
        related_name='review_comments',
        help_text="The result being commented on"
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        help_text="Comment author"
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        help_text="Parent comment for threading"
    )
    
    # Comment content
    comment_type = models.CharField(
        max_length=20,
        choices=COMMENT_TYPES,
        default='general',
        help_text="Type of comment"
    )
    content = models.TextField(
        help_text="Comment content"
    )
    
    # Metadata
    is_resolved = models.BooleanField(
        default=False,
        help_text="Whether this comment/issue is resolved"
    )
    is_pinned = models.BooleanField(
        default=False,
        help_text="Pin important comments"
    )
    
    # Mentions
    mentioned_users = models.ManyToManyField(
        User,
        blank=True,
        related_name='comment_mentions',
        help_text="Users mentioned in this comment"
    )
    
    # Edit tracking
    is_edited = models.BooleanField(
        default=False,
        help_text="Whether comment has been edited"
    )
    edited_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When comment was last edited"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'review_comments'
        ordering = ['result', 'created_at']
        indexes = [
            models.Index(fields=['result', 'created_at']),
            models.Index(fields=['author']),
            models.Index(fields=['is_resolved']),
        ]
    
    def __str__(self) -> str:
        return f"{self.author.username}: {self.content[:50]}..."
    
    def save(self, *args: Any, **kwargs: Any) -> None:
        """Track edits."""
        if self.pk:  # Existing comment
            old_comment = ReviewComment.objects.get(pk=self.pk)
            if old_comment.content != self.content:
                self.is_edited = True
                self.edited_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    def get_thread_depth(self) -> int:
        """Get the depth of this comment in the thread."""
        depth = 0
        current = self
        while current.parent:
            depth += 1
            current = current.parent
        return depth