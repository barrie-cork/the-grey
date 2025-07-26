# PRP: SERP Execution API Contract Refactor Implementation

**Goal**: Refactor SERP execution implementation to align with modern API contract specifications, correct Serper API integration, and implement comprehensive REST endpoints with real-time capabilities.

**Why**: Current implementation has critical issues preventing production deployment - wrong authentication method, incorrect pricing calculations, missing REST API endpoints, and no real-time updates. This refactor enables accurate cost tracking, modern API standards, and seamless frontend integration.

**Context**: Based on comprehensive research of existing codebase patterns, latest Serper API documentation, and modern Django REST Framework practices. This PRP implements the specifications defined in `/mnt/d/Python/Projects/django/HTA-projects/agent-grey/PRPs/contracts/serp-execution-api-contract.md`.

## Implementation Requirements

### Phase 1: Critical API Fixes (Priority: Urgent)

#### Fix Serper API Client Integration
**Current Issues**: Using `X-API-KEY` authentication (wrong), GET requests (wrong), incorrect pricing ($0.001 vs $0.0003), wrong rate limits.

**Required Changes**:
```python
# In apps/serp_execution/services/serper_client.py
class SerperClient:
    BASE_URL = "https://google.serper.dev/search"
    COST_PER_QUERY = Decimal('0.0003')  # $0.30 per 1,000 queries
    
    def _create_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            'Authorization': f'Bearer {self.api_key}',  # CRITICAL: Bearer token
            'Content-Type': 'application/json'
        })
        return session
    
    def search(self, query: str, **kwargs) -> Tuple[Dict, Dict]:
        payload = {
            'q': query,
            'num': kwargs.get('num_results', 10),
            'gl': kwargs.get('country', 'us'),
            'hl': kwargs.get('language', 'en')
        }
        
        # CRITICAL: POST request with JSON payload
        response = self.session.post(
            self.BASE_URL,
            json=payload,  # Not params
            timeout=30
        )
```

### Phase 2: Django REST Framework Implementation

#### Create API Directory Structure
Following existing patterns in `/apps/review_manager/api/`:
```
apps/serp_execution/api/
├── __init__.py
├── serializers.py
├── views.py
├── urls.py
└── permissions.py
```

#### Implement ViewSets
**Pattern Reference**: Follow `/apps/review_manager/api/views.py` patterns:
```python
# apps/serp_execution/api/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class SearchExecutionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for search execution management with real-time monitoring.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ExecutionSerializer
    filterset_class = ExecutionFilter
    lookup_field = 'id'  # UUID lookup
    
    def get_queryset(self):
        """Filter executions by user ownership."""
        return SearchExecution.objects.filter(
            query__session__owner=self.request.user
        ).select_related('query', 'query__session').prefetch_related('raw_results')
    
    @action(detail=True, methods=['get'])
    def status(self, request, id=None):
        """Get real-time execution status."""
        execution = self.get_object()
        serializer = ExecutionStatusSerializer(execution)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def retry(self, request, id=None):
        """Retry failed execution."""
        execution = self.get_object()
        
        if not execution.can_retry():
            return Response(
                {'error': 'Execution cannot be retried'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Trigger retry task
        from ..tasks import retry_failed_execution_task
        task = retry_failed_execution_task.delay(str(execution.id))
        
        return Response({
            'message': 'Retry initiated',
            'task_id': task.id
        })
    
    @action(detail=True, methods=['get'])
    def results(self, request, id=None):
        """Get paginated execution results."""
        execution = self.get_object()
        results = execution.raw_results.all()
        
        # Apply filtering
        filterset = RawSearchResultFilter(request.GET, queryset=results)
        filtered_results = filterset.qs
        
        # Paginate
        page = self.paginate_queryset(filtered_results)
        if page is not None:
            serializer = RawSearchResultSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = RawSearchResultSerializer(filtered_results, many=True)
        return Response(serializer.data)
```

#### Implement Serializers
**Pattern Reference**: Follow `/apps/review_manager/api/serializers.py` patterns:
```python
# apps/serp_execution/api/serializers.py
from rest_framework import serializers
from ..models import SearchExecution, RawSearchResult

class ExecutionSerializer(serializers.ModelSerializer):
    """Main execution serializer with computed fields."""
    
    # Computed read-only fields
    session_title = serializers.CharField(source='query.session.title', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    progress_percentage = serializers.SerializerMethodField()
    estimated_completion = serializers.SerializerMethodField()
    
    class Meta:
        model = SearchExecution
        fields = [
            'id', 'session_title', 'status', 'status_display',
            'progress_percentage', 'estimated_completion', 'results_count',
            'api_credits_used', 'estimated_cost', 'created_at', 'started_at'
        ]
        read_only_fields = ['id', 'created_at', 'started_at']
    
    def get_progress_percentage(self, obj):
        """Calculate real-time progress."""
        if obj.status == 'completed':
            return 100.0
        # Add logic for calculating progress
        return 0.0
    
    def get_estimated_completion(self, obj):
        """Calculate estimated completion time."""
        if obj.status not in ['running', 'pending']:
            return None
        # Add estimation logic
        return None

class ExecutionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new executions."""
    
    class Meta:
        model = SearchExecution
        fields = ['session_id', 'max_results_per_query', 'priority']
    
    def validate_session_id(self, value):
        """Validate session ownership and status."""
        try:
            session = SearchSession.objects.get(id=value)
            if session.owner != self.context['request'].user:
                raise serializers.ValidationError("Session not found")
            if session.status not in ['strategy_ready', 'ready_to_execute']:
                raise serializers.ValidationError("Session not ready for execution")
            return value
        except SearchSession.DoesNotExist:
            raise serializers.ValidationError("Session not found")
```

### Phase 3: WebSocket Real-time Updates

#### Install Dependencies
```bash
pip install channels[daphne]==4.0.0 channels-redis==4.2.0 redis==5.0.1
```

#### Configure Django Channels
**Update settings**:
```python
# grey_lit_project/settings/base.py
INSTALLED_APPS = [
    'daphne',  # Add at top
    # ... existing apps
    'channels',
]

ASGI_APPLICATION = 'grey_lit_project.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('127.0.0.1', 6379)],
        },
    },
}
```

#### Create ASGI Configuration
```python
# grey_lit_project/asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'grey_lit_project.settings.local')

django_asgi_app = get_asgi_application()

from apps.serp_execution import routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                routing.websocket_urlpatterns
            )
        )
    ),
})
```

#### Implement WebSocket Consumer
```python
# apps/serp_execution/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

class ExecutionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.execution_id = self.scope['url_route']['kwargs']['execution_id']
        self.group_name = f'execution_{self.execution_id}'
        self.user = self.scope["user"]
        
        # Authentication check
        if isinstance(self.user, AnonymousUser):
            await self.close()
            return
        
        # Permission check
        if not await self.check_execution_access():
            await self.close()
            return
        
        # Join group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        
        # Send current status
        await self.send_current_status()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
    
    @database_sync_to_async
    def check_execution_access(self):
        """Check if user can access this execution."""
        try:
            from .models import SearchExecution
            execution = SearchExecution.objects.select_related('query__session').get(
                id=self.execution_id
            )
            return execution.query.session.owner == self.user
        except SearchExecution.DoesNotExist:
            return False
    
    async def send_current_status(self):
        """Send current execution status."""
        execution = await self.get_execution()
        if execution:
            await self.send(text_data=json.dumps({
                'type': 'status_update',
                'execution_id': str(execution.id),
                'status': execution.status,
                'progress_percentage': 0.0,  # Calculate actual progress
                'results_count': execution.results_count,
                'timestamp': execution.updated_at.isoformat()
            }))
    
    # Message handlers
    async def execution_update(self, event):
        await self.send(text_data=json.dumps(event['data']))
```

#### Update Celery Tasks for Real-time Updates
```python
# apps/serp_execution/tasks.py
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def send_execution_update(execution_id, update_type, data=None):
    """Send WebSocket update for execution."""
    channel_layer = get_channel_layer()
    group_name = f'execution_{execution_id}'
    
    message_data = {
        'type': update_type,
        'execution_id': execution_id,
        'timestamp': timezone.now().isoformat(),
    }
    
    if data:
        message_data.update(data)
    
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            'type': 'execution_update',
            'data': message_data
        }
    )

# Update existing task
@shared_task(bind=True)
def execute_search_queries(self, execution_id):
    try:
        execution = SearchExecution.objects.get(id=execution_id)
        
        # Send status update
        send_execution_update(execution_id, 'status_update', {
            'status': 'running',
            'progress_percentage': 0
        })
        
        # ... existing logic with periodic updates
        
    except Exception as e:
        send_execution_update(execution_id, 'error', {
            'error_message': str(e)
        })
```

### Phase 4: URL Configuration

#### Update Main URLs
```python
# grey_lit_project/urls.py
urlpatterns = [
    # ... existing patterns
    path("api/v1/", include("apps.serp_execution.api.urls")),
]
```

#### Create API URLs
```python
# apps/serp_execution/api/urls.py
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from . import views

router = DefaultRouter()
router.register(r'executions', views.SearchExecutionViewSet, basename='execution')

urlpatterns = [
    path('', include(router.urls)),
    # Additional custom endpoints if needed
]
```

#### WebSocket Routing
```python
# apps/serp_execution/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/executions/(?P<execution_id>[0-9a-f-]+)/$', 
            consumers.ExecutionConsumer.as_asgi()),
]
```

## Testing Implementation

### Test Structure
Following existing patterns in `/apps/accounts/tests/` and `/apps/serp_execution/tests/`:

```python
# apps/serp_execution/tests/test_api_endpoints.py
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from unittest.mock import patch, Mock
from ..models import SearchExecution

class ExecutionAPITestCase(APITestCase):
    def setUp(self):
        """Follow existing test patterns."""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        self.session = SearchSession.objects.create(
            title='Test Session',
            owner=self.user,
            status='strategy_ready'
        )
    
    def test_create_execution_success(self):
        """Test successful execution creation."""
        url = reverse('execution-list')
        data = {
            'session_id': str(self.session.id),
            'max_results_per_query': 50,
            'priority': 5
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['status'], 'pending')
    
    @patch('apps.serp_execution.services.serper_client.requests.Session.post')
    def test_execution_with_serper_mock(self, mock_post):
        """Test execution with mocked Serper API."""
        # Mock Serper response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'organic': [
                {
                    'title': 'Test Result',
                    'link': 'https://example.com',
                    'snippet': 'Test snippet'
                }
            ]
        }
        mock_post.return_value = mock_response
        
        # Test API call
        url = reverse('execution-list')
        data = {'session_id': str(self.session.id)}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
```

### WebSocket Testing
```python
# apps/serp_execution/tests/test_websocket.py
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.test import TransactionTestCase
from ..consumers import ExecutionConsumer

class WebSocketTestCase(TransactionTestCase):
    async def test_execution_websocket_connection(self):
        """Test WebSocket connection for execution monitoring."""
        communicator = WebsocketCommunicator(
            ExecutionConsumer.as_asgi(),
            f"/ws/executions/{self.execution.id}/"
        )
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Test receiving status update
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'status_update')
        
        await communicator.disconnect()
```

## Validation Gates

### Code Quality Checks
```bash
# Use existing linting setup
flake8 apps/serp_execution/ --max-line-length=120
mypy apps/serp_execution/
black apps/serp_execution/
isort apps/serp_execution/

# Django-specific checks
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
```

### Testing
```bash
# Run all SERP execution tests
python manage.py test apps.serp_execution

# Run with coverage (using existing setup)
pytest apps/serp_execution/tests/ -v --cov=apps.serp_execution --cov-report=html

# Integration testing
python manage.py test apps.serp_execution.tests.test_integration
```

### API Testing
```bash
# Test API endpoints
python manage.py test apps.serp_execution.tests.test_api_endpoints

# Test serializers
python manage.py test apps.serp_execution.tests.test_serializers

# WebSocket testing
python manage.py test apps.serp_execution.tests.test_websocket
```

## Known Gotchas & Solutions

### 1. Serper API Authentication
**Gotcha**: Easy to use wrong header format
**Solution**: Always use `Authorization: Bearer {token}`, never `X-API-KEY`

### 2. Django Channels ASGI
**Gotcha**: ASGI app must be configured correctly
**Solution**: Follow exact pattern in existing `asgi.py`, add daphne at top of INSTALLED_APPS

### 3. WebSocket Authentication
**Gotcha**: Session auth may not work with WebSocket
**Solution**: Use AuthMiddlewareStack and verify user in consumer connect()

### 4. Celery Task Integration
**Gotcha**: Sending WebSocket messages from tasks can fail
**Solution**: Use async_to_sync(channel_layer.group_send()) pattern

### 5. Model Migrations
**Gotcha**: Adding fields to existing model may require data migration
**Solution**: Create data migration to populate new fields with default values

## Implementation Tasks (Ordered)

1. **Fix Serper Client** (apps/serp_execution/services/serper_client.py)
   - Update authentication to Bearer token
   - Change GET to POST requests
   - Fix pricing calculations

2. **Create API Structure** (apps/serp_execution/api/)
   - Create directory and files
   - Implement ViewSets following review_manager patterns
   - Add serializers with validation

3. **Update URL Configuration**
   - Add API v1 routing
   - Configure WebSocket routing

4. **Install and Configure Channels**
   - Add dependencies
   - Update settings and ASGI
   - Create WebSocket consumers

5. **Update Celery Tasks**
   - Add WebSocket integration
   - Implement real-time progress updates

6. **Comprehensive Testing**
   - API endpoint tests
   - WebSocket functionality tests
   - Serper integration tests (mocked)

7. **Documentation and Deployment**
   - Update API documentation
   - Configure production settings
   - Deploy and verify

## Success Criteria

- [ ] All API contract endpoints responding correctly
- [ ] Serper API integration working with correct authentication
- [ ] WebSocket real-time updates functional
- [ ] Test coverage > 90%
- [ ] No breaking changes to existing functionality
- [ ] Cost calculations accurate within 0.1%
- [ ] Performance meets < 2s response time requirement

## Resources & References

- **API Contract**: `/mnt/d/Python/Projects/django/HTA-projects/agent-grey/PRPs/contracts/serp-execution-api-contract.md`
- **Existing Patterns**: `/apps/review_manager/api/` (DRF implementation reference)
- **Test Patterns**: `/apps/accounts/tests/` (comprehensive test examples)
- **Django Channels Docs**: https://channels.readthedocs.io/en/latest/
- **DRF Documentation**: https://www.django-rest-framework.org/
- **Serper API Docs**: https://serper.dev/

**PRP Confidence Score**: 9/10 - Comprehensive research completed, existing patterns identified, critical issues documented, implementation path clear with validation gates.