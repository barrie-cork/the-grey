"""
Views for the SERP execution module.
Handles search execution, monitoring, and error recovery.
"""

import json
import logging
from typing import Dict, Any, Optional
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import DetailView, FormView, TemplateView
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse, Http404
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg
from django.db import transaction

from apps.review_manager.models import SearchSession
from apps.review_manager.signals import get_session_data
from apps.search_strategy.signals import get_session_queries_data
from .models import SearchExecution, RawSearchResult, ExecutionMetrics
from .forms import ExecutionConfirmationForm, ErrorRecoveryForm
from .tasks import (
    initiate_search_session_execution_task,
    perform_serp_query_task,
    retry_failed_execution_task
)
from .utils import (
    calculate_api_cost,
    estimate_execution_time,
    get_execution_statistics,
    get_failed_executions_with_analysis,
    calculate_search_coverage,
    optimize_retry_strategy,
    get_engine_performance_comparison
)
from .services.usage_tracker import UsageTracker
from .services.cache_manager import CacheManager

logger = logging.getLogger(__name__)


class SessionOwnershipMixin:
    """Mixin to ensure user owns the search session."""
    
    def get_session(self) -> SearchSession:
        """Get and validate session ownership."""
        session_id = self.kwargs.get('session_id')
        session = get_object_or_404(SearchSession, id=session_id)
        
        if session.owner != self.request.user:
            raise PermissionDenied("You don't have permission to access this session.")
        
        return session


class ExecuteSearchView(LoginRequiredMixin, SessionOwnershipMixin, FormView):
    """
    Preview and initiate search execution.
    Shows queries, cost estimation, and requires confirmation.
    """
    template_name = 'serp_execution/execute_search.html'
    form_class = ExecutionConfirmationForm
    
    def dispatch(self, request, *args, **kwargs):
        """Validate session status before processing."""
        self.session = self.get_session()
        
        if self.session.status != 'ready_to_execute':
            messages.error(
                request,
                f"Session must be in 'Ready to Execute' status. Current status: {self.session.get_status_display()}"
            )
            return redirect('review_manager:session_detail', pk=self.session.id)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Add queries and cost estimation to context."""
        context = super().get_context_data(**kwargs)
        
        # Get active queries
        queries = SearchQuery.objects.filter(
            session=self.session,
            is_active=True
        ).order_by('order', 'created_at')
        
        # Calculate cost estimation
        usage_tracker = UsageTracker()
        total_queries = queries.count()
        engines_used = set()
        
        for query in queries:
            engines_used.update(query.search_engines)
        
        # Estimate based on 100 results per query per engine
        estimated_api_calls = total_queries * len(engines_used)
        estimated_credits = estimated_api_calls * 100  # 100 credits per search
        estimated_cost = calculate_api_cost(estimated_credits)
        
        # Check current usage
        current_usage = usage_tracker.get_current_usage()
        remaining_credits = current_usage.get('remaining_credits', 0)
        
        # Estimate execution time
        total_execution_time = 0
        for query in queries:
            complexity = len(query.include_keywords) + len(query.exclude_keywords)
            time_estimate = estimate_execution_time(complexity, query.search_engines)
            total_execution_time += time_estimate
        
        context.update({
            'session': self.session,
            'queries': queries,
            'total_queries': total_queries,
            'engines_used': list(engines_used),
            'estimated_api_calls': estimated_api_calls,
            'estimated_credits': estimated_credits,
            'estimated_cost': estimated_cost,
            'remaining_credits': remaining_credits,
            'has_sufficient_credits': remaining_credits >= estimated_credits,
            'estimated_time_minutes': round(total_execution_time / 60, 1),
        })
        
        return context
    
    def form_valid(self, form):
        """Initiate search execution after confirmation."""
        try:
            # Start the execution task
            task = initiate_search_session_execution_task.delay(str(self.session.id))
            
            # Log the execution start
            logger.info(f"Started search execution for session {self.session.id}, task ID: {task.id}")
            
            messages.success(
                self.request,
                "Search execution has been initiated. You'll be notified when it's complete."
            )
            
            # Redirect to status page
            return redirect('serp_execution:execution_status', session_id=self.session.id)
            
        except Exception as e:
            logger.error(f"Failed to initiate search execution: {str(e)}")
            messages.error(
                self.request,
                "Failed to start search execution. Please try again or contact support."
            )
            return self.form_invalid(form)
    
    def get_form_kwargs(self):
        """Pass session to form."""
        kwargs = super().get_form_kwargs()
        kwargs['session'] = self.session
        return kwargs


class SearchExecutionStatusView(LoginRequiredMixin, SessionOwnershipMixin, DetailView):
    """
    Monitor execution progress in real-time.
    Shows individual query status, results count, and errors.
    """
    template_name = 'serp_execution/execution_status.html'
    context_object_name = 'session'
    
    def get_object(self):
        """Get the search session."""
        return self.get_session()
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Add execution details to context."""
        context = super().get_context_data(**kwargs)
        
        # Get all executions for this session
        executions = SearchExecution.objects.filter(
            query__session=self.object
        ).select_related('query').order_by('-created_at')
        
        # Calculate statistics
        stats = get_execution_statistics(str(self.object.id))
        
        # Get failed executions with analysis
        failed_executions = get_failed_executions_with_analysis(str(self.object.id))
        
        # Check if any executions are still running
        has_running = executions.filter(status__in=['pending', 'running']).exists()
        
        # Get coverage metrics if completed
        coverage_metrics = {}
        if self.object.status in ['ready_for_review', 'under_review', 'completed']:
            coverage_metrics = calculate_search_coverage(str(self.object.id))
        
        context.update({
            'executions': executions,
            'stats': stats,
            'failed_executions': failed_executions,
            'has_running': has_running,
            'coverage_metrics': coverage_metrics,
            'refresh_interval': 5000 if has_running else 0,  # 5 seconds if running
        })
        
        return context


class ErrorRecoveryView(LoginRequiredMixin, SessionOwnershipMixin, FormView):
    """
    Handle execution errors with recovery options.
    Allows manual retry of failed executions.
    """
    template_name = 'serp_execution/error_recovery.html'
    form_class = ErrorRecoveryForm
    
    def dispatch(self, request, *args, **kwargs):
        """Get execution and validate ownership."""
        execution_id = kwargs.get('execution_id')
        self.execution = get_object_or_404(SearchExecution, id=execution_id)
        self.session = self.execution.query.session
        
        # Validate ownership
        if self.session.owner != request.user:
            raise PermissionDenied("You don't have permission to access this execution.")
        
        # Check if execution can be retried
        if not self.execution.can_retry():
            messages.error(request, "This execution cannot be retried.")
            return redirect('serp_execution:execution_status', session_id=self.session.id)
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Add execution details and retry strategy to context."""
        context = super().get_context_data(**kwargs)
        
        retry_strategy = optimize_retry_strategy(self.execution)
        
        context.update({
            'execution': self.execution,
            'session': self.session,
            'retry_strategy': retry_strategy,
            'error_category': self.execution.error_message,
        })
        
        return context
    
    def form_valid(self, form):
        """Process recovery action."""
        action = form.cleaned_data['recovery_action']
        
        try:
            if action == 'retry':
                # Schedule retry task
                task = retry_failed_execution_task.delay(
                    str(self.execution.id),
                    delay_seconds=form.cleaned_data.get('retry_delay', 60)
                )
                
                messages.success(
                    self.request,
                    f"Retry scheduled for execution. Task ID: {task.id}"
                )
                
            elif action == 'skip':
                # Mark as skipped
                self.execution.status = 'cancelled'
                self.execution.save(update_fields=['status'])
                
                messages.info(self.request, "Execution skipped.")
                
            elif action == 'manual':
                # Provide manual instructions
                messages.info(
                    self.request,
                    "Please check the API credentials and try again manually."
                )
            
            return redirect('serp_execution:execution_status', session_id=self.session.id)
            
        except Exception as e:
            logger.error(f"Recovery action failed: {str(e)}")
            messages.error(self.request, "Recovery action failed. Please try again.")
            return self.form_invalid(form)
    
    def get_form_kwargs(self):
        """Pass execution to form."""
        kwargs = super().get_form_kwargs()
        kwargs['execution'] = self.execution
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
        if execution.query.session.owner != request.user:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Get result count
        result_count = RawSearchResult.objects.filter(execution=execution).count()
        
        # Calculate progress
        progress = 0
        if execution.status == 'completed':
            progress = 100
        elif execution.status == 'running' and execution.results_count > 0:
            # Estimate based on typical 100 results
            progress = min(90, (result_count / 100) * 90)
        elif execution.status == 'pending':
            progress = 10
        
        response_data = {
            'id': str(execution.id),
            'status': execution.status,
            'status_display': execution.get_status_display(),
            'results_count': execution.results_count,
            'progress': progress,
            'error_message': execution.error_message,
            'duration_seconds': execution.duration_seconds,
            'can_retry': execution.can_retry(),
            'created_at': execution.created_at.isoformat(),
            'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
        }
        
        return JsonResponse(response_data)
        
    except Http404:
        return JsonResponse({'error': 'Execution not found'}, status=404)
    except Exception as e:
        logger.error(f"Error getting execution status: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@require_http_methods(["GET"])
def session_progress_api(request, session_id: str) -> JsonResponse:
    """
    Get overall session execution progress via AJAX.
    Returns aggregated statistics and status.
    """
    try:
        session = get_object_or_404(SearchSession, id=session_id)
        
        # Verify ownership
        if session.owner != request.user:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Get execution statistics
        stats = get_execution_statistics(session_id)
        
        # Get current executions
        executions = SearchExecution.objects.filter(
            query__session=session
        ).values('id', 'status', 'results_count', 'error_message')
        
        # Calculate overall progress
        total_queries = stats['total_executions']
        completed_queries = stats['successful_executions'] + stats['failed_executions']
        progress = (completed_queries / total_queries * 100) if total_queries > 0 else 0
        
        # Determine if still running
        has_running = any(e['status'] in ['pending', 'running'] for e in executions)
        
        response_data = {
            'session_id': session_id,
            'session_status': session.status,
            'progress': round(progress, 1),
            'statistics': stats,
            'executions': list(executions),
            'has_running': has_running,
            'total_results': session.total_results,
            'updated_at': timezone.now().isoformat(),
        }
        
        return JsonResponse(response_data)
        
    except Http404:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        logger.error(f"Error getting session progress: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


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
        if execution.query.session.owner != request.user:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Check if can retry
        if not execution.can_retry():
            return JsonResponse({
                'success': False,
                'error': 'Execution cannot be retried',
                'reason': 'Maximum retry attempts reached or invalid status'
            }, status=400)
        
        # Get retry strategy
        retry_strategy = optimize_retry_strategy(execution)
        
        if not retry_strategy['should_retry']:
            return JsonResponse({
                'success': False,
                'error': 'Retry not recommended',
                'reason': retry_strategy.get('modifications', ['Manual intervention required'])[0]
            }, status=400)
        
        # Schedule retry
        with transaction.atomic():
            execution.retry_count += 1
            execution.status = 'pending'
            execution.error_message = ''
            execution.save(update_fields=['retry_count', 'status', 'error_message'])
            
            # Schedule task with recommended delay
            task = retry_failed_execution_task.apply_async(
                args=[str(execution.id)],
                countdown=retry_strategy['delay_seconds']
            )
            
            # Update task ID
            execution.celery_task_id = task.id
            execution.save(update_fields=['celery_task_id'])
        
        response_data = {
            'success': True,
            'execution_id': str(execution.id),
            'task_id': task.id,
            'retry_count': execution.retry_count,
            'delay_seconds': retry_strategy['delay_seconds'],
            'message': f"Retry scheduled with {retry_strategy['delay_seconds']}s delay"
        }
        
        return JsonResponse(response_data)
        
    except Http404:
        return JsonResponse({'error': 'Execution not found'}, status=404)
    except Exception as e:
        logger.error(f"Error retrying execution: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to schedule retry',
            'details': str(e)
        }, status=500)
