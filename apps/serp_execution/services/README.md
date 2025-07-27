# SERP Execution Services

This directory contains the simplified service layer for the SERP (Search Engine Results Page) execution functionality in Thesis Grey. These services handle the core pipeline from search query execution through basic result processing.

## Overview

The SERP execution services provide a streamlined system for:

- **Search Execution**: Execute search queries via the Serper API (Google Search)
- **Result Processing**: Extract and normalize raw search results  
- **Basic Caching**: Simple result caching to reduce API costs
- **Execution Management**: Basic execution coordination and statistics
- **Query Building**: Simple PIC framework query construction

## Simplified Service Architecture

The services follow a simplified, focused architecture:

```
SerperClient ────► ResultProcessor
     │                    │
     ▼                    ▼
CacheManager        ExecutionService
     │                    │
     ▼                    ▼
QueryBuilder ◄──── (Basic Error Recovery)
```

### Data Flow

1. **Query Building**: `QueryBuilder` converts PIC framework terms into basic search strings
2. **Search Execution**: `SerperClient` executes queries with rate limiting and caching
3. **Result Processing**: `ResultProcessor` extracts and normalizes raw API responses
4. **Execution Management**: `ExecutionService` provides basic statistics and coordination

## Individual Service Documentation

### SerperClient

**Purpose**: Core API client for executing search queries via Serper API.

**Key Methods**:
- `search(query, num_results=10, use_cache=True, **kwargs)` - Execute search query
- `validate_query(query)` - Validate query syntax and length
- `check_rate_limits()` - Get current rate limit status
- `get_usage_stats()` - Get basic usage statistics

**Configuration Options**:
```python
SERPER_API_KEY = "your-api-key"  # Required
```

**Rate Limiting**: 
- 300 requests per second (Serper's limit)
- Built-in rate limiting with automatic delays
- Connection pooling for efficiency

**Error Handling**:
- `SerperRateLimitError` - Rate limit exceeded
- `SerperAuthError` - Invalid API key
- `SerperQuotaError` - API quota exhausted
- `SerperAPIError` - General API errors

**Example Usage**:
```python
from .services import SerperClient

client = SerperClient()
results, metadata = client.search(
    "climate change research",
    num_results=50,
    file_types=["pdf"],
    location="United States"
)
```

### QueryBuilder

**Purpose**: Simple query construction from PIC framework components.

**Key Methods**:
- `build_query(population, interest, context, file_types=None)` - Build basic search query
- `encode_for_url(query)` - URL encode query string

**Features**:
- **Basic Boolean Logic**: Simple AND operator between PIC components
- **File Type Filtering**: Support for PDF, DOC, PPT, etc.
- **Quote Wrapping**: Wraps PIC terms in quotes for exact matching

**Example Usage**:
```python
from .services import QueryBuilder

builder = QueryBuilder()
query = builder.build_query(
    population="elderly patients",
    interest="telemedicine interventions", 
    context="rural healthcare settings",
    file_types=["pdf"]
)
# Result: "elderly patients" AND "telemedicine interventions" AND "rural healthcare settings" filetype:pdf
```

### ResultProcessor

**Purpose**: Simple processing of raw search results from Serper API into normalized data.

**Key Methods**:
- `process_search_results(raw_results)` - Process API results
- `extract_metadata(result)` - Extract basic metadata from a result

**Processing Features**:
- **Basic Normalization**: URL, title, and snippet extraction
- **File Type Detection**: Simple file type detection from URLs
- **Domain Extraction**: Extract domain from URLs
- **Metadata Extraction**: Basic result metadata

**Example Processing Flow**:
```python
processor = ResultProcessor()
processed_results = processor.process_search_results(
    raw_results=api_response['organic']
)
```



### CacheManager

**Purpose**: Simple caching system to reduce API costs and improve performance.

**Key Methods**:
- `get_search_results(query_params)` - Retrieve cached results
- `set_search_results(query_params, results)` - Cache new results
- `invalidate_search_results(query_params)` - Remove cached results

**Caching Strategy**:
- **Fixed TTL**: Default 1 hour cache duration
- **MD5 Hash Keys**: Consistent cache key generation from query parameters
- **Redis Backend**: Uses Django's cache framework

**Configuration**:
- `SERP_CACHE_ENABLED` - Enable/disable caching (default: True)
- `SERP_CACHE_TTL` - Cache duration in seconds (default: 3600)

### ExecutionService

**Purpose**: Basic execution coordination and statistics.

**Key Methods**:
- `get_execution_statistics(session_id)` - Basic session execution stats

**Features**:
- **Basic Statistics**: Total, successful, and failed execution counts
- **Success Rate**: Percentage of successful executions
- **Simple Metrics**: No complex analysis or estimation


## Usage Examples

### Simple Search Execution Flow

```python
from apps.serp_execution.services import (
    QueryBuilder, SerperClient, ResultProcessor, CacheManager
)

# 1. Build simple query
builder = QueryBuilder()
query = builder.build_query(
    population="diabetes patients",
    interest="mobile health apps",
    context="self-management",
    file_types=["pdf"]
)

# 2. Execute search with caching
client = SerperClient()
results, metadata = client.search(query, num_results=100, use_cache=True)

# 3. Process results
processor = ResultProcessor()
processed_results = processor.process_search_results(
    raw_results=results.get('organic', [])
)

# 4. Extract metadata if needed
for result in processed_results:
    metadata = processor.extract_metadata(result)
    print(f"Domain: {metadata['domain']}, File Type: {metadata['file_type']}")
```

### Basic Query Processing

```python
from apps.serp_execution.services import QueryBuilder, SerperClient

builder = QueryBuilder()
client = SerperClient()

queries = [
    ("elderly", "telemedicine", "rural areas"),
    ("children", "mental health", "school settings"),
    ("cancer patients", "support groups", "online communities")
]

for population, interest, context in queries:
    query = builder.build_query(population, interest, context)
    
    # Validate before execution
    is_valid, error = client.validate_query(query)
    if not is_valid:
        print(f"Invalid query: {error}")
        continue
    
    try:
        results, metadata = client.search(query)
        print(f"Found {len(results.get('organic', []))} results")
    except Exception as e:
        print(f"Search failed: {e}")
```

## Configuration Guide

### Environment Variables

Required environment variables in `.env`:

```bash
# Serper API Configuration
SERPER_API_KEY=your-serper-api-key-here

# Cache Configuration (optional)
SERP_CACHE_ENABLED=True
SERP_CACHE_TTL=3600  # Default TTL in seconds (1 hour)
```

### Django Settings

Add to your Django settings:

```python
# API Configuration
SERPER_API_KEY = config('SERPER_API_KEY', default='')

# Cache Configuration
SERP_CACHE_ENABLED = config('SERP_CACHE_ENABLED', default=True, cast=bool)
SERP_CACHE_TTL = config('SERP_CACHE_TTL', default=3600, cast=int)

# Caching Backend (Redis recommended for production)
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

### API Limits and Costs

**Serper API Limits**:
- Rate limit: 300 requests per second
- Cost: $0.001 per search query
- Free tier: 2,500 queries per month

**Built-in Rate Limiting**:
- Automatic rate limiting to respect API limits
- Connection pooling for efficiency
- Retry logic for transient failures

## Error Handling

### Basic Error Recovery

The services include basic error handling with automatic retries:

1. **Built-in Retries**: Automatic retry for network and rate limit errors
2. **Rate Limit Handling**: Respects API rate limits with delays
3. **Connection Pooling**: Reduces connection-related errors
4. **Authentication/Quota Errors**: Clear error messages for manual intervention

### Common Error Scenarios

**Rate Limit Exceeded**:
```python
try:
    results, metadata = client.search(query)
except SerperRateLimitError as e:
    # Automatic retry handled by client
    # Log error and handle gracefully
    logger.error(f"Rate limit exceeded: {e}")
```

**API Authentication**:
```python
try:
    client = SerperClient()
except ValueError as e:
    # Missing or invalid API key
    logger.error("SERPER_API_KEY not configured")
```

### Error Recovery Strategies

1. **Rate Limit Strategy**: Uses `Retry-After` header or built-in delays
2. **Network Error Strategy**: Basic retry with exponential backoff
3. **Quota/Auth Errors**: No automatic retry, requires manual intervention

## Development Guidelines

### Extending Services

To add new services:

1. **Simple Pattern**: Follow the existing simple service patterns
2. **Basic Error Handling**: Implement basic exception handling
3. **Testing**: Write unit tests with mocking for external APIs
4. **Documentation**: Update this README with new service information

### Simple Service Guidelines

```python
class NewService:
    """Simple service description."""
    
    def __init__(self):
        """Initialize service."""
        self.config = getattr(settings, 'CONFIG_NAME', 'default')
    
    def main_operation(self, required_param: str) -> Dict[str, Any]:
        """
        Primary service operation.
        
        Args:
            required_param: Description of required parameter
            
        Returns:
            Dictionary with operation results
        """
        try:
            # Simple implementation
            return {"success": True, "data": result}
        except Exception as e:
            logger.error(f"Operation failed: {str(e)}")
            raise
```

### Testing Services

Services should have basic test coverage. Example test pattern:

```python
from unittest.mock import Mock, patch
from django.test import TestCase, override_settings

class TestSerperClient(TestCase):
    
    @override_settings(SERPER_API_KEY="test-key")
    def setUp(self):
        self.client = SerperClient()
    
    @patch('requests.Session.post')
    def test_successful_search(self, mock_post):
        # Setup mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"organic": []}
        mock_post.return_value = mock_response
        
        # Test search
        results, metadata = self.client.search("test query")
        
        # Assertions
        self.assertIsInstance(results, dict)
        self.assertIn("organic", results)
```

### Performance Considerations

1. **Caching**: Enable caching for production to reduce API costs
2. **Connection Pooling**: SerperClient uses connection pooling for efficiency
3. **Rate Limiting**: Built-in rate limiting prevents API abuse
4. **Basic Monitoring**: Error logging and basic statistics

### Security Considerations

1. **API Key Protection**: Never log or expose API keys
2. **Input Validation**: Basic validation before API calls
3. **Rate Limiting**: Built-in protection against API abuse
4. **Error Information**: Error details are logged but not exposed to users

## Integration with Other Apps

The SERP execution services integrate with other Thesis Grey apps:

- **review_manager**: Session status management and workflow transitions
- **search_strategy**: PIC framework query building and strategy configuration
- **results_manager**: Processed result handoff for quality assessment
- **accounts**: User authentication and ownership validation

This simplified service layer provides a focused foundation for executing grey literature searches with basic error handling and performance optimization.