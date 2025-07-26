"""
Views for the results_manager app.

This module implements the Results Manager user interface including:
- Results overview with filtering and statistics
- Processing status with real-time updates
- API endpoints for status and result filtering
"""

import json
from typing import Dict, Any, List, Optional
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponseRedirect, HttpRequest, HttpResponse
from django.views.generic import TemplateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.review_manager.models import SearchSession
from .models import ProcessedResult, ProcessingSession, DuplicateGroup
from .utils import get_processing_statistics, prioritize_results_for_review


class ResultsOverviewView(LoginRequiredMixin, TemplateView):
    """
    Main results overview page showing processed results with filtering and statistics.
    
    This view implements the interface described in section 4.2 of the PRP:
    - Summary statistics (total, unique, duplicates, quality)
    - Filtering by domain, file type, quality score, duplicate status
    - Paginated results display with quality indicators
    """
    template_name = 'results_manager/results_overview.html'
    paginate_by = 50
    
    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        
        # Get session and validate ownership
        session_id = kwargs.get('session_id')
        session = get_object_or_404(
            SearchSession,
            id=session_id,
            owner=self.request.user
        )
        
        # Get processing session if exists
        processing_session = getattr(session, 'processing_session', None)
        
        # Get filter parameters
        filters = self._get_filter_params()
        
        # Get filtered results queryset
        results_qs = self._get_filtered_results(session_id, filters)
        
        # Paginate results
        paginator = Paginator(results_qs, self.paginate_by)
        page = self.request.GET.get('page', 1)
        
        try:
            results = paginator.page(page)
        except PageNotAnInteger:
            results = paginator.page(1)
        except EmptyPage:
            results = paginator.page(paginator.num_pages)
        
        # Get processing statistics
        stats = get_processing_statistics(str(session_id))
        
        # Get filter options for dropdowns
        filter_options = self._get_filter_options(session_id)
        
        context.update({
            'session': session,
            'processing_session': processing_session,
            'results': results,
            'statistics': stats,
            'filters': filters,
            'filter_options': filter_options,
            'is_processing': processing_session and processing_session.status == 'in_progress',
            'can_start_processing': (
                not processing_session or 
                processing_session.status in ['failed', 'pending']
            ),
            'processing_status': processing_session.status if processing_session else None,
        })
        
        return context
    
    def _get_filter_params(self) -> Dict[str, Any]:
        """Extract filter parameters from request."""
        return {
            'domain': self.request.GET.get('domain', ''),
            'file_type': self.request.GET.get('file_type', ''),
            'quality_min': self.request.GET.get('quality_min', ''),
            'duplicate_status': self.request.GET.get('duplicate_status', 'all'),
            'search_term': self.request.GET.get('search_term', ''),
            'sort_by': self.request.GET.get('sort_by', 'relevance'),
        }
    
    def _get_filtered_results(self, session_id: str, filters: Dict[str, Any]) -> Any:
        """Get filtered and sorted results queryset."""
        queryset = ProcessedResult.objects.filter(
            session_id=session_id
        ).select_related('duplicate_group', 'metadata')
        
        # Apply filters
        if filters['domain']:
            # Extract domain from URL for filtering
            queryset = queryset.extra(
                where=["LOWER(SUBSTRING(url FROM 'https?://([^/]+)')) LIKE %s"],
                params=[f"%{filters['domain'].lower()}%"]
            )
        
        if filters['file_type']:
            queryset = queryset.filter(document_type=filters['file_type'])
        
        if filters['quality_min']:
            try:
                min_quality = float(filters['quality_min'])
                queryset = queryset.filter(relevance_score__gte=min_quality)
            except (ValueError, TypeError):
                pass
        
        if filters['duplicate_status'] == 'duplicates':
            queryset = queryset.filter(duplicate_group__isnull=False)
        elif filters['duplicate_status'] == 'unique':
            queryset = queryset.filter(duplicate_group__isnull=True)
        
        if filters['search_term']:
            term = filters['search_term']
            queryset = queryset.filter(
                Q(title__icontains=term) |
                Q(snippet__icontains=term) |
                Q(source_organization__icontains=term)
            )
        
        # Apply sorting
        sort_options = {
            'relevance': '-relevance_score',
            'date': '-publication_date',
            'title': 'title',
            'quality': '-relevance_score',
        }
        
        sort_field = sort_options.get(filters['sort_by'], '-relevance_score')
        queryset = queryset.order_by(sort_field, '-created_at')
        
        return queryset
    
    def _get_filter_options(self, session_id: str) -> Dict[str, List]:
        """Get available filter options for dropdowns."""
        results = ProcessedResult.objects.filter(session_id=session_id)
        
        # Get unique document types
        document_types = list(
            results.exclude(document_type='')
            .values_list('document_type', flat=True)
            .distinct()
        )
        
        # Get domains from URLs
        domains = []
        domain_query = results.extra(
            select={'domain': "SUBSTRING(url FROM 'https?://([^/]+)')"}
        ).values_list('domain', flat=True).distinct()
        
        for domain in domain_query:
            if domain:
                # Clean up domain (remove www, etc.)
                clean_domain = domain.lower().replace('www.', '')
                if clean_domain not in domains:
                    domains.append(clean_domain)
        
        return {
            'document_types': sorted(document_types),
            'domains': sorted(domains),
            'quality_ranges': [
                ('0.8', '0.8+ (High Quality)'),
                ('0.6', '0.6+ (Good Quality)'),
                ('0.4', '0.4+ (Fair Quality)'),
                ('0.2', '0.2+ (Low Quality)'),
            ],
            'duplicate_options': [
                ('all', 'Show All'),
                ('unique', 'Unique Only'),
                ('duplicates', 'Duplicates Only'),
            ],
            'sort_options': [
                ('relevance', 'Relevance Score'),
                ('date', 'Publication Date'),
                ('title', 'Title (A-Z)'),
                ('quality', 'Quality Score'),
            ]
        }


class ProcessingStatusView(LoginRequiredMixin, TemplateView):
    """
    Processing status page with real-time updates.
    
    This view implements the interface described in section 4.3 of the PRP:
    - Overall progress bar and percentage
    - Current stage and stage-specific progress
    - Processing statistics (duplicates, errors, time remaining)
    - Action buttons (pause, view errors, cancel)
    """
    template_name = 'results_manager/processing_status.html'
    
    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        
        # Get session and validate ownership
        session_id = kwargs.get('session_id')
        session = get_object_or_404(
            SearchSession,
            id=session_id,
            owner=self.request.user
        )
        
        # Get or create processing session
        processing_session, created = ProcessingSession.objects.get_or_create(
            search_session=session,
            defaults={'status': 'pending'}
        )
        
        # Calculate stage completion percentages
        stage_info = self._get_stage_info(processing_session)
        
        # Get error details if any
        recent_errors = processing_session.error_details[-5:] if processing_session.error_details else []
        
        context.update({
            'session': session,
            'processing_session': processing_session,
            'stage_info': stage_info,
            'recent_errors': recent_errors,
            'can_retry': processing_session.status == 'failed',
            'can_cancel': processing_session.status == 'in_progress',
            'estimated_completion': processing_session.estimated_completion,
            'processing_time': processing_session.duration_seconds,
        })
        
        return context
    
    def _get_stage_info(self, processing_session: ProcessingSession) -> List[Dict[str, Any]]:
        """Get detailed information about each processing stage."""
        stages = [
            {'name': 'Initialization', 'key': 'initialization'},
            {'name': 'URL Normalization', 'key': 'url_normalization'},
            {'name': 'Metadata Extraction', 'key': 'metadata_extraction'},
            {'name': 'Deduplication', 'key': 'deduplication'},
            {'name': 'Quality Scoring', 'key': 'quality_scoring'},
            {'name': 'Finalization', 'key': 'finalization'},
        ]
        
        current_stage = processing_session.current_stage
        stage_progress = processing_session.stage_progress
        
        for i, stage in enumerate(stages):
            if stage['key'] == current_stage:
                stage['status'] = 'in_progress'
                stage['progress'] = stage_progress
                stage['icon'] = '⟳'
            elif i < [s['key'] for s in stages].index(current_stage):
                stage['status'] = 'completed'
                stage['progress'] = 100
                stage['icon'] = '✓'
            else:
                stage['status'] = 'pending'
                stage['progress'] = 0
                stage['icon'] = '○'
        
        return stages


class StartProcessingView(LoginRequiredMixin, TemplateView):
    """Handle starting results processing for a session."""
    
    def post(self, request: HttpRequest, session_id: str) -> HttpResponse:
        """Start processing for the session."""
        session = get_object_or_404(
            SearchSession,
            id=session_id,
            owner=request.user
        )
        
        # Import here to avoid circular imports
        from .tasks import process_session_results_task
        
        # Start processing task
        result = process_session_results_task.delay(str(session_id))
        
        # Update session status
        session.status = 'processing_results'
        session.save(update_fields=['status'])
        
        return HttpResponseRedirect(
            reverse('results_manager:processing_status', kwargs={'session_id': session_id})
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
            session = SearchSession.objects.get(
                id=session_id,
                owner=request.user
            )
            
            processing_session = getattr(session, 'processing_session', None)
            
            if not processing_session:
                return Response({
                    'status': 'not_started',
                    'message': 'Processing has not been started for this session'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Format response according to API spec
            response_data = {
                'status': processing_session.status,
                'progress_percentage': processing_session.progress_percentage,
                'current_stage': processing_session.current_stage or '',
                'stage_progress': processing_session.stage_progress,
                'total_raw_results': processing_session.total_raw_results,
                'processed_count': processing_session.processed_count,
                'duplicate_count': processing_session.duplicate_count,
                'error_count': processing_session.error_count,
                'started_at': processing_session.started_at.isoformat() if processing_session.started_at else None,
                'estimated_completion': processing_session.estimated_completion.isoformat() if processing_session.estimated_completion else None,
            }
            
            return Response(response_data)
            
        except SearchSession.DoesNotExist:
            return Response({
                'error': 'Session not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)


class ResultsFilterAPIView(APIView):
    """
    API endpoint for filtered results retrieval.
    
    Implements the API specification from section 6.2 of the PRP.
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request: HttpRequest, session_id: str) -> Response:
        """Get filtered processed results."""
        try:
            session = SearchSession.objects.get(
                id=session_id,
                owner=request.user
            )
            
            # Extract query parameters
            domain = request.query_params.get('domain', '')
            file_type = request.query_params.get('file_type', '')
            duplicate_status = request.query_params.get('duplicate_status', 'all')
            quality_score_min = request.query_params.get('quality_score_min', '')
            page = int(request.query_params.get('page', 1))
            page_size = min(int(request.query_params.get('page_size', 50)), 100)
            
            # Build queryset with filters
            queryset = ProcessedResult.objects.filter(session_id=session_id)
            
            if domain:
                queryset = queryset.extra(
                    where=["LOWER(SUBSTRING(url FROM 'https?://([^/]+)')) LIKE %s"],
                    params=[f"%{domain.lower()}%"]
                )
            
            if file_type:
                queryset = queryset.filter(document_type=file_type)
            
            if duplicate_status == 'duplicates':
                queryset = queryset.filter(duplicate_group__isnull=False)
            elif duplicate_status == 'unique':
                queryset = queryset.filter(duplicate_group__isnull=True)
            
            if quality_score_min:
                try:
                    min_score = float(quality_score_min)
                    queryset = queryset.filter(relevance_score__gte=min_score)
                except (ValueError, TypeError):
                    pass
            
            # Paginate
            paginator = Paginator(queryset.order_by('-relevance_score'), page_size)
            
            try:
                results_page = paginator.page(page)
            except (EmptyPage, PageNotAnInteger):
                results_page = paginator.page(1)
            
            # Serialize results
            results_data = []
            for result in results_page:
                results_data.append({
                    'id': str(result.id),
                    'title': result.title,
                    'url': result.url,
                    'snippet': result.snippet,
                    'document_type': result.document_type,
                    'publication_year': result.publication_year,
                    'relevance_score': result.relevance_score,
                    'has_full_text': result.has_full_text,
                    'is_duplicate': bool(result.duplicate_group),
                    'duplicate_count': result.duplicate_group.result_count if result.duplicate_group else 0,
                    'domain': result.get_display_url(),
                })
            
            # Build pagination info
            response_data = {
                'count': paginator.count,
                'next': None,
                'previous': None,
                'results': results_data
            }
            
            if results_page.has_next():
                response_data['next'] = f"?page={results_page.next_page_number()}"
            
            if results_page.has_previous():
                response_data['previous'] = f"?page={results_page.previous_page_number()}"
            
            return Response(response_data)
            
        except SearchSession.DoesNotExist:
            return Response({
                'error': 'Session not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)
