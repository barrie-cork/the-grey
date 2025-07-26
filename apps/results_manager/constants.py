"""
Constants for the results_manager app.

Simplified constants for essential processing functionality.
"""

from typing import Dict, Set


class DeduplicationConstants:
    """Constants for deduplication service."""

    # Basic similarity threshold
    DEFAULT_SIMILARITY_THRESHOLD: float = 0.85
    
    # URL normalization - tracking parameters to remove
    TRACKING_PARAMS: Set[str] = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "gclid", "fbclid", "ref", "source", "medium", "campaign"
    }



class ProcessingConstants:
    """Constants for processing services."""

    # Batch processing
    DEFAULT_BATCH_SIZE: int = 50
    
    # Statistics defaults
    EMPTY_STATS_DEFAULTS: Dict[str, int] = {
        "total_results": 0,
        "processed_results": 0,
        "duplicate_groups": 0,
        "unique_results": 0,
        "document_types": {},
        "publication_years": {},
        "pdf_count": 0
    }


