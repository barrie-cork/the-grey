"""
Views for the SERP execution module.
Handles search execution, monitoring, and error recovery.
"""

import logging
from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, FormView

from apps.core.bootstrap import get_dependencies
from apps.search_strategy.models import SearchQuery

from .forms import ErrorRecoveryForm, ExecutionConfirmationForm
from .models import RawSearchResult, SearchExecution
# Removed usage_tracker - using simplified approach
from .tasks import initiate_search_session_execution_task, retry_failed_execution_task
from .utils import get_execution_statistics
from .recovery import recovery_manager

logger = logging.getLogger(__name__)


class SessionOwnershipMixin:
    """Mixin to ensure user owns the search session."""

    def get_session(self):
        """Get and validate session ownership."""
        session_id = self.kwargs.get("session_id")
        deps = get_dependencies()
        session_provider = deps.get_session_provider()

        # Get session through provider
        session = session_provider.get_session(session_id)

        # Verify ownership through provider
        if not session_provider.verify_session_ownership(session_id, self.request.user):
            raise PermissionDenied("You don't have permission to access this session.")

        return session


class ExecuteSearchView(LoginRequiredMixin, SessionOwnershipMixin, FormView):
    """
    Preview and initiate search execution.
    Shows queries and requires confirmation.
    """

    template_name = "serp_execution/execute_search.html"
    form_class = ExecutionConfirmationForm

    def dispatch(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        """Validate session status before processing."""
        self.session = self.get_session()

        if self.session.status != "ready_to_execute":
            messages.error(
                request,
                f"Session must be in 'Ready to Execute' status. Current status: {self.session.get_status_display()}",
            )
            return redirect("review_manager:session_detail", session_id=self.session.id)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """Add queries to context."""
        context = super().get_context_data(**kwargs)

        # Get active queries
        queries = SearchQuery.objects.filter(
            strategy__session=self.session, is_active=True
        ).order_by("execution_order", "created_at")

        # Query statistics
        total_queries = queries.count()

        # Since we're using Serper API, we have one engine
        engines_used = {"serper"}

        # Estimate based on 100 results per query
        estimated_api_calls = total_queries

        # Estimate execution time (simplified - 5 seconds per query)
        total_execution_time = total_queries * 5

        context.update(
            {
                "session": self.session,
                "queries": queries,
                "total_queries": total_queries,
                "engines_used": list(engines_used),
                "estimated_api_calls": estimated_api_calls,
                "estimated_time_minutes": round(total_execution_time / 60, 1),
            }
        )

        return context

    def form_valid(self, form):
        """Initiate search execution after confirmation."""
        try:
            # Start the execution task
            task = initiate_search_session_execution_task.delay(str(self.session.id))

            # Log the execution start
            logger.info(
                f"Started search execution for session {self.session.id}, task ID: {task.id}"
            )

            messages.success(
                self.request,
                "Search execution has been initiated. You'll be notified when it's complete.",
            )

            # Redirect to status page
            return redirect(
                "serp_execution:execution_status", session_id=self.session.id
            )

        except Exception as e:
            logger.error(f"Failed to initiate search execution: {str(e)}")
            messages.error(
                self.request,
                "Failed to start search execution. Please try again or contact support.",
            )
            return self.form_invalid(form)

    def get_form_kwargs(self):
        """Pass session to form."""
        kwargs = super().get_form_kwargs()
        kwargs["session"] = self.session
        return kwargs


class SearchExecutionStatusView(LoginRequiredMixin, SessionOwnershipMixin, DetailView):
    """
    Monitor execution progress in real-time.
    Shows individual query status, results count, and errors.
    """

    template_name = "serp_execution/execution_status.html"
    context_object_name = "session"

    def get_object(self):
        """Get the search session."""
        return self.get_session()

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """Add execution details to context with enhanced statistics for card layout."""
        context = super().get_context_data(**kwargs)

        # Get all executions for this session
        executions = (
            SearchExecution.objects.filter(query__strategy__session=self.object)
            .select_related("query")
            .order_by("-created_at")
        )

        # Calculate enhanced statistics for our new card layout
        stats = self._calculate_enhanced_statistics(executions, str(self.object.id))

        # Get basic failed executions info
        failed_executions = executions.filter(status="failed")

        # Check if any executions are still running
        has_running = executions.filter(status__in=["pending", "running"]).exists()

        context.update(
            {
                "executions": executions,
                "stats": stats,
                "failed_executions": failed_executions,
                "has_running": has_running,
                "refresh_interval": 5000 if has_running else 0,  # 5 seconds if running
            }
        )

        return context

    @staticmethod
    def _calculate_enhanced_statistics(
        executions, session_id: str = None
    ) -> Dict[str, Any]:
        """Calculate enhanced statistics for the new card-based layout."""
        # Get basic statistics if session_id is provided
        basic_stats = {}
        if session_id:
            basic_stats = get_execution_statistics(session_id)

        # Calculate additional statistics efficiently using aggregation
        from django.db.models import Count, Case, When, IntegerField
        
        stats = executions.aggregate(
            total_executions=Count('id'),
            successful_executions=Count(Case(When(status='completed', then=1), output_field=IntegerField())),
            failed_executions=Count(Case(When(status='failed', then=1), output_field=IntegerField())),
            running_executions=Count(Case(When(status='running', then=1), output_field=IntegerField())),
            pending_executions=Count(Case(When(status='pending', then=1), output_field=IntegerField())),
            retrying_executions=Count(Case(When(status='pending', retry_count__gt=0, then=1), output_field=IntegerField())),
        )
        
        total_executions = stats['total_executions']
        successful_executions = stats['successful_executions']
        failed_executions = stats['failed_executions']
        running_executions = stats['running_executions']
        pending_executions = stats['pending_executions']
        retrying_executions = stats['retrying_executions']

        # Calculate total results
        total_results = sum(
            execution.results_count
            for execution in executions
            if execution.results_count
        )

        # Calculate success rate
        success_rate = (
            (successful_executions / total_executions * 100)
            if total_executions > 0
            else 0
        )

        # Get timing information
        last_execution_date = executions.filter(completed_at__isnull=False).first()
        last_execution_date = (
            last_execution_date.completed_at if last_execution_date else None
        )

        # Enhanced statistics dictionary
        enhanced_stats = {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "running_executions": running_executions,
            "pending_executions": pending_executions,
            "retrying_executions": retrying_executions,
            "total_results": total_results,
            "success_rate": round(success_rate, 1),
            "last_execution_date": last_execution_date,
        }

        # Merge with basic stats for backward compatibility
        enhanced_stats.update(basic_stats)

        return enhanced_stats


class ErrorRecoveryView(LoginRequiredMixin, SessionOwnershipMixin, FormView):
    """
    Handle execution errors with recovery options.
    Allows manual retry of failed executions.
    """

    template_name = "serp_execution/error_recovery.html"
    form_class = ErrorRecoveryForm

    def dispatch(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        """Get execution and validate ownership."""
        execution_id = kwargs.get("execution_id")
        self.execution = get_object_or_404(SearchExecution, id=execution_id)
        self.session = self.execution.query.strategy.session

        # Validate ownership
        if self.session.owner != request.user:
            raise PermissionDenied(
                "You don't have permission to access this execution."
            )

        # Check if execution can be retried
        if not self.execution.can_retry():
            messages.error(request, "This execution cannot be retried.")
            return redirect(
                "serp_execution:execution_status", session_id=self.session.id
            )

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """Add execution details to context."""
        context = super().get_context_data(**kwargs)

        # Simple retry strategy - just check if it can be retried
        can_retry = self.execution.can_retry()
        error_category = recovery_manager.get_error_category(self.execution.error_message)

        context.update(
            {
                "execution": self.execution,
                "session": self.session,
                "can_retry": can_retry,
                "error_category": error_category,
            }
        )

        return context

    def form_valid(self, form):
        """Process recovery action."""
        action = form.cleaned_data["recovery_action"]

        try:
            if action == "retry":
                # Schedule retry task
                task = retry_failed_execution_task.delay(
                    str(self.execution.id),
                    delay_seconds=form.cleaned_data.get("retry_delay", 60),
                )

                messages.success(
                    self.request, f"Retry scheduled for execution. Task ID: {task.id}"
                )

            elif action == "skip":
                # Mark as skipped
                self.execution.status = "cancelled"
                self.execution.save(update_fields=["status"])

                messages.info(self.request, "Execution skipped.")

            elif action == "manual":
                # Provide manual instructions
                messages.info(
                    self.request,
                    "Please check the API credentials and try again manually.",
                )

            return redirect(
                "serp_execution:execution_status", session_id=self.session.id
            )

        except Exception as e:
            logger.error(f"Recovery action failed: {str(e)}")
            messages.error(self.request, "Recovery action failed. Please try again.")
            return self.form_invalid(form)

    def get_form_kwargs(self):
        """Pass execution to form."""
        kwargs = super().get_form_kwargs()
        kwargs["execution"] = self.execution
        return kwargs


# AJAX API Views


@login_required
@require_http_methods(["GET"])
def execution_status_api(request, execution_id: str) -> JsonResponse:
    """
    Get execution status via AJAX.
    Returns JSON with current status and progress.
    """
    try:
        execution = get_object_or_404(SearchExecution, id=execution_id)

        # Verify ownership
        if execution.query.strategy.session.owner != request.user:
            return JsonResponse({"error": "Permission denied"}, status=403)

        # Get result count
        result_count = RawSearchResult.objects.filter(execution=execution).count()

        # Calculate progress
        progress = 0
        if execution.status == "completed":
            progress = 100
        elif execution.status == "running" and execution.results_count > 0:
            # Estimate based on typical 100 results
            progress = min(90, (result_count / 100) * 90)
        elif execution.status == "pending":
            progress = 10

        response_data = {
            "id": str(execution.id),
            "status": execution.status,
            "status_display": execution.get_status_display(),
            "results_count": execution.results_count,
            "progress": progress,
            "error_message": execution.error_message,
            "duration_seconds": execution.duration_seconds,
            "can_retry": execution.can_retry(),
            "created_at": execution.created_at.isoformat(),
            "completed_at": (
                execution.completed_at.isoformat() if execution.completed_at else None
            ),
        }

        return JsonResponse(response_data)

    except Http404:
        return JsonResponse({"error": "Execution not found"}, status=404)
    except Exception as e:
        logger.error(f"Error getting execution status: {str(e)}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@login_required
@require_http_methods(["GET"])
def session_progress_api(request, session_id: str) -> JsonResponse:
    """
    Get overall session execution progress via AJAX.
    Returns aggregated statistics and status.
    """
    try:
        deps = get_dependencies()
        session_provider = deps.get_session_provider()

        # Get session and verify ownership through provider
        session = session_provider.get_session(session_id)
        if not session_provider.verify_session_ownership(session_id, request.user):
            return JsonResponse({"error": "Permission denied"}, status=403)

        # Get enhanced execution statistics
        executions = (
            SearchExecution.objects.filter(query__strategy__session=session)
            .select_related("query")
            .order_by("-created_at")
        )

        stats = SearchExecutionStatusView._calculate_enhanced_statistics(
            executions, session_id
        )

        # Get current executions data
        executions_data = executions.values(
            "id", "status", "results_count", "error_message"
        )

        # Calculate overall progress
        total_queries = stats["total_executions"]
        completed_queries = stats["successful_executions"] + stats["failed_executions"]
        progress = (completed_queries / total_queries * 100) if total_queries > 0 else 0

        # Determine if still running
        has_running = any(
            e["status"] in ["pending", "running"] for e in executions_data
        )

        response_data = {
            "session_id": session_id,
            "session_status": session.status,
            "progress": round(progress, 1),
            "statistics": stats,
            "executions": list(executions_data),
            "has_running": has_running,
            "total_results": stats["total_results"],
            "updated_at": timezone.now().isoformat(),
        }

        return JsonResponse(response_data)

    except Http404:
        return JsonResponse({"error": "Session not found"}, status=404)
    except Exception as e:
        logger.error(f"Error getting session progress: {str(e)}")
        return JsonResponse({"error": "Internal server error"}, status=500)


@login_required
@require_http_methods(["POST"])
def retry_execution_api(request, execution_id: str) -> JsonResponse:
    """
    Retry a failed execution via AJAX.
    Validates retry eligibility and schedules task.
    """
    try:
        execution = get_object_or_404(SearchExecution, id=execution_id)

        # Verify ownership
        if execution.query.strategy.session.owner != request.user:
            return JsonResponse({"error": "Permission denied"}, status=403)

        # Check if can retry
        if not execution.can_retry():
            return JsonResponse(
                {
                    "success": False,
                    "error": "Execution cannot be retried",
                    "reason": "Maximum retry attempts reached or invalid status",
                },
                status=400,
            )

        # Simple retry logic - if it can retry, allow it
        if execution.can_retry():
            # Schedule retry
            with transaction.atomic():
                execution.retry_count += 1
                execution.status = "pending"
                execution.error_message = ""
                execution.save(update_fields=["retry_count", "status", "error_message"])

                # Get delay based on error type
                delay_seconds = recovery_manager.get_retry_delay(Exception(execution.error_message))
                task = retry_failed_execution_task.apply_async(
                    args=[str(execution.id)], countdown=delay_seconds
                )

            # Update task ID
            execution.celery_task_id = task.id
            execution.save(update_fields=["celery_task_id"])
        else:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Retry not allowed",
                    "reason": "Maximum retry attempts reached",
                },
                status=400,
            )

        response_data = {
            "success": True,
            "execution_id": str(execution.id),
            "task_id": task.id,
            "retry_count": execution.retry_count,
            "delay_seconds": delay_seconds,
            "message": f"Retry scheduled with {delay_seconds}s delay",
        }

        return JsonResponse(response_data)

    except Http404:
        return JsonResponse({"error": "Execution not found"}, status=404)
    except Exception as e:
        logger.error(f"Error retrying execution: {str(e)}")
        return JsonResponse(
            {"success": False, "error": "Failed to schedule retry", "details": str(e)},
            status=500,
        )
