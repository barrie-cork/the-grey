"""
Monitoring and performance analysis service for serp_execution slice.
Business capability: Execution monitoring, failure analysis, and performance tracking.
"""

from decimal import Decimal
from typing import Any, Dict, List

from apps.core.logging import ServiceLoggerMixin


class MonitoringService(ServiceLoggerMixin):
    """Service for monitoring execution performance and analyzing failures."""

    def get_execution_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        Get comprehensive execution statistics for a session.

        Args:
            session_id: UUID of the SearchSession

        Returns:
            Dictionary containing execution statistics
        """
        from ..models import SearchExecution

        executions = SearchExecution.objects.filter(
            query__strategy__session_id=session_id
        )

        if not executions.exists():
            return self._empty_stats()

        counts = self._get_execution_counts(executions)
        aggregates = self._get_execution_aggregates(executions)
        success_rate = self._calculate_success_rate(
            counts["total_executions"], counts["successful_executions"]
        )

        return {
            **counts,
            "total_results": aggregates["total_results"] or 0,
            "total_cost": aggregates["total_cost"] or Decimal("0.00"),
            "average_execution_time": aggregates["avg_time"] or 0,
            "success_rate": round(success_rate, 1),
            "engines_used": list(
                executions.values_list("search_engine", flat=True).distinct()
            ),
            "last_execution_date": self._get_last_execution_date(executions),
        }

    def get_failed_executions_with_analysis(
        self, session_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get failed executions with failure analysis.

        Args:
            session_id: UUID of the SearchSession

        Returns:
            List of dictionaries with failure analysis
        """
        from ..models import SearchExecution

        failed_executions = SearchExecution.objects.filter(
            query__strategy__session_id=session_id, status="failed"
        ).order_by("-created_at")

        analyzed_failures = []

        for execution in failed_executions:
            analysis = {
                "execution_id": str(execution.id),
                "query_title": (
                    execution.query.query_string[:50] + "..."
                    if len(execution.query.query_string) > 50
                    else execution.query.query_string
                ),
                "search_engine": execution.search_engine,
                "error_message": execution.error_message,
                "retry_count": execution.retry_count,
                "can_retry": execution.can_retry(),
                "created_at": execution.created_at,
                "failure_category": self.categorize_failure(execution.error_message),
                "suggested_action": self.suggest_retry_action(execution),
            }
            analyzed_failures.append(analysis)

        return analyzed_failures

    def categorize_failure(self, error_message: str) -> str:
        """
        Categorize failure based on error message.

        Args:
            error_message: Error message from failed execution

        Returns:
            Failure category string
        """
        if not error_message:
            return "unknown"

        error_lower = error_message.lower()

        if "rate limit" in error_lower or "too many requests" in error_lower:
            return "rate_limit"
        elif "timeout" in error_lower or "timed out" in error_lower:
            return "timeout"
        elif "network" in error_lower or "connection" in error_lower:
            return "network"
        elif "api key" in error_lower or "authentication" in error_lower:
            return "authentication"
        elif "quota" in error_lower or "exceeded" in error_lower:
            return "quota_exceeded"
        else:
            return "api_error"

    def suggest_retry_action(self, execution) -> str:
        """
        Suggest action for retrying failed execution.

        Args:
            execution: Failed SearchExecution instance

        Returns:
            Suggested action string
        """
        if not execution.can_retry():
            return "Cannot retry - maximum attempts reached"

        category = self.categorize_failure(execution.error_message)

        actions = {
            "rate_limit": "Wait and retry automatically",
            "timeout": "Retry with longer timeout",
            "network": "Check connection and retry",
            "authentication": "Verify API credentials",
            "quota_exceeded": "Wait for quota reset",
            "api_error": "Contact support if persists",
            "unknown": "Retry with monitoring",
        }

        return actions.get(category, "Manual investigation required")

    def optimize_retry_strategy(self, execution) -> Dict[str, Any]:
        """
        Determine optimal retry strategy for failed execution.

        Args:
            execution: Failed SearchExecution instance

        Returns:
            Dictionary with retry strategy
        """
        strategy = {
            "should_retry": False,
            "delay_seconds": 0,
            "modifications": [],
            "priority": "low",
        }

        if not execution.can_retry():
            return strategy

        failure_category = self.categorize_failure(execution.error_message)

        # Strategy based on failure type
        if failure_category == "rate_limit":
            strategy.update(
                {
                    "should_retry": True,
                    "delay_seconds": min(
                        300 * (execution.retry_count + 1), 3600
                    ),  # Exponential backoff, max 1 hour
                    "priority": "medium",
                    "modifications": [
                        "Use exponential backoff",
                        "Consider alternative engine",
                    ],
                }
            )

        elif failure_category == "timeout":
            strategy.update(
                {
                    "should_retry": True,
                    "delay_seconds": 60,
                    "priority": "medium",
                    "modifications": ["Increase timeout", "Simplify query if complex"],
                }
            )

        elif failure_category == "network":
            strategy.update(
                {
                    "should_retry": True,
                    "delay_seconds": 120,
                    "priority": "high",
                    "modifications": [
                        "Check network connectivity",
                        "Use different endpoint",
                    ],
                }
            )

        elif failure_category in ["authentication", "quota_exceeded"]:
            strategy.update(
                {
                    "should_retry": False,
                    "priority": "high",
                    "modifications": ["Check API credentials", "Verify quota limits"],
                }
            )

        else:  # api_error or unknown
            strategy.update(
                {
                    "should_retry": execution.retry_count
                    < 2,  # More conservative for unknown errors
                    "delay_seconds": 300,
                    "priority": "low",
                    "modifications": ["Monitor closely", "Contact support if persists"],
                }
            )

        return strategy

    def get_engine_performance_comparison(
        self, session_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compare performance across different search engines.

        Args:
            session_id: UUID of the SearchSession

        Returns:
            Dictionary with engine performance comparison
        """
        from ..models import SearchExecution

        executions = SearchExecution.objects.filter(
            query__strategy__session_id=session_id
        )

        engines = {}

        for execution in executions:
            engine = execution.search_engine

            if engine not in engines:
                engines[engine] = {
                    "total_executions": 0,
                    "successful_executions": 0,
                    "failed_executions": 0,
                    "total_results": 0,
                    "total_cost": Decimal("0.00"),
                    "average_time": 0,
                    "success_rate": 0,
                    "average_results_per_execution": 0,
                }

            engines[engine]["total_executions"] += 1

            if execution.status == "completed":
                engines[engine]["successful_executions"] += 1
                engines[engine]["total_results"] += execution.results_count
                engines[engine]["total_cost"] += execution.estimated_cost

                if execution.duration_seconds:
                    # Calculate running average
                    current_avg = engines[engine]["average_time"]
                    count = engines[engine]["successful_executions"]
                    engines[engine]["average_time"] = (
                        (current_avg * (count - 1)) + execution.duration_seconds
                    ) / count

            elif execution.status == "failed":
                engines[engine]["failed_executions"] += 1

        # Calculate derived metrics
        for engine_data in engines.values():
            total = engine_data["total_executions"]
            successful = engine_data["successful_executions"]

            if total > 0:
                engine_data["success_rate"] = round((successful / total) * 100, 1)

            if successful > 0:
                engine_data["average_results_per_execution"] = round(
                    engine_data["total_results"] / successful, 1
                )

            # Round average time
            engine_data["average_time"] = round(engine_data["average_time"], 2)

        return engines

    def calculate_search_coverage(self, session_id: str) -> Dict[str, Any]:
        """
        Calculate search coverage and diversity metrics.

        Args:
            session_id: UUID of the SearchSession

        Returns:
            Dictionary with coverage metrics
        """
        from ..models import RawSearchResult
        from .content_analysis_service import ContentAnalysisService

        raw_results = RawSearchResult.objects.filter(
            execution__query__strategy__session_id=session_id
        )

        if not raw_results.exists():
            return {
                "total_results": 0,
                "unique_domains": 0,
                "domain_distribution": {},
                "content_type_distribution": {},
                "academic_percentage": 0,
                "pdf_percentage": 0,
                "date_coverage": {},
            }

        total_results = raw_results.count()
        content_analyzer = ContentAnalysisService()

        # Domain analysis
        domains = []
        content_types = {"webpage": 0, "pdf": 0, "news": 0, "other": 0}
        academic_count = 0
        pdf_count = 0
        dates = []

        for result in raw_results:
            # Domain extraction
            domain = result.get_domain()
            domains.append(domain)

            # Content type detection
            content_info = content_analyzer.detect_content_type(
                result.link, result.title, result.snippet
            )

            if content_info["is_pdf"]:
                content_types["pdf"] += 1
                pdf_count += 1
            elif content_info["is_news"]:
                content_types["news"] += 1
            else:
                content_types["webpage"] += 1

            if content_info["is_academic"]:
                academic_count += 1

            # Date analysis
            if result.detected_date:
                dates.append(result.detected_date.year)

        # Calculate metrics
        unique_domains = len(set(domains))
        domain_distribution = {domain: domains.count(domain) for domain in set(domains)}

        # Sort domain distribution by count
        domain_distribution = dict(
            sorted(domain_distribution.items(), key=lambda x: x[1], reverse=True)[:10]
        )

        academic_percentage = (
            (academic_count / total_results * 100) if total_results > 0 else 0
        )
        pdf_percentage = (pdf_count / total_results * 100) if total_results > 0 else 0

        # Date coverage
        date_coverage = {}
        if dates:
            date_distribution = {year: dates.count(year) for year in set(dates)}
            date_coverage = {
                "earliest_year": min(dates),
                "latest_year": max(dates),
                "year_distribution": dict(sorted(date_distribution.items())),
            }

        return {
            "total_results": total_results,
            "unique_domains": unique_domains,
            "domain_distribution": domain_distribution,
            "content_type_distribution": content_types,
            "academic_percentage": round(academic_percentage, 1),
            "pdf_percentage": round(pdf_percentage, 1),
            "date_coverage": date_coverage,
        }

    def get_execution_timeline(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get execution timeline for visualization.

        Args:
            session_id: UUID of the SearchSession

        Returns:
            List of timeline events
        """
        from ..models import SearchExecution

        executions = (
            SearchExecution.objects.filter(query__strategy__session_id=session_id)
            .select_related("query")
            .order_by("created_at")
        )

        timeline = []

        for execution in executions:
            # Start event
            if execution.started_at:
                timeline.append(
                    {
                        "timestamp": execution.started_at,
                        "type": "start",
                        "execution_id": str(execution.id),
                        "query": execution.query.query_string[:50] + "...",
                        "engine": execution.search_engine,
                        "status": execution.status,
                    }
                )

            # Completion event
            if execution.completed_at:
                timeline.append(
                    {
                        "timestamp": execution.completed_at,
                        "type": "complete",
                        "execution_id": str(execution.id),
                        "query": execution.query.query_string[:50] + "...",
                        "engine": execution.search_engine,
                        "status": execution.status,
                        "results_count": execution.results_count,
                        "duration": execution.duration_seconds,
                    }
                )

            # Error events
            if execution.status == "failed" and execution.updated_at:
                timeline.append(
                    {
                        "timestamp": execution.updated_at,
                        "type": "error",
                        "execution_id": str(execution.id),
                        "query": execution.query.query_string[:50] + "...",
                        "engine": execution.search_engine,
                        "error": (
                            execution.error_message[:100] + "..."
                            if len(execution.error_message) > 100
                            else execution.error_message
                        ),
                    }
                )

        # Sort by timestamp
        timeline.sort(key=lambda x: x["timestamp"])

        return timeline

    def format_execution_status(self, status: str) -> Dict[str, str]:
        """
        Format execution status with icon and CSS class.

        Args:
            status: Execution status

        Returns:
            Dictionary with icon and CSS class
        """
        status_formats = {
            "pending": {"icon": "clock", "class": "text-secondary"},
            "running": {"icon": "sync", "class": "text-primary"},
            "completed": {"icon": "check-circle", "class": "text-success"},
            "failed": {"icon": "times-circle", "class": "text-danger"},
            "cancelled": {"icon": "ban", "class": "text-warning"},
            "rate_limited": {"icon": "exclamation-triangle", "class": "text-warning"},
        }

        return status_formats.get(
            status, {"icon": "question-circle", "class": "text-muted"}
        )

    def _get_execution_counts(self, executions) -> Dict[str, int]:
        """Get basic execution counts."""
        return {
            "total_executions": executions.count(),
            "successful_executions": executions.filter(status="completed").count(),
            "failed_executions": executions.filter(status="failed").count(),
            "pending_executions": executions.filter(status="pending").count(),
        }

    def _get_execution_aggregates(self, executions) -> Dict[str, Any]:
        """Get aggregated execution data."""
        from django.db.models import Avg, Sum

        return executions.aggregate(
            total_results=Sum("results_count"),
            total_cost=Sum("estimated_cost"),
            avg_time=Avg("duration_seconds"),
        )

    def _calculate_success_rate(self, total: int, successful: int) -> float:
        """Calculate success rate percentage."""
        return (successful / total * 100) if total > 0 else 0

    def _get_last_execution_date(self, executions):
        """Get the date of the last execution."""
        last_execution = executions.order_by("-created_at").first()
        return last_execution.created_at if last_execution else None

    def _empty_stats(self) -> Dict[str, Any]:
        """Return empty statistics structure."""
        return {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "pending_executions": 0,
            "total_results": 0,
            "total_cost": Decimal("0.00"),
            "average_execution_time": 0,
            "success_rate": 0,
            "engines_used": [],
            "last_execution_date": None,
        }
