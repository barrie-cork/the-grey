"""
Simple cache management for serp_execution slice.
Business capability: Basic search result caching.
"""

import hashlib
import json
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.cache import cache


class CacheManager:
    """Simple service for caching search results."""

    # Cache settings
    PREFIX_SEARCH = "serp_search"
    DEFAULT_TTL = 3600  # 1 hour

    def __init__(self):
        """Initialize cache manager."""
        self.enabled = getattr(settings, "SERP_CACHE_ENABLED", True)
        self.ttl = getattr(settings, "SERP_CACHE_TTL", self.DEFAULT_TTL)

    def _generate_cache_key(self, query_params: Dict[str, Any]) -> str:
        """Generate cache key from query parameters."""
        sorted_params = json.dumps(query_params, sort_keys=True)
        hash_digest = hashlib.md5(sorted_params.encode()).hexdigest()
        return f"{self.PREFIX_SEARCH}:{hash_digest}"

    def get_search_results(self, query_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached search results if available."""
        if not self.enabled:
            return None

        cache_key = self._generate_cache_key(query_params)
        return cache.get(cache_key)

    def set_search_results(self, query_params: Dict[str, Any], results: Dict[str, Any]) -> bool:
        """Cache search results."""
        if not self.enabled:
            return False

        cache_key = self._generate_cache_key(query_params)
        cache.set(cache_key, results, self.ttl)
        return True

    def invalidate_search_results(self, query_params: Dict[str, Any]) -> bool:
        """Invalidate cached results for specific query."""
        if not self.enabled:
            return False

        cache_key = self._generate_cache_key(query_params)
        cache.delete(cache_key)
        return True
