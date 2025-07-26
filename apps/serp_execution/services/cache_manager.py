"""
Cache management for SERP execution results.
Implements intelligent caching with TTL strategies.
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Manages caching of search results to reduce API costs and improve performance.
    Implements different TTL strategies based on query characteristics.
    """

    # Cache key prefixes
    PREFIX_SEARCH = "serp_search"
    PREFIX_STATS = "serp_stats"
    PREFIX_USAGE = "serp_usage"

    # TTL strategies (in seconds)
    TTL_RECENT = 3600  # 1 hour for very recent searches
    TTL_STANDARD = 86400  # 24 hours for standard searches
    TTL_HISTORICAL = 604800  # 7 days for historical searches
    TTL_STATIC = 2592000  # 30 days for static content

    def __init__(self):
        """Initialize cache manager with configuration."""
        self.enabled = getattr(settings, "SERP_CACHE_ENABLED", True)
        self.default_ttl = getattr(settings, "SERP_CACHE_TTL", self.TTL_STANDARD)

    def _generate_cache_key(self, prefix: str, params: Dict[str, Any]) -> str:
        """
        Generate a unique cache key from parameters.

        Args:
            prefix: Cache key prefix
            params: Parameters to hash

        Returns:
            Unique cache key
        """
        # Sort parameters for consistent hashing
        sorted_params = json.dumps(params, sort_keys=True)
        hash_digest = hashlib.md5(sorted_params.encode()).hexdigest()
        return f"{prefix}:{hash_digest}"

    def _determine_ttl(self, query_params: Dict[str, Any]) -> int:
        """
        Determine appropriate TTL based on query characteristics.

        Args:
            query_params: Query parameters

        Returns:
            TTL in seconds
        """
        # Recent date ranges get shorter TTL
        if "date_from" in query_params:
            try:
                date_from = datetime.fromisoformat(query_params["date_from"])
                days_old = (timezone.now().date() - date_from.date()).days

                if days_old < 7:
                    return self.TTL_RECENT
                elif days_old < 30:
                    return self.TTL_STANDARD
                else:
                    return self.TTL_HISTORICAL
            except (ValueError, TypeError):
                pass

        # File type searches are more static
        if "file_types" in query_params and query_params["file_types"]:
            return self.TTL_HISTORICAL

        # Default TTL
        return self.default_ttl

    def get_search_results(
        self, query_params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached search results if available.

        Args:
            query_params: Search query parameters

        Returns:
            Cached results or None
        """
        if not self.enabled:
            return None

        cache_key = self._generate_cache_key(self.PREFIX_SEARCH, query_params)

        try:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for query: {query_params.get('q', '')[:50]}...")
                # Update hit statistics
                self._increment_cache_stats("hits")
                return cached_data
            else:
                self._increment_cache_stats("misses")
                return None
        except Exception as e:
            logger.error(f"Error retrieving from cache: {str(e)}")
            return None

    def set_search_results(
        self,
        query_params: Dict[str, Any],
        results: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Cache search results with appropriate TTL.

        Args:
            query_params: Search query parameters
            results: Search results to cache
            metadata: Additional metadata to store

        Returns:
            Success status
        """
        if not self.enabled:
            return False

        cache_key = self._generate_cache_key(self.PREFIX_SEARCH, query_params)
        ttl = self._determine_ttl(query_params)

        # Prepare cache data
        cache_data = {
            "results": results,
            "metadata": metadata or {},
            "cached_at": timezone.now().isoformat(),
            "ttl": ttl,
            "query_params": query_params,
        }

        try:
            cache.set(cache_key, cache_data, ttl)
            logger.info(
                f"Cached results for query: {query_params.get('q', '')[:50]}... "
                f"(TTL: {ttl} seconds)"
            )
            self._increment_cache_stats("sets")
            return True
        except Exception as e:
            logger.error(f"Error setting cache: {str(e)}")
            return False

    def invalidate_search_results(self, query_params: Dict[str, Any]) -> bool:
        """
        Invalidate cached results for specific query.

        Args:
            query_params: Search query parameters

        Returns:
            Success status
        """
        if not self.enabled:
            return False

        cache_key = self._generate_cache_key(self.PREFIX_SEARCH, query_params)

        try:
            cache.delete(cache_key)
            logger.info(
                f"Invalidated cache for query: {query_params.get('q', '')[:50]}..."
            )
            return True
        except Exception as e:
            logger.error(f"Error invalidating cache: {str(e)}")
            return False

    def invalidate_session_cache(self, session_id: str) -> int:
        """
        Invalidate all cached results for a session.

        Args:
            session_id: Search session ID

        Returns:
            Number of keys invalidated
        """
        # This would require pattern-based deletion which Redis supports
        # but Django's cache abstraction doesn't directly expose
        # For now, return 0 as placeholder
        logger.info(f"Session cache invalidation requested for: {session_id}")
        return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache performance statistics.

        Returns:
            Dictionary of cache statistics
        """
        stats_key = f"{self.PREFIX_STATS}:global"
        stats = cache.get(stats_key) or {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "invalidations": 0,
            "last_reset": timezone.now().isoformat(),
        }

        # Calculate hit rate
        total_requests = stats["hits"] + stats["misses"]
        hit_rate = (stats["hits"] / total_requests * 100) if total_requests > 0 else 0

        stats["hit_rate"] = round(hit_rate, 2)
        stats["total_requests"] = total_requests

        return stats

    def reset_cache_stats(self) -> bool:
        """
        Reset cache statistics.

        Returns:
            Success status
        """
        stats_key = f"{self.PREFIX_STATS}:global"

        try:
            cache.set(
                stats_key,
                {
                    "hits": 0,
                    "misses": 0,
                    "sets": 0,
                    "invalidations": 0,
                    "last_reset": timezone.now().isoformat(),
                },
                None,
            )  # No expiration
            return True
        except Exception as e:
            logger.error(f"Error resetting cache stats: {str(e)}")
            return False

    def _increment_cache_stats(self, stat_type: str) -> None:
        """
        Increment a cache statistic counter.

        Args:
            stat_type: Type of statistic to increment
        """
        stats_key = f"{self.PREFIX_STATS}:global"

        try:
            stats = cache.get(stats_key) or {
                "hits": 0,
                "misses": 0,
                "sets": 0,
                "invalidations": 0,
                "last_reset": timezone.now().isoformat(),
            }

            if stat_type in stats:
                stats[stat_type] += 1
                cache.set(stats_key, stats, None)  # No expiration
        except Exception as e:
            logger.error(f"Error incrementing cache stat {stat_type}: {str(e)}")

    def estimate_cache_savings(self) -> Dict[str, Any]:
        """
        Estimate cost savings from cache usage.

        Returns:
            Dictionary with savings estimates
        """
        stats = self.get_cache_stats()

        # Assuming $0.001 per API call
        cost_per_call = 0.001
        saved_calls = stats["hits"]

        return {
            "saved_api_calls": saved_calls,
            "estimated_savings_usd": round(saved_calls * cost_per_call, 4),
            "cache_efficiency_percent": stats["hit_rate"],
        }
