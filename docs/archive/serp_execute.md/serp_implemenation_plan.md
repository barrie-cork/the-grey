# SERP Execution Task 1.0 Implementation Plan

## Task 1.0: Foundation Setup and Models

This plan details the implementation of the foundation for the SERP Execution app, focusing on creating the core models with proper relationships to existing apps.

### Overview

The SERP Execution app is responsible for:
- Executing search queries against Google Search via the Serper API
- Tracking execution progress and status
- Storing raw search results
- Managing error recovery and retry logic

### Dependencies

- **Review Manager App**: `SearchSession` model (already exists)
- **Accounts App**: Custom `User` model with UUID primary key (already exists)
- **Search Strategy App**: Provides PIC framework terms for query generation

### Implementation Steps

## 1.1 Create App Directory Structure

The basic app structure already exists. We need to create additional directories:

```
apps/serp_execution/
├── migrations/          # Already exists
├── services/           # Create this
│   ├── __init__.py
│   ├── serper_client.py
│   ├── query_builder.py
│   └── result_processor.py
├── management/         # Create this
│   ├── __init__.py
│   └── commands/
│       ├── __init__.py
│       └── test_serper_connection.py
├── templates/          # Create this
│   └── serp_execution/
│       ├── execute_confirm.html
│       └── execution_status.html
├── static/             # Create this
│   └── serp_execution/
│       ├── css/
│       │   └── execution.css
│       └── js/
│           └── execution_monitor.js
└── tests/              # Create this
    ├── __init__.py
    ├── test_models.py
    ├── test_views.py
    ├── test_tasks.py
    ├── test_api_client.py
    └── test_integration.py
```

## 1.2 Implement SearchQuery Model

```python
# apps/serp_execution/models.py

import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class SearchQuery(models.Model):
    """
    Represents a single search query to be executed against a search engine.
    Links to a SearchSession and tracks query construction parameters.
    """
    
    SEARCH_ENGINE_CHOICES = [
        ('google_serper', 'Google (via Serper.dev)'),
    ]
    
    # UUID primary key for consistency with project standards
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_('Unique identifier for this search query')
    )
    
    # Relationship to SearchSession
    session = models.ForeignKey(
        'review_manager.SearchSession',
        on_delete=models.CASCADE,
        related_name='search_queries',
        help_text=_('The search session this query belongs to')
    )
    
    # Query details
    query_string = models.TextField(
        help_text=_('The complete search query string to execute')
    )
    
    search_engine = models.CharField(
        max_length=50,
        choices=SEARCH_ENGINE_CHOICES,
        default='google_serper',
        help_text=_('Search engine/API to use for this query')
    )
    
    # Query parameters stored as JSON
    parameters = models.JSONField(
        default=dict,
        help_text=_('Search parameters (region, language, filters, etc.)')
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('When this query was created')
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_queries',
        help_text=_('User who created this query')
    )
    
    class Meta:
        ordering = ['session', 'created_at']
        verbose_name = _('Search Query')
        verbose_name_plural = _('Search Queries')
        indexes = [
            models.Index(fields=['session']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.query_string[:50]}... ({self.session.title})"
    
    def get_execution_status(self):
        """Get the current execution status for this query"""
        latest_execution = self.executions.order_by('-created_at').first()
        return latest_execution.status if latest_execution else 'pending'
    
    def has_successful_execution(self):
        """Check if this query has been successfully executed"""
        return self.executions.filter(status='completed').exists()
```

## 1.3 Implement SearchExecution Model

```python
class SearchExecution(models.Model):
    """
    Tracks individual execution attempts of a search query.
    Supports retry logic and detailed progress tracking.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    ]
    
    # UUID primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_('Unique identifier for this execution')
    )
    
    # Relationship to SearchQuery
    query = models.ForeignKey(
        'SearchQuery',
        on_delete=models.CASCADE,
        related_name='executions',
        help_text=_('The search query being executed')
    )
    
    # Execution status and progress
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text=_('Current status of this execution')
    )
    
    progress_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_('Execution progress percentage (0-100)')
    )
    
    # Timing information
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When execution started')
    )
    
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When execution completed (success or failure)')
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('When this execution was created')
    )
    
    # Results summary
    results_found = models.IntegerField(
        default=0,
        help_text=_('Number of results found in this execution')
    )
    
    # Error handling
    error_message = models.TextField(
        blank=True,
        help_text=_('Error message if execution failed')
    )
    
    retry_count = models.IntegerField(
        default=0,
        help_text=_('Number of times this query has been retried')
    )
    
    # API usage tracking
    api_calls_made = models.IntegerField(
        default=0,
        help_text=_('Number of API calls made during this execution')
    )
    
    api_credits_used = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=0,
        help_text=_('API credits/cost for this execution')
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Search Execution')
        verbose_name_plural = _('Search Executions')
        indexes = [
            models.Index(fields=['query', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.query.query_string[:30]}... - {self.get_status_display()}"
    
    @property
    def duration(self):
        """Calculate execution duration"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        elif self.started_at:
            return timezone.now() - self.started_at
        return None
    
    def can_transition_to(self, new_status):
        """Validate status transitions"""
        allowed_transitions = {
            'pending': ['running'],
            'running': ['completed', 'failed'],
            'completed': [],  # Terminal state
            'failed': ['retrying'],
            'retrying': ['running'],
        }
        return new_status in allowed_transitions.get(self.status, [])
```

## 1.4 Implement RawSearchResult Model

```python
class RawSearchResult(models.Model):
    """
    Stores individual search results from SERP API.
    Captures all data from search API for later processing.
    """
    
    # UUID primary key
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_('Unique identifier for this result')
    )
    
    # Relationship to SearchExecution
    execution = models.ForeignKey(
        'SearchExecution',
        on_delete=models.CASCADE,
        related_name='raw_results',
        help_text=_('The execution that found this result')
    )
    
    # Result position and basic data
    position = models.IntegerField(
        help_text=_('Position in search results (1-based)')
    )
    
    url = models.URLField(
        max_length=2048,
        help_text=_('URL of the result')
    )
    
    title = models.TextField(
        help_text=_('Title of the search result')
    )
    
    snippet = models.TextField(
        blank=True,
        help_text=_('Search result snippet/description')
    )
    
    domain = models.CharField(
        max_length=255,
        help_text=_('Domain of the result URL')
    )
    
    # Raw API data
    raw_data = models.JSONField(
        default=dict,
        help_text=_('Complete raw data from search API')
    )
    
    # Timestamps
    retrieved_at = models.DateTimeField(
        default=timezone.now,
        help_text=_('When this result was retrieved')
    )
    
    class Meta:
        ordering = ['execution', 'position']
        verbose_name = _('Raw Search Result')
        verbose_name_plural = _('Raw Search Results')
        indexes = [
            models.Index(fields=['execution', 'position']),
            models.Index(fields=['url']),
            models.Index(fields=['domain']),
            models.Index(fields=['retrieved_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['execution', 'position'],
                name='unique_result_position_per_execution'
            )
        ]
    
    def __str__(self):
        return f"{self.title[:50]}... (Position {self.position})"
```

## 1.5 Create Initial Migrations

After implementing the models, create and run migrations:

```bash
python manage.py makemigrations serp_execution
python manage.py migrate serp_execution
```

## 1.6 Register Models in Admin Interface

```python
# apps/serp_execution/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import SearchQuery, SearchExecution, RawSearchResult


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ['query_string_truncated', 'session_link', 'search_engine', 
                    'execution_status', 'created_at']
    list_filter = ['search_engine', 'created_at']
    search_fields = ['query_string', 'session__title']
    readonly_fields = ['id', 'created_at', 'created_by']
    
    fieldsets = (
        ('Query Information', {
            'fields': ('id', 'session', 'query_string', 'search_engine')
        }),
        ('Parameters', {
            'fields': ('parameters',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'created_by')
        })
    )
    
    def query_string_truncated(self, obj):
        return obj.query_string[:75] + '...' if len(obj.query_string) > 75 else obj.query_string
    query_string_truncated.short_description = 'Query'
    
    def session_link(self, obj):
        url = reverse('admin:review_manager_searchsession_change', args=[obj.session.id])
        return format_html('<a href="{}">{}</a>', url, obj.session.title[:30])
    session_link.short_description = 'Session'
    
    def execution_status(self, obj):
        status = obj.get_execution_status()
        colors = {
            'pending': '#FFA500',
            'running': '#007BFF',
            'completed': '#28A745',
            'failed': '#DC3545',
            'retrying': '#FFC107'
        }
        color = colors.get(status, '#6C757D')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, status.upper()
        )
    execution_status.short_description = 'Status'


@admin.register(SearchExecution)
class SearchExecutionAdmin(admin.ModelAdmin):
    list_display = ['id', 'query_truncated', 'status_colored', 'progress_bar', 
                    'results_found', 'duration_display', 'retry_count', 'created_at']
    list_filter = ['status', 'created_at', 'retry_count']
    search_fields = ['query__query_string', 'error_message']
    readonly_fields = ['id', 'created_at', 'duration']
    
    fieldsets = (
        ('Execution Information', {
            'fields': ('id', 'query', 'status', 'progress_percentage')
        }),
        ('Timing', {
            'fields': ('created_at', 'started_at', 'completed_at', 'duration')
        }),
        ('Results', {
            'fields': ('results_found',)
        }),
        ('Error Information', {
            'fields': ('error_message', 'retry_count'),
            'classes': ('collapse',)
        }),
        ('API Usage', {
            'fields': ('api_calls_made', 'api_credits_used'),
            'classes': ('collapse',)
        })
    )
    
    def query_truncated(self, obj):
        return obj.query.query_string[:50] + '...'
    query_truncated.short_description = 'Query'
    
    def status_colored(self, obj):
        colors = {
            'pending': '#FFA500',
            'running': '#007BFF',
            'completed': '#28A745',
            'failed': '#DC3545',
            'retrying': '#FFC107'
        }
        color = colors.get(obj.status, '#6C757D')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, obj.get_status_display()
        )
    status_colored.short_description = 'Status'
    
    def progress_bar(self, obj):
        color = '#28A745' if obj.status == 'completed' else '#007BFF'
        return format_html(
            '<div style="width: 100px; height: 20px; background-color: #f0f0f0; '
            'border: 1px solid #ccc; position: relative;">'
            '<div style="width: {}%; height: 100%; background-color: {}; '
            'position: absolute; top: 0; left: 0;"></div>'
            '<span style="position: relative; z-index: 1; display: block; '
            'text-align: center; line-height: 20px;">{}%</span></div>',
            obj.progress_percentage, color, obj.progress_percentage
        )
    progress_bar.short_description = 'Progress'
    
    def duration_display(self, obj):
        if obj.duration:
            total_seconds = int(obj.duration.total_seconds())
            return f"{total_seconds}s"
        return "-"
    duration_display.short_description = 'Duration'


@admin.register(RawSearchResult)
class RawSearchResultAdmin(admin.ModelAdmin):
    list_display = ['title_truncated', 'position', 'domain', 'retrieved_at']
    list_filter = ['domain', 'retrieved_at']
    search_fields = ['title', 'url', 'snippet']
    readonly_fields = ['id', 'retrieved_at', 'raw_data_formatted']
    
    fieldsets = (
        ('Result Information', {
            'fields': ('id', 'execution', 'position', 'url', 'title', 'snippet')
        }),
        ('Metadata', {
            'fields': ('domain', 'retrieved_at')
        }),
        ('Raw Data', {
            'fields': ('raw_data_formatted',),
            'classes': ('collapse',)
        })
    )
    
    def title_truncated(self, obj):
        return obj.title[:60] + '...' if len(obj.title) > 60 else obj.title
    title_truncated.short_description = 'Title'
    
    def raw_data_formatted(self, obj):
        import json
        formatted = json.dumps(obj.raw_data, indent=2)
        return format_html('<pre style="max-height: 400px; overflow-y: auto;">{}</pre>', formatted)
    raw_data_formatted.short_description = 'Raw API Data'
```

## 1.7 Write Comprehensive Model Tests

```python
# apps/serp_execution/tests/test_models.py

import uuid
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.review_manager.models import SearchSession
from apps.serp_execution.models import SearchQuery, SearchExecution, RawSearchResult

User = get_user_model()


class SearchQueryModelTest(TestCase):
    """Test SearchQuery model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.session = SearchSession.objects.create(
            title='Test Search Session',
            description='Test description',
            created_by=self.user
        )
    
    def test_create_search_query(self):
        """Test creating a search query"""
        query = SearchQuery.objects.create(
            session=self.session,
            query_string='diabetes management grey literature',
            search_engine='google_serper',
            parameters={'region': 'uk', 'language': 'en'},
            created_by=self.user
        )
        
        self.assertIsInstance(query.id, uuid.UUID)
        self.assertEqual(query.session, self.session)
        self.assertEqual(query.query_string, 'diabetes management grey literature')
        self.assertEqual(query.search_engine, 'google_serper')
        self.assertEqual(query.parameters['region'], 'uk')
        self.assertEqual(query.created_by, self.user)
    
    def test_query_string_representation(self):
        """Test string representation of query"""
        query = SearchQuery.objects.create(
            session=self.session,
            query_string='A very long query string that should be truncated in the string representation',
            created_by=self.user
        )
        
        str_repr = str(query)
        self.assertIn('A very long query string that should be truncated', str_repr)
        self.assertIn(self.session.title, str_repr)
        self.assertTrue(len(str_repr) < 100)
    
    def test_get_execution_status_no_executions(self):
        """Test execution status when no executions exist"""
        query = SearchQuery.objects.create(
            session=self.session,
            query_string='test query',
            created_by=self.user
        )
        
        self.assertEqual(query.get_execution_status(), 'pending')
    
    def test_get_execution_status_with_executions(self):
        """Test execution status with multiple executions"""
        query = SearchQuery.objects.create(
            session=self.session,
            query_string='test query',
            created_by=self.user
        )
        
        # Create failed execution
        SearchExecution.objects.create(
            query=query,
            status='failed'
        )
        
        # Create successful execution (more recent)
        SearchExecution.objects.create(
            query=query,
            status='completed'
        )
        
        self.assertEqual(query.get_execution_status(), 'completed')
    
    def test_has_successful_execution(self):
        """Test checking for successful execution"""
        query = SearchQuery.objects.create(
            session=self.session,
            query_string='test query',
            created_by=self.user
        )
        
        self.assertFalse(query.has_successful_execution())
        
        # Add failed execution
        SearchExecution.objects.create(
            query=query,
            status='failed'
        )
        
        self.assertFalse(query.has_successful_execution())
        
        # Add successful execution
        SearchExecution.objects.create(
            query=query,
            status='completed'
        )
        
        self.assertTrue(query.has_successful_execution())


class SearchExecutionModelTest(TestCase):
    """Test SearchExecution model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.session = SearchSession.objects.create(
            title='Test Search Session',
            created_by=self.user
        )
        self.query = SearchQuery.objects.create(
            session=self.session,
            query_string='test query',
            created_by=self.user
        )
    
    def test_create_search_execution(self):
        """Test creating a search execution"""
        execution = SearchExecution.objects.create(
            query=self.query,
            status='pending'
        )
        
        self.assertIsInstance(execution.id, uuid.UUID)
        self.assertEqual(execution.query, self.query)
        self.assertEqual(execution.status, 'pending')
        self.assertEqual(execution.progress_percentage, 0)
        self.assertEqual(execution.results_found, 0)
        self.assertEqual(execution.retry_count, 0)
    
    def test_execution_duration_calculation(self):
        """Test duration property calculation"""
        execution = SearchExecution.objects.create(
            query=self.query,
            status='running',
            started_at=timezone.now()
        )
        
        # Running execution
        duration = execution.duration
        self.assertIsNotNone(duration)
        self.assertGreater(duration.total_seconds(), 0)
        
        # Completed execution
        execution.completed_at = execution.started_at + timezone.timedelta(seconds=30)
        execution.status = 'completed'
        execution.save()
        
        duration = execution.duration
        self.assertEqual(duration.total_seconds(), 30)
    
    def test_status_transitions(self):
        """Test valid status transitions"""
        execution = SearchExecution.objects.create(
            query=self.query,
            status='pending'
        )
        
        # Valid transitions from pending
        self.assertTrue(execution.can_transition_to('running'))
        self.assertFalse(execution.can_transition_to('completed'))
        self.assertFalse(execution.can_transition_to('failed'))
        
        # Move to running
        execution.status = 'running'
        execution.save()
        
        # Valid transitions from running
        self.assertTrue(execution.can_transition_to('completed'))
        self.assertTrue(execution.can_transition_to('failed'))
        self.assertFalse(execution.can_transition_to('pending'))
        
        # Move to failed
        execution.status = 'failed'
        execution.save()
        
        # Valid transitions from failed
        self.assertTrue(execution.can_transition_to('retrying'))
        self.assertFalse(execution.can_transition_to('completed'))
    
    def test_progress_percentage_validation(self):
        """Test progress percentage constraints"""
        execution = SearchExecution.objects.create(
            query=self.query,
            progress_percentage=50
        )
        
        self.assertEqual(execution.progress_percentage, 50)
        
        # Test validation (should be enforced at form/serializer level)
        execution.progress_percentage = 150
        execution.save()  # Django doesn't enforce validators on save()
        
        # Manual validation
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            execution.full_clean()


class RawSearchResultModelTest(TestCase):
    """Test RawSearchResult model functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.session = SearchSession.objects.create(
            title='Test Search Session',
            created_by=self.user
        )
        self.query = SearchQuery.objects.create(
            session=self.session,
            query_string='test query',
            created_by=self.user
        )
        self.execution = SearchExecution.objects.create(
            query=self.query,
            status='running'
        )
    
    def test_create_raw_search_result(self):
        """Test creating a raw search result"""
        result = RawSearchResult.objects.create(
            execution=self.execution,
            position=1,
            url='https://example.com/document.pdf',
            title='Test Document Title',
            snippet='This is a test snippet...',
            domain='example.com',
            raw_data={'test': 'data'}
        )
        
        self.assertIsInstance(result.id, uuid.UUID)
        self.assertEqual(result.execution, self.execution)
        self.assertEqual(result.position, 1)
        self.assertEqual(result.url, 'https://example.com/document.pdf')
        self.assertEqual(result.title, 'Test Document Title')
        self.assertEqual(result.domain, 'example.com')
        self.assertEqual(result.raw_data['test'], 'data')
    
    def test_unique_position_constraint(self):
        """Test unique position per execution constraint"""
        # Create first result
        RawSearchResult.objects.create(
            execution=self.execution,
            position=1,
            url='https://example.com/doc1.pdf',
            title='Document 1',
            domain='example.com'
        )
        
        # Try to create another result with same position
        with self.assertRaises(Exception):  # IntegrityError
            RawSearchResult.objects.create(
                execution=self.execution,
                position=1,  # Same position
                url='https://example.com/doc2.pdf',
                title='Document 2',
                domain='example.com'
            )
    
    def test_multiple_results_different_positions(self):
        """Test creating multiple results with different positions"""
        results = []
        for i in range(1, 4):
            result = RawSearchResult.objects.create(
                execution=self.execution,
                position=i,
                url=f'https://example.com/doc{i}.pdf',
                title=f'Document {i}',
                domain='example.com'
            )
            results.append(result)
        
        self.assertEqual(RawSearchResult.objects.filter(execution=self.execution).count(), 3)
        
        # Check ordering
        ordered_results = RawSearchResult.objects.filter(execution=self.execution)
        for i, result in enumerate(ordered_results):
            self.assertEqual(result.position, i + 1)
    
    def test_string_representation(self):
        """Test string representation of result"""
        result = RawSearchResult.objects.create(
            execution=self.execution,
            position=1,
            url='https://example.com/document.pdf',
            title='A very long title that should be truncated in the string representation of the result',
            domain='example.com'
        )
        
        str_repr = str(result)
        self.assertIn('A very long title that should be truncated', str_repr)
        self.assertIn('Position 1', str_repr)
        self.assertTrue(len(str_repr) < 80)
```

## 1.8 Create Model Managers

```python
# Add to apps/serp_execution/models.py

class SearchQueryManager(models.Manager):
    """Manager for SearchQuery model with common query patterns"""
    
    def active(self):
        """Get active queries"""
        return self.filter(is_active=True)
    
    def for_session(self, session):
        """Get queries for a specific session"""
        return self.filter(session=session)
    
    def pending_execution(self):
        """Get queries that haven't been executed yet"""
        from django.db.models import Exists, OuterRef
        executed = SearchExecution.objects.filter(
            query=OuterRef('pk'),
            status='completed'
        )
        return self.filter(~Exists(executed))
    
    def with_failed_executions(self):
        """Get queries with failed executions"""
        from django.db.models import Exists, OuterRef
        failed = SearchExecution.objects.filter(
            query=OuterRef('pk'),
            status='failed'
        )
        return self.filter(Exists(failed))


class SearchExecutionManager(models.Manager):
    """Manager for SearchExecution model with common query patterns"""
    
    def pending(self):
        """Get pending executions"""
        return self.filter(status='pending')
    
    def running(self):
        """Get currently running executions"""
        return self.filter(status='running')
    
    def completed(self):
        """Get completed executions"""
        return self.filter(status='completed')
    
    def failed(self):
        """Get failed executions"""
        return self.filter(status='failed')
    
    def retriable(self):
        """Get executions that can be retried"""
        return self.filter(
            status='failed',
            retry_count__lt=3
        )
    
    def for_session(self, session):
        """Get executions for a specific session"""
        return self.filter(query__session=session)


class RawSearchResultManager(models.Manager):
    """Manager for RawSearchResult model with common query patterns"""
    
    def for_session(self, session):
        """Get results for a specific session"""
        return self.filter(execution__query__session=session)
    
    def for_execution(self, execution):
        """Get results for a specific execution"""
        return self.filter(execution=execution)
    
    def by_domain(self, domain):
        """Get results from a specific domain"""
        return self.filter(domain=domain)
```

Then update the models to use these managers:

```python
# In SearchQuery model
objects = SearchQueryManager()

# In SearchExecution model  
objects = SearchExecutionManager()

# In RawSearchResult model
objects = RawSearchResultManager()
```

## Summary

This implementation plan provides:

1. **Core Models**: Three essential models (`SearchQuery`, `SearchExecution`, `RawSearchResult`) with UUID primary keys
2. **Proper Relationships**: Foreign keys to `SearchSession` and custom `User` model
3. **Status Tracking**: Execution status with validation for transitions
4. **Progress Monitoring**: Progress percentage and timing fields
5. **Error Handling**: Error message and retry count fields
6. **API Usage Tracking**: Fields for monitoring API calls and credits
7. **Admin Interface**: Comprehensive admin configuration with custom displays
8. **Model Tests**: Complete test coverage for all model functionality
9. **Model Managers**: Common query patterns for efficient data access

