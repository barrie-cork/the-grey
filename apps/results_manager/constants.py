"""
Constants for the results_manager app.

This module contains all constants used across results_manager services to avoid magic
numbers and strings in the codebase.
"""
from typing import Dict, List, Set


# MetadataConstants removed - simplified approach no longer needs complex metadata extraction


class DeduplicationConstants:
    """Constants for deduplication service."""
    
    # Similarity thresholds
    DEFAULT_SIMILARITY_THRESHOLD: float = 0.85
    TITLE_SIMILARITY_THRESHOLD: float = 0.9
    FUZZY_MATCH_THRESHOLD: float = 0.7
    CONTENT_HASH_THRESHOLD: float = 0.8
    
    # Confidence scores
    EXACT_URL_CONFIDENCE: float = 1.0
    
    # Text processing
    MIN_WORD_LENGTH: int = 2
    
    # URL normalization
    TRACKING_PARAMS: Set[str] = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
        'gclid', 'fbclid', 'msclkid', '_ga', 'ref', 'source'
    }
    
    # Stop words for title keyword extraction
    STOP_WORDS: Set[str] = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
        'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
        'to', 'was', 'were', 'will', 'with', 'this', 'these', 'they', 'been'
    }
    
    # URL prefixes to remove
    WWW_PREFIX: str = 'www.'
    
    # Default path
    DEFAULT_PATH: str = '/'


class QualityConstants:
    """Constants for quality assessment service."""
    
    # Default scores
    DEFAULT_RELEVANCE_SCORE: float = 0.5
    
    # Relevance score weights
    RELEVANCE_WEIGHTS: Dict[str, float] = {
        'title': 0.4,
        'snippet': 0.3,
        'url': 0.1,
        'recency': 0.1,
    }
    
    # Quality bonuses
    QUALITY_BONUSES: Dict[str, float] = {
        'is_pdf': 0.03,
    }
    
    # Publication recency
    RECENCY_DECAY_YEARS: int = 20
    
    # Quality scoring
    QUALITY_SCORES: Dict[str, int] = {
        'full_text_available': 20,
        'pdf_format': 15,
        'recent_publication': 15,
        'moderately_recent': 10,
        'good_title': 5,
        'good_snippet': 5
    }
    
    # Maximum quality score
    MAX_QUALITY_SCORE: int = 100
    
    # Publication year thresholds
    RECENT_PUBLICATION_THRESHOLD: int = 2020
    MODERATELY_RECENT_THRESHOLD: int = 2010
    
    # Content quality thresholds
    MIN_TITLE_LENGTH: int = 20
    MIN_SNIPPET_LENGTH: int = 50
    
    # Score bounds
    MIN_SCORE: float = 0.0
    MAX_SCORE: float = 1.0


class ProcessingConstants:
    """Constants for processing analytics service."""
    
    # Percentage calculations
    PERCENTAGE_MULTIPLIER: int = 100
    
    # Relevance thresholds
    RELEVANCE_THRESHOLDS: Dict[str, float] = {
        'high': 0.8,
        'medium': 0.5,
        'low': 0.0
    }
    
    # Priority scoring weights (simplified approach - no relevance scoring)
    PRIORITY_WEIGHTS: Dict[str, int] = {
        'not_duplicate': 40,
        'very_recent': 25,  # >= 2020
        'recent': 15,       # >= 2015
        'is_pdf': 20
    }
    
    # Publication year thresholds for priority scoring
    PRIORITY_YEAR_THRESHOLDS: Dict[str, int] = {
        'very_recent': 2020,
        'recent': 2015
    }
    
    # Default limits
    DEFAULT_PRIORITIZATION_LIMIT: int = 50
    
    # Decimal precision
    DECIMAL_PLACES: Dict[str, int] = {
        'relevance': 3,
        'percentage': 1
    }
    
    # Empty statistics default
    EMPTY_STATS_DEFAULTS: Dict[str, any] = {
        'total_results': 0,
        'processed_results': 0,
        'duplicate_groups': 0,
        'unique_results': 0,
        'average_relevance': 0,
        'document_types': {},
        'publication_years': {},
        'pdf_count': 0,
        'academic_results': 0,
        'pdf_percentage': 0,
        'academic_percentage': 0
    }
    
    # Quality distribution categories
    QUALITY_CATEGORIES: List[str] = ['high', 'medium', 'low']
    
    # Sample result limit per document type
    SAMPLE_RESULTS_LIMIT: int = 3