"""
Serper API client for executing search queries.
Handles rate limiting, retries, and error recovery.
"""

import logging
import time
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.cache import cache

from apps.core.config import get_config
from .http_client import HTTPClient
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class SerperAPIError(Exception):
    """Base exception for Serper API errors."""


class SerperRateLimitError(SerperAPIError):
    """Raised when API rate limit is exceeded."""


class SerperAuthError(SerperAPIError):
    """Raised when API authentication fails."""


class SerperQuotaError(SerperAPIError):
    """Raised when API quota is exceeded."""


class SerperClient:
    """
    Client for interacting with the Serper API.
    Implements rate limiting, caching, and error recovery.
    """

    BASE_URL = "https://google.serper.dev/search"

    def __init__(
        self,
        http_client: Optional[HTTPClient] = None,
        rate_limiter: Optional[RateLimiter] = None,
    ):
        """
        Initialize the Serper client with configuration.
        
        Args:
            http_client: HTTP client instance (creates one if not provided)
            rate_limiter: Rate limiter instance (creates one if not provided)
        """
        self.api_key = getattr(settings, "SERPER_API_KEY", None)
        if not self.api_key:
            raise ValueError("SERPER_API_KEY not configured in settings")

        # Get configuration
        self.config = get_config()

        # Use provided services or create defaults
        self.http_client = http_client or HTTPClient(
            base_url=self.BASE_URL,
            api_key=self.api_key,
            timeout=self.config.api.serper_timeout,
            max_retries=self.config.api.max_retries
        )
        
        # Use Serper's documented rate limit of 300 requests per second
        self.rate_limiter = rate_limiter or RateLimiter(
            rate_limit_per_minute=300 * 60  # 300 per second = 18000 per minute
        )


    def _build_request_params(
        self,
        query: str,
        num_results: int = 10,
        search_type: str = "search",
        location: str = "United States",
        language: str = "en",
        **kwargs,
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
        params = self._build_base_params(
            query, num_results, search_type, location, language
        )
        params.update(self._build_date_params(kwargs))
        params.update(self._build_file_type_params(query, kwargs))
        return params

    def _build_base_params(
        self,
        query: str,
        num_results: int,
        search_type: str,
        location: str,
        language: str,
    ) -> Dict[str, Any]:
        """Build base request parameters."""
        # Use configuration defaults if not specified
        location = location or self.config.search.default_location or "United States"
        language = language or self.config.search.default_language
        
        return {
            "q": query,
            "num": min(num_results, self.config.search.default_num_results),  # Respect config max
            "type": search_type,
            "location": location,
            "gl": "us",  # Country code
            "hl": language,
            "engine": "google",
        }

    def _build_date_params(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Build date filtering parameters."""
        params = {}
        if "date_from" in kwargs and kwargs["date_from"]:
            params["tbs"] = f"cdr:1,cd_min:{kwargs['date_from']}"
        return params

    def _build_file_type_params(
        self, query: str, kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build file type filtering parameters."""
        params = {}
        if "file_types" in kwargs and kwargs["file_types"]:
            file_type_query = " OR ".join(
                [f"filetype:{ft}" for ft in kwargs["file_types"]]
            )
            params["q"] = f"{query} ({file_type_query})"
        return params

    def search(
        self, query: str, num_results: int = 10, use_cache: bool = True, **kwargs
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
                return cached_result, {"cache_hit": True, "credits_used": 0}

        # Enforce rate limiting
        self.rate_limiter.wait_if_needed()

        try:
            # Make API request
            logger.info(f"Executing Serper search: {query[:50]}...")
            response = self.http_client.post("", json_data=params)

            # Handle different response codes
            if response.status_code == 200:
                data = response.json()

                # Extract metadata
                metadata = {
                    "cache_hit": False,
                    "credits_used": data.get("credits", 1),
                    "total_results": data.get("searchInformation", {}).get(
                        "totalResults", "0"
                    ),
                    "time_taken": data.get("searchInformation", {}).get(
                        "searchTime", 0
                    ),
                    "request_id": response.headers.get("X-Request-ID", ""),
                }

                # Cache successful results
                if use_cache:
                    cache_ttl = self.config.processing.cache_ttl
                    cache.set(cache_key, (data, metadata), cache_ttl)

                return data, metadata

            elif response.status_code == 401:
                raise SerperAuthError("Invalid API key")
            elif response.status_code == 402:
                raise SerperQuotaError("API quota exceeded")
            elif response.status_code == 429:
                retry_after = response.headers.get("Retry-After", 60)
                raise SerperRateLimitError(
                    f"Rate limit exceeded. Retry after {retry_after} seconds"
                )
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
            "requests_in_window": self.rate_limiter.request_count,
            "rate_limit": self.rate_limiter.rate_limit_per_second,
            "window_start": self.rate_limiter.last_request_time,
            "can_make_request": self.rate_limiter.check_rate_limit(),
            "remaining_requests": self.rate_limiter.get_remaining_requests(),
            "wait_time": self.rate_limiter.get_wait_time(),
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
            "credits_remaining": 10000,
            "credits_used_today": 150,
            "requests_today": 150,
            "average_response_time": 0.45,
        }


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

    def close(self):
        """Clean up resources."""
        if hasattr(self.http_client, 'close'):
            self.http_client.close()
