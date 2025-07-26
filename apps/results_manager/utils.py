"""
Utility functions for the results_manager app.

This module contains helper functions for result processing.
Business logic has been moved to dedicated services.
"""

from typing import Dict, List, Optional, Tuple, Any, Set
from django.db.models import QuerySet

# Service imports for backward compatibility
from .services.deduplication_service import DeduplicationService
from .services.quality_assessment_service import QualityAssessmentService
from .services.processing_analytics_service import ProcessingAnalyticsService

# Initialize services for backward compatibility
deduplication_service = DeduplicationService()
quality_assessment_service = QualityAssessmentService()
processing_analytics_service = ProcessingAnalyticsService()

# Legacy function proxies for backward compatibility
normalize_url = deduplication_service.normalize_url
calculate_similarity_score = deduplication_service.calculate_similarity_score
extract_title_keywords = deduplication_service.extract_title_keywords
detect_duplicates = deduplication_service.detect_duplicates
check_duplicate_methods = deduplication_service.check_duplicate_methods
calculate_relevance_score = quality_assessment_service.calculate_relevance_score
get_processing_statistics = processing_analytics_service.get_processing_statistics
prioritize_results_for_review = processing_analytics_service.prioritize_results_for_review
export_results_summary = processing_analytics_service.export_results_summary