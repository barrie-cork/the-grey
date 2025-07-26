"""
Custom template tags for SearchExecution and API integration rendering.

These tags provide convenient filters and tags for displaying
execution status, performance metrics, and cost information.
"""

from typing import Any, Dict

from django import template
from django.utils.html import format_html
from django.utils.timesince import timesince

from ..models import ExecutionMetrics, SearchExecution
from ..utils import categorize_failure, get_execution_statistics

register = template.Library()


@register.filter
def execution_status_badge(execution: SearchExecution) -> str:
    """
    Render a status badge for search execution.

    Args:
        execution: SearchExecution instance

    Returns:
        HTML string with styled badge
    """
    status_colors = {
        "pending": "secondary",
        "running": "info",
        "completed": "success",
        "failed": "danger",
        "cancelled": "warning",
        "rate_limited": "warning",
    }

    color = status_colors.get(execution.status, "secondary")
    display_text = execution.get_status_display()

    return format_html('<span class="badge bg-{}">{}</span>', color, display_text)


@register.filter
def format_duration(seconds: float) -> str:
    """
    Format execution duration in human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if not seconds:
        return "N/A"

    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}min"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


@register.filter
def format_cost(cost) -> str:
    """
    Format cost with currency symbol.

    Args:
        cost: Cost amount (Decimal)

    Returns:
        Formatted cost string
    """
    if not cost:
        return "$0.00"

    return f"${cost:.4f}"


@register.simple_tag
def execution_progress_bar(execution: SearchExecution) -> str:
    """
    Render a progress bar based on execution status.

    Args:
        execution: SearchExecution instance

    Returns:
        HTML string with progress bar
    """
    progress_map = {
        "pending": (0, "secondary"),
        "running": (50, "info"),
        "completed": (100, "success"),
        "failed": (100, "danger"),
        "cancelled": (0, "warning"),
        "rate_limited": (25, "warning"),
    }

    percentage, color = progress_map.get(execution.status, (0, "secondary"))

    return format_html(
        '<div class="progress">'
        '<div class="progress-bar bg-{}" role="progressbar" style="width: {}%" aria-valuenow="{}" aria-valuemin="0" aria-valuemax="100">'
        "{}%"
        "</div>"
        "</div>",
        color,
        percentage,
        percentage,
        percentage,
    )


@register.inclusion_tag("serp_execution/tags/execution_summary.html")
def execution_summary_card(execution: SearchExecution):
    """
    Render a summary card for search execution.

    Args:
        execution: SearchExecution instance

    Returns:
        Context for the execution summary template
    """
    return {
        "execution": execution,
        "can_retry": execution.can_retry(),
        "duration_formatted": format_duration(execution.duration_seconds or 0),
        "cost_formatted": format_cost(execution.estimated_cost),
        "time_since_created": timesince(execution.created_at),
    }


@register.filter
def engine_icon(engine_name: str) -> str:
    """
    Return an icon class for search engines.

    Args:
        engine_name: Name of the search engine

    Returns:
        HTML string with icon
    """
    icons = {
        "google": "bi-google",
        "bing": "bi-microsoft",
        "duckduckgo": "bi-shield-check",
        "yahoo": "bi-search",
    }

    icon_class = icons.get(engine_name.lower(), "bi-search")

    return format_html(
        '<i class="{} me-1" title="{}"></i>', icon_class, engine_name.title()
    )


@register.simple_tag
def retry_button(execution: SearchExecution) -> str:
    """
    Render retry button if execution can be retried.

    Args:
        execution: SearchExecution instance

    Returns:
        HTML string with retry button or empty string
    """
    if not execution.can_retry():
        return ""

    return format_html(
        '<button class="btn btn-outline-warning btn-sm" onclick="retryExecution(\'{}\')">',
        '<i class="bi bi-arrow-clockwise me-1"></i>Retry ({}/3)',
        "</button>",
        execution.id,
        execution.retry_count + 1,
    )


@register.filter
def failure_category_badge(execution: SearchExecution) -> str:
    """
    Render a badge for failure category.

    Args:
        execution: SearchExecution instance

    Returns:
        HTML string with failure category badge
    """
    if execution.status != "failed":
        return ""

    category = categorize_failure(execution.error_message)

    category_colors = {
        "rate_limit": "warning",
        "timeout": "info",
        "network": "danger",
        "authentication": "danger",
        "quota_exceeded": "warning",
        "api_error": "danger",
        "unknown": "secondary",
    }

    color = category_colors.get(category, "secondary")
    display_name = category.replace("_", " ").title()

    return format_html('<span class="badge bg-{} ms-1">{}</span>', color, display_name)


@register.simple_tag
def session_execution_stats(session_id: str) -> Dict[str, Any]:
    """
    Get execution statistics for a session.

    Args:
        session_id: UUID of the SearchSession

    Returns:
        Dictionary with execution statistics
    """
    return get_execution_statistics(session_id)


@register.inclusion_tag("serp_execution/tags/metrics_dashboard.html")
def execution_metrics_dashboard(session):
    """
    Render execution metrics dashboard.

    Args:
        session: SearchSession instance

    Returns:
        Context for the metrics dashboard template
    """
    try:
        metrics = session.execution_metrics
    except ExecutionMetrics.DoesNotExist:
        metrics = None

    stats = get_execution_statistics(str(session.id))

    return {
        "session": session,
        "metrics": metrics,
        "stats": stats,
        "has_executions": stats["total_executions"] > 0,
    }


@register.filter
def results_per_credit(execution: SearchExecution) -> str:
    """
    Calculate results per API credit used.

    Args:
        execution: SearchExecution instance

    Returns:
        Formatted ratio string
    """
    if not execution.api_credits_used or execution.api_credits_used == 0:
        return "N/A"

    ratio = execution.results_count / execution.api_credits_used
    return f"{ratio:.1f}"


@register.simple_tag
def execution_timeline_item(execution: SearchExecution) -> str:
    """
    Render a timeline item for execution.

    Args:
        execution: SearchExecution instance

    Returns:
        HTML string with timeline item
    """
    status_icons = {
        "pending": "bi-clock text-secondary",
        "running": "bi-arrow-clockwise text-info",
        "completed": "bi-check-circle text-success",
        "failed": "bi-x-circle text-danger",
        "cancelled": "bi-stop-circle text-warning",
        "rate_limited": "bi-shield-exclamation text-warning",
    }

    icon_class = status_icons.get(execution.status, "bi-circle text-secondary")
    time_display = timesince(execution.created_at)

    return format_html(
        '<div class="timeline-item">'
        '<div class="timeline-marker">'
        '<i class="{}"></i>'
        "</div>"
        '<div class="timeline-content">'
        '<h6 class="mb-1">{} - {}</h6>'
        '<small class="text-muted">{} ago</small>'
        "{}"
        "</div>"
        "</div>",
        icon_class,
        execution.get_status_display(),
        execution.search_engine.title(),
        time_display,
        (
            f'<div class="mt-1"><small class="text-danger">{execution.error_message[:100]}...</small></div>'
            if execution.error_message
            else ""
        ),
    )


@register.filter
def api_health_indicator(success_rate: float) -> str:
    """
    Show API health indicator based on success rate.

    Args:
        success_rate: Success rate percentage

    Returns:
        HTML string with health indicator
    """
    if success_rate >= 95:
        return '<span class="badge bg-success">Excellent</span>'
    elif success_rate >= 85:
        return '<span class="badge bg-info">Good</span>'
    elif success_rate >= 70:
        return '<span class="badge bg-warning">Fair</span>'
    else:
        return '<span class="badge bg-danger">Poor</span>'


@register.simple_tag
def cost_per_result(total_cost, total_results) -> str:
    """
    Calculate cost per result.

    Args:
        total_cost: Total cost (Decimal)
        total_results: Total number of results

    Returns:
        Formatted cost per result string
    """
    if not total_results or total_results == 0:
        return "N/A"

    cost_per_result = float(total_cost) / total_results
    return f"${cost_per_result:.4f}"
