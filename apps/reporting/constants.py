"""
Constants for the reporting app.

This module contains all constants used across reporting services to avoid magic
numbers and strings in the codebase.
"""
from typing import Dict, List


class ExportConstants:
    """Constants for export service."""
    
    # Content types mapping
    CONTENT_TYPES: Dict[str, str] = {
        'json': 'application/json',
        'csv': 'text/csv',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'bibtex': 'application/x-bibtex'
    }
    
    # Default content type for unknown formats
    DEFAULT_CONTENT_TYPE: str = 'application/octet-stream'
    
    # File size estimation multipliers
    SIZE_MULTIPLIERS: Dict[str, float] = {
        'json': 1.0,
        'csv': 0.7,
        'xlsx': 1.5,
        'pdf': 2.0,
        'docx': 1.8,
        'bibtex': 0.8
    }
    
    # Default size multiplier
    DEFAULT_SIZE_MULTIPLIER: float = 1.0
    
    # CSV export field names
    STUDY_CSV_FIELDS: List[str] = [
        'id', 'title', 'authors', 'publication_year', 'document_type',
        'url', 'has_full_text'
    ]
    
    QUERY_CSV_FIELDS: List[str] = [
        'id', 'query_string', 'population', 'interest', 'context',
        'search_engines', 'total_results', 'success_rate'
    ]
    
    # BibTeX type mapping
    BIBTEX_TYPE_MAPPING: Dict[str, str] = {
        'journal_article': 'article',
        'report': 'techreport',
        'thesis': 'phdthesis',
        'working_paper': 'unpublished',
        'book': 'book',
        'conference': 'inproceedings',
        'pdf': 'misc'
    }
    
    # Default BibTeX type
    DEFAULT_BIBTEX_TYPE: str = 'misc'
    
    # Export type names
    EXPORT_TYPE_NAMES: Dict[str, str] = {
        'prisma_flow': 'PRISMA Flow Diagram',
        'study_characteristics': 'Study Characteristics Table',
        'search_strategy': 'Search Strategy Report',
        'bibliography': 'Bibliography'
    }
    
    # Available formats per export type
    EXPORT_FORMATS: Dict[str, List[str]] = {
        'prisma_flow': ['json', 'pdf', 'docx'],
        'study_characteristics': ['csv', 'xlsx', 'json'],
        'search_strategy': ['json', 'pdf', 'docx'],
        'bibliography': ['bibtex', 'csv', 'json']
    }


class PerformanceConstants:
    """Constants for performance analytics service."""
    
    # Time period labels
    TIME_PERIODS: Dict[str, int] = {
        'last_hour': 1,
        'last_24_hours': 24,
        'last_week': 168,
        'last_month': 720
    }
    
    # Performance thresholds
    RESPONSE_TIME_THRESHOLDS: Dict[str, float] = {
        'excellent': 1.0,    # < 1 second
        'good': 3.0,        # < 3 seconds
        'acceptable': 5.0,  # < 5 seconds
        'poor': 10.0        # < 10 seconds
    }
    
    # Success rate thresholds
    SUCCESS_RATE_THRESHOLDS: Dict[str, float] = {
        'excellent': 0.95,   # >= 95%
        'good': 0.90,       # >= 90%
        'acceptable': 0.80, # >= 80%
        'poor': 0.70        # >= 70%
    }
    
    # Cache TTL (in seconds)
    CACHE_TTL: Dict[str, int] = {
        'real_time': 60,         # 1 minute
        'short_term': 300,       # 5 minutes
        'medium_term': 3600,     # 1 hour
        'long_term': 86400       # 24 hours
    }
    
    # Percentage calculation
    PERCENTAGE_MULTIPLIER: int = 100
    
    # Decimal precision
    DECIMAL_PLACES: Dict[str, int] = {
        'percentage': 1,
        'cost': 4,
        'time': 1,
        'ratio': 2
    }
    
    # Default minimum divisor to avoid division by zero
    MIN_DIVISOR: int = 1
    
    # Tag names for metrics
    INCLUDE_TAG: str = 'Include'
    EXCLUDE_TAG: str = 'Exclude'
    
    # Execution status
    COMPLETED_STATUS: str = 'completed'
    
    # Recommendation thresholds
    SUCCESS_RATE_THRESHOLD: float = 90.0
    PRECISION_THRESHOLD: float = 50.0
    COST_PER_STUDY_THRESHOLD: float = 1.0
    ENGINE_PERFORMANCE_DIFF_THRESHOLD: float = 20.0
    
    # Priority levels
    PRIORITY_HIGH: str = 'high'
    PRIORITY_MEDIUM: str = 'medium'
    PRIORITY_LOW: str = 'low'
    
    # Recommendation categories
    RECOMMENDATION_CATEGORIES: List[str] = [
        'execution_reliability',
        'search_precision',
        'cost_optimization',
        'engine_optimization'
    ]
    
    # Max priority actions to show
    MAX_PRIORITY_ACTIONS: int = 3


class PRISMAConstants:
    """Constants for PRISMA reporting service."""
    
    # PRISMA flow stages
    FLOW_STAGES: List[str] = [
        'identification',
        'screening',
        'eligibility',
        'included'
    ]
    
    # Record sources
    RECORD_SOURCES: List[str] = [
        'database_searches',
        'other_sources',
        'duplicates_removed',
        'records_screened',
        'records_excluded',
        'full_text_assessed',
        'full_text_excluded',
        'studies_included'
    ]
    
    # Exclusion reasons
    EXCLUSION_REASONS: List[str] = [
        'not_grey_literature',
        'wrong_population',
        'wrong_intervention',
        'wrong_outcome',
        'wrong_study_design',
        'duplicate',
        'language',
        'no_full_text'
    ]
    
    # PRISMA checklist items
    CHECKLIST_SECTIONS: Dict[str, List[str]] = {
        'title': ['title', 'abstract'],
        'introduction': ['rationale', 'objectives'],
        'methods': ['protocol', 'eligibility', 'sources', 'search', 'selection', 'data_collection'],
        'results': ['selection', 'characteristics', 'risk_of_bias', 'results_individual', 'synthesis'],
        'discussion': ['summary', 'limitations', 'conclusions']
    }
    
    # Standardized exclusion reasons
    STANDARD_EXCLUSION_REASONS: Dict[str, str] = {
        'not_relevant': 'Not relevant to research question',
        'no_full_text': 'Full text unavailable',
        'duplicate': 'Duplicate study',
        'wrong_study_type': 'Inappropriate study design',
        'language': 'Language other than English'
    }
    
    # Tag names
    EXCLUDE_TAG: str = 'Exclude'
    
    # Checklist completion
    MIN_DESCRIPTION_LENGTH: int = 100
    PERCENTAGE_MULTIPLIER: int = 100


class StudyAnalysisConstants:
    """Constants for study analysis service."""
    
    # Document quality indicators
    QUALITY_INDICATORS: List[str] = [
        'has_abstract',
        'has_methodology',
        'has_references',
        'has_author_info',
        'has_publication_date',
        'has_doi',
        'peer_reviewed'
    ]
    
    # Quality score weights
    QUALITY_WEIGHTS: Dict[str, float] = {
        'has_abstract': 0.15,
        'has_methodology': 0.20,
        'has_references': 0.15,
        'has_author_info': 0.10,
        'has_publication_date': 0.10,
        'has_doi': 0.15,
        'peer_reviewed': 0.15
    }
    
    # Document type priorities
    DOCUMENT_TYPE_PRIORITY: Dict[str, int] = {
        'journal_article': 1,
        'report': 2,
        'thesis': 3,
        'working_paper': 4,
        'conference': 5,
        'book': 6,
        'pdf': 7,
        'website': 8,
        'blog_post': 9,
        'other': 10
    }
    
    # Analysis thresholds
    THRESHOLDS: Dict[str, float] = {
        'high_quality': 0.8,
        'medium_quality': 0.6,
        'low_quality': 0.4,
        'relevance_threshold': 0.7,
        'confidence_threshold': 0.75
    }
    
    # Time periods for recency analysis (in years)
    RECENCY_PERIODS: Dict[str, int] = {
        'recent': 5,
        'fairly_recent': 10
    }
    
    # Domain to country mapping for geographical analysis
    DOMAIN_TO_COUNTRY: Dict[str, str] = {
        '.gov': 'United States',
        '.edu': 'United States',
        '.uk': 'United Kingdom',
        '.ca': 'Canada',
        '.au': 'Australia',
        '.de': 'Germany',
        '.fr': 'France',
        '.nl': 'Netherlands',
        'europa.eu': 'European Union',
        'who.int': 'International'
    }


class SearchStrategyConstants:
    """Constants for search strategy reporting service."""
    
    # PIC framework components
    PIC_COMPONENTS: List[str] = ['population', 'interest', 'context']
    
    # Search engine names
    SEARCH_ENGINES: Dict[str, str] = {
        'google': 'Google Search',
        'google_scholar': 'Google Scholar',
        'bing': 'Bing Search',
        'base': 'BASE',
        'core': 'CORE',
        'oaister': 'OAIster'
    }
    
    # Query effectiveness metrics
    EFFECTIVENESS_METRICS: List[str] = [
        'precision',
        'recall',
        'f1_score',
        'coverage_score'
    ]
    
    # Report sections
    REPORT_SECTIONS: List[str] = [
        'executive_summary',
        'search_objectives',
        'methodology',
        'search_strings',
        'sources_searched',
        'inclusion_criteria',
        'exclusion_criteria',
        'results_summary',
        'quality_assessment',
        'recommendations'
    ]
    
    # Analysis limits
    TOP_ENGINES_LIMIT: int = 3