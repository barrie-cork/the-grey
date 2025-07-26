"""
Utility functions for the review_results app.

This module contains helper functions for result review management.
Business logic has been moved to dedicated services.
"""

from typing import Dict, List, Optional, Tuple, Any
from django.db.models import QuerySet
from django.contrib.auth import get_user_model

User = get_user_model()

# Service imports for backward compatibility
from .services.review_progress_service import ReviewProgressService
from .services.review_recommendation_service import ReviewRecommendationService
from .services.tagging_management_service import TaggingManagementService
from .services.review_analytics_service import ReviewAnalyticsService

# Initialize services for backward compatibility
review_progress_service = ReviewProgressService()
review_recommendation_service = ReviewRecommendationService()
tagging_management_service = TaggingManagementService()
review_analytics_service = ReviewAnalyticsService()

# Legacy function proxies for backward compatibility
calculate_review_progress = review_progress_service.calculate_review_progress
calculate_review_velocity = review_progress_service.calculate_review_velocity
get_review_recommendations = review_recommendation_service.get_review_recommendations
get_similar_results = review_recommendation_service.get_similar_results
get_tag_usage_statistics = tagging_management_service.get_tag_usage_statistics
bulk_tag_results = tagging_management_service.bulk_tag_results
export_review_data = review_analytics_service.export_review_data
validate_review_completeness = review_analytics_service.validate_review_completeness