"""
Django admin configuration for SERP execution models.
"""

from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import ExecutionMetrics, RawSearchResult, SearchExecution


@admin.register(SearchExecution)
class SearchExecutionAdmin(admin.ModelAdmin):
    """Admin interface for SearchExecution model."""

    list_display = [
        "id_short",
        "query_link",
        "status_display",
        "search_engine",
        "results_count",
        "api_credits_used",
        "cost_display",
        "duration_display",
        "created_at",
    ]

    list_filter = [
        "status",
        "search_engine",
        "created_at",
        ("query__session", admin.RelatedOnlyFieldListFilter),
    ]

    search_fields = [
        "id",
        "api_request_id",
        "query__query_string",
        "query__session__title",
        "error_message",
    ]

    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
        "duration_seconds",
        "api_request_id",
        "results_count",
        "api_credits_used",
        "estimated_cost",
    ]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("id", "query", "initiated_by", "status", "search_engine")},
        ),
        (
            "Execution Details",
            {"fields": ("api_request_id", "api_parameters", "celery_task_id")},
        ),
        (
            "Timing",
            {
                "fields": (
                    "started_at",
                    "completed_at",
                    "duration_seconds",
                    "created_at",
                    "updated_at",
                )
            },
        ),
        (
            "Results",
            {
                "fields": (
                    "results_count",
                    "results_offset",
                    "api_credits_used",
                    "estimated_cost",
                )
            },
        ),
        (
            "Error Information",
            {"fields": ("error_message", "retry_count"), "classes": ("collapse",)},
        ),
    )

    actions = ["retry_failed_executions", "export_execution_data"]

    def id_short(self, obj):
        """Display shortened ID."""
        return str(obj.id)[:8]

    id_short.short_description = "ID"

    def query_link(self, obj):
        """Link to related query."""
        if obj.query:
            url = reverse(
                "admin:search_strategy_searchquery_change", args=[obj.query.id]
            )
            return format_html(
                '<a href="{}">{}</a>', url, obj.query.query_string[:50] + "..."
            )
        return "-"

    query_link.short_description = "Query"

    def status_display(self, obj):
        """Display status with color coding."""
        colors = {
            "pending": "#6c757d",
            "running": "#0d6efd",
            "completed": "#198754",
            "failed": "#dc3545",
            "cancelled": "#ffc107",
            "rate_limited": "#fd7e14",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_display.short_description = "Status"

    def cost_display(self, obj):
        """Display cost in USD."""
        return f"${obj.estimated_cost:.4f}"

    cost_display.short_description = "Cost"

    def duration_display(self, obj):
        """Display duration in human-readable format."""
        if obj.duration_seconds:
            return f"{obj.duration_seconds:.2f}s"
        return "-"

    duration_display.short_description = "Duration"

    def retry_failed_executions(self, request, queryset):
        """Action to retry failed executions."""
        failed = queryset.filter(status="failed")
        count = 0
        for execution in failed:
            if execution.can_retry():
                # Import here to avoid circular import
                from .tasks import retry_failed_execution_task

                retry_failed_execution_task.delay(str(execution.id))
                count += 1

        self.message_user(request, f"Started retry for {count} failed executions.")

    retry_failed_executions.short_description = "Retry failed executions"

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return (
            super()
            .get_queryset(request)
            .select_related("query", "query__session", "initiated_by")
        )


@admin.register(RawSearchResult)
class RawSearchResultAdmin(admin.ModelAdmin):
    """Admin interface for RawSearchResult model."""

    list_display = [
        "position",
        "title_truncated",
        "domain_display",
        "has_pdf",
        "is_academic",
        "language_code",
        "is_processed",
        "created_at",
    ]

    list_filter = [
        "is_processed",
        "has_pdf",
        "is_academic",
        "language_code",
        "created_at",
        ("execution__search_engine", admin.RelatedOnlyFieldListFilter),
    ]

    search_fields = ["title", "link", "snippet", "source"]

    readonly_fields = ["id", "created_at", "get_domain", "raw_data_pretty"]

    fieldsets = (
        (
            "Basic Information",
            {"fields": ("id", "execution", "position", "title", "link", "snippet")},
        ),
        (
            "Additional Metadata",
            {
                "fields": (
                    "display_link",
                    "source",
                    "get_domain",
                    "has_pdf",
                    "has_date",
                    "detected_date",
                    "is_academic",
                    "language_code",
                )
            },
        ),
        ("Processing", {"fields": ("is_processed", "processing_error", "created_at")}),
        ("Raw Data", {"fields": ("raw_data_pretty",), "classes": ("collapse",)}),
    )

    actions = ["mark_as_processed", "mark_as_unprocessed", "detect_academic_sources"]

    def title_truncated(self, obj):
        """Display truncated title."""
        return obj.title[:60] + "..." if len(obj.title) > 60 else obj.title

    title_truncated.short_description = "Title"

    def domain_display(self, obj):
        """Display domain from URL."""
        return obj.get_domain()

    domain_display.short_description = "Domain"

    def raw_data_pretty(self, obj):
        """Display raw data in pretty format."""
        import json

        return format_html(
            '<pre style="max-height: 400px; overflow-y: auto;">{}</pre>',
            json.dumps(obj.raw_data, indent=2),
        )

    raw_data_pretty.short_description = "Raw Data (JSON)"

    def mark_as_processed(self, request, queryset):
        """Mark selected results as processed."""
        count = queryset.update(is_processed=True)
        self.message_user(request, f"Marked {count} results as processed.")

    mark_as_processed.short_description = "Mark as processed"

    def mark_as_unprocessed(self, request, queryset):
        """Mark selected results as unprocessed."""
        count = queryset.update(is_processed=False)
        self.message_user(request, f"Marked {count} results as unprocessed.")

    mark_as_unprocessed.short_description = "Mark as unprocessed"

    def detect_academic_sources(self, request, queryset):
        """Detect and mark academic sources."""
        count = 0
        academic_domains = [
            ".edu",
            ".ac.uk",
            "scholar.google",
            "arxiv.org",
            "pubmed",
            "researchgate",
            "academia.edu",
        ]

        for result in queryset:
            domain = result.get_domain().lower()
            if any(academic in domain for academic in academic_domains):
                result.is_academic = True
                result.save(update_fields=["is_academic"])
                count += 1

        self.message_user(request, f"Detected {count} academic sources.")

    detect_academic_sources.short_description = "Detect academic sources"

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related("execution")


@admin.register(ExecutionMetrics)
class ExecutionMetricsAdmin(admin.ModelAdmin):
    """Admin interface for ExecutionMetrics model."""

    list_display = [
        "session_title",
        "total_executions",
        "successful_executions",
        "failed_executions",
        "total_results_retrieved",
        "unique_results",
        "total_cost_display",
        "last_execution",
    ]

    list_filter = [
        "last_execution",
        "created_at",
    ]

    search_fields = ["session__title", "session__id"]

    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "last_execution",
        "success_rate",
        "cost_per_result",
    ]

    fieldsets = (
        ("Session Information", {"fields": ("id", "session")}),
        (
            "Execution Statistics",
            {
                "fields": (
                    "total_executions",
                    "successful_executions",
                    "failed_executions",
                    "success_rate",
                    "average_execution_time",
                )
            },
        ),
        (
            "Results Statistics",
            {
                "fields": (
                    "total_results_retrieved",
                    "unique_results",
                    "academic_results_count",
                    "pdf_results_count",
                )
            },
        ),
        (
            "Cost Metrics",
            {
                "fields": (
                    "total_api_credits",
                    "total_estimated_cost",
                    "cost_per_result",
                )
            },
        ),
        ("Rate Limiting", {"fields": ("rate_limit_hits", "last_rate_limit")}),
        ("Timestamps", {"fields": ("created_at", "updated_at", "last_execution")}),
    )

    actions = ["update_metrics", "export_metrics_report"]

    def session_title(self, obj):
        """Display session title."""
        return obj.session.title

    session_title.short_description = "Session"

    def total_cost_display(self, obj):
        """Display total cost in USD."""
        return f"${obj.total_estimated_cost:.2f}"

    total_cost_display.short_description = "Total Cost"

    def success_rate(self, obj):
        """Calculate and display success rate."""
        if obj.total_executions > 0:
            rate = (obj.successful_executions / obj.total_executions) * 100
            return f"{rate:.1f}%"
        return "N/A"

    success_rate.short_description = "Success Rate"

    def cost_per_result(self, obj):
        """Calculate cost per result."""
        if obj.total_results_retrieved > 0:
            cost = obj.total_estimated_cost / obj.total_results_retrieved
            return f"${cost:.4f}"
        return "N/A"

    cost_per_result.short_description = "Cost/Result"

    def update_metrics(self, request, queryset):
        """Update metrics for selected sessions."""
        count = 0
        for metrics in queryset:
            metrics.update_metrics()
            count += 1

        self.message_user(request, f"Updated metrics for {count} sessions.")

    update_metrics.short_description = "Update metrics"

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related("session")
