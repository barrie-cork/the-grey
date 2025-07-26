# SERP Execution - Google Search API Documentation

**Date:** 31st May 2025  
**App:** `apps/serp_execution/`  
**Purpose:** Executing Google searches via SERP APIs for grey literature discovery

## 📋 Executive Summary

This document provides the latest guidance on accessing Google Search Engine Results Pages (SERP) programmatically for the Thesis Grey project. Based on 2024-2025 research, we recommend using **Serper.dev** as the primary SERP API provider due to its superior speed, cost-effectiveness, and reliability.

## 🔍 Google SERP API Options (2025)

### 1. **Serper.dev** ⭐ RECOMMENDED
- **Speed:** 1-2 seconds response time
- **Cost:** $0.30 - $1.00 per 1,000 queries (volume-based)
- **Rate Limit:** 50-300 queries per second (based on plan)
- **Reliability:** Industry-leading uptime
- **Documentation:** https://serper.dev/

### 2. **SerpApi**
- **Speed:** 0.8-1.3 seconds response time
- **Cost:** $0.0075 - $0.050 per query
- **Features:** 80+ search engine APIs, comprehensive parsing
- **Documentation:** https://serpapi.com/

### 3. **Google Custom Search API** (Official but Limited)
- **Cost:** 100 free queries/day, then $5 per 1,000 queries
- **Limitations:** Only searches within specified sites, not full web
- **Documentation:** https://developers.google.com/custom-search/

## 🚀 Serper.dev Implementation

### Installation & Setup

```python
# No specific SDK required - uses standard HTTP requests
import requests
import os
from typing import Dict, List, Optional

# Environment variable
SERPER_API_KEY = os.getenv('SERPER_API_KEY')
```

### Basic Search Implementation

```python
class SerperClient:
    """Client for Serper.dev Google Search API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = 'https://google.serper.dev/search'
        self.headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }
    
    def search(self, query: str, num: int = 10, gl: str = 'uk', **kwargs) -> Dict:
        """
        Execute a Google search via Serper API
        
        Args:
            query: Search query string
            num: Number of results (default: 10)
            gl: Country code for geolocation (default: 'uk')
            **kwargs: Additional parameters
        
        Returns:
            Dict containing search results
        """
        payload = {
            'q': query,
            'num': num,
            'gl': gl,
            **kwargs
        }
        
        try:
            response = requests.post(
                self.base_url,
                json=payload,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Serper API error: {str(e)}")
```

### Django Integration Example

```python
# apps/serp_execution/services/serper_service.py

from django.conf import settings
from django.core.cache import cache
import hashlib
import json

class SerperSearchService:
    """Service for executing searches with caching and rate limiting"""
    
    def __init__(self):
        self.client = SerperClient(settings.SERPER_API_KEY)
        self.cache_timeout = 3600  # 1 hour
    
    def execute_search(self, query: str, parameters: Dict) -> Dict:
        """Execute search with caching"""
        # Create cache key
        cache_key = self._get_cache_key(query, parameters)
        
        # Check cache first
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        # Execute search
        result = self.client.search(
            query=query,
            num=parameters.get('num_results', 100),
            gl=parameters.get('region', 'uk'),
            hl=parameters.get('language', 'en'),
            type=parameters.get('search_type', 'search')  # or 'news', 'images'
        )
        
        # Cache result
        cache.set(cache_key, result, self.cache_timeout)
        
        return result
    
    def _get_cache_key(self, query: str, parameters: Dict) -> str:
        """Generate cache key for query"""
        key_data = f"{query}:{json.dumps(parameters, sort_keys=True)}"
        return f"serper:{hashlib.md5(key_data.encode()).hexdigest()}"
```

### Celery Task Implementation

```python
# apps/serp_execution/tasks.py

from celery import shared_task
from django.utils import timezone
from .models import SearchExecution, RawSearchResult
from .services.serper_service import SerperSearchService

@shared_task(bind=True, max_retries=3)
def perform_serp_query_task(self, execution_id: str):
    """Execute a search query against Serper API"""
    
    try:
        execution = SearchExecution.objects.get(id=execution_id)
        execution.status = 'running'
        execution.started_at = timezone.now()
        execution.save()
        
        # Initialize service
        service = SerperSearchService()
        
        # Execute search
        results = service.execute_search(
            query=execution.query.query_string,
            parameters=execution.query.parameters
        )
        
        # Process and store results
        organic_results = results.get('organic', [])
        
        for position, result in enumerate(organic_results, 1):
            RawSearchResult.objects.create(
                execution=execution,
                position=position,
                url=result.get('link', ''),
                title=result.get('title', ''),
                snippet=result.get('snippet', ''),
                domain=result.get('domain', ''),
                raw_data=result,
                retrieved_at=timezone.now()
            )
        
        # Update execution status
        execution.status = 'completed'
        execution.completed_at = timezone.now()
        execution.results_found = len(organic_results)
        execution.save()
        
        return {'status': 'success', 'results_count': len(organic_results)}
        
    except Exception as e:
        execution.status = 'failed'
        execution.error_message = str(e)
        execution.save()
        
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
```

## 📊 Response Structure

### Serper.dev Response Format

```json
{
  "searchParameters": {
    "q": "grey literature diabetes management",
    "gl": "uk",
    "hl": "en",
    "num": 10,
    "type": "search"
  },
  "organic": [
    {
      "title": "Managing diabetes: grey literature insights",
      "link": "https://example.com/diabetes-grey-lit",
      "snippet": "This report examines grey literature sources for diabetes management...",
      "position": 1,
      "date": "2 days ago",
      "domain": "example.com"
    }
  ],
  "peopleAlsoAsk": [
    {
      "question": "What is grey literature in healthcare?",
      "snippet": "Grey literature refers to research...",
      "title": "Understanding Grey Literature",
      "link": "https://example.com/grey-lit-guide"
    }
  ],
  "relatedSearches": [
    {
      "query": "diabetes clinical guidelines grey literature"
    }
  ]
}
```

## 🔒 Security & Rate Limiting

### Rate Limiting Implementation

```python
# apps/serp_execution/utils/rate_limiter.py

from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import time

class RateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self, max_calls: int, time_window: int):
        self.max_calls = max_calls
        self.time_window = time_window  # in seconds
    
    def check_and_update(self, key: str) -> bool:
        """Check if request is allowed and update counter"""
        cache_key = f"rate_limit:{key}"
        current_count = cache.get(cache_key, 0)
        
        if current_count >= self.max_calls:
            return False
        
        # Increment counter
        cache.set(cache_key, current_count + 1, self.time_window)
        return True
    
    def wait_if_needed(self, key: str) -> None:
        """Wait if rate limit exceeded"""
        while not self.check_and_update(key):
            time.sleep(1)
```

### API Key Security

```python
# settings/production.py

import os

# Serper API Configuration
SERPER_API_KEY = os.environ.get('SERPER_API_KEY')
if not SERPER_API_KEY:
    raise ValueError("SERPER_API_KEY environment variable is required")

# Rate limiting
SERPER_RATE_LIMIT = int(os.environ.get('SERPER_RATE_LIMIT', '100'))
SERPER_TIME_WINDOW = int(os.environ.get('SERPER_TIME_WINDOW', '60'))
```

## 💰 Cost Optimization

### Caching Strategy

```python
# apps/serp_execution/utils/cache_manager.py

class SearchCacheManager:
    """Manage search result caching"""
    
    def should_use_cache(self, query: str, last_execution_date: timezone.datetime) -> bool:
        """Determine if cached results are still valid"""
        # Grey literature typically doesn't change rapidly
        cache_validity_days = 7
        
        if not last_execution_date:
            return False
        
        age = timezone.now() - last_execution_date
        return age.days < cache_validity_days
    
    def get_cached_results(self, query_hash: str) -> Optional[List[Dict]]:
        """Retrieve cached results if available"""
        return cache.get(f"search_results:{query_hash}")
```

### Batch Processing

```python
# Combine related searches to reduce API calls
def create_optimized_queries(session: SearchSession) -> List[str]:
    """Generate optimized search queries"""
    base_terms = []
    
    # Combine PIC terms strategically
    for pop_term in session.population_terms[:3]:  # Limit to top 3
        for int_term in session.interest_terms[:2]:
            for ctx_term in session.context_terms[:2]:
                query = f"{pop_term} {int_term} {ctx_term} filetype:pdf OR site:.gov OR site:.org"
                base_terms.append(query)
    
    return base_terms[:10]  # Max 10 queries per session
```

## 🧪 Testing

### Mock Serper Response

```python
# apps/serp_execution/tests/mocks.py

def get_mock_serper_response():
    """Get mock Serper API response for testing"""
    return {
        "searchParameters": {
            "q": "test query",
            "gl": "uk",
            "hl": "en",
            "num": 10,
            "type": "search"
        },
        "organic": [
            {
                "title": "Test Result 1",
                "link": "https://example.com/test1",
                "snippet": "This is a test result snippet...",
                "position": 1,
                "domain": "example.com"
            },
            {
                "title": "Test Result 2", 
                "link": "https://example.org/test2",
                "snippet": "Another test result snippet...",
                "position": 2,
                "domain": "example.org"
            }
        ],
        "searchMetadata": {
            "createdAt": "2025-05-31T10:00:00Z",
            "totalTime": 1.23
        }
    }

# Test implementation
@patch('requests.post')
def test_serper_search(mock_post):
    """Test Serper API search"""
    mock_post.return_value.json.return_value = get_mock_serper_response()
    mock_post.return_value.status_code = 200
    
    client = SerperClient('test-api-key')
    results = client.search('test query')
    
    assert len(results['organic']) == 2
    assert results['organic'][0]['title'] == 'Test Result 1'
```

## 📈 Performance Considerations

### Concurrent Searches

```python
# apps/serp_execution/utils/concurrent_search.py

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

class ConcurrentSearchExecutor:
    """Execute multiple searches concurrently"""
    
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.service = SerperSearchService()
    
    def execute_batch(self, queries: List[Tuple[str, Dict]]) -> Dict[str, Dict]:
        """Execute multiple searches concurrently"""
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all searches
            future_to_query = {
                executor.submit(
                    self.service.execute_search, 
                    query, 
                    params
                ): query 
                for query, params in queries
            }
            
            # Collect results
            for future in as_completed(future_to_query):
                query = future_to_query[future]
                try:
                    result = future.result(timeout=30)
                    results[query] = result
                except Exception as e:
                    results[query] = {'error': str(e)}
        
        return results
```

## 🌍 Localization & Grey Literature Focus

### Grey Literature Search Optimization

```python
def build_grey_literature_query(base_query: str, parameters: Dict) -> str:
    """Optimize query for grey literature discovery"""
    
    # Add grey literature indicators
    grey_lit_terms = [
        'report', 'white paper', 'technical report', 
        'working paper', 'preprint', 'thesis', 
        'dissertation', 'conference proceedings'
    ]
    
    # Add file type filters
    file_types = ['pdf', 'doc', 'docx']
    
    # Add institutional domains
    domains = ['.gov', '.org', '.edu', '.ac.uk', '.nhs.uk']
    
    # Build enhanced query
    enhanced_query = f"{base_query} ("
    enhanced_query += " OR ".join(grey_lit_terms) + ") ("
    enhanced_query += " OR ".join([f"filetype:{ft}" for ft in file_types]) + " OR "
    enhanced_query += " OR ".join([f"site:{d}" for d in domains]) + ")"
    
    # Exclude commercial sites if specified
    if parameters.get('exclude_commercial', True):
        enhanced_query += " -site:.com"
    
    return enhanced_query
```

## 🚨 Error Handling

### Comprehensive Error Types

```python
# apps/serp_execution/exceptions.py

class SerperAPIError(Exception):
    """Base exception for Serper API errors"""
    pass

class RateLimitError(SerperAPIError):
    """Rate limit exceeded"""
    pass

class AuthenticationError(SerperAPIError):
    """Invalid API key"""
    pass

class QuotaExceededError(SerperAPIError):
    """API quota exceeded"""
    pass

class InvalidQueryError(SerperAPIError):
    """Invalid search query"""
    pass

# Error handling in client
def handle_serper_response(response):
    """Handle API response and errors"""
    if response.status_code == 429:
        raise RateLimitError("Rate limit exceeded. Please wait.")
    elif response.status_code == 401:
        raise AuthenticationError("Invalid API key")
    elif response.status_code == 402:
        raise QuotaExceededError("API quota exceeded")
    elif response.status_code == 400:
        raise InvalidQueryError(response.json().get('error', 'Invalid query'))
    elif not response.ok:
        raise SerperAPIError(f"API error: {response.status_code}")
```

## 📚 Additional Resources

### Alternative SERP APIs (Fallback Options)

1. **SerpApi** (https://serpapi.com/)
   - Python SDK: `pip install google-search-results`
   - More expensive but very reliable
   - Good documentation and support

2. **ScrapingDog** (https://scrapingdog.com/)
   - Good for high-volume searches
   - Built-in proxy rotation

3. **Bright Data SERP API** (https://brightdata.com/)
   - Enterprise-grade solution
   - Higher cost but excellent reliability

### Best Practices

1. **Always implement caching** to reduce API costs
2. **Use batch processing** where possible
3. **Implement retry logic** with exponential backoff
4. **Monitor API usage** to avoid unexpected costs
5. **Filter for grey literature** indicators in queries
6. **Store raw responses** for future reprocessing
7. **Implement fallback** to alternative APIs

### Integration Checklist

- [ ] Set up Serper.dev account and obtain API key
- [ ] Configure environment variables
- [ ] Implement SerperClient class
- [ ] Create Celery tasks for async execution
- [ ] Set up rate limiting
- [ ] Implement caching strategy
- [ ] Create comprehensive error handling
- [ ] Write unit tests with mocks
- [ ] Test with real API (limited queries)
- [ ] Monitor initial usage and costs

## 🔮 Future Enhancements

1. **Multi-API Support**: Implement adapter pattern for multiple SERP providers
2. **ML-based Relevance**: Use machine learning to identify grey literature
3. **Advanced Filtering**: Implement NLP for better result filtering
4. **Cost Optimization**: Dynamic API selection based on query type
5. **Result Deduplication**: Cross-API result deduplication

---

**Note**: This documentation is based on the latest available information as of May 2025. SERP API landscapes change rapidly, so always verify current pricing and features before implementation.
