from typing import Any, Dict
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView, View
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.db.models import Q, Count, Prefetch, QuerySet
from django.http import HttpResponseForbidden, HttpResponse

from .models import SearchSession, SessionActivity
from .forms import SessionCreateForm, SessionEditForm
from .mixins import UserOwnerMixin, SessionNavigationMixin


class DashboardView(LoginRequiredMixin, SessionNavigationMixin, ListView):
    """
    Main dashboard showing all user's search sessions.
    Requirements: UC-1.1.1 through UC-1.3.5
    """
    model = SearchSession
    template_name = 'review_manager/dashboard.html'
    context_object_name = 'sessions'
    paginate_by = 12
    
    def get_queryset(self) -> QuerySet[SearchSession]:
        queryset = SearchSession.objects.filter(
            owner=self.request.user
        ).select_related('owner').prefetch_related(
            'activities'
        ).annotate(
            total_queries_count=Count('id'),  # Placeholder until other models exist
            total_results_count=Count('id')   # Placeholder until other models exist
        )
        
        # Apply filters
        status_filter = self.request.GET.get('status')
        search_query = self.request.GET.get('q')
        
        if status_filter and status_filter != 'all':
            if status_filter == 'active':
                queryset = queryset.exclude(
                    status__in=['completed', 'archived']
                )
            else:
                queryset = queryset.filter(status=status_filter)
        
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
        
        # Custom ordering with status priority
        return queryset.order_by('-updated_at')
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        all_sessions = SearchSession.objects.filter(owner=self.request.user)
        
        context.update({
            'total_sessions': all_sessions.count(),
            'active_sessions': all_sessions.exclude(
                status__in=['completed', 'archived']
            ).count(),
            'completed_sessions': all_sessions.filter(status='completed').count(),
            'current_filter': self.request.GET.get('status', 'all'),
            'search_query': self.request.GET.get('q', ''),
        })
        return context


class SessionCreateView(LoginRequiredMixin, CreateView):
    """
    Minimal session creation - just title and description.
    Requirements: UC-2.1.1 through UC-2.2.3
    """
    model = SearchSession
    form_class = SessionCreateForm
    template_name = 'review_manager/session_create.html'
    
    def form_valid(self, form) -> HttpResponse:
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        
        # Log activity
        SessionActivity.log_activity(
            session=self.object,
            activity_type='created',
            description=f'Session "{self.object.title}" created',
            user=self.request.user
        )
        
        messages.success(
            self.request,
            f'Review session "{self.object.title}" created successfully!'
        )
        return response
    
    def get_success_url(self):
        # Redirect to session detail for now (will redirect to search strategy later)
        return reverse('review_manager:session_detail', kwargs={'session_id': self.object.id})


class SessionDetailView(LoginRequiredMixin, UserOwnerMixin, SessionNavigationMixin, DetailView):
    """
    Comprehensive session details with smart navigation.
    Requirements: UC-5.1.1 through UC-5.2.3
    """
    model = SearchSession
    template_name = 'review_manager/session_detail.html'
    context_object_name = 'session'
    pk_url_kwarg = 'session_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.object
        
        # Get navigation info
        nav_info = self.get_session_next_url(session)
        
        # Get recent activities
        recent_activities = session.activities.select_related(
            'user'
        ).order_by('-created_at')[:10]
        
        # Status-specific context
        context.update({
            'nav_info': nav_info,
            'recent_activities': recent_activities,
            'can_edit': session.status in ['draft', 'defining_search'],
            'can_delete': session.status == 'draft',
            'can_archive': session.status == 'completed',
            'status_explanation': self.get_status_explanation(session.status),
            'progress_percentage': session.progress_percentage,
            'inclusion_rate': session.inclusion_rate,
            'allowed_transitions': session.get_allowed_transitions(),
        })
        
        return context


class SessionUpdateView(LoginRequiredMixin, UserOwnerMixin, UpdateView):
    """Edit session title and description only."""
    model = SearchSession
    form_class = SessionEditForm
    template_name = 'review_manager/session_edit.html'
    pk_url_kwarg = 'session_id'
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        SessionActivity.log_activity(
            session=self.object,
            activity_type='settings_changed',
            description='Session details updated',
            user=self.request.user
        )
        
        messages.success(
            self.request, 
            f'Session "{self.object.title}" has been updated successfully.'
        )
        return response
    
    def get_success_url(self):
        return reverse('review_manager:session_detail', kwargs={'session_id': self.object.id})


class SessionDeleteView(LoginRequiredMixin, UserOwnerMixin, DeleteView):
    """Delete draft sessions only."""
    model = SearchSession
    template_name = 'review_manager/session_confirm_delete.html'
    pk_url_kwarg = 'session_id'
    success_url = reverse_lazy('review_manager:dashboard')
    
    def test_func(self):
        # Additional check: only draft sessions can be deleted
        if not super().test_func():
            return False
        session = self.get_object()
        return session.status == 'draft'
    
    def delete(self, request, *args, **kwargs):
        session_title = self.get_object().title
        response = super().delete(request, *args, **kwargs)
        messages.success(
            request, 
            f'Session "{session_title}" has been deleted.'
        )
        return response


class DuplicateSessionView(LoginRequiredMixin, UserOwnerMixin, View):
    """Create a copy of an existing session."""
    
    def post(self, request, session_id):
        original = get_object_or_404(SearchSession, pk=session_id)
        
        # Check permission
        if original.owner != request.user:
            return HttpResponseForbidden()
        
        # Create duplicate
        duplicate = SearchSession.objects.create(
            title=f"{original.title} (Copy)",
            description=original.description,
            owner=request.user,
            status='draft',
            notes=original.notes,
            tags=original.tags.copy() if original.tags else []
        )
        
        SessionActivity.log_activity(
            session=duplicate,
            activity_type='created',
            description=f'Duplicated from session "{original.title}"',
            user=request.user,
            metadata={'original_session_id': str(original.id)}
        )
        
        messages.success(
            request,
            f'Session duplicated successfully. You can now edit "{duplicate.title}".'
        )
        
        return redirect('review_manager:edit_session', session_id=duplicate.id)


class ArchiveSessionView(LoginRequiredMixin, UserOwnerMixin, View):
    """Archive a completed session."""
    
    def post(self, request, session_id):
        session = get_object_or_404(SearchSession, pk=session_id)
        
        # Check permission and status
        if session.owner != request.user:
            return HttpResponseForbidden()
        
        if not session.can_transition_to('archived'):
            messages.error(request, 'This session cannot be archived in its current state.')
            return redirect('review_manager:session_detail', session_id=session.id)
        
        # Archive the session
        old_status = session.status
        session.status = 'archived'
        session.save()
        
        SessionActivity.log_activity(
            session=session,
            activity_type='status_changed',
            description=f'Session archived',
            user=request.user,
            metadata={'old_status': old_status, 'new_status': 'archived'}
        )
        
        messages.success(request, f'Session "{session.title}" has been archived.')
        return redirect('review_manager:dashboard')


class SessionNavigateView(LoginRequiredMixin, UserOwnerMixin, SessionNavigationMixin, View):
    """Smart navigation based on session status."""
    
    def get_object(self):
        """Get the session object for the UserOwnerMixin."""
        session_id = self.kwargs.get('session_id')
        return get_object_or_404(SearchSession, pk=session_id)
    
    def get(self, request, session_id):
        session = self.get_object()
        
        # Get navigation info and redirect
        nav_info = self.get_session_next_url(session)
        return redirect(nav_info['url'])