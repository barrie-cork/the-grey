 **Project:** Thesis Grey - Grey Literature Review Application  
**App:** `apps/serp_execution/`  
**Dependencies:** `review_manager` (SearchSession model), `accounts` (User model)  
**Master PRD:** `docs/PRD.md`  
**Architecture:** `docs/ARCHITECTURE.MD`

---

## 🎯 Executive Summary

The SERP Execution app is responsible for executing search queries against external search APIs (initially Google Search via Serper) and tracking their progress. This app bridges the gap between search strategy definition and results processing, handling the critical task of actually running the searches that users have configured.

This handover document provides comprehensive technical requirements and integration details for implementing the SERP Execution app within the existing Thesis Grey application architecture.

---

## 📋 Pre-Implementation Requirements

### **Critical Architecture Awareness**
- [ ] **MANDATORY**: Read `CUSTOM_USER_ALERT.md` - Project uses custom User model with UUID primary keys
- [ ] Understand the 9-state workflow from Review Manager app
- [ ] Review existing security implementation from Sprint 8
- [ ] Understand real-time infrastructure from Sprint 7
- [ ] Celery and Redis configured and working
- [ ] Serper API credentials available

### **Current Project State**
- **Review Manager App**: Fully implemented (Sprints 1-11 complete)
- **Database**: PostgreSQL with UUID primary keys throughout
- **Authentication**: Custom `accounts.User` model
- **Background Tasks**: Celery with Redis broker
- **Security**: Enterprise-grade security with comprehensive testing
- **Testing**: 95%+ coverage standard established

---

## 1. App Responsibilities & Core Functions

### **Primary Functions**
1. **Search Query Management**: Create and manage individual search queries within a session
2. **API Integration**: Execute searches against Serper API with proper error handling
3. **Progress Tracking**: Monitor and report search execution status in real-time
4. **Result Storage**: Store raw search results for processing by `results_manager` app
5. **Error Recovery**: Handle API failures gracefully with retry mechanisms

### **Key User Stories**
- As a researcher, I want to execute my defined search strategy across Google
- As a researcher, I want to see real-time progress of my search execution
- As a researcher, I want to retry failed searches without losing progress
- As a researcher, I want clear error messages if searches fail

---

## 2. Data Models

### **SearchQuery Model**
```python
class SearchQuery(models.Model):
    """Represents an individual search query within a session"""
    
    # UUID primary key (mandatory for all models)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Foreign key to SearchSession from review_manager app
    session = models.ForeignKey(
        'review_manager.SearchSession',
        on_delete=models.CASCADE,
        related_name='search_queries',
        db_comment='Foreign key to SearchSession'
    )
    
    # Query details
    query_string = models.TextField(
        db_comment='The actual search query string'
    )
    search_engine = models.CharField(
        max_length=50,
        default='google_serper',
        choices=[
            ('google_serper', 'Google (via Serper)'),
            # Future: ('bing_api', 'Bing'),
        ],
        db_comment='Search engine to use'
    )
    
    # Query parameters
    parameters = models.JSONField(
        default=dict,
        blank=True,
        db_comment='Additional search parameters (num results, region, etc.)'
    )
    
    # Metadata
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_comment='Timestamp of creation'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_queries',
        db_comment='User who created the query'
    )
    
    class Meta:
        db_table = 'serp_search_query'
        db_table_comment = 'Defines specific queries within a session'
        indexes = [
            models.Index(fields=['session', 'created_at']),
        ]
        
    def __str__(self):
        return f"{self.query_string[:50]}... ({self.session.title})"
```

### **SearchExecution Model**
```python
class SearchExecution(models.Model):
    """Tracks the execution of search queries"""
    
    # Status choices
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        RETRYING = 'retrying', 'Retrying'
    
    # UUID primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    query = models.ForeignKey(
        SearchQuery,
        on_delete=models.CASCADE,
        related_name='executions',
        db_comment='Foreign key to SearchQuery'
    )
    
    # Execution details
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_comment='Execution status'
    )
    
    # Celery task tracking
    task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_comment='Celery task ID for tracking'
    )
    
    # Progress tracking
    progress_percentage = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        db_comment='Progress percentage (0-100)'
    )
    results_found = models.IntegerField(
        default=0,
        db_comment='Number of results found so far'
    )
    
    # Timing
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        db_comment='When execution started'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        db_comment='When execution completed'
    )
    
    # Error handling
    error_message = models.TextField(
        null=True,
        blank=True,
        db_comment='Error message if execution failed'
    )
    retry_count = models.IntegerField(
        default=0,
        db_comment='Number of retry attempts'
    )
    
    # API tracking
    api_calls_made = models.IntegerField(
        default=0,
        db_comment='Number of API calls made'
    )
    api_credits_used = models.IntegerField(
        default=0,
        db_comment='API credits consumed'
    )
    
    class Meta:
        db_table = 'serp_search_execution'
        db_table_comment = 'Tracks the execution of search queries'
        indexes = [
            models.Index(fields=['query', 'status']),
            models.Index(fields=['started_at']),
            models.Index(fields=['task_id']),
        ]
```

### **RawSearchResult Model**
```python
class RawSearchResult(models.Model):
    """Stores raw results from search engines"""
    
    # UUID primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Relationships
    execution = models.ForeignKey(
        SearchExecution,
        on_delete=models.CASCADE,
        related_name='raw_results',
        db_comment='Foreign key to SearchExecution'
    )
    
    # Result data
    position = models.IntegerField(
        db_comment='Position in search results (1-based)'
    )
    url = models.URLField(
        max_length=2048,
        db_comment='URL of the search result'
    )
    title = models.TextField(
        db_comment='Title of the search result'
    )
    snippet = models.TextField(
        db_comment='Snippet or description from search result'
    )
    
    # Raw API response
    raw_data = models.JSONField(
        db_comment='Complete raw JSON data from search engine API'
    )
    
    # Metadata
    domain = models.CharField(
        max_length=255,
        db_comment='Domain extracted from URL'
    )
    retrieved_at = models.DateTimeField(
        auto_now_add=True,
        db_comment='Timestamp when result was retrieved'
    )
    
    # Additional extracted data
    published_date = models.DateField(
        null=True,
        blank=True,
        db_comment='Published date if available'
    )
    author = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_comment='Author if available'
    )
    
    class Meta:
        db_table = 'serp_raw_search_result'
        db_table_comment = 'Stores raw data from search engines'
        indexes = [
            models.Index(fields=['execution', 'position']),
            models.Index(fields=['domain']),
            models.Index(fields=['retrieved_at']),
        ]
        unique_together = [['execution', 'url']]  # Prevent duplicate URLs per execution
```

---

## 3. Integration with Review Manager

### **Status Workflow Integration**
```python
# Status transitions handled by SERP Execution app
SERP_STATUS_TRANSITIONS = {
    'strategy_ready': 'executing',     # When search execution starts
    'executing': 'processing',         # When all searches complete successfully
    'executing': 'failed',            # When search execution fails
}
```

### **Activity Logging Integration**
```python
# Log all significant events using SessionActivity
from apps.review_manager.models import SessionActivity

# Example activity logging
SessionActivity.log_activity(
    session=session,
    action='SEARCH_EXECUTION_STARTED',
    user=request.user,
    description=f'Started executing {query_count} search queries',
    details={
        'query_count': query_count,
        'search_engines': ['google_serper'],
        'ip_address': get_client_ip(request),
    }
)
```

### **Real-time Updates Integration**
- Use existing `StatusMonitor` JavaScript class from Sprint 7
- Emit notifications using `NotificationManager` for status changes
- Update progress bars in real-time during execution

---

## 4. Celery Task Architecture

### **Main Orchestration Task**
```python
# apps/serp_execution/tasks.py

@shared_task(bind=True, max_retries=3)
def initiate_search_session_execution_task(self, session_id):
    """Main task that orchestrates search execution for a session"""
    try:
        session = SearchSession.objects.get(id=session_id)
        
        # Update session status
        session.status = 'executing'
        session.save()
        
        # Log activity
        SessionActivity.log_activity(
            session=session,
            action='SEARCH_EXECUTION_STARTED',
            user=session.created_by,
            description='Search execution initiated'
        )
        
        # Create search queries from strategy
        queries = create_search_queries_from_strategy(session)
        
        # Create executions and dispatch individual tasks
        for query in queries:
            execution = SearchExecution.objects.create(
                query=query,
                status='pending'
            )
            
            # Dispatch individual query task
            task = perform_serp_query_task.delay(execution.id)
            execution.task_id = task.id
            execution.save()
        
        # Monitor completion
        monitor_session_completion_task.delay(session_id)
        
    except Exception as e:
        # Handle errors
        handle_execution_error(session_id, str(e))
        raise self.retry(exc=e, countdown=60)
```

### **Individual Query Execution Task**
```python
@shared_task(bind=True, max_retries=3)
def perform_serp_query_task(self, execution_id):
    """Execute a single search query against Serper API"""
    execution = SearchExecution.objects.get(id=execution_id)
    
    try:
        # Update status
        execution.status = 'running'
        execution.started_at = timezone.now()
        execution.save()
        
        # Make API call with rate limiting
        results = call_serper_api(
            query=execution.query.query_string,
            params=execution.query.parameters
        )
        
        # Store results
        store_raw_results(execution, results)
        
        # Update execution
        execution.status = 'completed'
        execution.completed_at = timezone.now()
        execution.results_found = len(results.get('organic', []))
        execution.save()
        
    except RateLimitException:
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** execution.retry_count)
    except Exception as e:
        execution.status = 'failed'
        execution.error_message = str(e)
        execution.save()
        raise
```

### **Serper API Integration**
```python
# apps/serp_execution/services/serper_client.py

class SerperClient:
    """Client for interacting with Serper API"""
    
    def __init__(self):
        self.api_key = settings.SERPER_API_KEY
        self.base_url = 'https://google.serper.dev/search'
        self.timeout = 30
        self.rate_limiter = RateLimiter(
            max_calls=100,
            time_window=60  # 100 calls per minute
        )
    
    def search(self, query, num=10, region='uk', **kwargs):
        """Execute a search query"""
        
        # Rate limiting
        self.rate_limiter.check()
        
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }
        
        payload = {
            'q': query,
            'num': num,
            'gl': region,
            **kwargs
        }
        
        try:
            response = requests.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            raise SerperTimeoutError("API request timed out")
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                raise RateLimitException("Rate limit exceeded")
            raise SerperAPIError(f"API error: {e}")
```

---

## 5. Views and User Interface

### **Search Execution View**
```python
# apps/serp_execution/views.py

class ExecuteSearchView(LoginRequiredMixin, SessionOwnershipMixin, View):
    """Initiates search execution for a session"""
    
    def test_func(self):
        session = self.get_session()
        return (
            super().test_func() and 
            session.status == 'strategy_ready'
        )
    
    def post(self, request, session_id):
        session = self.get_session()
        
        # Start execution
        task = initiate_search_session_execution_task.delay(str(session.id))
        
        # Store task ID for monitoring
        request.session[f'execution_task_{session.id}'] = task.id
        
        messages.success(
            request,
            "Search execution started. You'll be notified when results are ready."
        )
        
        return redirect('serp_execution:status', session_id=session.id)
```

### **Execution Status View**
```python
class SearchExecutionStatusView(LoginRequiredMixin, SessionOwnershipMixin, DetailView):
    """Shows real-time search execution progress"""
    
    model = SearchSession
    template_name = 'serp_execution/execution_status.html'
    context_object_name = 'session'
    pk_url_kwarg = 'session_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.object
        
        # Get all executions for this session
        executions = SearchExecution.objects.filter(
            query__session=session
        ).select_related('query').order_by('query__created_at')
        
        # Calculate overall progress
        total_queries = executions.count()
        completed_queries = executions.filter(
            status='completed'
        ).count()
        
        overall_progress = (
            (completed_queries / total_queries * 100) 
            if total_queries > 0 else 0
        )
        
        context.update({
            'executions': executions,
            'overall_progress': overall_progress,
            'total_queries': total_queries,
            'completed_queries': completed_queries,
            'failed_queries': executions.filter(status='failed').count(),
            'can_retry': session.status == 'failed',
        })
        
        return context
```

### **AJAX Progress Endpoint**
```python
@require_http_methods(["GET"])
@login_required
def execution_progress_api(request, session_id):
    """API endpoint for real-time execution progress"""
    
    session = get_object_or_404(
        SearchSession,
        id=session_id,
        created_by=request.user
    )
    
    executions = SearchExecution.objects.filter(
        query__session=session
    ).values(
        'id', 'status', 'progress_percentage', 
        'results_found', 'error_message'
    )
    
    # Calculate summary
    summary = executions.aggregate(
        total=Count('id'),
        completed=Count('id', filter=Q(status='completed')),
        failed=Count('id', filter=Q(status='failed')),
        total_results=Sum('results_found')
    )
    
    return JsonResponse({
        'session_status': session.status,
        'executions': list(executions),
        'summary': summary,
        'overall_progress': (
            summary['completed'] / summary['total'] * 100 
            if summary['total'] > 0 else 0
        )
    })
```

---

## 6. Templates and UI Components

### **Execution Status Template Structure**
```html
<!-- serp_execution/templates/serp_execution/execution_status.html -->
{% extends "base.html" %}
{% load static %}

{% block content %}
<div class="execution-status-container">
    <header class="status-header">
        <h1>Search Execution Progress</h1>
        <div class="session-info">
            <h2>{{ session.title }}</h2>
            <span class="status-badge status-{{ session.status }}">
                {{ session.get_status_display }}
            </span>
        </div>
    </header>
    
    <!-- Overall Progress -->
    <div class="overall-progress-section">
        <h3>Overall Progress</h3>
        <div class="progress-bar-container">
            <div class="progress-bar" 
                 role="progressbar"
                 aria-valuenow="{{ overall_progress }}"
                 aria-valuemin="0"
                 aria-valuemax="100"
                 style="width: {{ overall_progress }}%">
                {{ overall_progress|floatformat:0 }}%
            </div>
        </div>
        <p class="progress-text">
            {{ completed_queries }} of {{ total_queries }} queries completed
            {% if failed_queries > 0 %}
                ({{ failed_queries }} failed)
            {% endif %}
        </p>
    </div>
    
    <!-- Individual Query Status -->
    <div class="query-status-section">
        <h3>Search Queries</h3>
        <div class="query-list">
            {% for execution in executions %}
            <div class="query-item" data-execution-id="{{ execution.id }}">
                <div class="query-header">
                    <h4>{{ execution.query.query_string|truncatewords:10 }}</h4>
                    <span class="query-status status-{{ execution.status }}">
                        {{ execution.get_status_display }}
                    </span>
                </div>
                
                {% if execution.status == 'running' %}
                <div class="query-progress">
                    <div class="progress-bar-small">
                        <div class="progress-fill" 
                             style="width: {{ execution.progress_percentage }}%">
                        </div>
                    </div>
                </div>
                {% endif %}
                
                {% if execution.error_message %}
                <div class="error-message">
                    <i class="icon-error"></i>
                    {{ execution.error_message }}
                    {% if can_retry %}
                    <button class="btn-retry-single" 
                            data-execution-id="{{ execution.id }}">
                        Retry
                    </button>
                    {% endif %}
                </div>
                {% endif %}
                
                {% if execution.results_found %}
                <p class="results-count">
                    {{ execution.results_found }} results found
                </p>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>
    
    <!-- Action Buttons -->
    <div class="action-buttons">
        {% if session.status == 'executing' %}
        <button class="btn btn-secondary" id="pause-execution">
            <i class="icon-pause"></i> Pause Execution
        </button>
        {% elif session.status == 'failed' and can_retry %}
        <button class="btn btn-primary" id="retry-all">
            <i class="icon-retry"></i> Retry Failed Searches
        </button>
        {% elif session.status == 'processing' %}
        <a href="{% url 'results_manager:processing_status' session.id %}" 
           class="btn btn-primary">
            <i class="icon-processing"></i> View Processing Status
        </a>
        {% endif %}
        
        <a href="{% url 'review_manager:dashboard' %}" 
           class="btn btn-secondary">
            <i class="icon-dashboard"></i> Back to Dashboard
        </a>
    </div>
</div>

<!-- Real-time update script -->
<script>
// Extend existing StatusMonitor for execution tracking
class ExecutionMonitor extends StatusMonitor {
    constructor() {
        super();
        this.sessionId = '{{ session.id }}';
        this.executionEndpoint = '{% url "serp_execution:progress_api" session.id %}';
    }
    
    async pollExecutionStatus() {
        try {
            const response = await fetch(this.executionEndpoint);
            const data = await response.json();
            
            this.updateExecutionProgress(data);
            
            // Stop polling if execution is complete
            if (['completed', 'failed', 'processing'].includes(data.session_status)) {
                this.stopPolling();
                this.showCompletionNotification(data.session_status);
            }
        } catch (error) {
            console.error('Failed to fetch execution status:', error);
        }
    }
    
    updateExecutionProgress(data) {
        // Update overall progress
        const progressBar = document.querySelector('.progress-bar');
        progressBar.style.width = `${data.overall_progress}%`;
        progressBar.textContent = `${Math.round(data.overall_progress)}%`;
        
        // Update individual executions
        data.executions.forEach(execution => {
            const element = document.querySelector(
                `[data-execution-id="${execution.id}"]`
            );
            if (element) {
                this.updateExecutionElement(element, execution);
            }
        });
    }
}

// Initialize monitoring
const monitor = new ExecutionMonitor();
monitor.startPolling();
</script>
{% endblock %}
```

---

## 7. Error Handling and Recovery

### **Error Recovery Manager Integration**
```python
# apps/serp_execution/recovery.py

from apps.review_manager.recovery import ErrorRecoveryManager

class SerpExecutionRecoveryManager(ErrorRecoveryManager):
    """Extended recovery manager for SERP execution errors"""
    
    SERP_RECOVERY_STRATEGIES = {
        'rate_limit_exceeded': {
            'message': 'Search API rate limit exceeded',
            'suggestions': [
                {
                    'text': 'Wait 5 minutes and retry',
                    'action': 'retry_after_delay',
                    'icon': 'clock',
                    'primary': True,
                    'delay': 300  # 5 minutes
                },
                {
                    'text': 'Reduce number of queries',
                    'action': 'modify_strategy',
                    'icon': 'edit'
                }
            ]
        },
        'api_timeout': {
            'message': 'Search API request timed out',
            'suggestions': [
                {
                    'text': 'Retry search',
                    'action': 'retry_execution',
                    'icon': 'refresh',
                    'primary': True
                },
                {
                    'text': 'Try with fewer results',
                    'action': 'reduce_results_count',
                    'icon': 'minimize'
                }
            ]
        },
        'invalid_api_key': {
            'message': 'Search API authentication failed',
            'suggestions': [
                {
                    'text': 'Contact administrator',
                    'action': 'contact_admin',
                    'icon': 'user',
                    'primary': True
                },
                {
                    'text': 'Check API configuration',
                    'action': 'view_docs',
                    'icon': 'book'
                }
            ]
        }
    }
```

### **Retry Mechanism**
```python
class RetryFailedSearchesView(LoginRequiredMixin, SessionOwnershipMixin, View):
    """Retry failed search executions"""
    
    def post(self, request, session_id):
        session = self.get_session()
        
        # Get failed executions
        failed_executions = SearchExecution.objects.filter(
            query__session=session,
            status='failed'
        )
        
        retry_count = 0
        for execution in failed_executions:
            # Reset execution
            execution.status = 'pending'
            execution.retry_count += 1
            execution.error_message = None
            execution.save()
            
            # Dispatch retry task
            perform_serp_query_task.delay(execution.id)
            retry_count += 1
        
        messages.success(
            request,
            f"Retrying {retry_count} failed searches."
        )
        
        # Update session status back to executing
        session.status = 'executing'
        session.save()
        
        return redirect('serp_execution:status', session_id=session.id)
```

---

## 8. Testing Requirements

### **Unit Tests**
```python
# apps/serp_execution/tests/test_models.py

class SearchQueryModelTest(TestCase):
    """Test SearchQuery model"""
    
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='researcher',
            password='testpass123'
        )
        self.session = SearchSession.objects.create(
            title='Test Review',
            created_by=self.user,
            status='strategy_ready'
        )
    
    def test_create_search_query(self):
        """Test creating a search query"""
        query = SearchQuery.objects.create(
            session=self.session,
            query_string='diabetes management guidelines UK',
            search_engine='google_serper',
            created_by=self.user
        )
        
        self.assertEqual(query.session, self.session)
        self.assertEqual(query.search_engine, 'google_serper')
        self.assertIsInstance(query.id, uuid.UUID)


# apps/serp_execution/tests/test_tasks.py

@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class CeleryTaskTest(TestCase):
    """Test Celery tasks"""
    
    @patch('apps.serp_execution.services.serper_client.SerperClient.search')
    def test_perform_serp_query_task(self, mock_search):
        """Test individual query execution"""
        mock_search.return_value = {
            'organic': [
                {
                    'position': 1,
                    'title': 'Test Result',
                    'link': 'https://example.com',
                    'snippet': 'Test snippet'
                }
            ]
        }
        
        execution = SearchExecution.objects.create(
            query=self.query,
            status='pending'
        )
        
        perform_serp_query_task(execution.id)
        
        execution.refresh_from_db()
        self.assertEqual(execution.status, 'completed')
        self.assertEqual(execution.results_found, 1)
        self.assertEqual(execution.raw_results.count(), 1)
```

### **Integration Tests**
```python
class SearchExecutionWorkflowTest(TestCase):
    """Test complete search execution workflow"""
    
    def test_complete_execution_workflow(self):
        """Test from strategy_ready to processing"""
        # Create session with strategy
        session = create_test_session_with_strategy()
        
        # Execute searches
        response = self.client.post(
            reverse('serp_execution:execute', args=[session.id])
        )
        
        # Should redirect to status page
        self.assertRedirects(
            response,
            reverse('serp_execution:status', args=[session.id])
        )
        
        # Session status should be executing
        session.refresh_from_db()
        self.assertEqual(session.status, 'executing')
        
        # Should have created search queries
        self.assertTrue(
            SearchQuery.objects.filter(session=session).exists()
        )
```

### **Performance Tests**
```python
class PerformanceTest(TestCase):
    """Test performance requirements"""
    
    def test_api_timeout_handling(self):
        """Ensure API timeouts are handled gracefully"""
        with patch('requests.post') as mock_post:
            mock_post.side_effect = requests.exceptions.Timeout()
            
            client = SerperClient()
            
            with self.assertRaises(SerperTimeoutError):
                client.search('test query')
    
    def test_progress_api_performance(self):
        """Test progress API responds quickly"""
        # Create 100 executions
        create_bulk_executions(100)
        
        start_time = time.time()
        response = self.client.get(
            reverse('serp_execution:progress_api', args=[session.id])
        )
        end_time = time.time()
        
        self.assertEqual(response.status_code, 200)
        self.assertLess(end_time - start_time, 0.5)  # Under 500ms
```

---

## 9. Security Requirements

### **Applied Security Patterns**
1. **Ownership Validation**: All views must use `SessionOwnershipMixin`
2. **Status Validation**: Only allow execution when status is `strategy_ready`
3. **Rate Limiting**: Apply `@rate_limit` decorator to prevent abuse
4. **Audit Logging**: Log all significant actions with `SessionActivity`
5. **Input Validation**: Sanitize all search queries before API calls
6. **API Key Security**: Store API keys in environment variables only

### **Security Implementation Example**
```python
@method_decorator(
    [login_required, owns_session, audit_action('SEARCH_EXECUTED')],
    name='dispatch'
)
class SecureExecuteSearchView(ExecuteSearchView):
    """Security-enhanced search execution view"""
    pass
```

---

## 10. Performance Requirements

### **Target Metrics**
- API response time: < 5 seconds per query
- Progress updates: < 200ms response time
- Concurrent executions: Support 10+ sessions simultaneously
- Retry delay: Exponential backoff starting at 30 seconds
- Database queries: Optimized with select_related/prefetch_related

### **Optimization Strategies**
1. **Batch API Calls**: Group multiple queries when possible
2. **Caching**: Cache API responses for identical queries
3. **Progress Debouncing**: Update progress every 5 seconds max
4. **Database Indexing**: Index on frequently queried fields
5. **Connection Pooling**: Reuse HTTP connections for API calls

---

## 11. Configuration Requirements

### **Django Settings**
```python
# settings/base.py additions

# Serper API Configuration
SERPER_API_KEY = env('SERPER_API_KEY')
SERPER_API_TIMEOUT = 30  # seconds
SERPER_RATE_LIMIT = 100  # requests per minute

# Celery Configuration for SERP tasks
CELERY_ROUTES = {
    'apps.serp_execution.tasks.*': {'queue': 'serp_queue'},
}

# Search execution settings
MAX_RESULTS_PER_QUERY = 100
DEFAULT_SEARCH_REGION = 'uk'
SEARCH_RETRY_ATTEMPTS = 3
SEARCH_RETRY_DELAY = 30  # seconds
```

### **URL Configuration**
```python
# apps/serp_execution/urls.py

app_name = 'serp_execution'

urlpatterns = [
    path('session/<uuid:session_id>/execute/', 
         ExecuteSearchView.as_view(), 
         name='execute'),
    
    path('session/<uuid:session_id>/status/', 
         SearchExecutionStatusView.as_view(), 
         name='status'),
    
    path('session/<uuid:session_id>/retry/', 
         RetryFailedSearchesView.as_view(), 
         name='retry'),
    
    # API endpoints
    path('api/session/<uuid:session_id>/progress/', 
         execution_progress_api, 
         name='progress_api'),
    
    path('api/execution/<uuid:execution_id>/retry/', 
         retry_single_execution_api, 
         name='retry_single_api'),
]
```

---

## 12. Development Guidelines

### **Code Organisation**
```
apps/serp_execution/
├── __init__.py
├── models.py              # SearchQuery, SearchExecution, RawSearchResult
├── views.py               # Main views
├── urls.py                # URL configuration
├── admin.py               # Admin interface
├── forms.py               # If needed for configuration
├── tasks.py               # Celery tasks
├── services/
│   ├── __init__.py
│   ├── serper_client.py   # Serper API client
│   └── query_builder.py   # Query construction logic
├── managers.py            # Custom model managers
├── decorators.py          # App-specific decorators
├── recovery.py            # Error recovery extensions
├── templates/
│   └── serp_execution/
│       ├── execute_confirm.html
│       ├── execution_status.html
│       └── components/
│           └── query_card.html
├── static/
│   └── serp_execution/
│       ├── css/
│       │   └── execution.css
│       └── js/
│           └── execution_monitor.js
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_views.py
│   ├── test_tasks.py
│   ├── test_api_client.py
│   └── test_integration.py
├── migrations/
└── management/
    └── commands/
        └── test_serper_connection.py
```

### **Development Process**
1. **Always use UUID primary keys** for all models
2. **Import User correctly**: `User = get_user_model()`
3. **Apply security decorators** to all views
4. **Log activities** for audit trail
5. **Write tests first** following TDD approach
6. **Use type hints** for better code clarity
7. **Follow Review Manager patterns** for consistency

### **Common Pitfalls to Avoid**
1. **Don't hardcode API keys** - use environment variables
2. **Don't forget rate limiting** - API has usage limits
3. **Don't ignore timeouts** - API calls can be slow
4. **Don't skip ownership checks** - security is critical
5. **Don't forget progress updates** - users need feedback

---

## 13. Acceptance Criteria

### **Functional Requirements**
- [ ] Users can execute searches for sessions in 'strategy_ready' status
- [ ] Real-time progress shown during execution
- [ ] Failed searches can be retried individually or in bulk
- [ ] Clear error messages with recovery options
- [ ] Results stored for processing by next app

### **Non-Functional Requirements**
- [ ] 95%+ test coverage achieved
- [ ] Response times meet performance targets
- [ ] Security measures properly implemented
- [ ] Accessibility standards maintained
- [ ] Documentation complete

### **Integration Requirements**
- [ ] Status workflow correctly updates SearchSession
- [ ] Activity logging captures all events
- [ ] Real-time updates use existing infrastructure
- [ ] Error recovery follows established patterns
- [ ] UI consistent with Review Manager

---

## 14. Handover Checklist

### **For Development Team**
- [ ] Review this document completely
- [ ] Understand Review Manager patterns
- [ ] Set up Serper API account
- [ ] Configure Celery queues
- [ ] Review security requirements
- [ ] Understand testing standards

### **Key Dependencies**
- [ ] Review Manager app functional
- [ ] Celery/Redis configured
- [ ] Serper API credentials
- [ ] UUID migrations understood
- [ ] Security framework understood

### **Success Criteria**
- [ ] Can execute searches from UI
- [ ] Progress updates in real-time
- [ ] Errors handled gracefully
- [ ] Tests achieve 95%+ coverage
- [ ] Performance targets met
- [ ] Security audit passed

---

## 🎯 Summary

The SERP Execution app is a critical component that brings search strategies to life. By following the established patterns from the Review Manager app and maintaining the high standards for security, testing, and user experience, this app will provide researchers with a reliable, efficient way to execute their grey literature searches.

The development team should focus on:
1. **Robust error handling** - API calls will fail
2. **Real-time feedback** - Users need to see progress
3. **Security first** - Follow established patterns
4. **Test thoroughly** - Aim for 95%+ coverage
5. **Performance matters** - Keep response times low