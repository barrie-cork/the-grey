# SERP Execution API Contract

**Feature**: Search Execution and Results Processing  
**Version**: 1.0  
**Date**: 2025-01-26  
**Status**: Draft

## Overview

This API contract defines the interface between frontend and backend for the SERP (Search Engine Results Page) execution feature. It enables systematic search query execution via Serper API with real-time monitoring, cost tracking, and error handling.

## Serper API Integration Details

### API Specifications
- **Service**: Serper.dev - Industry-leading SERP API
- **Performance**: 1-2 seconds response time
- **Pricing**: $0.30 per 1,000 queries (after free tier)
- **Free Tier**: 2,500 requests per account
- **Base Endpoint**: https://google.serper.dev/search
- **Scholar Endpoint**: https://google.serper.dev/scholar
- **Authentication**: Bearer token via Authorization header

### Supported Parameters
- **q**: Search query string (required)
- **gl**: Country/geolocation (e.g., "us", "ca", "gb")
- **hl**: Language (e.g., "en", "fr", "de")
- **location**: Specific geographic location
- **num**: Number of results (1-100, default: 10)
- **page**: Result page for pagination

### Response Format
Serper API returns JSON with structured data including:
- **organic**: Standard Google search results
- **answerBox**: Direct answers and featured snippets
- **knowledgeGraph**: Entity information and knowledge panels
- **peopleAlsoAsk**: Related questions
- **relatedSearches**: Suggested search terms
- **searchParameters**: Echo of request parameters

## Base Configuration

```yaml
Base URL: /api/v1/executions
Content-Type: application/json
Authentication: Bearer token (Django session auth)
CORS: Allow frontend origin
Pagination: Django REST Framework format
```

## RESTful Endpoints

### 1. Execution Management

#### POST /api/v1/executions/
**Purpose**: Create and start a search execution  
**Request Body**:
```typescript
interface ExecutionRequest {
  session_id: string;           // UUID of SearchSession
  query_ids: string[];          // Array of SearchQuery UUIDs
  search_engines: string[];     // ["google", "bing"] - default: ["google"]
  max_results_per_query: number; // 1-1000, default: 100
  priority: number;             // 1-10, default: 5
  estimated_cost_limit?: number; // Optional budget limit in USD
}
```

**Response (201 Created)**:
```typescript
interface ExecutionResponse {
  id: string;                   // UUID
  session_id: string;
  status: ExecutionStatus;      // "pending" | "running" | "completed" | "failed" | "cancelled"
  query_count: number;
  estimated_total_cost: number;
  estimated_duration_seconds: number;
  celery_task_id: string;
  created_at: string;           // ISO 8601
  started_at?: string;
  progress_url: string;         // WebSocket URL for real-time updates
}
```

#### GET /api/v1/executions/
**Purpose**: List executions with filtering  
**Query Parameters**:
```typescript
interface ExecutionListParams {
  session_id?: string;          // Filter by session
  status?: ExecutionStatus;     // Filter by status
  search_engine?: string;       // Filter by engine
  page?: number;                // Pagination (default: 1)
  page_size?: number;           // Results per page (default: 25, max: 100)
  ordering?: string;            // Sort field (default: "-created_at")
}
```

**Response (200 OK)**:
```typescript
interface ExecutionListResponse {
  count: number;
  next?: string;
  previous?: string;
  results: ExecutionResponse[];
}
```

#### GET /api/v1/executions/{id}/
**Purpose**: Get execution details  
**Path Parameter**: `id` (UUID)  
**Response (200 OK)**: `ExecutionResponse`

#### PUT /api/v1/executions/{id}/
**Purpose**: Update execution parameters (only if status is "pending")  
**Path Parameter**: `id` (UUID)  
**Request Body**: `ExecutionRequest`  
**Response (200 OK)**: `ExecutionResponse`

#### DELETE /api/v1/executions/{id}/
**Purpose**: Cancel execution  
**Path Parameter**: `id` (UUID)  
**Response (204 No Content)**

### 2. Execution Monitoring

#### GET /api/v1/executions/{id}/status/
**Purpose**: Get current execution status and progress  
**Response (200 OK)**:
```typescript
interface ExecutionStatusResponse {
  id: string;
  status: ExecutionStatus;
  progress_percentage: number;  // 0-100
  completed_queries: number;
  total_queries: number;
  running_queries: string[];    // Array of query IDs currently executing
  results_count: number;
  api_credits_used: number;
  estimated_cost: number;
  duration_seconds?: number;
  error_message?: string;
  retry_count: number;
  estimated_completion?: string; // ISO 8601
  last_updated: string;         // ISO 8601
}
```

#### POST /api/v1/executions/{id}/retry/
**Purpose**: Retry failed execution  
**Request Body**:
```typescript
interface RetryRequest {
  retry_reason: string;         // Required, 1-500 chars
  max_retries?: number;         // 1-5, default: 3
  retry_delay_seconds?: number; // 30-3600, default: 60
}
```
**Response (200 OK)**: `ExecutionResponse`

### 3. Results Management

#### GET /api/v1/executions/{id}/results/
**Purpose**: Get paginated search results from execution  
**Query Parameters**:
```typescript
interface ExecutionResultsParams {
  page?: number;
  page_size?: number;           // Max 100
  search_engine?: string;       // Filter by engine
  has_pdf?: boolean;           // Filter PDF results
  is_academic?: boolean;       // Filter academic results
  min_position?: number;       // Filter by result position
  max_position?: number;
  ordering?: string;           // "position", "-position", "created_at"
}
```

**Response (200 OK)**:
```typescript
interface ExecutionResultsResponse {
  count: number;
  next?: string;
  previous?: string;
  results: RawSearchResult[];
}

interface RawSearchResult {
  id: string;
  execution_id: string;
  position: number;
  title: string;
  url: string;
  snippet: string;
  display_link: string;
  source: string;
  has_pdf: boolean;
  has_date: boolean;
  detected_date?: string;       // ISO 8601 date
  is_academic: boolean;
  language_code: string;
  domain: string;               // Computed field
  is_processed: boolean;
  created_at: string;
}
```

### 4. Cost and Usage Tracking

#### GET /api/v1/executions/{id}/metrics/
**Purpose**: Get execution metrics and cost breakdown  
**Response (200 OK)**:
```typescript
interface ExecutionMetricsResponse {
  id: string;
  execution_id: string;
  total_api_calls: number;
  successful_calls: number;
  failed_calls: number;
  total_results_retrieved: number;
  unique_results_count: number;
  api_credits_used: number;
  total_cost: number;           // USD
  cost_per_result: number;
  average_response_time: number; // Seconds
  success_rate: number;         // 0-1
  rate_limit_hits: number;
  quality_metrics: {
    academic_results: number;
    pdf_results: number;
    results_with_dates: number;
  };
  engine_breakdown: EngineMetrics[];
}

interface EngineMetrics {
  engine_name: string;
  executions: number;
  success_rate: number;
  avg_response_time: number;
  avg_results_count: number;
  cost_efficiency: number;
}
```

#### GET /api/v1/sessions/{session_id}/cost-estimate/
**Purpose**: Get cost estimate before starting execution  
**Query Parameters**:
```typescript
interface CostEstimateParams {
  query_count: number;
  max_results_per_query: number;
  search_engines: string[];
}
```

**Response (200 OK)**:
```typescript
interface CostEstimateResponse {
  session_id: string;
  estimated_total_cost: number; // USD
  cost_per_query: number;
  estimated_credits: number;
  estimated_duration_minutes: number;
  budget_warning: boolean;
  cost_breakdown: {
    [engine: string]: {
      queries: number;
      cost_per_query: number;
      total_cost: number;
    };
  };
}
```

## Real-time Updates

### WebSocket Connection
**URL**: `ws://localhost:8000/ws/executions/{execution_id}/`  
**Authentication**: WebSocket accepts Django session cookies

**Message Types**:
```typescript
// Status update message
interface StatusUpdateMessage {
  type: "status_update";
  execution_id: string;
  status: ExecutionStatus;
  progress_percentage: number;
  completed_queries: number;
  results_count: number;
  timestamp: string;
}

// Error message
interface ErrorMessage {
  type: "error";
  execution_id: string;
  error_message: string;
  query_id?: string;
  retry_recommended: boolean;
  timestamp: string;
}

// Completion message
interface CompletionMessage {
  type: "completion";
  execution_id: string;
  final_status: ExecutionStatus;
  total_results: number;
  total_cost: number;
  duration_seconds: number;
  next_action: "processing" | "review" | "failed";
  timestamp: string;
}
```

## Error Responses

### Standard Error Format
```typescript
interface ApiErrorResponse {
  timestamp: string;            // ISO 8601
  status: number;               // HTTP status code
  error: string;                // Error type
  message: string;              // Human-readable message
  path: string;                 // Request path
  details?: {
    field?: string;             // Field name for validation errors
    code?: string;              // Error code
    context?: any;              // Additional context
  }[];
}
```

### Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | GET, PUT successful |
| 201 | Created | POST successful |
| 204 | No Content | DELETE successful |
| 400 | Bad Request | Validation errors, invalid parameters |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Execution/resource not found |
| 409 | Conflict | Execution already running, duplicate request |
| 422 | Unprocessable Entity | Business logic validation failed |
| 429 | Too Many Requests | Rate limiting exceeded |
| 500 | Internal Server Error | Server-side errors |
| 503 | Service Unavailable | External API (Serper) unavailable |

### Specific Error Scenarios

#### Budget Exceeded (422)
```json
{
  "timestamp": "2025-01-26T10:30:00Z",
  "status": 422,
  "error": "Budget Exceeded",
  "message": "Estimated cost ($15.50) exceeds session budget ($10.00)",
  "path": "/api/v1/executions/",
  "details": [{
    "field": "estimated_cost_limit",
    "code": "BUDGET_EXCEEDED",
    "context": {
      "estimated_cost": 15.50,
      "budget_limit": 10.00,
      "session_id": "uuid-here"
    }
  }]
}
```

#### Rate Limited (429)
```json
{
  "timestamp": "2025-01-26T10:30:00Z",
  "status": 429,
  "error": "Rate Limited",
  "message": "API rate limit exceeded. Retry after 60 seconds.",
  "path": "/api/v1/executions/",
  "details": [{
    "code": "RATE_LIMIT_EXCEEDED",
    "context": {
      "retry_after_seconds": 60,
      "rate_limit_type": "serper_api"
    }
  }]
}
```

## Validation Rules

### ExecutionRequest Validation
```typescript
// Backend (Django) validation
const validation = {
  session_id: "required, valid UUID, must exist",
  query_ids: "required, array of UUIDs, 1-50 items, all must exist",
  search_engines: "array of strings, valid engines only",
  max_results_per_query: "integer, 1-1000",
  priority: "integer, 1-10",
  estimated_cost_limit: "decimal, > 0, <= 1000"
};

// Frontend (Zod) validation
import { z } from 'zod';

const ExecutionRequestSchema = z.object({
  session_id: z.string().uuid(),
  query_ids: z.array(z.string().uuid()).min(1).max(50),
  search_engines: z.array(z.enum(['google', 'bing'])).default(['google']),
  max_results_per_query: z.number().int().min(1).max(1000).default(100),
  priority: z.number().int().min(1).max(10).default(5),
  estimated_cost_limit: z.number().positive().max(1000).optional()
});
```

## Integration Requirements

### Authentication
- **Development**: Django session authentication via cookies
- **Production**: JWT tokens or API keys
- **WebSocket**: Session cookies passed via WebSocket headers

### CORS Configuration
```python
# Django settings
CORS_ALLOWED_ORIGINS = ["http://localhost:3000"]  # Frontend origin
CORS_ALLOW_CREDENTIALS = True
```

### Rate Limiting
- **User-level**: 100 execution requests per hour
- **Session-level**: 10 concurrent executions
- **API-level**: Respect Serper API rate limits (1000 requests/month)

### Caching Strategy
- **Cost estimates**: Cache for 1 hour
- **Execution status**: No caching (real-time)
- **Results**: Cache paginated results for 5 minutes

## Backend Implementation Notes

### Django Models Mapping
```python
# Maps to existing models:
# - SearchExecution (main execution tracking)
# - RawSearchResult (individual results)
# - ExecutionMetrics (aggregated metrics)

# Required serializers:
class ExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchExecution
        fields = ['id', 'session_id', 'status', ...]

# Custom managers for filtering:
class ExecutionQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status__in=['pending', 'running'])
    
    def by_session(self, session_id):
        return self.filter(query__session_id=session_id)
```

### Celery Task Integration
```python
import requests
from celery import shared_task
from django.conf import settings

@shared_task(bind=True)
def execute_search_queries(self, execution_id):
    """Execute search queries via Serper API"""
    execution = SearchExecution.objects.get(id=execution_id)
    
    # Update status to running
    execution.status = 'running'
    execution.started_at = timezone.now()
    execution.save()
    
    try:
        # Prepare Serper API request
        headers = {
            'Authorization': f'Bearer {settings.SERPER_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Process each query
        for query in execution.query.session.search_queries.all():
            search_data = {
                'q': query.query_text,
                'gl': query.country_code or 'us',
                'hl': query.language_code or 'en',
                'num': execution.max_results_per_query or 10
            }
            
            # Call Serper API
            response = requests.post(
                'https://google.serper.dev/search',
                headers=headers,
                json=search_data,
                timeout=30
            )
            
            if response.status_code == 200:
                # Process and save results
                results_data = response.json()
                save_raw_search_results(execution, results_data)
                
                # Update cost tracking
                execution.api_credits_used += 1
                execution.estimated_cost += Decimal('0.0003')  # $0.30/1000
            else:
                handle_api_error(execution, response)
        
        # Mark as completed
        execution.status = 'completed'
        execution.completed_at = timezone.now()
        execution.save()
        
        # Send WebSocket completion message
        send_execution_update(execution.id, 'completion')
        
    except Exception as e:
        execution.status = 'failed'
        execution.error_message = str(e)
        execution.save()
        send_execution_update(execution.id, 'error')

def save_raw_search_results(execution, serper_response):
    """Process Serper API response and save results"""
    
    # Extract organic results
    organic_results = serper_response.get('organic', [])
    for idx, result in enumerate(organic_results):
        RawSearchResult.objects.create(
            execution=execution,
            position=idx + 1,
            title=result.get('title', ''),
            link=result.get('link', ''),
            snippet=result.get('snippet', ''),
            display_link=result.get('displayLink', ''),
            source=result.get('source', ''),
            raw_data=result,
            has_pdf='.pdf' in result.get('link', '').lower(),
            detected_date=extract_date_from_snippet(result.get('snippet', ''))
        )
    
    # Process additional data if available
    if 'answerBox' in serper_response:
        # Save answer box as special result
        answer_box = serper_response['answerBox']
        RawSearchResult.objects.create(
            execution=execution,
            position=0,  # Special position for answer box
            title=answer_box.get('title', 'Answer Box'),
            link=answer_box.get('link', ''),
            snippet=answer_box.get('answer', ''),
            raw_data=answer_box,
            is_academic=True  # Answer boxes often contain authoritative info
        )
    
    # Update execution metrics
    execution.results_count = len(organic_results)
    execution.save()
```

### WebSocket Implementation
```python
# Django Channels consumer
class ExecutionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.execution_id = self.scope['url_route']['kwargs']['execution_id']
        await self.channel_layer.group_add(f"execution_{self.execution_id}", self.channel_name)
    
    # Send progress updates, errors, completion
```

## Frontend Implementation Notes

### TypeScript API Client
```typescript
// Base API client configuration
const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  withCredentials: true,  // For session auth
});

// TanStack Query hooks
export const useExecutionStatus = (executionId: string) => {
  return useQuery({
    queryKey: ['execution', executionId, 'status'],
    queryFn: () => fetchExecutionStatus(executionId),
    refetchInterval: 5000,  // Poll every 5 seconds
  });
};

export const useCreateExecution = () => {
  return useMutation({
    mutationFn: createExecution,
    onSuccess: (data) => {
      // Start WebSocket connection for real-time updates
      connectToExecutionUpdates(data.id);
    },
  });
};
```

### WebSocket Client
```typescript
// Real-time updates
class ExecutionWebSocket {
  private ws: WebSocket;
  
  connect(executionId: string) {
    this.ws = new WebSocket(`ws://localhost:8000/ws/executions/${executionId}/`);
    
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };
  }
  
  private handleMessage(message: StatusUpdateMessage | ErrorMessage | CompletionMessage) {
    // Update UI based on message type
    // Trigger react-query cache updates
  }
}
```

### Error Handling
```typescript
// Centralized error handling
export const handleApiError = (error: AxiosError) => {
  if (error.response?.status === 429) {
    // Show rate limit message
    toast.error('Rate limit exceeded. Please wait before retrying.');
  } else if (error.response?.status === 422) {
    // Handle business logic errors
    const details = error.response.data.details;
    if (details?.[0]?.code === 'BUDGET_EXCEEDED') {
      showBudgetExceededDialog(details[0].context);
    }
  }
};
```

## Testing Strategy

### Backend Tests
```python
# API endpoint tests
class ExecutionAPITestCase(APITestCase):
    def test_create_execution_success(self):
        # Test successful execution creation
    
    def test_create_execution_budget_exceeded(self):
        # Test budget validation
    
    def test_websocket_updates(self):
        # Test real-time updates

# Integration tests with Celery
class ExecutionIntegrationTestCase(TestCase):
    def test_full_execution_workflow(self):
        # Test end-to-end execution flow
```

### Frontend Tests
```typescript
// Component tests
describe('ExecutionMonitor', () => {
  it('should display execution progress', () => {
    // Test UI updates
  });
  
  it('should handle WebSocket messages', () => {
    // Test real-time updates
  });
});

// API integration tests
describe('Execution API', () => {
  it('should create execution successfully', () => {
    // Test API calls
  });
});
```

## Deployment Considerations

### Environment Variables
```bash
# Backend
SERPER_API_KEY=your_serper_key
SERPER_API_BASE_URL=https://google.serper.dev
EXECUTION_RATE_LIMIT=100
MAX_CONCURRENT_EXECUTIONS=10

# Frontend
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_BASE_URL=ws://localhost:8000/ws
```

### Monitoring & Logging
- **Execution metrics**: Track success rates, costs, performance
- **Error tracking**: Sentry integration for error monitoring
- **API usage**: Monitor Serper API quota and costs
- **WebSocket connections**: Track active connections and message throughput

---

## Research Insights and Implementation Recommendations

### Critical Implementation Insights

Based on comprehensive research conducted on 2025-01-26, several critical implementation patterns and corrections have been identified:

#### **1. Serper API Integration Corrections**
**Current Implementation Issues Identified:**
- ❌ **Wrong Authentication**: Current code uses `X-API-KEY` header instead of `Authorization: Bearer`
- ❌ **Wrong HTTP Method**: Using GET requests instead of required POST with JSON payload
- ❌ **Incorrect Pricing**: Calculating $0.001 per query instead of actual $0.30 per 1,000 queries ($0.0003)
- ❌ **Wrong Rate Limits**: Set to 300/second instead of actual Serper specifications

**Corrected Implementation Pattern:**
```python
# Correct authentication and request format
headers = {
    'Authorization': f'Bearer {settings.SERPER_API_KEY}',  # NOT X-API-KEY
    'Content-Type': 'application/json'
}

# POST request with JSON payload (NOT GET)
response = requests.post(
    'https://google.serper.dev/search',
    headers=headers,
    json={'q': query, 'gl': 'us', 'hl': 'en', 'num': 10},
    timeout=30
)

# Correct pricing calculation
COST_PER_QUERY = Decimal('0.0003')  # $0.30 per 1,000 queries
```

#### **2. Django REST Framework Patterns (From Existing Codebase)**
**Follow Existing Patterns in `/apps/review_manager/api/`:**
```python
# Use ModelViewSet with custom actions
class SearchExecutionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ExecutionSerializer
    filterset_class = ExecutionFilter
    
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        # Custom business logic actions
```

**URL Structure Convention:**
- Use `/api/v1/` prefix for versioning (add to existing structure)
- Follow existing pattern: `/api/review-manager/sessions/` → `/api/v1/executions/`

#### **3. WebSocket Implementation Requirements**
**Django Channels Integration:**
```python
# Installation requirements
pip install channels[daphne] channels-redis redis

# ASGI configuration required in asgi.py
# WebSocket consumer for real-time execution updates
# Redis channel layer for message broadcasting
```

#### **4. Testing Patterns (From Codebase Analysis)**
**Follow Existing Test Structure:**
```
apps/serp_execution/tests/
├── test_api_endpoints.py      # New DRF API tests
├── test_serializers.py        # Serializer validation tests  
├── test_websocket.py          # WebSocket functionality tests
└── test_serper_integration.py # Mocked external API tests
```

**Mock Patterns to Follow:**
```python
@patch('apps.serp_execution.services.serper_client.requests.Session.post')
def test_api_execution_success(self, mock_post):
    # Use existing mock patterns from codebase
```

### **Remaining Implementation Tasks**

#### **Phase 1: Critical Fixes (Week 1)**
1. **Fix Serper Client Authentication**
   - Change from `X-API-KEY` to `Authorization: Bearer`
   - Update request format from GET to POST with JSON
   - Correct pricing calculations throughout codebase

2. **Implement Django REST Framework Structure**
   - Create `/apps/serp_execution/api/` directory
   - Implement ViewSets following `/apps/review_manager/api/` patterns
   - Add URL routing with `/api/v1/executions/` prefix

#### **Phase 2: API Implementation (Week 2-3)**
3. **Create REST API Endpoints**
   - Implement all endpoints from contract specification
   - Add proper serializers with validation
   - Implement filtering and pagination

4. **Add WebSocket Support**
   - Install and configure Django Channels
   - Create WebSocket consumers for real-time updates
   - Integrate with existing Celery tasks

#### **Phase 3: Testing and Polish (Week 4-5)**
5. **Comprehensive Testing**
   - Follow existing test patterns from codebase
   - Mock external APIs appropriately
   - Achieve 90%+ test coverage target

6. **Integration and Documentation**
   - Update API documentation
   - Ensure backward compatibility
   - Performance optimization

### **Validation Gates for Implementation**

```bash
# Code Quality (existing tools in codebase)
flake8 apps/serp_execution/ --max-line-length=120
mypy apps/serp_execution/
black apps/serp_execution/

# Testing (existing patterns)
python manage.py test apps.serp_execution
pytest apps/serp_execution/tests/ -v --cov=apps.serp_execution

# Django checks
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
```

### **Resource Requirements**

#### **Dependencies to Add:**
```python
# requirements/base.txt additions
channels[daphne]==4.0.0
channels-redis==4.2.0
redis==5.0.1

# Update existing DRF to latest version
djangorestframework==3.14.0
django-filter==23.5
```

#### **Environment Variables:**
```bash
# Update .env file
SERPER_API_KEY=your_bearer_token_here  # Not X-API-KEY format
REDIS_URL=redis://localhost:6379/0     # For Channels
```

### **Success Metrics**

1. **Functional Requirements:**
   - ✅ All API contract endpoints implemented and responding
   - ✅ WebSocket real-time updates working
   - ✅ Correct Serper API integration (authentication, pricing, response parsing)
   - ✅ Test coverage > 90%

2. **Performance Requirements:**
   - ✅ API response time < 2 seconds
   - ✅ WebSocket connection handling > 100 concurrent users
   - ✅ Proper error handling and retry mechanisms

3. **Integration Requirements:**
   - ✅ Seamless integration with existing review_manager workflows
   - ✅ Backward compatibility maintained
   - ✅ Proper cost tracking and budget management

---

**Contract Version**: 1.1  
**Last Updated**: 2025-01-26  
**Research Completed**: 2025-01-26  
**Review Date**: 2025-02-26  
**Status**: Ready for Implementation with Research Insights