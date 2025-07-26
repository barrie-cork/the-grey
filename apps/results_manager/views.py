"""
Views for the results_manager app.

This module implements the Results Manager user interface including:
- Results overview with filtering and statistics
- Processing status with real-time updates
- API endpoints for status and result filtering
"""

from typing import Any, Dict, List

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# Removed unused decorators
from rest_framework.views import APIView

from apps.review_manager.models import SearchSession

from .models import ProcessedResult, ProcessingSession
from .utils import get_processing_statistics


class ResultsOverviewView(LoginRequiredMixin, TemplateView):
    """
    Main results overview page showing processed results with filtering and statistics.

    This view implements the interface described in section 4.2 of the PRP:
    - Summary statistics (total, unique, duplicates, quality)
    - Filtering by domain, file type, quality score, duplicate status
    - Paginated results display with quality indicators
    """

    template_name = "results_manager/results_overview.html"
    paginate_by = 50

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)

        # Get session and validate ownership
        session_id = kwargs.get("session_id")
        session = get_object_or_404(
            SearchSession, id=session_id, owner=self.request.user
        )

        # Get processing session if exists
        processing_session = getattr(session, "processing_session", None)

        # Get results queryset (simplified - no filtering)
        results_qs = self._get_results(session_id)

        # Paginate results
        paginator = Paginator(results_qs, self.paginate_by)
        page = self.request.GET.get("page", 1)

        try:
            results = paginator.page(page)
        except PageNotAnInteger:
            results = paginator.page(1)
        except EmptyPage:
            results = paginator.page(paginator.num_pages)

        # Get processing statistics
        stats = get_processing_statistics(str(session_id))

        context.update(
            {
                "session": session,
                "processing_session": processing_session,
                "results": results,
                "statistics": stats,
                "is_processing": processing_session
                and processing_session.status == "in_progress",
                "can_start_processing": (
                    not processing_session
                    or processing_session.status in ["failed", "pending"]
                ),
                "processing_status": (
                    processing_session.status if processing_session else None
                ),
            }
        )

        return context

    def _get_results(self, session_id: str) -> Any:
        """Get simple results queryset without filtering."""
        return ProcessedResult.objects.filter(session_id=session_id).select_related(
            "duplicate_group"
        ).order_by("-processed_at")


class ProcessingStatusView(LoginRequiredMixin, TemplateView):
    """
    Processing status page with real-time updates.

    This view implements the interface described in section 4.3 of the PRP:
    - Overall progress bar and percentage
    - Current stage and stage-specific progress
    - Processing statistics (duplicates, errors, time remaining)
    - Action buttons (pause, view errors, cancel)
    """

    template_name = "results_manager/processing_status.html"

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)

        # Get session and validate ownership
        session_id = kwargs.get("session_id")
        session = get_object_or_404(
            SearchSession, id=session_id, owner=self.request.user
        )

        # Get or create processing session
        processing_session, created = ProcessingSession.objects.get_or_create(
            search_session=session, defaults={"status": "pending"}
        )

        # Calculate stage completion percentages
        stage_info = self._get_stage_info(processing_session)

        # Get error details if any
        recent_errors = (
            processing_session.error_details[-5:]
            if processing_session.error_details
            else []
        )

        context.update(
            {
                "session": session,
                "processing_session": processing_session,
                "stage_info": stage_info,
                "recent_errors": recent_errors,
                "can_retry": processing_session.status == "failed",
                "can_cancel": processing_session.status == "in_progress",
                "estimated_completion": processing_session.estimated_completion,
                "processing_time": processing_session.duration_seconds,
            }
        )

        return context

    def _get_stage_info(
        self, processing_session: ProcessingSession
    ) -> List[Dict[str, Any]]:
        """Get detailed information about each processing stage."""
        stages = [
            {"name": "Initialization", "key": "initialization"},
            {"name": "URL Normalization", "key": "url_normalization"},
            {"name": "Metadata Extraction", "key": "metadata_extraction"},
            {"name": "Deduplication", "key": "deduplication"},
            {"name": "Quality Scoring", "key": "quality_scoring"},
            {"name": "Finalization", "key": "finalization"},
        ]

        current_stage = processing_session.current_stage or "initialization"
        stage_progress = processing_session.stage_progress

        # Find current stage index safely
        stage_keys = [s["key"] for s in stages]
        current_stage_index = (
            stage_keys.index(current_stage) if current_stage in stage_keys else -1
        )

        for i, stage in enumerate(stages):
            if stage["key"] == current_stage:
                stage["status"] = "in_progress"
                stage["progress"] = stage_progress
                stage["icon"] = "⟳"
            elif current_stage_index >= 0 and i < current_stage_index:
                stage["status"] = "completed"
                stage["progress"] = 100
                stage["icon"] = "✓"
            else:
                stage["status"] = "pending"
                stage["progress"] = 0
                stage["icon"] = "○"

        return stages


class StartProcessingView(LoginRequiredMixin, TemplateView):
    """Handle starting results processing for a session."""

    def post(self, request: HttpRequest, session_id: str) -> HttpResponse:
        """Start processing for the session."""
        session = get_object_or_404(SearchSession, id=session_id, owner=request.user)

        # Import here to avoid circular imports
        from .tasks import process_session_results_task

        # Start processing task
        result = process_session_results_task.delay(str(session_id))

        # Update session status
        session.status = "processing_results"
        session.save(update_fields=["status"])

        return HttpResponseRedirect(
            reverse(
                "results_manager:processing_status", kwargs={"session_id": session_id}
            )
        )


# API Views for real-time updates and data retrieval


class ProcessingStatusAPIView(APIView):
    """
    API endpoint for real-time processing status updates.

    Implements the API specification from section 6.1 of the PRP.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: HttpRequest, session_id: str) -> Response:
        """Get current processing status."""
        try:
            session = SearchSession.objects.get(id=session_id, owner=request.user)

            processing_session = getattr(session, "processing_session", None)

            if not processing_session:
                return Response(
                    {
                        "status": "not_started",
                        "message": "Processing has not been started for this session",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Format response according to API spec
            response_data = {
                "status": processing_session.status,
                "progress_percentage": processing_session.progress_percentage,
                "current_stage": processing_session.current_stage or "",
                "stage_progress": processing_session.stage_progress,
                "total_raw_results": processing_session.total_raw_results,
                "processed_count": processing_session.processed_count,
                "duplicate_count": processing_session.duplicate_count,
                "error_count": processing_session.error_count,
                "started_at": (
                    processing_session.started_at.isoformat()
                    if processing_session.started_at
                    else None
                ),
                "estimated_completion": (
                    processing_session.estimated_completion.isoformat()
                    if processing_session.estimated_completion
                    else None
                ),
            }

            return Response(response_data)

        except SearchSession.DoesNotExist:
            return Response(
                {"error": "Session not found or access denied"},
                status=status.HTTP_404_NOT_FOUND,
            )


class ResultsListAPIView(APIView):
    """
    API endpoint for results retrieval (simplified without filtering).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: HttpRequest, session_id: str) -> Response:
        """Get processed results."""
        try:
            session = SearchSession.objects.get(id=session_id, owner=request.user)

            # Extract pagination parameters only
            page = int(request.query_params.get("page", 1))
            page_size = min(int(request.query_params.get("page_size", 50)), 100)

            # Simple queryset without filtering
            queryset = ProcessedResult.objects.filter(session_id=session_id).select_related(
                "duplicate_group"
            ).order_by("-processed_at")

            # Paginate
            paginator = Paginator(queryset, page_size)

            try:
                results_page = paginator.page(page)
            except (EmptyPage, PageNotAnInteger):
                results_page = paginator.page(1)

            # Serialize results
            results_data = []
            for result in results_page:
                results_data.append(
                    {
                        "id": str(result.id),
                        "title": result.title,
                        "url": result.url,
                        "snippet": result.snippet,
                        "document_type": result.document_type,
                        "publication_year": result.publication_year,
                        "is_pdf": result.is_pdf,
                        "is_duplicate": bool(result.duplicate_group),
                        "duplicate_count": (
                            result.duplicate_group.result_count
                            if result.duplicate_group
                            else 0
                        ),
                        "domain": result.get_display_url(),
                    }
                )

            # Build pagination info
            response_data = {
                "count": paginator.count,
                "next": None,
                "previous": None,
                "results": results_data,
            }

            if results_page.has_next():
                response_data["next"] = f"?page={results_page.next_page_number()}"

            if results_page.has_previous():
                response_data["previous"] = (
                    f"?page={results_page.previous_page_number()}"
                )

            return Response(response_data)

        except SearchSession.DoesNotExist:
            return Response(
                {"error": "Session not found or access denied"},
                status=status.HTTP_404_NOT_FOUND,
            )
