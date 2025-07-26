"""
API usage tracking and budget management for SERP execution.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.core.cache import cache
from django.db.models import Avg, Count, Max, Q, Sum
from django.utils import timezone

from apps.serp_execution.models import ExecutionMetrics, SearchExecution

logger = logging.getLogger(__name__)


class UsageTracker:
    """
    Tracks API usage, enforces budget limits, and provides analytics.
    """

    # Budget configuration
    DEFAULT_DAILY_BUDGET = Decimal("10.00")  # $10 per day
    DEFAULT_MONTHLY_BUDGET = Decimal("300.00")  # $300 per month
    COST_PER_QUERY = Decimal("0.001")  # $0.001 per query

    # Alert thresholds
    BUDGET_WARNING_THRESHOLD = 0.8  # Warn at 80% usage
    BUDGET_CRITICAL_THRESHOLD = 0.95  # Critical at 95% usage

    def __init__(self):
        """Initialize usage tracker with configuration."""
        self.daily_budget = getattr(
            settings, "SERPER_DAILY_BUDGET", self.DEFAULT_DAILY_BUDGET
        )
        self.monthly_budget = getattr(
            settings, "SERPER_MONTHLY_BUDGET", self.DEFAULT_MONTHLY_BUDGET
        )

    def track_usage(
        self, execution: SearchExecution, credits_used: int, cost: Decimal
    ) -> Dict[str, Any]:
        """
        Track API usage for an execution.

        Args:
            execution: SearchExecution instance
            credits_used: Number of API credits consumed
            cost: Estimated cost in USD

        Returns:
            Usage tracking results
        """
        # Update execution record
        execution.api_credits_used = credits_used
        execution.estimated_cost = cost
        execution.save(update_fields=["api_credits_used", "estimated_cost"])

        # Update session metrics
        self._update_session_metrics(execution)

        # Check budget status
        budget_status = self.check_budget_status()

        # Log if approaching limits
        if budget_status["daily"]["percentage"] >= self.BUDGET_WARNING_THRESHOLD:
            logger.warning(
                f"Daily budget usage at {budget_status['daily']['percentage']:.1%}"
            )

        return {
            "credits_used": credits_used,
            "cost": float(cost),
            "budget_status": budget_status,
            "warnings": self._generate_usage_warnings(budget_status),
        }

    def check_budget_status(self) -> Dict[str, Any]:
        """
        Check current budget status and remaining allowance.

        Returns:
            Dictionary with budget status information
        """
        now = timezone.now()

        # Daily usage
        daily_usage = self._get_period_usage(
            start_time=now.replace(hour=0, minute=0, second=0, microsecond=0),
            end_time=now,
        )

        # Monthly usage
        monthly_usage = self._get_period_usage(
            start_time=now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            end_time=now,
        )

        return {
            "daily": {
                "used": float(daily_usage["total_cost"]),
                "budget": float(self.daily_budget),
                "remaining": float(
                    Decimal(str(self.daily_budget)) - daily_usage["total_cost"]
                ),
                "percentage": (
                    float(daily_usage["total_cost"] / Decimal(str(self.daily_budget)))
                    if self.daily_budget > 0
                    else 0
                ),
                "queries": daily_usage["total_queries"],
            },
            "monthly": {
                "used": float(monthly_usage["total_cost"]),
                "budget": float(self.monthly_budget),
                "remaining": float(
                    Decimal(str(self.monthly_budget)) - monthly_usage["total_cost"]
                ),
                "percentage": (
                    float(
                        monthly_usage["total_cost"] / Decimal(str(self.monthly_budget))
                    )
                    if self.monthly_budget > 0
                    else 0
                ),
                "queries": monthly_usage["total_queries"],
            },
        }

    def can_execute_queries(self, num_queries: int) -> Tuple[bool, Optional[str]]:
        """
        Check if the specified number of queries can be executed within budget.

        Args:
            num_queries: Number of queries to check

        Returns:
            Tuple of (can_execute, reason_if_not)
        """
        estimated_cost = self.COST_PER_QUERY * num_queries
        budget_status = self.check_budget_status()

        # Check daily budget
        if budget_status["daily"]["remaining"] < estimated_cost:
            return (
                False,
                f"Insufficient daily budget. Need ${estimated_cost:.3f}, have ${budget_status['daily']['remaining']:.3f}",
            )

        # Check monthly budget
        if budget_status["monthly"]["remaining"] < estimated_cost:
            return (
                False,
                f"Insufficient monthly budget. Need ${estimated_cost:.3f}, have ${budget_status['monthly']['remaining']:.3f}",
            )

        # Check if we're at critical threshold
        new_daily_percentage = (
            Decimal(str(budget_status["daily"]["used"])) + estimated_cost
        ) / Decimal(str(self.daily_budget))
        if float(new_daily_percentage) >= self.BUDGET_CRITICAL_THRESHOLD:
            return (
                False,
                f"Execution would exceed {self.BUDGET_CRITICAL_THRESHOLD:.0%} of daily budget",
            )

        return True, None

    def get_usage_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get detailed usage analytics for the specified period.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with usage analytics
        """
        end_time = timezone.now()
        start_time = end_time - timedelta(days=days)

        # Get executions in period
        executions = SearchExecution.objects.filter(
            created_at__gte=start_time, created_at__lte=end_time
        )

        # Aggregate statistics
        stats = executions.aggregate(
            total_queries=Count("id"),
            successful_queries=Count("id", filter=Q(status="completed")),
            failed_queries=Count("id", filter=Q(status="failed")),
            total_cost=Sum("estimated_cost"),
            total_credits=Sum("api_credits_used"),
            avg_cost_per_query=Avg("estimated_cost"),
            max_credits_single_query=Max("api_credits_used"),
            avg_execution_time=Avg("duration_seconds"),
        )

        # Calculate daily averages
        total_days = (end_time - start_time).days or 1
        daily_avg_cost = (stats["total_cost"] or 0) / total_days
        daily_avg_queries = stats["total_queries"] / total_days

        # Success rate
        success_rate = (
            stats["successful_queries"] / stats["total_queries"] * 100
            if stats["total_queries"] > 0
            else 0
        )

        return {
            "period_days": days,
            "total_queries": stats["total_queries"],
            "successful_queries": stats["successful_queries"],
            "failed_queries": stats["failed_queries"],
            "success_rate": round(success_rate, 2),
            "total_cost": float(stats["total_cost"] or 0),
            "total_credits": stats["total_credits"] or 0,
            "avg_cost_per_query": float(stats["avg_cost_per_query"] or 0),
            "daily_avg_cost": float(daily_avg_cost),
            "daily_avg_queries": round(daily_avg_queries, 1),
            "avg_execution_time": round(stats["avg_execution_time"] or 0, 2),
        }

    def get_usage_trend(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get daily usage trend for the specified period.

        Args:
            days: Number of days to analyze

        Returns:
            List of daily usage data
        """
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days - 1)

        trend_data = []
        current_date = start_date

        while current_date <= end_date:
            start_time = timezone.make_aware(
                datetime.combine(current_date, datetime.min.time())
            )
            end_time = start_time + timedelta(days=1)

            daily_usage = self._get_period_usage(start_time, end_time)

            trend_data.append(
                {
                    "date": current_date.isoformat(),
                    "queries": daily_usage["total_queries"],
                    "cost": float(daily_usage["total_cost"]),
                    "credits": daily_usage["total_credits"],
                }
            )

            current_date += timedelta(days=1)

        return trend_data

    def _get_period_usage(
        self, start_time: datetime, end_time: datetime
    ) -> Dict[str, Any]:
        """
        Get usage statistics for a specific time period.

        Args:
            start_time: Period start time
            end_time: Period end time

        Returns:
            Usage statistics for the period
        """
        executions = SearchExecution.objects.filter(
            created_at__gte=start_time, created_at__lte=end_time
        )

        stats = executions.aggregate(
            total_queries=Count("id"),
            total_cost=Sum("estimated_cost"),
            total_credits=Sum("api_credits_used"),
        )

        return {
            "total_queries": stats["total_queries"] or 0,
            "total_cost": stats["total_cost"] or Decimal("0"),
            "total_credits": stats["total_credits"] or 0,
        }

    def _update_session_metrics(self, execution: SearchExecution) -> None:
        """
        Update session-level metrics after an execution.

        Args:
            execution: SearchExecution instance
        """
        try:
            session = execution.query.strategy.session
            metrics, _ = ExecutionMetrics.objects.get_or_create(session=session)
            metrics.update_metrics()
        except Exception as e:
            logger.error(f"Error updating session metrics: {str(e)}")

    def _generate_usage_warnings(self, budget_status: Dict[str, Any]) -> List[str]:
        """
        Generate warning messages based on budget status.

        Args:
            budget_status: Current budget status

        Returns:
            List of warning messages
        """
        warnings = []

        # Daily budget warnings
        daily_percentage = budget_status["daily"]["percentage"]
        if daily_percentage >= self.BUDGET_CRITICAL_THRESHOLD:
            warnings.append(f"CRITICAL: Daily budget usage at {daily_percentage:.1%}")
        elif daily_percentage >= self.BUDGET_WARNING_THRESHOLD:
            warnings.append(f"WARNING: Daily budget usage at {daily_percentage:.1%}")

        # Monthly budget warnings
        monthly_percentage = budget_status["monthly"]["percentage"]
        if monthly_percentage >= self.BUDGET_CRITICAL_THRESHOLD:
            warnings.append(
                f"CRITICAL: Monthly budget usage at {monthly_percentage:.1%}"
            )
        elif monthly_percentage >= self.BUDGET_WARNING_THRESHOLD:
            warnings.append(
                f"WARNING: Monthly budget usage at {monthly_percentage:.1%}"
            )

        return warnings

    def reset_daily_usage_cache(self) -> bool:
        """
        Reset daily usage cache (for testing or manual reset).

        Returns:
            Success status
        """
        cache_key = "serper_usage:daily"
        try:
            cache.delete(cache_key)
            logger.info("Daily usage cache reset")
            return True
        except Exception as e:
            logger.error(f"Error resetting daily usage cache: {str(e)}")
            return False
