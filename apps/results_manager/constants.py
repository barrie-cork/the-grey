"""
Constants for the results_manager app.

Simplified constants for essential processing functionality.
"""

from typing import Dict, Set


class DeduplicationConstants:
    """Simplified constants for deduplication service."""

    # Basic similarity threshold
    DEFAULT_SIMILARITY_THRESHOLD: float = 0.85

    # URL normalization - common tracking parameters to remove
    TRACKING_PARAMS: Set[str] = {
        "utm_source",
        "utm_medium", 
        "utm_campaign",
        "gclid",
        "fbclid",
        "ref",
    }



class ProcessingConstants:
    """Simplified constants for basic processing."""

    # Default batch size for processing
    DEFAULT_BATCH_SIZE: int = 50

    # Basic statistics defaults
    EMPTY_STATS_DEFAULTS: Dict[str, any] = {
        "total_results": 0,
        "processed_results": 0,
        "duplicate_groups": 0,
        "unique_results": 0,
    }

