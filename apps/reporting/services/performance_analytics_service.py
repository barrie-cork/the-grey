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
                "number_needed_to_read": round(
                    unique_processed
                    / max(include_count, PerformanceConstants.MIN_DIVISOR),
                    PerformanceConstants.DECIMAL_PLACES["ratio"],
                ),
            },
            "cost_effectiveness": {
                "total_cost": sum(e.estimated_cost for e in executions),
                "cost_per_result": round(
                    float(sum(e.estimated_cost for e in executions))
                    / max(unique_processed, PerformanceConstants.MIN_DIVISOR),
                    PerformanceConstants.DECIMAL_PLACES["cost"],
                ),
                "cost_per_included_study": (
                    round(
                        float(sum(e.estimated_cost for e in executions))
                        / max(include_count, PerformanceConstants.MIN_DIVISOR),
                        PerformanceConstants.DECIMAL_PLACES["cost"],
                    )
                    if include_count > 0
                    else 0
                ),
            },
            "time_efficiency": {
                "avg_execution_time": round(
                    sum(e.duration_seconds or 0 for e in executions)
                    / max(successful_executions, PerformanceConstants.MIN_DIVISOR),
                    PerformanceConstants.DECIMAL_PLACES["time"],
                ),
                "total_execution_time": sum(
                    e.duration_seconds or 0 for e in executions
                ),
            },
        }

        return metrics

    def calculate_engine_comparison_metrics(self, session_id: str) -> Dict[str, Any]:
        """
        Compare performance metrics across different search engines.

        Args:
            session_id: UUID of the SearchSession

        Returns:
            Dictionary with engine comparison metrics
        """
        executions = SearchExecution.objects.filter(query__session_id=session_id)

        engine_metrics = {}

        for execution in executions:
            engine = execution.search_engine

            if engine not in engine_metrics:
                engine_metrics[engine] = {
                    "total_executions": 0,
                    "successful_executions": 0,
                    "total_results": 0,
                    "total_cost": 0,
                    "total_time": 0,
                    "unique_results": 0,
                }

            metrics = engine_metrics[engine]
            metrics["total_executions"] += 1

            if execution.status == PerformanceConstants.COMPLETED_STATUS:
                metrics["successful_executions"] += 1
                metrics["total_results"] += execution.results_count
                metrics["total_cost"] += float(execution.estimated_cost)
                metrics["total_time"] += execution.duration_seconds or 0

        # Calculate derived metrics
        for engine, metrics in engine_metrics.items():
            total_exec = metrics["total_executions"]
            successful_exec = metrics["successful_executions"]

            metrics["success_rate"] = round(
                successful_exec
                / max(total_exec, PerformanceConstants.MIN_DIVISOR)
                * PerformanceConstants.PERCENTAGE_MULTIPLIER,
                PerformanceConstants.DECIMAL_PLACES["percentage"],
            )
            metrics["avg_results_per_execution"] = round(
                metrics["total_results"]
                / max(successful_exec, PerformanceConstants.MIN_DIVISOR),
                PerformanceConstants.DECIMAL_PLACES["ratio"],
            )
            metrics["avg_cost_per_execution"] = round(
                metrics["total_cost"]
                / max(successful_exec, PerformanceConstants.MIN_DIVISOR),
                PerformanceConstants.DECIMAL_PLACES["cost"],
            )
            metrics["avg_time_per_execution"] = round(
                metrics["total_time"]
                / max(successful_exec, PerformanceConstants.MIN_DIVISOR),
                PerformanceConstants.DECIMAL_PLACES["time"],
            )

            # Cost effectiveness
            metrics["cost_per_result"] = round(
                metrics["total_cost"]
                / max(metrics["total_results"], PerformanceConstants.MIN_DIVISOR),
                PerformanceConstants.DECIMAL_PLACES["cost"],
            )

        return engine_metrics

    def calculate_temporal_performance(self, session_id: str) -> Dict[str, Any]:
        """
        Analyze performance metrics over time.

        Args:
            session_id: UUID of the SearchSession

        Returns:
            Dictionary with temporal performance analysis
        """
        executions = SearchExecution.objects.filter(
            query__session_id=session_id
        ).order_by("created_at")

        if not executions.exists():
            return {"total_executions": 0}

        # Group by day
        daily_metrics = {}

        for execution in executions:
            date_key = execution.created_at.date().isoformat()

            if date_key not in daily_metrics:
                daily_metrics[date_key] = {
                    "executions": 0,
                    "successful": 0,
                    "results": 0,
                    "cost": 0,
                    "avg_time": 0,
                    "times": [],
                }

            metrics = daily_metrics[date_key]
            metrics["executions"] += 1

            if execution.status == PerformanceConstants.COMPLETED_STATUS:
                metrics["successful"] += 1
                metrics["results"] += execution.results_count
                metrics["cost"] += float(execution.estimated_cost)

                if execution.duration_seconds:
                    metrics["times"].append(execution.duration_seconds)

        # Calculate averages for each day
        for date_key, metrics in daily_metrics.items():
            if metrics["times"]:
                metrics["avg_time"] = round(
                    sum(metrics["times"]) / len(metrics["times"]),
                    PerformanceConstants.DECIMAL_PLACES["time"],
                )

            metrics["success_rate"] = round(
                metrics["successful"]
                / max(metrics["executions"], PerformanceConstants.MIN_DIVISOR)
                * PerformanceConstants.PERCENTAGE_MULTIPLIER,
                PerformanceConstants.DECIMAL_PLACES["percentage"],
            )

            # Remove raw times array for cleaner output
            del metrics["times"]

        return {
            "session_id": session_id,
            "daily_metrics": daily_metrics,
            "date_range": {
                "start": min(daily_metrics.keys()),
                "end": max(daily_metrics.keys()),
            },
        }

    def generate_efficiency_recommendations(self, session_id: str) -> Dict[str, Any]:
        """
        Generate recommendations for improving search efficiency.

        Args:
            session_id: UUID of the SearchSession

        Returns:
            Dictionary with efficiency recommendations
        """
        performance_metrics = self.calculate_search_performance_metrics(session_id)
        engine_comparison = self.calculate_engine_comparison_metrics(session_id)

        recommendations = {
            "session_id": session_id,
            "recommendations": [],
            "priority_actions": [],
            "performance_summary": performance_metrics,
        }

        # Analyze success rate
        success_rate = performance_metrics["search_efficiency"]["success_rate"]
        if success_rate < PerformanceConstants.SUCCESS_RATE_THRESHOLD:
            recommendations["recommendations"].append(
                {
                    "category": PerformanceConstants.RECOMMENDATION_CATEGORIES[
                        0
                    ],  # execution_reliability
                    "priority": PerformanceConstants.PRIORITY_HIGH,
                    "issue": f"Low execution success rate ({success_rate}%)",
                    "recommendation": "Review failed executions and implement retry strategies",
                }
            )

        # Analyze precision
        precision = performance_metrics["relevance_metrics"]["precision"]
        if precision < PerformanceConstants.PRECISION_THRESHOLD:
            recommendations["recommendations"].append(
                {
                    "category": PerformanceConstants.RECOMMENDATION_CATEGORIES[
                        1
                    ],  # search_precision
                    "priority": PerformanceConstants.PRIORITY_HIGH,
                    "issue": f"Low precision ({precision}%)",
                    "recommendation": "Refine search queries and add more specific exclusion criteria",
                }
            )

        # Analyze cost effectiveness
        cost_per_study = performance_metrics["cost_effectiveness"][
            "cost_per_included_study"
        ]
        if cost_per_study > PerformanceConstants.COST_PER_STUDY_THRESHOLD:
            recommendations["recommendations"].append(
                {
                    "category": PerformanceConstants.RECOMMENDATION_CATEGORIES[
                        2
                    ],  # cost_optimization
                    "priority": PerformanceConstants.PRIORITY_MEDIUM,
                    "issue": f"High cost per included study (${cost_per_study})",
                    "recommendation": "Optimize query parameters and consider engine selection",
                }
            )

        # Engine recommendations
        if engine_comparison:
            best_engine = max(
                engine_comparison.items(), key=lambda x: x[1]["success_rate"]
            )
            worst_engine = min(
                engine_comparison.items(), key=lambda x: x[1]["success_rate"]
            )

            if (
                best_engine[1]["success_rate"] - worst_engine[1]["success_rate"]
                > PerformanceConstants.ENGINE_PERFORMANCE_DIFF_THRESHOLD
            ):
                recommendations["recommendations"].append(
                    {
                        "category": PerformanceConstants.RECOMMENDATION_CATEGORIES[
                            3
                        ],  # engine_optimization
                        "priority": PerformanceConstants.PRIORITY_MEDIUM,
                        "issue": f"Significant performance difference between engines",
                        "recommendation": f"Consider using {best_engine[0]} more frequently and reducing use of {worst_engine[0]}",
                    }
                )

        # Priority actions
        high_priority = [
            r
            for r in recommendations["recommendations"]
            if r["priority"] == PerformanceConstants.PRIORITY_HIGH
        ]
        recommendations["priority_actions"] = high_priority[
            : PerformanceConstants.MAX_PRIORITY_ACTIONS
        ]

        return recommendations
