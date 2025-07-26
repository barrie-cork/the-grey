"""
Utility functions for the results_manager app.

This module contains helper functions for result processing.
Business logic has been moved to dedicated services.
"""

# Legacy function proxies for backward compatibility - no type hints needed

# Service imports for backward compatibility
from .services.deduplication_service import DeduplicationService
from .services.processing_analytics_service import ProcessingAnalyticsService
from .services.quality_assessment_service import QualityAssessmentService

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
get_processing_statistics = processing_analytics_service.get_processing_statistics
get_results_for_review = processing_analytics_service.get_results_for_review
export_results_summary = processing_analytics_service.export_results_summary
