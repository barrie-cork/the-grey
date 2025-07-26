# Review Results Product Requirements Document

**Project:** Thesis Grey - Systematic Grey Literature Review Tool  
**App:** Review Results  
**Version:** 1.0  
**Date:** 2025-01-25  
**App Path:** `apps/review_results/`  
**Master PRD:** [docs/PRD.md](../PRD.md)  
**Dependencies:** results_manager, review_manager, accounts  
**Status:** Planned

## 1. Executive Summary

### 1.1 Key Responsibilities
The Review Results app provides the core interface for researchers to systematically review, tag, and annotate processed search results. It implements PRISMA-compliant review workflows with sophisticated tagging systems, note-taking capabilities, and comprehensive audit trails. The app manages the critical human review phase where researchers determine which grey literature to include in their systematic review.

### 1.2 Integration Points
- **Results Manager**: Consumes ProcessedResult records ready for review
- **Review Manager**: Updates SearchSession status through review lifecycle
- **Accounts**: Associates all review actions with authenticated users
- **Reporting**: Provides data for PRISMA flow diagrams and export

## 2. Technical Architecture

### 2.1 Technology Stack
- **Framework**: Django 4.2 with Class-Based Views (CBVs)
- **Database**: PostgreSQL with UUID primary keys
- **Frontend**: Django templates with AJAX for dynamic interactions
- **JavaScript**: Vanilla JS with fetch API for AJAX operations
- **CSS Framework**: Bootstrap 5 for responsive design
- **Testing**: Django TestCase with factory patterns

### 2.2 App Structure
```
apps/review_results/
├── __init__.py
├── apps.py
├── models.py           # ReviewTag, ReviewTagAssignment, Note models
├── views.py            # ResultsOverviewView, tagging/note AJAX views
├── forms.py            # ReviewTagAssignmentForm, NoteForm
├── urls.py             # URL patterns for review interface
├── admin.py            # Django admin configuration
├── services.py         # Business logic for review operations
├── managers.py         # Custom model managers
├── utils.py            # Helper functions
├── signals.py          # Django signals for status updates
├── templates/
│   └── review_results/
│       ├── base.html
│       ├── results_overview.html
│       ├── partials/
│       │   ├── result_item.html
│       │   ├── tag_buttons.html
│       │   ├── note_modal.html
│       │   └── duplicate_modal.html
│       └── includes/
│           ├── filters.html
│           └── progress_bar.html
├── static/
│   └── review_results/
│       ├── css/
│       │   └── review.css
│       └── js/
│           ├── tagging.js
│           ├── notes.js
│           └── filters.js
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_views.py
│   ├── test_forms.py
│   ├── test_services.py
│   └── factories.py
└── migrations/
```

### 2.3 Database Models

#### ReviewTag Model
```python
import uuid
from django.db import models
from django.core.validators import RegexValidator

class ReviewTag(models.Model):
    """
    Represents tags that can be assigned to search results during review.
    Pre-populated with standard tags: Include, Exclude, Maybe.
    """
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    name = models.CharField(
        max_length=50, 
        unique=True, 
        help_text='Tag name (e.g., "Include", "Exclude", "Maybe")'
    )
    description = models.TextField(
        blank=True,
        help_text='Detailed description of when to use this tag'
    )
    slug = models.SlugField(
        max_length=50, 
        unique=True, 
        help_text='URL-friendly identifier for the tag'
    )
    color = models.CharField(
        max_length=7, 
        blank=True,
        validators=[RegexValidator(
            regex='^#[0-9A-Fa-f]{6}$',
            message='Enter a valid hex color code'
        )],
        help_text='Hex color code for UI display (e.g., #FF0000)'
    )
    requires_reason = models.BooleanField(
        default=False,
        help_text='Whether this tag requires a reason when assigned'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this tag is available for use'
    )
    display_order = models.IntegerField(
        default=0,
        help_text='Order for displaying tags in UI'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active', 'display_order']),
        ]

    def __str__(self):
        return self.name
```

#### ReviewTagAssignment Model
```python
class ReviewTagAssignment(models.Model):
    """
    Links review tags to specific results within a session context.
    Ensures one tag per result per user per session.
    """
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    processed_result = models.ForeignKey(
        'results_manager.ProcessedResult', 
        on_delete=models.CASCADE, 
        related_name='tag_assignments'
    )
    tag = models.ForeignKey(
        ReviewTag, 
        on_delete=models.PROTECT, 
        related_name='assignments'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT,
        related_name='review_tag_assignments',
        help_text='User who assigned the tag'
    )
    session = models.ForeignKey(
        'review_manager.SearchSession', 
        on_delete=models.CASCADE, 
        related_name='review_tag_assignments'
    )
    reason = models.TextField(
        blank=True, 
        null=True,
        help_text='Required for exclusion tags, optional otherwise'
    )
    confidence_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Reviewer confidence in assignment (0.00-1.00)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Audit fields
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_tag_assignments',
        editable=False
    )
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='modified_tag_assignments',
        editable=False,
        null=True
    )

    class Meta:
        unique_together = [['processed_result', 'session', 'user']]
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['session', 'user', '-updated_at']),
            models.Index(fields=['tag', 'session']),
            models.Index(fields=['processed_result', 'user']),
        ]

    def __str__(self):
        return f"{self.tag.name} - {self.processed_result.title[:50]} by {self.user.email}"

    def clean(self):
        """Validate that required reasons are provided."""
        super().clean()
        if self.tag.requires_reason and not self.reason:
            raise ValidationError({
                'reason': f'A reason is required for the "{self.tag.name}" tag.'
            })
```

#### Note Model
```python
class Note(models.Model):
    """
    Allows reviewers to add contextual notes to search results.
    """
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    processed_result = models.ForeignKey(
        'results_manager.ProcessedResult', 
        on_delete=models.CASCADE, 
        related_name='notes'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT,
        related_name='review_notes',
        help_text='User who created the note'
    )
    session = models.ForeignKey(
        'review_manager.SearchSession', 
        on_delete=models.CASCADE, 
        related_name='review_notes'
    )
    text = models.TextField(
        help_text='Note content - supports markdown formatting'
    )
    note_type = models.CharField(
        max_length=20,
        choices=[
            ('general', 'General Note'),
            ('methodology', 'Methodology Concern'),
            ('relevance', 'Relevance Note'),
            ('quality', 'Quality Assessment'),
            ('follow_up', 'Follow-up Required'),
        ],
        default='general'
    )
    is_private = models.BooleanField(
        default=False,
        help_text='Private notes are only visible to the creator'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['session', 'user', '-updated_at']),
            models.Index(fields=['processed_result', '-created_at']),
        ]

    def __str__(self):
        return f"Note by {self.user.email} on {self.processed_result.title[:50]}"
```

## 3. API Endpoints

### 3.1 Phase 1 Endpoints (Current Implementation)
While the Review Results app primarily uses server-side rendering with AJAX enhancements in Phase 1, these endpoints support the dynamic functionality:

#### AJAX Endpoints
```python
# Tag Assignment
POST /api/review-results/tag-assignment/
    Request: {
        "processed_result_id": "uuid",
        "tag_id": "uuid",
        "session_id": "uuid",
        "reason": "string (required for exclude tags)"
    }
    Response: {
        "success": true,
        "assignment_id": "uuid",
        "tag_name": "Include",
        "tag_color": "#28a745"
    }

# Note Management
POST /api/review-results/notes/
    Request: {
        "processed_result_id": "uuid",
        "session_id": "uuid",
        "text": "string",
        "note_type": "general"
    }
    Response: {
        "success": true,
        "note_id": "uuid",
        "created_at": "2025-01-25T10:00:00Z"
    }

PUT /api/review-results/notes/{note_id}/
    Request: {
        "text": "updated note text"
    }
    Response: {
        "success": true,
        "updated_at": "2025-01-25T10:05:00Z"
    }

# Session Progress
GET /api/review-results/session/{session_id}/progress/
    Response: {
        "total_results": 150,
        "tagged_results": 75,
        "progress_percentage": 50,
        "tags_breakdown": {
            "include": 30,
            "exclude": 35,
            "maybe": 10
        }
    }
```

### 3.2 Phase 2 API Endpoints (Future RESTful API)
```python
# Full RESTful API implementation for external integrations
GET    /api/v1/review-results/sessions/{session_id}/results/
POST   /api/v1/review-results/bulk-tag/
GET    /api/v1/review-results/export/{session_id}/
```

## 4. User Interface

### 4.1 Views

#### ResultsOverviewView
```python
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Prefetch, Q, Count, OuterRef, Subquery
from apps.results_manager.models import ProcessedResult
from apps.review_manager.models import SearchSession
from apps.review_results.models import ReviewTag, ReviewTagAssignment, Note
from apps.review_results.forms import ResultFilterForm

class ResultsOverviewView(LoginRequiredMixin, ListView):
    """
    Main view for reviewing search results with filtering and pagination.
    """
    model = ProcessedResult
    template_name = 'review_results/results_overview.html'
    context_object_name = 'results'
    paginate_by = 25
    
    def get_queryset(self):
        session_id = self.kwargs['session_id']
        queryset = ProcessedResult.objects.filter(
            session_id=session_id
        ).select_related(
            'raw_result__search_execution__search_query'
        ).prefetch_related(
            Prefetch(
                'tag_assignments',
                queryset=ReviewTagAssignment.objects.filter(
                    user=self.request.user,
                    session_id=session_id
                ).select_related('tag'),
                to_attr='user_tag_assignments'
            ),
            Prefetch(
                'notes',
                queryset=Note.objects.filter(
                    user=self.request.user,
                    session_id=session_id
                ),
                to_attr='user_notes'
            ),
            'duplicate_relationships'
        )
        
        # Apply filters
        filter_form = ResultFilterForm(self.request.GET)
        if filter_form.is_valid():
            filters = filter_form.cleaned_data
            
            # Tag filter
            if filters.get('tag'):
                if filters['tag'] == 'untagged':
                    # Subquery to find results without tags
                    tagged_results = ReviewTagAssignment.objects.filter(
                        processed_result=OuterRef('pk'),
                        user=self.request.user,
                        session_id=session_id
                    ).values('processed_result')
                    queryset = queryset.exclude(pk__in=Subquery(tagged_results))
                else:
                    queryset = queryset.filter(
                        tag_assignments__tag_id=filters['tag'],
                        tag_assignments__user=self.request.user
                    )
            
            # Other filters
            if filters.get('has_notes'):
                queryset = queryset.filter(
                    notes__user=self.request.user,
                    notes__session_id=session_id
                ).distinct()
            
            if filters.get('file_type'):
                queryset = queryset.filter(file_type=filters['file_type'])
            
            if filters.get('quality_score_min'):
                queryset = queryset.filter(
                    quality_score__gte=filters['quality_score_min']
                )
            
            if filters.get('is_duplicate') is not None:
                queryset = queryset.filter(is_duplicate=filters['is_duplicate'])
        
        # Apply sorting
        sort_by = self.request.GET.get('sort', '-processed_at')
        valid_sorts = [
            'processed_at', '-processed_at',
            'title', '-title',
            'quality_score', '-quality_score',
            'domain', '-domain'
        ]
        if sort_by in valid_sorts:
            queryset = queryset.order_by(sort_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.get_session()
        
        # Add session and progress data
        context['session'] = session
        context['filter_form'] = ResultFilterForm(self.request.GET)
        context['available_tags'] = ReviewTag.objects.filter(is_active=True)
        
        # Calculate progress
        total_results = session.processed_results.count()
        tagged_results = ReviewTagAssignment.objects.filter(
            session=session,
            user=self.request.user
        ).values('processed_result').distinct().count()
        
        context['progress'] = {
            'total': total_results,
            'tagged': tagged_results,
            'percentage': (tagged_results / total_results * 100) if total_results > 0 else 0
        }
        
        # Tag breakdown
        tag_counts = ReviewTagAssignment.objects.filter(
            session=session,
            user=self.request.user
        ).values('tag__name').annotate(count=Count('id'))
        
        context['tag_breakdown'] = {item['tag__name']: item['count'] for item in tag_counts}
        
        return context
    
    def get_session(self):
        """Get and validate session ownership."""
        session = SearchSession.objects.get(pk=self.kwargs['session_id'])
        if session.created_by != self.request.user:
            raise PermissionDenied("You don't have permission to review this session.")
        return session
```

#### AJAX Tag Assignment View
```python
from django.views import View
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
import json

@method_decorator(csrf_protect, name='dispatch')
class TagAssignmentView(LoginRequiredMixin, View):
    """
    AJAX endpoint for assigning tags to results.
    """
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            # Validate inputs
            result = ProcessedResult.objects.get(pk=data['processed_result_id'])
            tag = ReviewTag.objects.get(pk=data['tag_id'])
            session = SearchSession.objects.get(pk=data['session_id'])
            
            # Check permissions
            if session.created_by != request.user:
                return JsonResponse({'error': 'Permission denied'}, status=403)
            
            # Validate reason for exclusion tags
            if tag.requires_reason and not data.get('reason'):
                return JsonResponse({
                    'error': f'A reason is required for the "{tag.name}" tag'
                }, status=400)
            
            # Create or update assignment
            assignment, created = ReviewTagAssignment.objects.update_or_create(
                processed_result=result,
                session=session,
                user=request.user,
                defaults={
                    'tag': tag,
                    'reason': data.get('reason', ''),
                    'created_by': request.user,
                    'modified_by': request.user if not created else None
                }
            )
            
            # Update session status if needed
            if session.status == 'ready_for_review':
                session.status = 'under_review'
                session.save()
            
            # Check if review is complete
            self._check_review_completion(session)
            
            return JsonResponse({
                'success': True,
                'assignment_id': str(assignment.id),
                'tag_name': tag.name,
                'tag_color': tag.color,
                'created': created
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    def _check_review_completion(self, session):
        """Check if all results are tagged and update session status."""
        total_results = session.processed_results.count()
        tagged_results = ReviewTagAssignment.objects.filter(
            session=session,
            user=self.request.user
        ).values('processed_result').distinct().count()
        
        if tagged_results == total_results and total_results > 0:
            session.status = 'completed'
            session.save()
```

### 4.2 Forms

#### ReviewTagAssignmentForm
```python
from django import forms
from apps.review_results.models import ReviewTag, ReviewTagAssignment

class ReviewTagAssignmentForm(forms.ModelForm):
    """
    Form for tag assignment with conditional reason requirement.
    """
    class Meta:
        model = ReviewTagAssignment
        fields = ['tag', 'reason', 'confidence_score']
        widgets = {
            'reason': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Please provide a reason for exclusion...'
            }),
            'confidence_score': forms.NumberInput(attrs={
                'min': 0,
                'max': 1,
                'step': 0.1,
                'placeholder': '0.0 - 1.0'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tag'].queryset = ReviewTag.objects.filter(is_active=True)
        self.fields['reason'].required = False
        self.fields['confidence_score'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        tag = cleaned_data.get('tag')
        reason = cleaned_data.get('reason')
        
        if tag and tag.requires_reason and not reason:
            raise forms.ValidationError({
                'reason': f'A reason is required for the "{tag.name}" tag.'
            })
        
        return cleaned_data
```

#### ResultFilterForm
```python
class ResultFilterForm(forms.Form):
    """
    Form for filtering results in the overview.
    """
    tag = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    has_notes = forms.BooleanField(
        required=False,
        label='Has notes',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    file_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All file types')] + ProcessedResult.FILE_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    quality_score_min = forms.DecimalField(
        required=False,
        min_value=0,
        max_value=1,
        decimal_places=2,
        label='Minimum quality score',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'placeholder': '0.0'
        })
    )
    is_duplicate = forms.NullBooleanField(
        required=False,
        label='Duplicate status',
        widget=forms.Select(
            choices=[('', 'All'), ('true', 'Duplicates only'), ('false', 'Non-duplicates only')],
            attrs={'class': 'form-select'}
        )
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate tag choices
        tag_choices = [('', 'All tags'), ('untagged', 'Untagged')]
        tag_choices.extend(
            ReviewTag.objects.filter(is_active=True).values_list('id', 'name')
        )
        self.fields['tag'].choices = tag_choices
```

### 4.3 URLs
```python
# apps/review_results/urls.py
from django.urls import path
from apps.review_results import views

app_name = 'review_results'

urlpatterns = [
    # Main review interface
    path(
        'session/<uuid:session_id>/',
        views.ResultsOverviewView.as_view(),
        name='results_overview'
    ),
    
    # AJAX endpoints
    path(
        'api/tag-assignment/',
        views.TagAssignmentView.as_view(),
        name='tag_assignment'
    ),
    path(
        'api/notes/',
        views.NoteCreateView.as_view(),
        name='note_create'
    ),
    path(
        'api/notes/<uuid:note_id>/',
        views.NoteUpdateView.as_view(),
        name='note_update'
    ),
    path(
        'api/session/<uuid:session_id>/progress/',
        views.SessionProgressView.as_view(),
        name='session_progress'
    ),
    path(
        'api/duplicates/<uuid:result_id>/',
        views.DuplicateDetailsView.as_view(),
        name='duplicate_details'
    ),
    
    # Session management
    path(
        'session/<uuid:session_id>/conclude/',
        views.ConcludeReviewView.as_view(),
        name='conclude_review'
    ),
]
```

## 5. Business Logic

### 5.1 Services

#### ReviewService
```python
# apps/review_results/services.py
from django.db import transaction
from django.db.models import Count, Q
from apps.review_results.models import ReviewTag, ReviewTagAssignment, Note
from apps.review_manager.models import SearchSession
from apps.results_manager.models import ProcessedResult

class ReviewService:
    """
    Core business logic for review operations.
    """
    
    @staticmethod
    @transaction.atomic
    def assign_tag(processed_result, tag, user, session, reason=None, confidence=None):
        """
        Assign or update a tag for a result.
        """
        # Validate tag requirements
        if tag.requires_reason and not reason:
            raise ValueError(f'Reason required for {tag.name} tag')
        
        # Create or update assignment
        assignment, created = ReviewTagAssignment.objects.update_or_create(
            processed_result=processed_result,
            session=session,
            user=user,
            defaults={
                'tag': tag,
                'reason': reason or '',
                'confidence_score': confidence,
                'created_by': user,
                'modified_by': user if not created else None
            }
        )
        
        # Update session status if first review action
        if created and session.status == 'ready_for_review':
            session.status = 'under_review'
            session.save()
        
        # Log activity
        SessionActivity.objects.create(
            session=session,
            user=user,
            activity_type='tag_assigned',
            details={
                'result_id': str(processed_result.id),
                'tag': tag.name,
                'created': created
            }
        )
        
        return assignment
    
    @staticmethod
    def get_review_progress(session, user):
        """
        Calculate detailed review progress for a session.
        """
        total_results = session.processed_results.count()
        
        if total_results == 0:
            return {
                'total': 0,
                'tagged': 0,
                'percentage': 0,
                'is_complete': False,
                'tag_breakdown': {},
                'remaining': 0
            }
        
        # Get tagged results count
        tagged_results = ReviewTagAssignment.objects.filter(
            session=session,
            user=user
        ).values('processed_result').distinct().count()
        
        # Get tag breakdown
        tag_breakdown = ReviewTagAssignment.objects.filter(
            session=session,
            user=user
        ).values('tag__name', 'tag__color').annotate(
            count=Count('id')
        )
        
        breakdown_dict = {
            item['tag__name']: {
                'count': item['count'],
                'color': item['tag__color']
            }
            for item in tag_breakdown
        }
        
        return {
            'total': total_results,
            'tagged': tagged_results,
            'percentage': round((tagged_results / total_results) * 100, 1),
            'is_complete': tagged_results == total_results,
            'tag_breakdown': breakdown_dict,
            'remaining': total_results - tagged_results
        }
    
    @staticmethod
    @transaction.atomic
    def conclude_review(session, user, force=False):
        """
        Conclude the review process for a session.
        """
        progress = ReviewService.get_review_progress(session, user)
        
        if progress['is_complete']:
            session.status = 'completed'
        elif force:
            session.status = 'archived'
        else:
            raise ValueError(
                f"Cannot conclude review: {progress['remaining']} results remain untagged"
            )
        
        session.save()
        
        # Log activity
        SessionActivity.objects.create(
            session=session,
            user=user,
            activity_type='review_concluded',
            details={
                'forced': force,
                'progress': progress
            }
        )
        
        return session
    
    @staticmethod
    def bulk_assign_tags(result_ids, tag, user, session, reason=None):
        """
        Assign the same tag to multiple results.
        """
        results = ProcessedResult.objects.filter(
            id__in=result_ids,
            session=session
        )
        
        if tag.requires_reason and not reason:
            raise ValueError(f'Reason required for bulk {tag.name} assignment')
        
        assignments = []
        with transaction.atomic():
            for result in results:
                assignment = ReviewService.assign_tag(
                    result, tag, user, session, reason
                )
                assignments.append(assignment)
        
        return assignments
```

### 5.2 Managers

#### ReviewTagManager
```python
# apps/review_results/managers.py
from django.db import models

class ReviewTagManager(models.Manager):
    """Custom manager for ReviewTag model."""
    
    def active(self):
        """Return only active tags."""
        return self.filter(is_active=True)
    
    def get_default_tags(self):
        """Get the standard review tags."""
        return self.active().filter(
            slug__in=['include', 'exclude', 'maybe']
        ).order_by('display_order')
```

#### ReviewTagAssignmentManager(models.Manager):
    """Custom manager for ReviewTagAssignment model."""
    
    def for_session_user(self, session, user):
        """Get all assignments for a session by a specific user."""
        return self.filter(session=session, user=user)
    
    def get_user_tags_for_results(self, result_ids, user, session):
        """Get user's tags for a list of results efficiently."""
        return self.filter(
            processed_result_id__in=result_ids,
            user=user,
            session=session
        ).select_related('tag')
```

### 5.3 Utilities

#### Review Helpers
```python
# apps/review_results/utils.py
from django.core.cache import cache
from django.db.models import Prefetch
import hashlib

def get_cached_review_progress(session_id, user_id):
    """
    Get cached review progress with 5-minute TTL.
    """
    cache_key = f'review_progress:{session_id}:{user_id}'
    progress = cache.get(cache_key)
    
    if progress is None:
        from apps.review_results.services import ReviewService
        session = SearchSession.objects.get(pk=session_id)
        user = User.objects.get(pk=user_id)
        progress = ReviewService.get_review_progress(session, user)
        cache.set(cache_key, progress, 300)  # 5 minutes
    
    return progress

def invalidate_review_cache(session_id, user_id):
    """
    Invalidate cached review data when changes occur.
    """
    cache_key = f'review_progress:{session_id}:{user_id}'
    cache.delete(cache_key)

def export_review_data(session, user, format='csv'):
    """
    Export review data in various formats.
    """
    assignments = ReviewTagAssignment.objects.filter(
        session=session,
        user=user
    ).select_related(
        'processed_result',
        'tag'
    ).order_by('processed_result__title')
    
    if format == 'csv':
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Title', 'URL', 'Tag', 'Reason', 'Confidence', 'Date Tagged'])
        
        for assignment in assignments:
            writer.writerow([
                assignment.processed_result.title,
                assignment.processed_result.normalized_url,
                assignment.tag.name,
                assignment.reason or '',
                assignment.confidence_score or '',
                assignment.updated_at.strftime('%Y-%m-%d %H:%M')
            ])
        
        return output.getvalue()
    
    # Add other export formats as needed
    raise ValueError(f'Unsupported export format: {format}')
```

## 6. Testing Requirements

### 6.1 Unit Tests

#### Model Tests
```python
# apps/review_results/tests/test_models.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.review_results.models import ReviewTag, ReviewTagAssignment, Note
from apps.review_results.tests.factories import (
    ReviewTagFactory, ReviewTagAssignmentFactory, NoteFactory
)

class ReviewTagModelTest(TestCase):
    """Test ReviewTag model functionality."""
    
    def test_tag_creation(self):
        """Test creating a review tag with all fields."""
        tag = ReviewTag.objects.create(
            name='Include',
            description='Result should be included in the review',
            slug='include',
            color='#28a745',
            requires_reason=False,
            display_order=1
        )
        self.assertEqual(str(tag), 'Include')
        self.assertTrue(tag.is_active)
    
    def test_color_validation(self):
        """Test hex color code validation."""
        tag = ReviewTag(name='Test', slug='test', color='invalid')
        with self.assertRaises(ValidationError):
            tag.full_clean()
    
    def test_unique_constraints(self):
        """Test unique constraints on name and slug."""
        ReviewTag.objects.create(name='Test', slug='test')
        with self.assertRaises(Exception):
            ReviewTag.objects.create(name='Test', slug='different')

class ReviewTagAssignmentModelTest(TestCase):
    """Test ReviewTagAssignment model functionality."""
    
    def setUp(self):
        self.exclude_tag = ReviewTagFactory(
            name='Exclude',
            requires_reason=True
        )
        self.include_tag = ReviewTagFactory(
            name='Include',
            requires_reason=False
        )
    
    def test_assignment_with_required_reason(self):
        """Test that exclude tags require a reason."""
        assignment = ReviewTagAssignmentFactory.build(
            tag=self.exclude_tag,
            reason=''
        )
        with self.assertRaises(ValidationError) as context:
            assignment.full_clean()
        self.assertIn('reason', context.exception.message_dict)
    
    def test_unique_assignment_per_user_session(self):
        """Test that a user can only have one tag per result per session."""
        assignment = ReviewTagAssignmentFactory(tag=self.include_tag)
        
        # Try to create another assignment for the same result/user/session
        duplicate = ReviewTagAssignmentFactory.build(
            processed_result=assignment.processed_result,
            user=assignment.user,
            session=assignment.session,
            tag=self.exclude_tag
        )
        with self.assertRaises(Exception):
            duplicate.save()
    
    def test_assignment_cascade_deletion(self):
        """Test that assignments are deleted when result is deleted."""
        assignment = ReviewTagAssignmentFactory()
        result_id = assignment.processed_result.id
        assignment.processed_result.delete()
        
        self.assertFalse(
            ReviewTagAssignment.objects.filter(
                processed_result_id=result_id
            ).exists()
        )
```

#### View Tests
```python
# apps/review_results/tests/test_views.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from apps.review_results.tests.factories import *
from apps.review_manager.tests.factories import SearchSessionFactory
from apps.results_manager.tests.factories import ProcessedResultFactory

User = get_user_model()

class ResultsOverviewViewTest(TestCase):
    """Test the main results overview view."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.session = SearchSessionFactory(
            created_by=self.user,
            status='ready_for_review'
        )
        self.results = [
            ProcessedResultFactory(session=self.session)
            for _ in range(30)
        ]
    
    def test_requires_authentication(self):
        """Test that view requires login."""
        url = reverse('review_results:results_overview', args=[self.session.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('login', response.url)
    
    def test_ownership_validation(self):
        """Test that users can only review their own sessions."""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='otherpass'
        )
        self.client.login(email='other@example.com', password='otherpass')
        
        url = reverse('review_results:results_overview', args=[self.session.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
    
    def test_pagination(self):
        """Test results pagination."""
        self.client.login(email='test@example.com', password='testpass123')
        url = reverse('review_results:results_overview', args=[self.session.id])
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['results']), 25)
        self.assertTrue(response.context['is_paginated'])
    
    def test_filtering_by_tag(self):
        """Test filtering results by tag."""
        include_tag = ReviewTagFactory(name='Include', slug='include')
        
        # Tag some results
        for result in self.results[:10]:
            ReviewTagAssignmentFactory(
                processed_result=result,
                session=self.session,
                user=self.user,
                tag=include_tag
            )
        
        self.client.login(email='test@example.com', password='testpass123')
        url = reverse('review_results:results_overview', args=[self.session.id])
        
        response = self.client.get(url, {'tag': str(include_tag.id)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['results']), 10)

class TagAssignmentViewTest(TestCase):
    """Test AJAX tag assignment functionality."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.session = SearchSessionFactory(
            created_by=self.user,
            status='ready_for_review'
        )
        self.result = ProcessedResultFactory(session=self.session)
        self.tag = ReviewTagFactory(name='Include')
    
    def test_ajax_tag_assignment(self):
        """Test assigning a tag via AJAX."""
        self.client.login(email='test@example.com', password='testpass123')
        
        response = self.client.post(
            reverse('review_results:tag_assignment'),
            data={
                'processed_result_id': str(self.result.id),
                'tag_id': str(self.tag.id),
                'session_id': str(self.session.id)
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['tag_name'], 'Include')
        
        # Verify assignment was created
        assignment = ReviewTagAssignment.objects.get(
            processed_result=self.result,
            user=self.user
        )
        self.assertEqual(assignment.tag, self.tag)
    
    def test_session_status_update(self):
        """Test that session status updates on first tag."""
        self.client.login(email='test@example.com', password='testpass123')
        
        self.assertEqual(self.session.status, 'ready_for_review')
        
        self.client.post(
            reverse('review_results:tag_assignment'),
            data={
                'processed_result_id': str(self.result.id),
                'tag_id': str(self.tag.id),
                'session_id': str(self.session.id)
            },
            content_type='application/json'
        )
        
        self.session.refresh_from_db()
        self.assertEqual(self.session.status, 'under_review')
```

### 6.2 Integration Tests

```python
# apps/review_results/tests/test_integration.py
class ReviewWorkflowIntegrationTest(TestCase):
    """Test complete review workflow integration."""
    
    def test_complete_review_workflow(self):
        """Test reviewing all results and completing session."""
        # Setup
        user = User.objects.create_user(
            email='reviewer@example.com',
            password='reviewpass'
        )
        session = SearchSessionFactory(
            created_by=user,
            status='ready_for_review'
        )
        results = [
            ProcessedResultFactory(session=session)
            for _ in range(10)
        ]
        
        include_tag = ReviewTagFactory(name='Include', slug='include')
        exclude_tag = ReviewTagFactory(
            name='Exclude',
            slug='exclude',
            requires_reason=True
        )
        
        service = ReviewService()
        
        # Tag all results
        for i, result in enumerate(results):
            if i < 5:
                assignment = service.assign_tag(
                    result, include_tag, user, session
                )
            else:
                assignment = service.assign_tag(
                    result, exclude_tag, user, session,
                    reason='Not relevant to research question'
                )
        
        # Check progress
        progress = service.get_review_progress(session, user)
        self.assertEqual(progress['total'], 10)
        self.assertEqual(progress['tagged'], 10)
        self.assertTrue(progress['is_complete'])
        
        # Conclude review
        service.conclude_review(session, user)
        session.refresh_from_db()
        self.assertEqual(session.status, 'completed')
```

### 6.3 Security Tests

```python
# apps/review_results/tests/test_security.py
class ReviewSecurityTest(TestCase):
    """Test security measures in review functionality."""
    
    def test_cross_user_tag_isolation(self):
        """Test that users cannot see or modify other users' tags."""
        # Create two users with sessions
        user1 = User.objects.create_user('user1@test.com', 'pass1')
        user2 = User.objects.create_user('user2@test.com', 'pass2')
        
        session = SearchSessionFactory(created_by=user1)
        result = ProcessedResultFactory(session=session)
        tag = ReviewTagFactory(name='Include')
        
        # User1 tags a result
        ReviewTagAssignmentFactory(
            processed_result=result,
            session=session,
            user=user1,
            tag=tag
        )
        
        # User2 should not be able to access this session
        self.client.login(email='user2@test.com', password='pass2')
        url = reverse('review_results:results_overview', args=[session.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
    
    def test_sql_injection_protection(self):
        """Test protection against SQL injection in filters."""
        user = User.objects.create_user('test@test.com', 'testpass')
        session = SearchSessionFactory(created_by=user)
        
        self.client.login(email='test@test.com', password='testpass')
        
        # Attempt SQL injection via filter parameters
        malicious_params = {
            'tag': "'; DROP TABLE review_results_reviewtag; --",
            'sort': "processed_at; DELETE FROM auth_user;"
        }
        
        url = reverse('review_results:results_overview', args=[session.id])
        response = self.client.get(url, malicious_params)
        
        # Should handle gracefully without executing malicious SQL
        self.assertEqual(response.status_code, 200)
        
        # Verify tables still exist
        self.assertTrue(ReviewTag.objects.exists())
        self.assertTrue(User.objects.exists())
```

## 7. Performance Optimization

### 7.1 Database Optimization
```python
# Database indexes (defined in models)
class Meta:
    indexes = [
        models.Index(fields=['session', 'user', '-updated_at']),
        models.Index(fields=['tag', 'session']),
        models.Index(fields=['processed_result', 'user']),
    ]

# Query optimization in views
queryset = ProcessedResult.objects.filter(
    session_id=session_id
).select_related(
    'raw_result__search_execution__search_query'  # Avoid N+1 queries
).prefetch_related(
    Prefetch(
        'tag_assignments',
        queryset=ReviewTagAssignment.objects.filter(
            user=self.request.user,
            session_id=session_id
        ).select_related('tag'),
        to_attr='user_tag_assignments'  # Store in memory
    )
)
```

### 7.2 Caching Strategy
```python
# Redis caching for expensive operations
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'review_results',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# Cache warming for frequently accessed data
def warm_review_cache(session_id):
    """Pre-populate cache with review data."""
    session = SearchSession.objects.get(pk=session_id)
    users = session.review_tag_assignments.values_list(
        'user_id', flat=True
    ).distinct()
    
    for user_id in users:
        get_cached_review_progress(session_id, user_id)
```

### 7.3 Frontend Optimization
```javascript
// Debounced filtering to reduce server requests
let filterTimeout;
function applyFilters() {
    clearTimeout(filterTimeout);
    filterTimeout = setTimeout(() => {
        const form = document.getElementById('filter-form');
        form.submit();
    }, 500);  // 500ms delay
}

// Lazy loading for scroll pagination
const observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) {
        loadMoreResults();
    }
}, {
    rootMargin: '100px'  // Start loading before reaching bottom
});
```

## 8. Security Considerations

### 8.1 Authentication & Authorization
- All views protected with `LoginRequiredMixin`
- Session ownership validation in every view
- CSRF protection on all POST requests
- Rate limiting on AJAX endpoints

### 8.2 Data Validation
- Server-side validation for all user inputs
- Sanitization of user-provided text (notes, reasons)
- Protection against XSS through Django template auto-escaping
- SQL injection prevention through ORM usage

### 8.3 Audit Trail
- All review actions logged with user and timestamp
- Immutable audit records for compliance
- Separate created_by/modified_by tracking
- Activity logs for forensic analysis

## 9. Phase Implementation

### 9.1 Phase 1 (Current Scope)
- ✅ Core models (ReviewTag, ReviewTagAssignment, Note)
- ✅ Results overview with pagination
- ✅ AJAX-based tagging interface
- ✅ Note creation and editing
- ✅ Basic filtering and sorting
- ✅ Session status progression
- ✅ Duplicate indication
- ✅ Progress tracking

### 9.2 Phase 2 (Future Enhancements)
- [ ] RESTful API for external integrations
- [ ] Bulk tagging operations
- [ ] Advanced filtering with saved filters
- [ ] Collaborative review features
- [ ] Machine learning tag suggestions
- [ ] Export in multiple formats
- [ ] Review templates
- [ ] Inter-rater reliability metrics

## 10. Development Checklist

### 10.1 Implementation Checklist
- [ ] Create Django app structure
- [ ] Implement models with UUID primary keys
- [ ] Create database migrations
- [ ] Implement ResultsOverviewView with pagination
- [ ] Create AJAX tag assignment endpoint
- [ ] Implement note management system
- [ ] Add filtering and sorting forms
- [ ] Create progress tracking service
- [ ] Implement session status updates
- [ ] Add duplicate relationship display
- [ ] Create review conclusion workflow

### 10.2 Testing Checklist
- [ ] Unit tests for all models
- [ ] View tests with authentication
- [ ] Form validation tests
- [ ] Service layer tests
- [ ] Integration tests for complete workflow
- [ ] Security tests for data isolation
- [ ] Performance tests for large datasets
- [ ] JavaScript tests for AJAX functionality

### 10.3 Documentation Checklist
- [ ] API documentation for AJAX endpoints
- [ ] User guide for review interface
- [ ] Developer documentation for extending tags
- [ ] Deployment guide with performance tuning

## 11. Success Metrics

### 11.1 Performance Metrics
- Page load time < 3 seconds for 1000+ results
- AJAX operations complete < 1 second
- 95%+ test coverage
- Zero security vulnerabilities

### 11.2 User Experience Metrics
- Review completion rate > 90%
- Average time to review 100 results < 30 minutes
- User error rate < 5%
- Feature adoption rate > 80%

### 11.3 Technical Metrics
- Database query count < 10 per page load
- Memory usage < 256MB per worker
- Cache hit rate > 80%
- API response time < 200ms

## 12. References

### 12.1 Internal Documentation
- [Master PRD](../PRD.md)
- [Review Manager PRD](../review-manager/review-manager-prd.md)
- [Results Manager PRD](../results-manager/results-manager-prd.md)
- [UI Guidelines](../ui-guidelines.md)

### 12.2 External References
- [PRISMA Guidelines](http://www.prisma-statement.org/)
- [Django 4.2 Documentation](https://docs.djangoproject.com/en/4.2/)
- [AJAX Best Practices](https://developer.mozilla.org/en-US/docs/Web/Guide/AJAX)
- [Web Accessibility Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)

---

**Document Status:** Complete  
**Last Updated:** 2025-01-25  
**Next Review:** Phase 1 Implementation Completion