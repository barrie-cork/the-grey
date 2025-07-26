"""
Performance analytics service for reporting slice.
Business capability: Search performance metrics and analytics.
"""

from typing import Any, Dict

from apps.core.logging import ServiceLoggerMixin
from apps.reporting.constants import PerformanceConstants
from apps.results_manager.models import ProcessedResult
from apps.review_results.models import SimpleReviewDecision
from apps.serp_execution.models import SearchExecution


class PerformanceAnalyticsService(ServiceLoggerMixin):
    """Service for calculating search performance metrics and analytics."""

    def calculate_search_performance_metrics(self, session_id: str) -> Dict[str, Any]:
        """
        Calculate performance metrics for the search strategy.

        Args:
            session_id: UUID of the SearchSession

        Returns:
            Dictionary with performance metrics
        """
        executions = SearchExecution.objects.filter(query__session_id=session_id)
        processed_results = ProcessedResult.objects.filter(session_id=session_id)

        # Basic metrics
        total_executions = executions.count()
        successful_executions = executions.filter(
            status=PerformanceConstants.COMPLETED_STATUS
        ).count()
        total_raw_results = sum(e.results_count for e in executions)
        unique_processed = processed_results.count()

        # Review metrics
        include_count = SimpleReviewDecision.objects.filter(
            result__session_id=session_id, tag__name=PerformanceConstants.INCLUDE_TAG
        ).count()

        exclude_count = SimpleReviewDecision.objects.filter(
            result__session_id=session_id, tag__name=PerformanceConstants.EXCLUDE_TAG
        ).count()

        # Performance calculations
        metrics = {
            "search_efficiency": {
                "success_rate": round(
                    successful_executions
                    / max(total_executions, PerformanceConstants.MIN_DIVISOR)
                    * PerformanceConstants.PERCENTAGE_MULTIPLIER,
                    PerformanceConstants.DECIMAL_PLACES["percentage"],
                ),
                "deduplication_rate": round(
                    (total_raw_results - unique_processed)
                    / max(total_raw_results, PerformanceConstants.MIN_DIVISOR)
                    * PerformanceConstants.PERCENTAGE_MULTIPLIER,
                    PerformanceConstants.DECIMAL_PLACES["percentage"],
                ),
                "processing_rate": round(
                    unique_processed
                    / max(total_raw_results, PerformanceConstants.MIN_DIVISOR)
                    * PerformanceConstants.PERCENTAGE_MULTIPLIER,
                    PerformanceConstants.DECIMAL_PLACES["percentage"],
                ),
            },
            "relevance_metrics": {
                "precision": round(
                    include_count
                    / max(
                        include_count + exclude_count, PerformanceConstants.MIN_DIVISOR
                    )
                    * PerformanceConstants.PERCENTAGE_MULTIPLIER,
                    PerformanceConstants.DECIMAL_PLACES["percentage"],
                ),
                "inclusion_rate": round(
                    include_count
                    / max(unique_processed, PerformanceConstants.MIN_DIVISOR)
                    * PerformanceConstants.PERCENTAGE_MULTIPLIER,
                    PerformanceConstants.DECIMAL_PLACES["percentage"],
                ),
            },
        }

        return metrics

