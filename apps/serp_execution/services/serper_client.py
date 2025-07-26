"""
Serper API client for executing search queries.
Handles rate limiting, retries, and error recovery.
"""

import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.cache import cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

from apps.core.logging import ServiceLoggerMixin


class SerperAPIError(Exception):
    """Base exception for Serper API errors."""
    pass


class SerperRateLimitError(SerperAPIError):
    """Raised when API rate limit is exceeded."""
    pass


class SerperAuthError(SerperAPIError):
    """Raised when API authentication fails."""
    pass


class SerperQuotaError(SerperAPIError):
    """Raised when API quota is exceeded."""
    pass


class SerperClient:
    """
    Client for interacting with the Serper API.
    Implements rate limiting, caching, and error recovery.
    """
    
    BASE_URL = "https://google.serper.dev/search"
    RATE_LIMIT_PER_SECOND = 300  # Serper's rate limit
    COST_PER_QUERY = Decimal('0.001')  # $0.001 per query
    
    def __init__(self):
        """Initialize the Serper client with configuration."""
        self.api_key = getattr(settings, 'SERPER_API_KEY', None)
        if not self.api_key:
            raise ValueError("SERPER_API_KEY not configured in settings")
        
        # Create session with retry logic
        self.session = self._create_session()
        
        # Rate limiting
        self.last_request_time = 0
        self.request_count = 0
        self.rate_limit_window = 1.0  # 1 second window
        
    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry logic and connection pooling.
        """
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
            backoff_factor=1,
            respect_retry_after_header=True
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers
        session.headers.update({
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'ThesisGrey/1.0'
        })
        
        return session
    
    def _enforce_rate_limit(self):
        """
        Enforce rate limiting to prevent exceeding API limits.
        """
        current_time = time.time()
        
        # Reset counter if window has passed
        if current_time - self.last_request_time >= self.rate_limit_window:
            self.request_count = 0
            self.last_request_time = current_time
        
        # Check if we need to wait
        if self.request_count >= self.RATE_LIMIT_PER_SECOND:
            sleep_time = self.rate_limit_window - (current_time - self.last_request_time)
            if sleep_time > 0:
                logger.info(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
                self.request_count = 0
                self.last_request_time = time.time()
        
        self.request_count += 1
    
    def _build_request_params(
        self,
        query: str,
        num_results: int = 10,
        search_type: str = "search",
        location: str = "United States",
        language: str = "en",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Build request parameters for Serper API.
        
        Args:
            query: Search query string
            num_results: Number of results to retrieve (max 100)
            search_type: Type of search (search, images, news, etc.)
            location: Location for search results
            language: Language code for results
            **kwargs: Additional parameters
            
        Returns:
            Dictionary of API parameters
        """
        params = self._build_base_params(query, num_results, search_type, location, language)
        params.update(self._build_date_params(kwargs))
        params.update(self._build_file_type_params(query, kwargs))
        return params
    
    def _build_base_params(
        self, 
        query: str, 
        num_results: int, 
        search_type: str, 
        location: str, 
        language: str
    ) -> Dict[str, Any]:
        """Build base request parameters."""
        return {
            'q': query,
            'num': min(num_results, 100),  # Serper max is 100
            'type': search_type,
            'location': location,
            'gl': 'us',  # Country code
            'hl': language,
            'engine': 'google'
        }
    
    def _build_date_params(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Build date filtering parameters."""
        params = {}
        if 'date_from' in kwargs and kwargs['date_from']:
            params['tbs'] = f"cdr:1,cd_min:{kwargs['date_from']}"
        return params
    
    def _build_file_type_params(self, query: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Build file type filtering parameters."""
        params = {}
        if 'file_types' in kwargs and kwargs['file_types']:
            file_type_query = ' OR '.join([f'filetype:{ft}' for ft in kwargs['file_types']])
            params['q'] = f"{query} ({file_type_query})"
        return params
    
    def search(
        self,
        query: str,
        num_results: int = 10,
        use_cache: bool = True,
        **kwargs
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Execute a search query against the Serper API.
        
        Args:
            query: Search query string
            num_results: Number of results to retrieve
            use_cache: Whether to use cached results
            **kwargs: Additional search parameters
            
        Returns:
            Tuple of (results, metadata)
        """
        # Build request parameters
        params = self._build_request_params(query, num_results, **kwargs)
        
        # Check cache first
        if use_cache:
            cache_key = f"serper_search_{hash(urlencode(params))}"
            cached_result = cache.get(cache_key)
            if cached_result:
                logger.info(f"Cache hit for query: {query[:50]}...")
                return cached_result, {'cache_hit': True, 'credits_used': 0}
        
        # Enforce rate limiting
        self._enforce_rate_limit()
        
        try:
            # Make API request
            logger.info(f"Executing Serper search: {query[:50]}...")
            response = self.session.post(
                self.BASE_URL,
                json=params,
                timeout=30
            )
            
            # Handle different response codes
            if response.status_code == 200:
                data = response.json()
                
                # Extract metadata
                metadata = {
                    'cache_hit': False,
                    'credits_used': data.get('credits', 1),
                    'total_results': data.get('searchInformation', {}).get('totalResults', '0'),
                    'time_taken': data.get('searchInformation', {}).get('searchTime', 0),
                    'request_id': response.headers.get('X-Request-ID', '')
                }
                
                # Cache successful results
                if use_cache:
                    cache_ttl = 3600 * 24  # 24 hours for general queries
                    cache.set(cache_key, (data, metadata), cache_ttl)
                
                return data, metadata
                
            elif response.status_code == 401:
                raise SerperAuthError("Invalid API key")
            elif response.status_code == 402:
                raise SerperQuotaError("API quota exceeded")
            elif response.status_code == 429:
                retry_after = response.headers.get('Retry-After', 60)
                raise SerperRateLimitError(f"Rate limit exceeded. Retry after {retry_after} seconds")
            else:
                response.raise_for_status()
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout executing query: {query}")
            raise SerperAPIError("Request timed out")
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error executing query: {query}")
            raise SerperAPIError("Connection error")
        except Exception as e:
            logger.error(f"Unexpected error executing query: {query}, Error: {str(e)}")
            raise SerperAPIError(f"Unexpected error: {str(e)}")
    
    def check_rate_limits(self) -> Dict[str, Any]:
        """
        Check current rate limit status.
        
        Returns:
            Dictionary with rate limit information
        """
        return {
            'requests_in_window': self.request_count,
            'rate_limit': self.RATE_LIMIT_PER_SECOND,
            'window_start': self.last_request_time,
            'can_make_request': self.request_count < self.RATE_LIMIT_PER_SECOND
        }
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get API usage statistics (placeholder for actual implementation).
        
        Returns:
            Dictionary with usage statistics
        """
        # This would typically make an API call to get actual usage
        # For now, return mock data
        return {
            'credits_remaining': 10000,
            'credits_used_today': 150,
            'requests_today': 150,
            'average_response_time': 0.45
        }
    
    def estimate_cost(self, num_queries: int) -> Decimal:
        """
        Estimate the cost for a given number of queries.
        
        Args:
            num_queries: Number of queries to estimate
            
        Returns:
            Estimated cost in USD
        """
        return self.COST_PER_QUERY * num_queries
    
    def validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a search query before execution.
        
        Args:
            query: Query string to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not query or not query.strip():
            return False, "Query cannot be empty"
        
        if len(query) > 2048:
            return False, "Query too long (max 2048 characters)"
        
        # Check for common issues
        if query.count('"') % 2 != 0:
            return False, "Unmatched quotes in query"
        
        return True, None