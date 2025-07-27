"""
Simplified performance analytics service for reporting slice.
Business capability: Basic search performance metrics.
"""

from typing import Any, Dict

from apps.core.logging import ServiceLoggerMixin
from apps.results_manager.models import ProcessedResult
from apps.review_results.models import SimpleReviewDecision
from apps.serp_execution.models import SearchExecution


class PerformanceAnalyticsService(ServiceLoggerMixin):
    """Service for calculating basic search performance metrics."""

    def calculate_search_performance_metrics(self, session_id: str) -> Dict[str, Any]:
        """
        Calculate basic performance metrics for the search strategy.

        Args:
            session_id: UUID of the SearchSession

        Returns:
            Dictionary with basic performance metrics
        """
        # Basic execution counts
        total_executions = SearchExecution.objects.filter(
            query__session_id=session_id
        ).count()
        
        successful_executions = SearchExecution.objects.filter(
            query__session_id=session_id, status="completed"
        ).count()
        
        # Result counts
        unique_processed = ProcessedResult.objects.filter(
            session_id=session_id
        ).count()
        
        # Review counts
        include_count = SimpleReviewDecision.objects.filter(
            result__session_id=session_id, tag__name="Include"
        ).count()

        exclude_count = SimpleReviewDecision.objects.filter(
            result__session_id=session_id, tag__name="Exclude"
        ).count()

        # Simple calculations with safe division
        success_rate = (
            round((successful_executions / total_executions) * 100, 1)
            if total_executions > 0 else 0
        )
        
        precision = (
            round((include_count / (include_count + exclude_count)) * 100, 1)
            if (include_count + exclude_count) > 0 else 0
        )

        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": success_rate,
            "total_processed": unique_processed,
            "include_count": include_count,
            "exclude_count": exclude_count,
            "precision": precision,
        }

