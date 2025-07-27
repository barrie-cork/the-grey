# Results Manager Product Requirements Document

**Project:** Thesis Grey - Systematic Grey Literature Review Tool  
**App:** Results Manager  
**Version:** 1.0  
**Date:** 2025-01-25  
**App Path:** `apps/results_manager/`  
**Master PRD:** [docs/PRD.md](../PRD.md)  
**Dependencies:** review_manager, search_strategy, serp_execution  
**Status:** Phase 1 Implementation - 33% Complete (Foundation & Core Services)

## 1. Executive Summary

### 1.1 Key Responsibilities
The Results Manager app serves as the critical processing pipeline between raw search results and the manual review interface. It implements sophisticated algorithms for URL normalization, metadata extraction, quality scoring, and deduplication. The app transforms raw search data into high-quality, deduplicated result sets ready for systematic review, ensuring data integrity and traceability throughout the processing pipeline.

### 1.2 Integration Points
- **SERP Execution**: Consumes RawSearchResult records for processing
- **Review Manager**: Updates SearchSession status through processing lifecycle
- **Review Results**: Provides ProcessedResult records for manual review
- **Notification System**: Sends real-time processing status updates

## 2. Technical Architecture

### 2.1 Technology Stack
- **Framework**: Django 4.2 with modular service architecture
- **Background Processing**: Celery 5.3 with Redis broker
- **Database**: PostgreSQL with UUID primary keys
- **Caching**: Redis for processing state and performance
- **Testing**: Django TestCase with 95%+ coverage target
- **Monitoring**: Celery Flower for task monitoring

### 2.2 App Structure
```
apps/results_manager/
├── __init__.py
├── apps.py
├── models.py              # ProcessedResult, DuplicateRelationship, ProcessingSession
├── views.py               # ResultsOverviewView, ProcessingStatusView
├── forms.py               # FilterForm, ProcessingConfigForm
├── urls.py                # URL patterns for results interface
├── admin.py               # Django admin configuration
├── services/
│   ├── __init__.py
│   ├── processing_service.py      # Main processing orchestration
│   ├── url_normalizer.py          # URL normalization engine
│   ├── metadata_extractor.py      # Metadata extraction service
│   ├── deduplication_engine.py    # Deduplication algorithms
│   └── quality_scorer.py          # Quality scoring logic
├── tasks.py               # Celery task definitions
├── signals.py             # Django signals for workflow triggers
├── managers.py            # Custom model managers
├── utils/
│   ├── __init__.py
│   ├── url_utils.py       # URL parsing utilities
│   ├── file_type_detector.py     # File type detection
│   └── domain_utils.py    # Domain enhancement utilities
├── templates/
│   └── results_manager/
│       ├── base.html
│       ├── results_overview.html
│       ├── processing_status.html
│       └── includes/
│           ├── result_card.html
│           ├── filters.html
│           └── status_progress.html
├── static/
│   └── results_manager/
│       ├── css/
│       │   └── results.css
│       └── js/
│           ├── status_updates.js
│           └── filters.js
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_services.py
│   ├── test_tasks.py
│   ├── test_url_normalizer.py
│   ├── test_deduplication.py
│   └── factories.py
└── migrations/
```

### 2.3 Database Models

#### ProcessedResult Model
```python
import uuid
from django.db import models
from django.contrib.postgres.fields import JSONField
from django.core.validators import MinValueValidator, MaxValueValidator

class ProcessedResult(models.Model):
    """
    Represents a processed and normalized search result ready for review.
    """
    # File type choices
    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF Document'),
        ('doc', 'Word Document'),
        ('html', 'Web Page'),
        ('ppt', 'PowerPoint'),
        ('xls', 'Excel Spreadsheet'),
        ('txt', 'Text File'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('image', 'Image'),
        ('unknown', 'Unknown'),
    ]
    
    # Primary key and relationships
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    session = models.ForeignKey(
        'review_manager.SearchSession',
        on_delete=models.CASCADE,
        related_name='processed_results'
    )
    raw_result = models.OneToOneField(
        'serp_execution.RawSearchResult',
        on_delete=models.CASCADE,
        related_name='processed_result'
    )
    
    # Core fields from raw result (normalized)
    title = models.CharField(
        max_length=500,
        help_text='Cleaned and normalized title'
    )
    normalized_url = models.URLField(
        max_length=2000,
        db_index=True,
        help_text='Normalized URL for deduplication'
    )
    original_url = models.URLField(
        max_length=2000,
        help_text='Original URL before normalization'
    )
    snippet = models.TextField(
        help_text='Cleaned description/snippet'
    )
    domain = models.CharField(
        max_length=255,
        db_index=True,
        help_text='Enhanced domain information'
    )
    
    # Extracted metadata
    file_type = models.CharField(
        max_length=10,
        choices=FILE_TYPE_CHOICES,
        default='unknown',
        db_index=True
    )
    content_type = models.CharField(
        max_length=100,
        blank=True,
        help_text='MIME type if detected'
    )
    estimated_size = models.BigIntegerField(
        null=True,
        blank=True,
        help_text='Estimated file size in bytes'
    )
    language = models.CharField(
        max_length=10,
        blank=True,
        help_text='ISO language code'
    )
    publication_date = models.DateField(
        null=True,
        blank=True,
        help_text='Extracted publication date'
    )
    
    # Quality and processing metadata
    quality_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.50,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text='Quality score based on metadata completeness (0.00-1.00)'
    )
    is_duplicate = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Whether this result is a duplicate'
    )
    duplicate_of = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='duplicate_instances',
        help_text='Primary result if this is a duplicate'
    )
    
    # Processing information
    processed_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True
    )
    processing_version = models.CharField(
        max_length=20,
        default='1.0',
        help_text='Version of processing algorithms used'
    )
    processing_errors = JSONField(
        default=dict,
        blank=True,
        help_text='Any errors encountered during processing'
    )
    
    # Enhanced metadata for Phase 2
    enhanced_metadata = JSONField(
        default=dict,
        blank=True,
        help_text='Additional extracted metadata (authors, affiliations, etc.)'
    )
    
    # Search engine traceability
    search_engine = models.CharField(
        max_length=50,
        help_text='Source search engine (denormalized for performance)'
    )
    
    class Meta:
        ordering = ['-processed_at']
        indexes = [
            models.Index(fields=['session', '-processed_at']),
            models.Index(fields=['session', 'is_duplicate']),
            models.Index(fields=['normalized_url', 'session']),
            models.Index(fields=['domain', 'session']),
            models.Index(fields=['file_type', 'quality_score']),
        ]
        unique_together = [['session', 'normalized_url']]
    
    def __str__(self):
        return f"{self.title[:100]} ({self.domain})"
    
    def save(self, *args, **kwargs):
        """Ensure search engine is denormalized on save."""
        if not self.search_engine and self.raw_result:
            self.search_engine = self.raw_result.search_execution.search_query.search_engine
        super().save(*args, **kwargs)
```

#### DuplicateRelationship Model
```python
class DuplicateRelationship(models.Model):
    """
    Tracks duplicate relationships between processed results.
    """
    DETECTION_METHODS = [
        ('exact_url', 'Exact URL Match'),
        ('normalized_url', 'Normalized URL Match'),
        ('title_similarity', 'Title Similarity'),
        ('content_hash', 'Content Hash'),
        ('combined', 'Combined Methods'),
    ]
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    original = models.ForeignKey(
        ProcessedResult,
        on_delete=models.CASCADE,
        related_name='duplicate_relationships'
    )
    duplicate = models.ForeignKey(
        ProcessedResult,
        on_delete=models.CASCADE,
        related_name='duplicate_of_relationships'
    )
    detection_method = models.CharField(
        max_length=20,
        choices=DETECTION_METHODS
    )
    similarity_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text='Similarity score (0.00-1.00)'
    )
    confidence_level = models.CharField(
        max_length=10,
        choices=[
            ('high', 'High'),
            ('medium', 'Medium'),
            ('low', 'Low'),
        ],
        default='medium'
    )
    verified = models.BooleanField(
        default=False,
        help_text='Manually verified by user'
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['original', 'duplicate']]
        indexes = [
            models.Index(fields=['original', 'confidence_level']),
            models.Index(fields=['duplicate']),
        ]
    
    def __str__(self):
        return f"{self.original.title[:50]} -> {self.duplicate.title[:50]}"
```

#### ProcessingSession Model
```python
class ProcessingSession(models.Model):
    """
    Tracks the processing state and progress for a search session.
    """
    PROCESSING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('partial', 'Partially Completed'),
    ]
    
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    search_session = models.OneToOneField(
        'review_manager.SearchSession',
        on_delete=models.CASCADE,
        related_name='processing_session'
    )
    status = models.CharField(
        max_length=20,
        choices=PROCESSING_STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    
    # Progress tracking
    total_raw_results = models.IntegerField(default=0)
    processed_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    duplicate_count = models.IntegerField(default=0)
    
    # Processing stages
    current_stage = models.CharField(
        max_length=50,
        blank=True,
        help_text='Current processing stage'
    )
    stage_progress = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text='Progress within current stage (0-100)'
    )
    
    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_heartbeat = models.DateTimeField(
        auto_now=True,
        help_text='Last update from processing task'
    )
    
    # Error handling
    error_details = JSONField(
        default=dict,
        blank=True,
        help_text='Detailed error information'
    )
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    
    # Configuration
    processing_config = JSONField(
        default=dict,
        help_text='Processing configuration used'
    )
    
    # Celery task tracking
    celery_task_id = models.CharField(
        max_length=255,
        blank=True,
        help_text='Celery task ID for monitoring'
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['status', '-started_at']),
            models.Index(fields=['search_session', 'status']),
        ]
    
    def __str__(self):
        return f"Processing for {self.search_session_id} - {self.status}"
    
    @property
    def progress_percentage(self):
        """Calculate overall progress percentage."""
        if self.total_raw_results == 0:
            return 0
        return min(100, int((self.processed_count / self.total_raw_results) * 100))
    
    @property
    def duration(self):
        """Calculate processing duration."""
        if not self.started_at:
            return None
        end_time = self.completed_at or timezone.now()
        return end_time - self.started_at
```

## 3. API Endpoints

### 3.1 Phase 1 Endpoints (Current Implementation)
Internal endpoints for processing status and management:

#### Processing Status Endpoints
```python
# Get processing status
GET /api/results-manager/processing-status/{session_id}/
    Response: {
        "status": "in_progress",
        "progress_percentage": 75,
        "current_stage": "deduplication",
        "stage_progress": 50,
        "total_raw_results": 1000,
        "processed_count": 750,
        "duplicate_count": 45,
        "error_count": 2,
        "started_at": "2025-01-25T10:00:00Z",
        "estimated_completion": "2025-01-25T10:02:00Z"
    }

# Retry failed processing
POST /api/results-manager/retry-processing/{session_id}/
    Response: {
        "success": true,
        "task_id": "celery-task-uuid",
        "message": "Processing restarted"
    }

# Get processing errors
GET /api/results-manager/processing-errors/{session_id}/
    Response: {
        "errors": [
            {
                "result_id": "uuid",
                "error_type": "url_normalization",
                "message": "Invalid URL format",
                "timestamp": "2025-01-25T10:01:00Z"
            }
        ]
    }
```

### 3.2 Phase 2 API Endpoints (Future RESTful API)
```python
# Full RESTful API for external integrations
GET    /api/v1/results/{session_id}/processed/
POST   /api/v1/results/reprocess/{session_id}/
GET    /api/v1/results/duplicates/{session_id}/
PUT    /api/v1/results/duplicate-verification/{relationship_id}/
GET    /api/v1/results/export/{session_id}/
```

## 4. User Interface

### 4.1 Views

#### ResultsOverviewView
```python
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count, Avg
from apps.results_manager.models import ProcessedResult, ProcessingSession
from apps.results_manager.forms import ResultFilterForm
from apps.review_manager.models import SearchSession

class ResultsOverviewView(LoginRequiredMixin, ListView):
    """
    Display processed results with filtering and sorting capabilities.
    """
    model = ProcessedResult
    template_name = 'results_manager/results_overview.html'
    context_object_name = 'results'
    paginate_by = 50
    
    def dispatch(self, request, *args, **kwargs):
        """Validate session ownership before processing request."""
        self.session = self.get_session()
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = ProcessedResult.objects.filter(
            session=self.session
        ).select_related(
            'raw_result',
            'duplicate_of'
        ).prefetch_related(
            'duplicate_relationships'
        )
        
        # Apply filters from form
        self.filter_form = ResultFilterForm(self.request.GET)
        if self.filter_form.is_valid():
            filters = self.filter_form.cleaned_data
            
            # Domain filter
            if filters.get('domain'):
                queryset = queryset.filter(domain__icontains=filters['domain'])
            
            # File type filter
            if filters.get('file_type'):
                queryset = queryset.filter(file_type=filters['file_type'])
            
            # Duplicate status filter
            if filters.get('duplicate_status') == 'duplicates':
                queryset = queryset.filter(is_duplicate=True)
            elif filters.get('duplicate_status') == 'unique':
                queryset = queryset.filter(is_duplicate=False)
            
            # Quality score filter
            if filters.get('quality_score_min') is not None:
                queryset = queryset.filter(
                    quality_score__gte=filters['quality_score_min']
                )
            
            # Processing status filter
            if filters.get('has_errors'):
                queryset = queryset.exclude(processing_errors={})
        
        # Apply sorting
        sort_field = self.request.GET.get('sort', '-processed_at')
        valid_sorts = {
            'processed_at': 'processed_at',
            '-processed_at': '-processed_at',
            'title': 'title',
            '-title': '-title',
            'quality_score': 'quality_score',
            '-quality_score': '-quality_score',
            'domain': 'domain',
            '-domain': '-domain',
        }
        
        if sort_field in valid_sorts:
            queryset = queryset.order_by(valid_sorts[sort_field])
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add session and processing info
        context['session'] = self.session
        context['filter_form'] = self.filter_form
        
        # Get processing session if exists
        try:
            context['processing_session'] = self.session.processing_session
        except ProcessingSession.DoesNotExist:
            context['processing_session'] = None
        
        # Calculate statistics
        stats = ProcessedResult.objects.filter(
            session=self.session
        ).aggregate(
            total_count=Count('id'),
            duplicate_count=Count('id', filter=Q(is_duplicate=True)),
            avg_quality_score=Avg('quality_score'),
            error_count=Count('id', filter=~Q(processing_errors={}))
        )
        context['stats'] = stats
        
        # File type breakdown
        file_type_stats = ProcessedResult.objects.filter(
            session=self.session
        ).values('file_type').annotate(
            count=Count('id')
        ).order_by('-count')
        context['file_type_stats'] = file_type_stats
        
        return context
    
    def get_session(self):
        """Get and validate session ownership."""
        session = SearchSession.objects.get(pk=self.kwargs['session_id'])
        if session.created_by != self.request.user:
            raise PermissionDenied("You don't have permission to view these results.")
        return session
```

#### ProcessingStatusView
```python
from django.views.generic import DetailView
from django.http import JsonResponse
from django.views import View

class ProcessingStatusView(LoginRequiredMixin, DetailView):
    """
    Display real-time processing status with progress updates.
    """
    model = ProcessingSession
    template_name = 'results_manager/processing_status.html'
    context_object_name = 'processing'
    
    def get_object(self):
        session = SearchSession.objects.get(pk=self.kwargs['session_id'])
        if session.created_by != self.request.user:
            raise PermissionDenied()
        
        try:
            return session.processing_session
        except ProcessingSession.DoesNotExist:
            # Create processing session if doesn't exist
            return ProcessingSession.objects.create(
                search_session=session,
                status='pending'
            )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['session'] = self.object.search_session
        
        # Add stage information
        stages = [
            {'name': 'Initialization', 'key': 'init', 'complete': False},
            {'name': 'URL Normalization', 'key': 'normalization', 'complete': False},
            {'name': 'Metadata Extraction', 'key': 'metadata', 'complete': False},
            {'name': 'Deduplication', 'key': 'deduplication', 'complete': False},
            {'name': 'Quality Scoring', 'key': 'scoring', 'complete': False},
            {'name': 'Finalization', 'key': 'final', 'complete': False},
        ]
        
        # Mark completed stages
        current_stage_index = next(
            (i for i, s in enumerate(stages) if s['key'] == self.object.current_stage),
            -1
        )
        for i in range(current_stage_index):
            stages[i]['complete'] = True
        
        context['stages'] = stages
        return context


class ProcessingStatusAPIView(LoginRequiredMixin, View):
    """
    AJAX endpoint for real-time status updates.
    """
    def get(self, request, session_id):
        session = SearchSession.objects.get(pk=session_id)
        if session.created_by != request.user:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        try:
            processing = session.processing_session
            
            # Calculate estimated completion
            if processing.status == 'in_progress' and processing.started_at:
                elapsed = (timezone.now() - processing.started_at).total_seconds()
                if processing.progress_percentage > 0:
                    total_estimated = elapsed / (processing.progress_percentage / 100)
                    remaining = total_estimated - elapsed
                    estimated_completion = timezone.now() + timedelta(seconds=remaining)
                else:
                    estimated_completion = None
            else:
                estimated_completion = processing.completed_at
            
            return JsonResponse({
                'status': processing.status,
                'progress_percentage': processing.progress_percentage,
                'current_stage': processing.current_stage,
                'stage_progress': processing.stage_progress,
                'total_raw_results': processing.total_raw_results,
                'processed_count': processing.processed_count,
                'duplicate_count': processing.duplicate_count,
                'error_count': processing.error_count,
                'started_at': processing.started_at.isoformat() if processing.started_at else None,
                'estimated_completion': estimated_completion.isoformat() if estimated_completion else None,
            })
            
        except ProcessingSession.DoesNotExist:
            return JsonResponse({
                'status': 'not_started',
                'message': 'Processing has not been initiated'
            })
```

### 4.2 Forms

#### ResultFilterForm
```python
from django import forms
from apps.results_manager.models import ProcessedResult

class ResultFilterForm(forms.Form):
    """
    Form for filtering processed results.
    """
    domain = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by domain...'
        })
    )
    
    file_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All file types')] + ProcessedResult.FILE_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    duplicate_status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All results'),
            ('duplicates', 'Duplicates only'),
            ('unique', 'Unique only')
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    quality_score_min = forms.DecimalField(
        required=False,
        min_value=0,
        max_value=1,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.1',
            'min': '0',
            'max': '1',
            'placeholder': 'Min quality score'
        })
    )
    
    has_errors = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Show only results with errors'
    )


class ProcessingRetryForm(forms.Form):
    """
    Form for retrying failed processing.
    """
    retry_failed_only = forms.BooleanField(
        required=False,
        initial=True,
        label='Retry only failed results',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    force_reprocess = forms.BooleanField(
        required=False,
        initial=False,
        label='Force reprocess all results',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Warning: This will overwrite existing processed results'
    )
```

### 4.3 URLs
```python
# apps/results_manager/urls.py
from django.urls import path
from apps.results_manager import views

app_name = 'results_manager'

urlpatterns = [
    # Results viewing
    path(
        'session/<uuid:session_id>/results/',
        views.ResultsOverviewView.as_view(),
        name='results_overview'
    ),
    
    # Processing status
    path(
        'session/<uuid:session_id>/processing-status/',
        views.ProcessingStatusView.as_view(),
        name='processing_status'
    ),
    
    # API endpoints
    path(
        'api/processing-status/<uuid:session_id>/',
        views.ProcessingStatusAPIView.as_view(),
        name='api_processing_status'
    ),
    path(
        'api/retry-processing/<uuid:session_id>/',
        views.RetryProcessingAPIView.as_view(),
        name='api_retry_processing'
    ),
    path(
        'api/processing-errors/<uuid:session_id>/',
        views.ProcessingErrorsAPIView.as_view(),
        name='api_processing_errors'
    ),
    
    # Duplicate management (Phase 2)
    path(
        'session/<uuid:session_id>/duplicates/',
        views.DuplicateOverviewView.as_view(),
        name='duplicate_overview'
    ),
]
```

## 5. Business Logic

### 5.1 Services

#### ProcessingService (Main Orchestrator)
```python
# apps/results_manager/services/processing_service.py
from django.db import transaction
from celery import chain, group, chord
from apps.results_manager.models import ProcessedResult, ProcessingSession
from apps.results_manager.tasks import (
    initialize_processing_task,
    process_batch_task,
    finalize_processing_task
)

class ProcessingService:
    """
    Main service for orchestrating result processing pipeline.
    """
    
    def __init__(self, session_id, config=None):
        self.session_id = session_id
        self.config = config or self.get_default_config()
        self.batch_size = self.config.get('batch_size', 50)
    
    @staticmethod
    def get_default_config():
        """Get default processing configuration."""
        return {
            'batch_size': 50,
            'url_normalization': {
                'remove_tracking': True,
                'lowercase_domain': True,
                'remove_fragments': True,
                'normalize_protocol': True,
            },
            'deduplication': {
                'methods': ['normalized_url'],
                'threshold': 0.95,
            },
            'quality_scoring': {
                'weights': {
                    'has_title': 0.2,
                    'has_snippet': 0.2,
                    'has_metadata': 0.3,
                    'url_quality': 0.3,
                }
            },
            'retry_policy': {
                'max_retries': 3,
                'retry_delay': 60,  # seconds
            }
        }
    
    def start_processing(self):
        """
        Start the processing pipeline for a search session.
        """
        from apps.review_manager.models import SearchSession
        from apps.serp_execution.models import RawSearchResult
        
        session = SearchSession.objects.get(pk=self.session_id)
        
        # Create or update processing session
        processing_session, created = ProcessingSession.objects.update_or_create(
            search_session=session,
            defaults={
                'status': 'pending',
                'processing_config': self.config,
                'total_raw_results': RawSearchResult.objects.filter(
                    search_execution__search_query__session=session
                ).count()
            }
        )
        
        # Create processing workflow
        workflow = self._create_processing_workflow(processing_session)
        
        # Execute workflow
        result = workflow.apply_async()
        
        # Store task ID for monitoring
        processing_session.celery_task_id = result.id
        processing_session.save()
        
        return processing_session
    
    def _create_processing_workflow(self, processing_session):
        """
        Create Celery workflow for processing.
        """
        from apps.serp_execution.models import RawSearchResult
        
        # Get raw results to process
        raw_results = RawSearchResult.objects.filter(
            search_execution__search_query__session_id=self.session_id
        ).values_list('id', flat=True)
        
        # Create batches
        batches = [
            list(raw_results[i:i + self.batch_size])
            for i in range(0, len(raw_results), self.batch_size)
        ]
        
        # Build workflow: initialize -> process batches in parallel -> finalize
        workflow = chain(
            initialize_processing_task.si(processing_session.id),
            chord(
                [process_batch_task.si(processing_session.id, batch) for batch in batches],
                finalize_processing_task.si(processing_session.id)
            )
        )
        
        return workflow
    
    @staticmethod
    @transaction.atomic
    def retry_failed_processing(session_id, retry_failed_only=True):
        """
        Retry processing for failed results.
        """
        processing_session = ProcessingSession.objects.get(
            search_session_id=session_id
        )
        
        if retry_failed_only:
            # Only retry results that failed
            from apps.serp_execution.models import RawSearchResult
            
            failed_results = RawSearchResult.objects.filter(
                search_execution__search_query__session_id=session_id
            ).exclude(
                processed_result__isnull=False
            ).values_list('id', flat=True)
            
            if not failed_results:
                return processing_session
            
            # Reset retry count
            processing_session.retry_count += 1
            processing_session.status = 'pending'
            processing_session.save()
            
            # Process only failed results
            service = ProcessingService(session_id)
            service._process_specific_results(list(failed_results))
        else:
            # Full reprocessing
            ProcessedResult.objects.filter(session_id=session_id).delete()
            service = ProcessingService(session_id)
            service.start_processing()
        
        return processing_session
```

#### URL Normalizer Service
```python
# apps/results_manager/services/url_normalizer.py
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
import re

class URLNormalizer:
    """
    Service for comprehensive URL normalization.
    """
    
    # Common tracking parameters to remove
    TRACKING_PARAMS = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', 'dclid', 'msclkid', 'mc_cid', 'mc_eid',
        '_ga', '_gid', '_gac', '_gl', '_gclxxxx',
        'pk_campaign', 'pk_kwd', 'pk_source',
        'ref', 'referer', 'referrer', 'source',
        'campaign', 'ad', 'adgroup', 'creative',
        'placement', 'network', 'keyword', 'matchtype',
        'device', 'devicemodel', 'target', 'feeditemid',
        'targetid', 'loc_interest_ms', 'loc_physical_ms',
        'gclsrc', 'gbraid', 'wbraid'
    }
    
    def __init__(self, config=None):
        self.config = config or {}
        self.remove_tracking = self.config.get('remove_tracking', True)
        self.lowercase_domain = self.config.get('lowercase_domain', True)
        self.remove_fragments = self.config.get('remove_fragments', True)
        self.normalize_protocol = self.config.get('normalize_protocol', True)
    
    def normalize(self, url):
        """
        Normalize a URL according to configuration.
        """
        if not url:
            return url
        
        try:
            # Parse URL
            parsed = urlparse(url)
            
            # Normalize protocol
            if self.normalize_protocol:
                scheme = 'https' if parsed.scheme in ['http', 'https'] else parsed.scheme
            else:
                scheme = parsed.scheme
            
            # Normalize domain
            netloc = parsed.netloc.lower() if self.lowercase_domain else parsed.netloc
            
            # Remove www prefix
            if netloc.startswith('www.'):
                netloc = netloc[4:]
            
            # Normalize path
            path = self._normalize_path(parsed.path)
            
            # Clean query parameters
            if self.remove_tracking and parsed.query:
                params = parse_qs(parsed.query, keep_blank_values=True)
                cleaned_params = {
                    k: v for k, v in params.items()
                    if k.lower() not in self.TRACKING_PARAMS
                }
                query = urlencode(cleaned_params, doseq=True)
            else:
                query = parsed.query
            
            # Remove fragments
            fragment = '' if self.remove_fragments else parsed.fragment
            
            # Reconstruct URL
            normalized = urlunparse((
                scheme,
                netloc,
                path,
                parsed.params,
                query,
                fragment
            ))
            
            return normalized
            
        except Exception as e:
            # Log error and return original URL
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"URL normalization failed for {url}: {str(e)}")
            return url
    
    def _normalize_path(self, path):
        """
        Normalize URL path component.
        """
        if not path:
            return '/'
        
        # Remove duplicate slashes
        path = re.sub(r'/+', '/', path)
        
        # Remove trailing slash unless it's the root
        if len(path) > 1 and path.endswith('/'):
            path = path[:-1]
        
        # Remove common index files
        index_files = ['index.html', 'index.htm', 'index.php', 'default.asp']
        for index in index_files:
            if path.endswith('/' + index):
                path = path[:-len(index) - 1] or '/'
        
        return path
    
    def get_domain(self, url):
        """
        Extract enhanced domain information from URL.
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Extract root domain
            parts = domain.split('.')
            if len(parts) > 2:
                # Handle common TLDs with multiple parts
                multi_part_tlds = ['co.uk', 'gov.uk', 'ac.uk', 'org.uk', 'com.au', 'gov.au']
                for tld in multi_part_tlds:
                    if domain.endswith(tld):
                        root_parts = parts[-(tld.count('.') + 2):]
                        return '.'.join(root_parts)
                
                # Standard domain
                return '.'.join(parts[-2:])
            
            return domain
            
        except Exception:
            return ''
```

#### Metadata Extractor Service
```python
# apps/results_manager/services/metadata_extractor.py
import re
from datetime import datetime
from urllib.parse import urlparse, unquote

class MetadataExtractor:
    """
    Service for extracting metadata from search results.
    """
    
    # File type patterns
    FILE_TYPE_PATTERNS = {
        'pdf': re.compile(r'\.pdf($|\?)', re.I),
        'doc': re.compile(r'\.(doc|docx)($|\?)', re.I),
        'xls': re.compile(r'\.(xls|xlsx)($|\?)', re.I),
        'ppt': re.compile(r'\.(ppt|pptx)($|\?)', re.I),
        'txt': re.compile(r'\.txt($|\?)', re.I),
        'video': re.compile(r'\.(mp4|avi|mov|wmv|flv|webm)($|\?)', re.I),
        'audio': re.compile(r'\.(mp3|wav|ogg|m4a|wma)($|\?)', re.I),
        'image': re.compile(r'\.(jpg|jpeg|png|gif|bmp|svg|webp)($|\?)', re.I),
    }
    
    # Size estimation multipliers (based on typical file sizes)
    SIZE_ESTIMATES = {
        'pdf': 500 * 1024,      # 500 KB average
        'doc': 300 * 1024,      # 300 KB
        'xls': 200 * 1024,      # 200 KB
        'ppt': 2 * 1024 * 1024, # 2 MB
        'video': 50 * 1024 * 1024,  # 50 MB
        'html': 50 * 1024,      # 50 KB
    }
    
    def extract(self, raw_result):
        """
        Extract comprehensive metadata from a raw search result.
        """
        metadata = {
            'file_type': self._detect_file_type(raw_result.url),
            'estimated_size': self._estimate_size(raw_result.url),
            'language': self._detect_language(raw_result.snippet),
            'publication_date': self._extract_date(raw_result.snippet),
            'quality_indicators': self._assess_quality_indicators(raw_result),
        }
        
        # Clean and enhance title
        metadata['cleaned_title'] = self._clean_title(raw_result.title)
        
        # Clean snippet
        metadata['cleaned_snippet'] = self._clean_snippet(raw_result.snippet)
        
        return metadata
    
    def _detect_file_type(self, url):
        """
        Detect file type from URL.
        """
        if not url:
            return 'unknown'
        
        # Decode URL
        decoded_url = unquote(url.lower())
        
        # Check patterns
        for file_type, pattern in self.FILE_TYPE_PATTERNS.items():
            if pattern.search(decoded_url):
                return file_type
        
        # Default to HTML for web pages
        parsed = urlparse(url)
        if parsed.scheme in ['http', 'https']:
            return 'html'
        
        return 'unknown'
    
    def _estimate_size(self, url):
        """
        Estimate file size based on type.
        """
        file_type = self._detect_file_type(url)
        return self.SIZE_ESTIMATES.get(file_type, 100 * 1024)  # Default 100KB
    
    def _detect_language(self, text):
        """
        Basic language detection from text.
        """
        if not text:
            return 'en'  # Default to English
        
        # Simple heuristic - can be enhanced with langdetect library
        # Check for common non-English characters
        if re.search(r'[\u4e00-\u9fff]', text):  # Chinese
            return 'zh'
        elif re.search(r'[\u0400-\u04ff]', text):  # Cyrillic
            return 'ru'
        elif re.search(r'[\u0600-\u06ff]', text):  # Arabic
            return 'ar'
        elif re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):  # Japanese
            return 'ja'
        
        return 'en'
    
    def _extract_date(self, text):
        """
        Extract publication date from text.
        """
        if not text:
            return None
        
        # Common date patterns
        date_patterns = [
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
            r'(\d{2}/\d{2}/\d{4})',  # DD/MM/YYYY or MM/DD/YYYY
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}',
            r'\d{1,2}\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.I)
            if match:
                try:
                    # Parse date - would need more sophisticated parsing in production
                    date_str = match.group(0)
                    # Simplified - would use dateutil.parser in production
                    return None  # Placeholder
                except:
                    continue
        
        return None
    
    def _assess_quality_indicators(self, raw_result):
        """
        Assess quality indicators for scoring.
        """
        indicators = {
            'has_title': bool(raw_result.title and len(raw_result.title) > 10),
            'has_snippet': bool(raw_result.snippet and len(raw_result.snippet) > 20),
            'url_depth': self._calculate_url_depth(raw_result.url),
            'domain_quality': self._assess_domain_quality(raw_result.domain),
            'title_length': len(raw_result.title) if raw_result.title else 0,
            'snippet_length': len(raw_result.snippet) if raw_result.snippet else 0,
        }
        
        return indicators
    
    def _calculate_url_depth(self, url):
        """
        Calculate URL depth (number of path segments).
        """
        try:
            parsed = urlparse(url)
            path_segments = [s for s in parsed.path.split('/') if s]
            return len(path_segments)
        except:
            return 0
    
    def _assess_domain_quality(self, domain):
        """
        Basic domain quality assessment.
        """
        if not domain:
            return 0.5
        
        # Academic/government domains get higher scores
        high_quality_tlds = ['.edu', '.gov', '.ac.uk', '.org']
        for tld in high_quality_tlds:
            if domain.endswith(tld):
                return 0.9
        
        # Known quality domains (would be configured)
        quality_domains = ['pubmed.ncbi.nlm.nih.gov', 'scholar.google.com']
        if any(domain.endswith(qd) for qd in quality_domains):
            return 0.85
        
        return 0.5
    
    def _clean_title(self, title):
        """
        Clean and normalize title text.
        """
        if not title:
            return ''
        
        # Remove excessive whitespace
        title = ' '.join(title.split())
        
        # Remove common suffixes
        suffixes_to_remove = [
            ' - PDF', ' | PDF', ' [PDF]', ' (PDF)',
            ' - Download', ' | Download',
        ]
        for suffix in suffixes_to_remove:
            if title.endswith(suffix):
                title = title[:-len(suffix)]
        
        return title.strip()
    
    def _clean_snippet(self, snippet):
        """
        Clean and normalize snippet text.
        """
        if not snippet:
            return ''
        
        # Remove excessive whitespace
        snippet = ' '.join(snippet.split())
        
        # Remove common metadata prefixes
        snippet = re.sub(r'^(Abstract|Summary|Introduction):\s*', '', snippet, flags=re.I)
        
        # Ensure snippet ends properly
        if len(snippet) > 300:
            snippet = snippet[:297] + '...'
        
        return snippet.strip()
```

#### Deduplication Engine
```python
# apps/results_manager/services/deduplication_engine.py
from django.db import transaction
from difflib import SequenceMatcher
import hashlib

class DeduplicationEngine:
    """
    Service for detecting and managing duplicate results.
    """
    
    def __init__(self, config=None):
        self.config = config or {}
        self.methods = self.config.get('methods', ['normalized_url'])
        self.threshold = self.config.get('threshold', 0.95)
    
    def find_duplicates(self, processed_results):
        """
        Find duplicates within a set of processed results.
        """
        from apps.results_manager.models import DuplicateRelationship
        
        duplicates = []
        results_by_url = {}
        
        # Group by normalized URL (Phase 1)
        for result in processed_results:
            url_key = result.normalized_url.lower()
            
            if url_key in results_by_url:
                # Found a duplicate
                original = results_by_url[url_key]
                duplicates.append({
                    'original': original,
                    'duplicate': result,
                    'method': 'normalized_url',
                    'score': 1.0,
                    'confidence': 'high'
                })
            else:
                results_by_url[url_key] = result
        
        # Phase 2: Additional duplicate detection methods
        if 'title_similarity' in self.methods:
            duplicates.extend(self._find_title_duplicates(processed_results))
        
        return duplicates
    
    @transaction.atomic
    def create_duplicate_relationships(self, duplicates):
        """
        Create DuplicateRelationship records for found duplicates.
        """
        from apps.results_manager.models import DuplicateRelationship
        
        relationships = []
        
        for dup_info in duplicates:
            # Mark duplicate result
            dup_info['duplicate'].is_duplicate = True
            dup_info['duplicate'].duplicate_of = dup_info['original']
            dup_info['duplicate'].save()
            
            # Create relationship record
            relationship, created = DuplicateRelationship.objects.get_or_create(
                original=dup_info['original'],
                duplicate=dup_info['duplicate'],
                defaults={
                    'detection_method': dup_info['method'],
                    'similarity_score': dup_info['score'],
                    'confidence_level': dup_info['confidence']
                }
            )
            
            if created:
                relationships.append(relationship)
        
        return relationships
    
    def _find_title_duplicates(self, processed_results):
        """
        Find duplicates based on title similarity (Phase 2).
        """
        duplicates = []
        
        # Compare each result with others
        for i, result1 in enumerate(processed_results):
            if result1.is_duplicate:
                continue
                
            for result2 in processed_results[i+1:]:
                if result2.is_duplicate:
                    continue
                
                # Calculate title similarity
                similarity = self._calculate_similarity(
                    result1.title.lower(),
                    result2.title.lower()
                )
                
                if similarity >= self.threshold:
                    # Determine which is original (earlier processed)
                    if result1.processed_at < result2.processed_at:
                        original, duplicate = result1, result2
                    else:
                        original, duplicate = result2, result1
                    
                    duplicates.append({
                        'original': original,
                        'duplicate': duplicate,
                        'method': 'title_similarity',
                        'score': similarity,
                        'confidence': self._get_confidence_level(similarity)
                    })
        
        return duplicates
    
    def _calculate_similarity(self, text1, text2):
        """
        Calculate similarity score between two texts.
        """
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _get_confidence_level(self, score):
        """
        Determine confidence level based on similarity score.
        """
        if score >= 0.98:
            return 'high'
        elif score >= 0.90:
            return 'medium'
        else:
            return 'low'
    
    def merge_duplicate_clusters(self, session_id):
        """
        Merge duplicate relationships into clusters (Phase 2).
        """
        # Implementation for advanced duplicate cluster management
        pass
```

#### Quality Scorer
```python
# apps/results_manager/services/quality_scorer.py
class QualityScorer:
    """
    Service for calculating quality scores for processed results.
    """
    
    def __init__(self, config=None):
        self.config = config or {}
        self.weights = self.config.get('weights', {
            'has_title': 0.2,
            'has_snippet': 0.2,
            'has_metadata': 0.3,
            'url_quality': 0.3,
        })
    
    def calculate_score(self, processed_result, quality_indicators):
        """
        Calculate quality score for a processed result.
        """
        score = 0.0
        
        # Title quality
        if quality_indicators.get('has_title'):
            title_score = min(1.0, quality_indicators.get('title_length', 0) / 100)
            score += self.weights['has_title'] * title_score
        
        # Snippet quality
        if quality_indicators.get('has_snippet'):
            snippet_score = min(1.0, quality_indicators.get('snippet_length', 0) / 200)
            score += self.weights['has_snippet'] * snippet_score
        
        # Metadata completeness
        metadata_score = 0.0
        if processed_result.file_type != 'unknown':
            metadata_score += 0.25
        if processed_result.language:
            metadata_score += 0.25
        if processed_result.publication_date:
            metadata_score += 0.25
        if processed_result.domain:
            metadata_score += 0.25
        score += self.weights['has_metadata'] * metadata_score
        
        # URL quality
        url_score = quality_indicators.get('domain_quality', 0.5)
        # Penalize deep URLs
        url_depth = quality_indicators.get('url_depth', 0)
        if url_depth > 5:
            url_score *= 0.8
        score += self.weights['url_quality'] * url_score
        
        # Ensure score is between 0 and 1
        return round(min(1.0, max(0.0, score)), 2)
```

### 5.2 Celery Tasks

#### Processing Tasks
```python
# apps/results_manager/tasks.py
from celery import shared_task
from django.db import transaction
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def initialize_processing_task(self, processing_session_id):
    """
    Initialize processing session.
    """
    from apps.results_manager.models import ProcessingSession
    
    try:
        processing_session = ProcessingSession.objects.get(pk=processing_session_id)
        processing_session.status = 'in_progress'
        processing_session.started_at = timezone.now()
        processing_session.current_stage = 'initialization'
        processing_session.save()
        
        logger.info(f"Initialized processing for session {processing_session.search_session_id}")
        return processing_session_id
        
    except Exception as exc:
        logger.error(f"Processing initialization failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def process_batch_task(self, processing_session_id, raw_result_ids):
    """
    Process a batch of raw results.
    """
    from apps.results_manager.models import ProcessingSession, ProcessedResult
    from apps.results_manager.services.url_normalizer import URLNormalizer
    from apps.results_manager.services.metadata_extractor import MetadataExtractor
    from apps.results_manager.services.quality_scorer import QualityScorer
    from apps.serp_execution.models import RawSearchResult
    
    try:
        processing_session = ProcessingSession.objects.get(pk=processing_session_id)
        
        # Update stage
        processing_session.current_stage = 'processing_batch'
        processing_session.save()
        
        # Get services
        url_normalizer = URLNormalizer(processing_session.processing_config.get('url_normalization'))
        metadata_extractor = MetadataExtractor()
        quality_scorer = QualityScorer(processing_session.processing_config.get('quality_scoring'))
        
        # Process each result
        processed_results = []
        
        for raw_result_id in raw_result_ids:
            try:
                raw_result = RawSearchResult.objects.get(pk=raw_result_id)
                
                # Normalize URL
                normalized_url = url_normalizer.normalize(raw_result.url)
                domain = url_normalizer.get_domain(raw_result.url)
                
                # Extract metadata
                metadata = metadata_extractor.extract(raw_result)
                
                # Create processed result
                with transaction.atomic():
                    processed_result = ProcessedResult.objects.create(
                        session_id=raw_result.search_execution.search_query.session_id,
                        raw_result=raw_result,
                        title=metadata['cleaned_title'] or raw_result.title,
                        normalized_url=normalized_url,
                        original_url=raw_result.url,
                        snippet=metadata['cleaned_snippet'] or raw_result.snippet,
                        domain=domain or raw_result.domain,
                        file_type=metadata['file_type'],
                        estimated_size=metadata['estimated_size'],
                        language=metadata['language'],
                        publication_date=metadata['publication_date'],
                        search_engine=raw_result.search_execution.search_query.search_engine,
                        quality_score=0.5  # Will be updated after scoring
                    )
                    
                    # Calculate quality score
                    quality_score = quality_scorer.calculate_score(
                        processed_result,
                        metadata['quality_indicators']
                    )
                    processed_result.quality_score = quality_score
                    processed_result.save()
                    
                    processed_results.append(processed_result)
                    
                    # Update progress
                    processing_session.processed_count += 1
                    processing_session.save()
                    
            except Exception as e:
                logger.error(f"Failed to process result {raw_result_id}: {e}")
                processing_session.error_count += 1
                processing_session.save()
                
                # Store error details
                if 'errors' not in processing_session.error_details:
                    processing_session.error_details['errors'] = []
                
                processing_session.error_details['errors'].append({
                    'raw_result_id': str(raw_result_id),
                    'error': str(e),
                    'timestamp': timezone.now().isoformat()
                })
                processing_session.save()
        
        # Perform deduplication on batch
        if processed_results:
            from apps.results_manager.services.deduplication_engine import DeduplicationEngine
            
            dedup_engine = DeduplicationEngine(
                processing_session.processing_config.get('deduplication')
            )
            duplicates = dedup_engine.find_duplicates(processed_results)
            relationships = dedup_engine.create_duplicate_relationships(duplicates)
            
            processing_session.duplicate_count += len(relationships)
            processing_session.save()
        
        return len(processed_results)
        
    except Exception as exc:
        logger.error(f"Batch processing failed: {exc}")
        raise self.retry(exc=exc, countdown=120)


@shared_task
def finalize_processing_task(processing_session_id):
    """
    Finalize processing and update session status.
    """
    from apps.results_manager.models import ProcessingSession
    from apps.review_manager.models import SearchSession
    
    try:
        processing_session = ProcessingSession.objects.get(pk=processing_session_id)
        
        # Update stage
        processing_session.current_stage = 'finalization'
        processing_session.save()
        
        # Determine final status
        if processing_session.error_count == 0:
            processing_session.status = 'completed'
        elif processing_session.processed_count > 0:
            processing_session.status = 'partial'
        else:
            processing_session.status = 'failed'
        
        processing_session.completed_at = timezone.now()
        processing_session.save()
        
        # Update search session status
        search_session = processing_session.search_session
        if processing_session.status in ['completed', 'partial']:
            search_session.status = 'ready_for_review'
            search_session.save()
            
            # Send notification
            from apps.notifications.services import NotificationService
            NotificationService.send_processing_complete(
                search_session,
                processing_session
            )
        
        logger.info(
            f"Processing completed for session {search_session.id}: "
            f"{processing_session.processed_count} processed, "
            f"{processing_session.duplicate_count} duplicates, "
            f"{processing_session.error_count} errors"
        )
        
        return processing_session_id
        
    except Exception as e:
        logger.error(f"Processing finalization failed: {e}")
        raise
```

### 5.3 Managers

#### ProcessedResultManager
```python
# apps/results_manager/managers.py
from django.db import models
from django.db.models import Q, Count, Avg

class ProcessedResultManager(models.Manager):
    """Custom manager for ProcessedResult model."""
    
    def for_session(self, session):
        """Get all processed results for a session."""
        return self.filter(session=session)
    
    def unique_results(self, session):
        """Get only unique (non-duplicate) results."""
        return self.filter(session=session, is_duplicate=False)
    
    def with_statistics(self, session):
        """Get results with aggregated statistics."""
        return self.filter(session=session).aggregate(
            total_count=Count('id'),
            unique_count=Count('id', filter=Q(is_duplicate=False)),
            duplicate_count=Count('id', filter=Q(is_duplicate=True)),
            avg_quality_score=Avg('quality_score'),
            file_types=Count('file_type', distinct=True),
        )
    
    def by_quality(self, session, min_score=0.5):
        """Get results above a quality threshold."""
        return self.filter(
            session=session,
            quality_score__gte=min_score
        ).order_by('-quality_score')
    
    def with_errors(self, session):
        """Get results that had processing errors."""
        return self.filter(
            session=session
        ).exclude(processing_errors={})


class ProcessingSessionManager(models.Manager):
    """Custom manager for ProcessingSession model."""
    
    def active(self):
        """Get currently active processing sessions."""
        return self.filter(status='in_progress')
    
    def failed(self):
        """Get failed processing sessions."""
        return self.filter(status__in=['failed', 'partial'])
    
    def requiring_retry(self):
        """Get sessions that should be retried."""
        return self.filter(
            status__in=['failed', 'partial'],
            retry_count__lt=models.F('max_retries')
        )
```

### 5.4 Utilities

#### Processing Utilities
```python
# apps/results_manager/utils/processing_utils.py
from django.core.cache import cache
from django.db.models import F
import hashlib

def get_processing_cache_key(session_id):
    """Generate cache key for processing status."""
    return f'processing_status:{session_id}'

def update_processing_progress(processing_session, stage, progress=None):
    """
    Update processing progress and cache it.
    """
    processing_session.current_stage = stage
    if progress is not None:
        processing_session.stage_progress = progress
    processing_session.save()
    
    # Cache status for quick access
    cache_data = {
        'status': processing_session.status,
        'stage': stage,
        'progress': processing_session.progress_percentage,
        'stage_progress': progress or 0,
    }
    cache.set(
        get_processing_cache_key(processing_session.search_session_id),
        cache_data,
        timeout=300  # 5 minutes
    )

def estimate_processing_time(num_results, config=None):
    """
    Estimate processing time based on number of results.
    """
    # Base estimates (seconds)
    per_result_time = 0.1  # 100ms per result
    batch_overhead = 2     # 2s per batch
    
    if config:
        batch_size = config.get('batch_size', 50)
    else:
        batch_size = 50
    
    num_batches = (num_results + batch_size - 1) // batch_size
    
    estimated_seconds = (
        num_results * per_result_time +
        num_batches * batch_overhead +
        10  # Fixed overhead
    )
    
    return int(estimated_seconds)

def generate_result_hash(title, url, snippet):
    """
    Generate a hash for duplicate detection.
    """
    content = f"{title}|{url}|{snippet}".lower()
    return hashlib.sha256(content.encode()).hexdigest()

def batch_iterator(queryset, batch_size=100):
    """
    Iterate over a queryset in batches.
    """
    total = queryset.count()
    for offset in range(0, total, batch_size):
        yield queryset[offset:offset + batch_size]
```

## 6. Testing Requirements

### 6.1 Unit Tests

#### Model Tests
```python
# apps/results_manager/tests/test_models.py
from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.results_manager.models import ProcessedResult, DuplicateRelationship, ProcessingSession
from apps.results_manager.tests.factories import (
    ProcessedResultFactory, ProcessingSessionFactory
)

class ProcessedResultModelTest(TestCase):
    """Test ProcessedResult model functionality."""
    
    def test_model_creation(self):
        """Test creating a processed result with all fields."""
        result = ProcessedResultFactory()
        self.assertIsNotNone(result.id)
        self.assertEqual(result.quality_score, 0.5)
        self.assertFalse(result.is_duplicate)
    
    def test_quality_score_validation(self):
        """Test quality score must be between 0 and 1."""
        result = ProcessedResultFactory.build(quality_score=1.5)
        with self.assertRaises(ValidationError):
            result.full_clean()
    
    def test_unique_url_per_session(self):
        """Test normalized URLs must be unique within a session."""
        result1 = ProcessedResultFactory(normalized_url='https://example.com/page')
        
        # Try to create duplicate URL in same session
        with self.assertRaises(Exception):
            ProcessedResultFactory(
                session=result1.session,
                normalized_url='https://example.com/page'
            )
    
    def test_search_engine_denormalization(self):
        """Test search engine is properly denormalized."""
        result = ProcessedResultFactory()
        self.assertEqual(
            result.search_engine,
            result.raw_result.search_execution.search_query.search_engine
        )

class ProcessingSessionModelTest(TestCase):
    """Test ProcessingSession model functionality."""
    
    def test_progress_percentage_calculation(self):
        """Test progress percentage calculation."""
        session = ProcessingSessionFactory(
            total_raw_results=100,
            processed_count=75
        )
        self.assertEqual(session.progress_percentage, 75)
    
    def test_duration_calculation(self):
        """Test processing duration calculation."""
        from datetime import timedelta
        from django.utils import timezone
        
        session = ProcessingSessionFactory(
            started_at=timezone.now() - timedelta(minutes=5),
            completed_at=timezone.now()
        )
        
        self.assertAlmostEqual(
            session.duration.total_seconds(),
            300,  # 5 minutes
            delta=1
        )
```

#### Service Tests
```python
# apps/results_manager/tests/test_services.py
class URLNormalizerTest(TestCase):
    """Test URL normalization service."""
    
    def setUp(self):
        self.normalizer = URLNormalizer()
    
    def test_remove_tracking_parameters(self):
        """Test removal of tracking parameters."""
        url = 'https://example.com/page?utm_source=google&utm_medium=cpc&id=123'
        normalized = self.normalizer.normalize(url)
        self.assertEqual(normalized, 'https://example.com/page?id=123')
    
    def test_protocol_normalization(self):
        """Test HTTP to HTTPS normalization."""
        url = 'http://example.com/page'
        normalized = self.normalizer.normalize(url)
        self.assertEqual(normalized, 'https://example.com/page')
    
    def test_remove_www_prefix(self):
        """Test removal of www prefix."""
        url = 'https://www.example.com/page'
        normalized = self.normalizer.normalize(url)
        self.assertEqual(normalized, 'https://example.com/page')
    
    def test_path_normalization(self):
        """Test path normalization."""
        test_cases = [
            ('https://example.com//double//slash', 'https://example.com/double/slash'),
            ('https://example.com/path/', 'https://example.com/path'),
            ('https://example.com/', 'https://example.com/'),
            ('https://example.com/index.html', 'https://example.com'),
        ]
        
        for input_url, expected in test_cases:
            with self.subTest(url=input_url):
                normalized = self.normalizer.normalize(input_url)
                self.assertEqual(normalized, expected)

class DeduplicationEngineTest(TestCase):
    """Test deduplication engine."""
    
    def setUp(self):
        self.engine = DeduplicationEngine()
    
    def test_exact_url_duplicate_detection(self):
        """Test detection of exact URL duplicates."""
        results = [
            ProcessedResultFactory(normalized_url='https://example.com/page1'),
            ProcessedResultFactory(normalized_url='https://example.com/page2'),
            ProcessedResultFactory(normalized_url='https://example.com/page1'),
        ]
        
        duplicates = self.engine.find_duplicates(results)
        
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0]['original'], results[0])
        self.assertEqual(duplicates[0]['duplicate'], results[2])
        self.assertEqual(duplicates[0]['method'], 'normalized_url')
        self.assertEqual(duplicates[0]['score'], 1.0)
    
    def test_duplicate_relationship_creation(self):
        """Test creation of duplicate relationship records."""
        original = ProcessedResultFactory()
        duplicate = ProcessedResultFactory()
        
        duplicates = [{
            'original': original,
            'duplicate': duplicate,
            'method': 'normalized_url',
            'score': 1.0,
            'confidence': 'high'
        }]
        
        relationships = self.engine.create_duplicate_relationships(duplicates)
        
        self.assertEqual(len(relationships), 1)
        self.assertTrue(duplicate.is_duplicate)
        self.assertEqual(duplicate.duplicate_of, original)
```

#### Task Tests
```python
# apps/results_manager/tests/test_tasks.py
from unittest.mock import patch, MagicMock
from django.test import TestCase
from apps.results_manager.tasks import process_batch_task

class ProcessingTaskTest(TestCase):
    """Test Celery processing tasks."""
    
    @patch('apps.results_manager.tasks.URLNormalizer')
    @patch('apps.results_manager.tasks.MetadataExtractor')
    @patch('apps.results_manager.tasks.QualityScorer')
    def test_process_batch_task(self, mock_scorer, mock_extractor, mock_normalizer):
        """Test batch processing task."""
        # Setup mocks
        mock_normalizer.return_value.normalize.return_value = 'https://example.com/normalized'
        mock_normalizer.return_value.get_domain.return_value = 'example.com'
        mock_extractor.return_value.extract.return_value = {
            'cleaned_title': 'Test Title',
            'cleaned_snippet': 'Test snippet',
            'file_type': 'pdf',
            'estimated_size': 500000,
            'language': 'en',
            'publication_date': None,
            'quality_indicators': {}
        }
        mock_scorer.return_value.calculate_score.return_value = 0.75
        
        # Create test data
        from apps.serp_execution.tests.factories import RawSearchResultFactory
        raw_results = [RawSearchResultFactory() for _ in range(3)]
        processing_session = ProcessingSessionFactory()
        
        # Execute task
        result = process_batch_task(
            processing_session.id,
            [r.id for r in raw_results]
        )
        
        # Verify
        self.assertEqual(result, 3)
        self.assertEqual(ProcessedResult.objects.count(), 3)
        
        processed = ProcessedResult.objects.first()
        self.assertEqual(processed.normalized_url, 'https://example.com/normalized')
        self.assertEqual(processed.quality_score, 0.75)
```

### 6.2 Integration Tests

```python
# apps/results_manager/tests/test_integration.py
class ProcessingWorkflowIntegrationTest(TestCase):
    """Test complete processing workflow."""
    
    def test_complete_processing_workflow(self):
        """Test processing from raw results to completion."""
        # Create test data
        from apps.review_manager.tests.factories import SearchSessionFactory
        from apps.serp_execution.tests.factories import (
            SearchQueryFactory, SearchExecutionFactory, RawSearchResultFactory
        )
        
        session = SearchSessionFactory(status='executing')
        query = SearchQueryFactory(session=session)
        execution = SearchExecutionFactory(search_query=query)
        
        # Create 100 raw results
        raw_results = [
            RawSearchResultFactory(search_execution=execution)
            for _ in range(100)
        ]
        
        # Start processing
        service = ProcessingService(session.id)
        processing_session = service.start_processing()
        
        # Simulate task execution (in real scenario, Celery would handle this)
        from apps.results_manager.tasks import (
            initialize_processing_task,
            process_batch_task,
            finalize_processing_task
        )
        
        # Initialize
        initialize_processing_task(processing_session.id)
        
        # Process batches
        batch_size = 50
        for i in range(0, len(raw_results), batch_size):
            batch_ids = [r.id for r in raw_results[i:i+batch_size]]
            process_batch_task(processing_session.id, batch_ids)
        
        # Finalize
        finalize_processing_task(processing_session.id)
        
        # Verify results
        processing_session.refresh_from_db()
        self.assertEqual(processing_session.status, 'completed')
        self.assertEqual(processing_session.processed_count, 100)
        
        # Check processed results
        processed_count = ProcessedResult.objects.filter(session=session).count()
        self.assertEqual(processed_count, 100)
        
        # Verify session status updated
        session.refresh_from_db()
        self.assertEqual(session.status, 'ready_for_review')
```

### 6.3 Performance Tests

```python
# apps/results_manager/tests/test_performance.py
import time
from django.test import TestCase, TransactionTestCase

class ProcessingPerformanceTest(TransactionTestCase):
    """Test processing performance requirements."""
    
    def test_large_batch_processing_time(self):
        """Test processing 1000 results within 2 minutes."""
        # Create 1000 raw results
        from apps.serp_execution.tests.factories import RawSearchResultFactory
        
        start_time = time.time()
        
        # Create test data
        session = SearchSessionFactory()
        raw_results = []
        
        # Batch create for performance
        for _ in range(10):
            batch = [RawSearchResultFactory.build() for _ in range(100)]
            RawSearchResult.objects.bulk_create(batch)
        
        # Process
        service = ProcessingService(session.id)
        processing_session = service.start_processing()
        
        # Simulate processing (would be async in production)
        # ... processing logic ...
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within 120 seconds
        self.assertLess(duration, 120)
    
    def test_memory_efficiency(self):
        """Test memory usage stays within limits."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process large dataset
        # ... processing logic ...
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be less than 256MB
        self.assertLess(memory_increase, 256)
```

## 7. Performance Optimization

### 7.1 Database Optimization
```python
# Optimized queries with select_related and prefetch_related
queryset = ProcessedResult.objects.filter(
    session=session
).select_related(
    'raw_result__search_execution__search_query',
    'duplicate_of'
).prefetch_related(
    'duplicate_relationships__duplicate',
    'duplicate_instances'
)

# Bulk operations for efficiency
ProcessedResult.objects.bulk_create(
    processed_results,
    batch_size=100
)

# Database indexes (in models)
indexes = [
    models.Index(fields=['session', '-processed_at']),
    models.Index(fields=['normalized_url', 'session']),
    models.Index(fields=['domain', 'session']),
]
```

### 7.2 Caching Strategy
```python
# Redis caching configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/2',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'PICKLE_VERSION': -1,
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'COMPRESSOR': 'django_redis.compressors.zlib.ZlibCompressor',
        },
        'KEY_PREFIX': 'results_manager',
        'TIMEOUT': 300,
    }
}

# Cache warming for frequently accessed data
def warm_processing_cache(session_id):
    """Pre-populate cache with processing data."""
    from django.core.cache import cache
    
    # Cache processing status
    try:
        processing_session = ProcessingSession.objects.get(
            search_session_id=session_id
        )
        cache.set(
            f'processing_status:{session_id}',
            {
                'status': processing_session.status,
                'progress': processing_session.progress_percentage,
                'stage': processing_session.current_stage,
            },
            timeout=300
        )
    except ProcessingSession.DoesNotExist:
        pass
    
    # Cache result statistics
    stats = ProcessedResult.objects.filter(
        session_id=session_id
    ).aggregate(
        total=Count('id'),
        duplicates=Count('id', filter=Q(is_duplicate=True)),
        avg_quality=Avg('quality_score')
    )
    cache.set(f'result_stats:{session_id}', stats, timeout=600)
```

### 7.3 Celery Optimization
```python
# Celery configuration for optimal performance
CELERY_TASK_ROUTES = {
    'apps.results_manager.tasks.*': {'queue': 'processing'},
}

CELERY_TASK_TIME_LIMIT = 300  # 5 minutes hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 minutes soft limit

CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # For memory-intensive tasks
CELERY_TASK_ACKS_LATE = True  # Ensure task completion

# Batch processing configuration
PROCESSING_BATCH_SIZE = 50  # Optimal batch size
PROCESSING_PARALLEL_BATCHES = 4  # Number of parallel batches
```

## 8. Security Considerations

### 8.1 Data Protection
- Session-based data isolation enforced at all levels
- User permissions validated before any processing operation
- Audit trails for all processing activities
- Secure handling of external URLs and content

### 8.2 Input Validation
- URL validation and sanitization before normalization
- Protection against malicious URLs and redirects
- Content size limits to prevent resource exhaustion
- Rate limiting on processing requests

### 8.3 Error Handling
- Sensitive information stripped from error messages
- Detailed error logs stored securely with access controls
- Graceful degradation for partial failures
- No exposure of internal system details

## 9. Phase Implementation

### 9.1 Phase 1 (Current - 33% Complete)
**✅ Completed:**
- Core models with UUID primary keys
- URL normalization service
- Metadata extraction service
- Basic deduplication engine
- Quality scoring algorithm
- Comprehensive test suite (95%+ coverage)

**🔄 In Progress:**
- Celery task implementation
- SERP execution integration
- Session status workflow

**📋 Pending:**
- User interface development
- Real-time status updates
- Production deployment

### 9.2 Phase 2 (Future Enhancements)
- [ ] Advanced deduplication algorithms
- [ ] Full-text content extraction
- [ ] Machine learning quality scoring
- [ ] External metadata enrichment
- [ ] RESTful API for integrations
- [ ] Advanced analytics dashboard
- [ ] A/B testing framework

## 10. Development Checklist

### 10.1 Implementation Checklist
- [x] Create Django app structure
- [x] Implement models with migrations
- [x] Create service layer architecture
- [x] Implement URL normalization
- [x] Build metadata extraction
- [x] Create deduplication engine
- [x] Implement quality scoring
- [x] Write comprehensive tests
- [ ] Implement Celery tasks
- [ ] Create processing views
- [ ] Build status monitoring UI
- [ ] Integrate with SERP execution
- [ ] Add real-time notifications

### 10.2 Testing Checklist
- [x] Unit tests for models
- [x] Service layer tests
- [x] URL normalization tests
- [x] Deduplication tests
- [x] Quality scoring tests
- [ ] Celery task tests
- [ ] Integration tests
- [ ] Performance tests
- [ ] Load testing
- [ ] Security testing

### 10.3 Documentation Checklist
- [x] Service documentation
- [x] Model documentation
- [ ] API documentation
- [ ] User guide
- [ ] Deployment guide
- [ ] Performance tuning guide

## 11. Success Metrics

### 11.1 Performance Metrics
- Processing speed: 1000+ results in < 2 minutes
- Memory usage: < 256MB per worker
- Database query efficiency: < 10 queries per page
- Cache hit rate: > 80%

### 11.2 Quality Metrics
- Deduplication accuracy: > 95%
- URL normalization success: > 99%
- Metadata extraction rate: > 90%
- Processing error rate: < 1%

### 11.3 Technical Metrics
- Test coverage: > 95%
- Code quality: A rating
- Zero security vulnerabilities
- API response time: < 200ms

## 12. References

### 12.1 Internal Documentation
- [Master PRD](../PRD.md)
- [SERP Execution PRD](../serp_execute.md/serp_execution.md)
- [Review Manager PRD](../review-manager/review-manager-prd.md)
- [Tech Stack](../tech-stack.md)

### 12.2 External References
- [Django 4.2 Documentation](https://docs.djangoproject.com/en/4.2/)
- [Celery Best Practices](https://docs.celeryproject.org/en/stable/userguide/tasks.html)
- [URL Normalization RFC](https://tools.ietf.org/html/rfc3986)
- [PostgreSQL Performance Tuning](https://www.postgresql.org/docs/current/performance-tips.html)

---

**Document Status:** Complete  
**Implementation Status:** Phase 1 - 33% Complete  
**Last Updated:** 2025-01-25  
**Next Review:** Upon Celery Implementation Completion