# Review Manager Views & API Implementation PRP

**PRP ID**: review-manager-views-api  
**Version**: 1.0  
**Date**: 2025-01-25  
**Status**: Ready for Implementation  
**Target App**: apps/review_manager  

## Goal

Implement comprehensive user-facing views and REST APIs for the Review Manager app following Django 4.2 best practices, meeting all user acceptance criteria from the PRD, and providing an intuitive experience for researchers conducting grey literature systematic reviews.

## Why

The Review Manager app is the central hub for the entire application. Users need intuitive views to:
- See all their search sessions at a glance
- Create new sessions quickly
- Navigate to the appropriate workflow step based on status
- Manage sessions (edit, delete, duplicate, archive)
- Track progress and understand session state

The API layer is needed for:
- Frontend interactivity (AJAX operations)
- Future mobile app support
- Integration with other services
- Programmatic access to session data

## Context

### Current State
- Models are fully implemented with 9-state workflow
- No views or URLs exist yet
- Authentication system is complete (accounts app)
- Project uses Django 4.2 with UUID primary keys
- Docker environment is configured

### Key Requirements
1. **Dashboard View**: Central hub showing all sessions with filtering
2. **Session CRUD**: Create, read, update, delete operations
3. **Smart Navigation**: Status-based routing to appropriate next steps
4. **REST API**: Full CRUD + custom actions via DRF
5. **Responsive Design**: Mobile-first approach
6. **Performance**: Dashboard loads < 2s with 100+ sessions
7. **Security**: Users can only access their own sessions

### User Acceptance Criteria (Key Items)
- UC-1.1.1: All review sessions visible in one place
- UC-1.2.1: Click on session card navigates to appropriate next step
- UC-2.1.4: Session creation completes in under 30 seconds
- UC-1.3.5: Any session findable within 10 seconds
- UC-4.1.5: User can identify session stage within 2 seconds

## Implementation

### Phase 1: Setup and Core Views

#### 1.1 Create URL Configuration

```python
# apps/review_manager/urls.py
from django.urls import path
from . import views

app_name = 'review_manager'

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Session CRUD
    path('sessions/create/', views.SessionCreateView.as_view(), name='create_session'),
    path('sessions/<uuid:session_id>/', views.SessionDetailView.as_view(), name='session_detail'),
    path('sessions/<uuid:session_id>/edit/', views.SessionUpdateView.as_view(), name='edit_session'),
    path('sessions/<uuid:session_id>/delete/', views.SessionDeleteView.as_view(), name='delete_session'),
    
    # Session Actions
    path('sessions/<uuid:session_id>/duplicate/', views.DuplicateSessionView.as_view(), name='duplicate_session'),
    path('sessions/<uuid:session_id>/archive/', views.ArchiveSessionView.as_view(), name='archive_session'),
    path('sessions/<uuid:session_id>/navigate/', views.SessionNavigateView.as_view(), name='session_navigate'),
]
```

#### 1.2 Create Forms

```python
# apps/review_manager/forms.py
from django import forms
from .models import SearchSession

class SessionCreateForm(forms.ModelForm):
    """Minimal form for session creation - just title and description."""
    
    class Meta:
        model = SearchSession
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Diabetes Management Guidelines Review',
                'autofocus': True,
                'required': True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Brief description of your systematic review objectives (optional)',
                'rows': 3,
            })
        }
        labels = {
            'title': 'Review Title',
            'description': 'Description (Optional)'
        }
        help_texts = {
            'title': 'Give your review a clear, descriptive title',
            'description': 'Add any additional context or objectives'
        }

class SessionEditForm(forms.ModelForm):
    """Form for editing session title and description only."""
    
    class Meta:
        model = SearchSession
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4})
        }
```

#### 1.3 Create Mixins

```python
# apps/review_manager/mixins.py
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse

class UserOwnerMixin(UserPassesTestMixin):
    """Mixin to ensure user owns the session."""
    
    def test_func(self):
        session = self.get_object()
        return session.owner == self.request.user
    
    def handle_no_permission(self):
        messages.error(
            self.request, 
            "You don't have permission to access this session."
        )
        return redirect('review_manager:dashboard')

class SessionNavigationMixin:
    """Mixin for smart session navigation based on status."""
    
    def get_session_next_url(self, session):
        """Determine where to send user when they click on a session."""
        navigation_map = {
            'draft': {
                'url': reverse('search_strategy:define', kwargs={'session_id': session.id}),
                'text': 'Define Search Strategy',
                'icon': 'bi-search',
                'help': 'Define your Population, Interest, and Context terms'
            },
            'defining_search': {
                'url': reverse('search_strategy:define', kwargs={'session_id': session.id}),
                'text': 'Complete Strategy',
                'icon': 'bi-pencil',
                'help': 'Finish defining your search strategy'
            },
            'ready_to_execute': {
                'url': reverse('serp_execution:execute', kwargs={'session_id': session.id}),
                'text': 'Execute Searches',
                'icon': 'bi-play-circle',
                'help': 'Run searches across selected sources'
            },
            'executing': {
                'url': reverse('serp_execution:status', kwargs={'session_id': session.id}),
                'text': 'View Progress',
                'icon': 'bi-hourglass-split',
                'help': 'Monitor search execution progress'
            },
            'processing_results': {
                'url': reverse('serp_execution:status', kwargs={'session_id': session.id}),
                'text': 'Processing Results',
                'icon': 'bi-gear-wide-connected',
                'help': 'Results are being processed'
            },
            'ready_for_review': {
                'url': reverse('review_results:overview', kwargs={'session_id': session.id}),
                'text': 'Start Review',
                'icon': 'bi-journal-check',
                'help': f'{session.total_results} results ready for review'
            },
            'under_review': {
                'url': reverse('review_results:overview', kwargs={'session_id': session.id}),
                'text': 'Continue Review',
                'icon': 'bi-journal-bookmark',
                'help': f'{session.reviewed_results} of {session.total_results} reviewed'
            },
            'completed': {
                'url': reverse('reporting:summary', kwargs={'session_id': session.id}),
                'text': 'View Report',
                'icon': 'bi-file-earmark-text',
                'help': 'Access final report and export options'
            },
            'archived': {
                'url': reverse('reporting:summary', kwargs={'session_id': session.id}),
                'text': 'View Archived',
                'icon': 'bi-archive',
                'help': 'Access archived review report'
            },
        }
        
        return navigation_map.get(
            session.status, 
            {
                'url': reverse('review_manager:session_detail', kwargs={'session_id': session.id}),
                'text': 'View Details',
                'icon': 'bi-info-circle',
                'help': 'View session information'
            }
        )
    
    def get_status_explanation(self, status):
        """Get user-friendly explanation of session status."""
        explanations = {
            'draft': 'Your session is created but needs a search strategy.',
            'defining_search': 'You are defining the search strategy for this review.',
            'ready_to_execute': 'Your search strategy is defined. Ready to execute searches.',
            'executing': 'Searches are currently running across selected sources.',
            'processing_results': 'Search results are being processed and deduplicated.',
            'ready_for_review': 'Results are ready for your review.',
            'under_review': 'You are actively reviewing the search results.',
            'completed': 'Your review is complete and ready for reporting.',
            'archived': 'This session has been archived but remains accessible.',
        }
        return explanations.get(status, 'Session status unknown.')
```

#### 1.4 Implement Views

```python
# apps/review_manager/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, DetailView, UpdateView, DeleteView, View
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.db.models import Q, Count, Prefetch
from django.http import HttpResponseForbidden

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
    
    def get_queryset(self):
        queryset = SearchSession.objects.filter(
            owner=self.request.user
        ).select_related('owner').prefetch_related(
            'activities',
            Prefetch('searchquery_set', to_attr='queries'),
            Prefetch('searchexecution_set', to_attr='executions')
        ).annotate(
            total_queries_count=Count('searchquery'),
            total_results_count=Count('rawsearchresult')
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
    
    def get_context_data(self, **kwargs):
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
    
    def form_valid(self, form):
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
        # Redirect to search strategy definition
        return reverse('search_strategy:define', kwargs={'session_id': self.object.id})


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
    
    def get(self, request, session_id):
        session = get_object_or_404(SearchSession, pk=session_id)
        
        # Check permission
        if session.owner != request.user:
            return HttpResponseForbidden()
        
        # Get navigation info and redirect
        nav_info = self.get_session_next_url(session)
        return redirect(nav_info['url'])
```

### Phase 2: Templates

#### 2.1 Base Template

```html
<!-- templates/review_manager/base.html -->
{% extends "base.html" %}
{% load static %}

{% block extra_css %}
<link rel="stylesheet" href="{% static 'review_manager/css/dashboard.css' %}">
<link rel="stylesheet" href="{% static 'review_manager/css/sessions.css' %}">
{% endblock %}

{% block breadcrumbs %}
<nav aria-label="breadcrumb">
    <ol class="breadcrumb">
        <li class="breadcrumb-item"><a href="{% url 'review_manager:dashboard' %}">Dashboard</a></li>
        {% block breadcrumb_items %}{% endblock %}
    </ol>
</nav>
{% endblock %}

{% block extra_js %}
<script src="{% static 'review_manager/js/messages.js' %}"></script>
<script src="{% static 'review_manager/js/dashboard.js' %}"></script>
{% endblock %}
```

#### 2.2 Dashboard Template

```html
<!-- templates/review_manager/dashboard.html -->
{% extends "review_manager/base.html" %}
{% load static session_tags %}

{% block title %}Your Literature Reviews - Thesis Grey{% endblock %}

{% block content %}
<div class="dashboard-container">
    <!-- Header Section -->
    <div class="dashboard-header">
        <div class="welcome-section">
            <h1>Your Literature Reviews</h1>
            <div class="quick-stats">
                <span class="stat">
                    <i class="bi bi-journal-text"></i>
                    <strong>{{ total_sessions }}</strong> Total
                </span>
                <span class="stat">
                    <i class="bi bi-activity"></i>
                    <strong>{{ active_sessions }}</strong> Active
                </span>
                <span class="stat">
                    <i class="bi bi-check-circle"></i>
                    <strong>{{ completed_sessions }}</strong> Completed
                </span>
            </div>
        </div>
        <a href="{% url 'review_manager:create_session' %}" 
           class="btn btn-primary btn-lg">
            <i class="bi bi-plus-lg"></i> New Review Session
        </a>
    </div>
    
    <!-- Filters Section -->
    <div class="filters-section">
        <form method="get" class="filter-form" id="dashboard-filter-form">
            <div class="row g-3">
                <div class="col-md-6">
                    <div class="search-box">
                        <input type="text" 
                               name="q" 
                               value="{{ search_query }}"
                               placeholder="Search sessions by title or description..."
                               class="form-control"
                               aria-label="Search sessions">
                    </div>
                </div>
                <div class="col-md-4">
                    <select name="status" 
                            class="form-select" 
                            onchange="this.form.submit()"
                            aria-label="Filter by status">
                        <option value="all">All Sessions</option>
                        <option value="active" {% if current_filter == 'active' %}selected{% endif %}>
                            Active Only
                        </option>
                        <option value="completed" {% if current_filter == 'completed' %}selected{% endif %}>
                            Completed
                        </option>
                        <option value="archived" {% if current_filter == 'archived' %}selected{% endif %}>
                            Archived
                        </option>
                    </select>
                </div>
                <div class="col-md-2">
                    {% if search_query or current_filter != 'all' %}
                    <a href="{% url 'review_manager:dashboard' %}" 
                       class="btn btn-outline-secondary w-100">
                        Clear Filters
                    </a>
                    {% endif %}
                </div>
            </div>
        </form>
    </div>
    
    <!-- Session Cards Grid -->
    <div class="sessions-grid">
        {% for session in sessions %}
            {% session_card session %}
        {% empty %}
        <div class="empty-state">
            <i class="bi bi-journal-x display-1 text-muted"></i>
            <h3>No sessions found</h3>
            <p class="text-muted">Create your first literature review to get started!</p>
            <a href="{% url 'review_manager:create_session' %}" 
               class="btn btn-primary">
                <i class="bi bi-plus-lg"></i> Create First Session
            </a>
        </div>
        {% endfor %}
    </div>
    
    <!-- Pagination -->
    {% if is_paginated %}
    <nav aria-label="Page navigation">
        <ul class="pagination justify-content-center">
            {% if page_obj.has_previous %}
            <li class="page-item">
                <a class="page-link" href="?page={{ page_obj.previous_page_number }}{% if search_query %}&q={{ search_query }}{% endif %}{% if current_filter != 'all' %}&status={{ current_filter }}{% endif %}">
                    Previous
                </a>
            </li>
            {% endif %}
            
            {% for num in page_obj.paginator.page_range %}
            <li class="page-item {% if page_obj.number == num %}active{% endif %}">
                <a class="page-link" href="?page={{ num }}{% if search_query %}&q={{ search_query }}{% endif %}{% if current_filter != 'all' %}&status={{ current_filter }}{% endif %}">
                    {{ num }}
                </a>
            </li>
            {% endfor %}
            
            {% if page_obj.has_next %}
            <li class="page-item">
                <a class="page-link" href="?page={{ page_obj.next_page_number }}{% if search_query %}&q={{ search_query }}{% endif %}{% if current_filter != 'all' %}&status={{ current_filter }}{% endif %}">
                    Next
                </a>
            </li>
            {% endif %}
        </ul>
    </nav>
    {% endif %}
</div>
{% endblock %}
```

### Phase 3: Template Tags

```python
# apps/review_manager/templatetags/session_tags.py
from django import template
from django.utils.html import format_html
from ..models import SearchSession
from ..mixins import SessionNavigationMixin

register = template.Library()

@register.inclusion_tag('review_manager/components/session_card.html')
def session_card(session):
    """Render a session card with all required information."""
    mixin = SessionNavigationMixin()
    nav_info = mixin.get_session_next_url(session)
    
    return {
        'session': session,
        'nav_info': nav_info,
        'status_class': get_status_class(session.status),
        'status_icon': get_status_icon(session.status),
    }

@register.filter
def status_badge(status):
    """Render a colored status badge."""
    status_colors = {
        'draft': 'secondary',
        'defining_search': 'info',
        'ready_to_execute': 'primary',
        'executing': 'warning',
        'processing_results': 'warning',
        'ready_for_review': 'success',
        'under_review': 'success',
        'completed': 'dark',
        'archived': 'secondary',
    }
    
    color = status_colors.get(status, 'secondary')
    display = dict(SearchSession.STATUS_CHOICES).get(status, status)
    
    return format_html(
        '<span class="badge bg-{}">{}</span>',
        color,
        display
    )

def get_status_class(status):
    """Helper to get CSS class for status."""
    return f'status-{status}'

def get_status_icon(status):
    """Helper to get icon for status."""
    icons = {
        'draft': 'bi-file-earmark',
        'defining_search': 'bi-pencil',
        'ready_to_execute': 'bi-play-circle',
        'executing': 'bi-hourglass-split',
        'processing_results': 'bi-gear-wide-connected',
        'ready_for_review': 'bi-journal-check',
        'under_review': 'bi-journal-bookmark',
        'completed': 'bi-check-circle',
        'archived': 'bi-archive',
    }
    return icons.get(status, 'bi-circle')
```

### Phase 4: API Implementation

#### 4.1 Create API Directory Structure

```bash
mkdir -p apps/review_manager/api
touch apps/review_manager/api/__init__.py
```

#### 4.2 API Serializers

```python
# apps/review_manager/api/serializers.py
from rest_framework import serializers
from ..models import SearchSession, SessionActivity

class SearchSessionSerializer(serializers.ModelSerializer):
    """Basic session serializer for list views."""
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    progress_percentage = serializers.FloatField(read_only=True)
    next_action = serializers.SerializerMethodField()
    
    class Meta:
        model = SearchSession
        fields = [
            'id', 'title', 'description', 'status', 'status_display',
            'owner', 'owner_username', 'created_at', 'updated_at',
            'total_queries', 'total_results', 'reviewed_results',
            'included_results', 'progress_percentage', 'next_action'
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']
    
    def get_next_action(self, obj):
        from ..mixins import SessionNavigationMixin
        mixin = SessionNavigationMixin()
        return mixin.get_session_next_url(obj)

class SearchSessionDetailSerializer(SearchSessionSerializer):
    """Detailed session serializer with related data."""
    recent_activities = serializers.SerializerMethodField()
    allowed_transitions = serializers.ListField(read_only=True)
    inclusion_rate = serializers.FloatField(read_only=True)
    
    class Meta(SearchSessionSerializer.Meta):
        fields = SearchSessionSerializer.Meta.fields + [
            'notes', 'tags', 'started_at', 'completed_at',
            'recent_activities', 'allowed_transitions', 'inclusion_rate'
        ]
    
    def get_recent_activities(self, obj):
        activities = obj.activities.select_related('user').order_by('-created_at')[:5]
        return SessionActivitySerializer(activities, many=True).data

class SessionActivitySerializer(serializers.ModelSerializer):
    """Activity log serializer."""
    user_username = serializers.CharField(source='user.username', read_only=True)
    activity_type_display = serializers.CharField(
        source='get_activity_type_display', 
        read_only=True
    )
    
    class Meta:
        model = SessionActivity
        fields = [
            'id', 'activity_type', 'activity_type_display',
            'description', 'user', 'user_username', 
            'created_at', 'metadata'
        ]
```

#### 4.3 API Views

```python
# apps/review_manager/api/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from ..models import SearchSession, SessionActivity
from .serializers import (
    SearchSessionSerializer, 
    SearchSessionDetailSerializer,
    SessionActivitySerializer
)

class SearchSessionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for search sessions.
    Provides CRUD operations and custom actions.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SearchSessionSerializer
    lookup_field = 'id'
    
    def get_queryset(self):
        return SearchSession.objects.filter(
            owner=self.request.user
        ).select_related('owner').prefetch_related(
            'activities',
            'searchquery_set',
            'searchexecution_set'
        )
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SearchSessionDetailSerializer
        return SearchSessionSerializer
    
    def perform_create(self, serializer):
        session = serializer.save(owner=self.request.user)
        SessionActivity.log_activity(
            session=session,
            activity_type='created',
            description='Session created via API',
            user=self.request.user
        )
    
    @action(detail=True, methods=['post'])
    def transition_status(self, request, id=None):
        """Transition session to new status with validation."""
        session = self.get_object()
        new_status = request.data.get('status')
        
        if not new_status:
            return Response(
                {'error': 'Status field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not session.can_transition_to(new_status):
            return Response(
                {'error': f'Cannot transition from {session.status} to {new_status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        old_status = session.status
        session.status = new_status
        session.save()
        
        SessionActivity.log_activity(
            session=session,
            activity_type='status_changed',
            description=f'Status changed from {old_status} to {new_status}',
            user=request.user,
            metadata={'old_status': old_status, 'new_status': new_status}
        )
        
        serializer = self.get_serializer(session)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, id=None):
        """Create a duplicate of the session."""
        original = self.get_object()
        
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
            description=f'Duplicated from session {original.id}',
            user=request.user,
            metadata={'original_session_id': str(original.id)}
        )
        
        serializer = self.get_serializer(duplicate)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False)
    def statistics(self, request):
        """Get user's session statistics."""
        sessions = self.get_queryset()
        
        stats = {
            'total_sessions': sessions.count(),
            'active_sessions': sessions.exclude(
                status__in=['completed', 'archived']
            ).count(),
            'completed_sessions': sessions.filter(status='completed').count(),
            'total_results_reviewed': sum(s.reviewed_results for s in sessions),
            'total_results_included': sum(s.included_results for s in sessions),
        }
        
        return Response(stats)
```

#### 4.4 API URLs

```python
# apps/review_manager/api/urls.py
from rest_framework.routers import DefaultRouter
from .views import SearchSessionViewSet

router = DefaultRouter()
router.register(r'sessions', SearchSessionViewSet, basename='session')

urlpatterns = router.urls
```

### Phase 5: Update Main URLs

```python
# grey_lit_project/urls.py
# Add these to the existing urlpatterns
path("", include("apps.review_manager.urls")),  # Dashboard at root
path("api/review-manager/", include("apps.review_manager.api.urls")),
```

### Phase 6: Static Files

#### 6.1 CSS

```css
/* static/review_manager/css/dashboard.css */

/* Mobile First Approach */
.dashboard-container {
    padding: 1rem;
}

.dashboard-header {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-bottom: 2rem;
}

.welcome-section h1 {
    font-size: 1.75rem;
    margin-bottom: 1rem;
}

.quick-stats {
    display: flex;
    gap: 1.5rem;
    flex-wrap: wrap;
}

.stat {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.9rem;
}

.stat i {
    font-size: 1.2rem;
    color: var(--bs-primary);
}

/* Session Grid */
.sessions-grid {
    display: grid;
    gap: 1.5rem;
    grid-template-columns: 1fr;
}

/* Session Card */
.session-card {
    background: var(--bs-white);
    border: 1px solid var(--bs-border-color);
    border-radius: 0.5rem;
    padding: 1.5rem;
    transition: all 0.2s ease;
    position: relative;
}

.session-card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);
}

.session-card .status-badge {
    position: absolute;
    top: 1rem;
    right: 1rem;
    font-size: 0.75rem;
}

/* Tablet and up */
@media (min-width: 768px) {
    .dashboard-header {
        flex-direction: row;
        justify-content: space-between;
        align-items: center;
    }
    
    .sessions-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

/* Desktop */
@media (min-width: 1200px) {
    .sessions-grid {
        grid-template-columns: repeat(3, 1fr);
        gap: 2rem;
    }
    
    .dashboard-container {
        padding: 2rem;
    }
}

/* Status-specific styling */
.status-draft { border-left: 4px solid var(--bs-secondary); }
.status-defining_search { border-left: 4px solid var(--bs-info); }
.status-ready_to_execute { border-left: 4px solid var(--bs-primary); }
.status-executing { border-left: 4px solid var(--bs-warning); }
.status-processing_results { border-left: 4px solid var(--bs-warning); }
.status-ready_for_review { border-left: 4px solid var(--bs-success); }
.status-under_review { border-left: 4px solid var(--bs-success); }
.status-completed { border-left: 4px solid var(--bs-dark); }
.status-archived { border-left: 4px solid var(--bs-secondary); }

/* Empty State */
.empty-state {
    text-align: center;
    padding: 4rem 2rem;
    grid-column: 1 / -1;
}

.empty-state h3 {
    margin: 1rem 0;
    color: var(--bs-gray-700);
}

/* Accessibility */
.session-card:focus-within {
    outline: 2px solid var(--bs-primary);
    outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
    .session-card {
        transition: none;
    }
}
```

#### 6.2 JavaScript

```javascript
// static/review_manager/js/dashboard.js
class DashboardManager {
    constructor() {
        this.initializeFilters();
        this.initializeCards();
        this.initializeMessages();
    }
    
    initializeFilters() {
        // Real-time search
        const searchInput = document.querySelector('input[name="q"]');
        if (searchInput) {
            let debounceTimer;
            searchInput.addEventListener('input', (e) => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    this.filterSessions(e.target.value);
                }, 300);
            });
        }
    }
    
    initializeCards() {
        // Make cards clickable
        document.querySelectorAll('.session-card').forEach(card => {
            const link = card.querySelector('.primary-action');
            if (link) {
                card.style.cursor = 'pointer';
                card.addEventListener('click', (e) => {
                    if (!e.target.closest('a, button')) {
                        link.click();
                    }
                });
            }
        });
    }
    
    filterSessions(query) {
        // Client-side filtering for immediate feedback
        const cards = document.querySelectorAll('.session-card');
        const lowerQuery = query.toLowerCase();
        
        cards.forEach(card => {
            const title = card.querySelector('.card-title').textContent.toLowerCase();
            const description = card.querySelector('.card-text').textContent.toLowerCase();
            
            if (title.includes(lowerQuery) || description.includes(lowerQuery)) {
                card.style.display = '';
            } else {
                card.style.display = 'none';
            }
        });
    }
    
    initializeMessages() {
        // Auto-dismiss messages
        document.querySelectorAll('.alert-dismissible').forEach(alert => {
            setTimeout(() => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        });
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    new DashboardManager();
});
```

## Validation

### Testing Checklist

1. **Unit Tests**:
   - [ ] Test all views with proper authentication
   - [ ] Test permission checks (UserOwnerMixin)
   - [ ] Test status transitions
   - [ ] Test form validation
   - [ ] Test API endpoints

2. **Integration Tests**:
   - [ ] Test complete session creation workflow
   - [ ] Test navigation based on status
   - [ ] Test filtering and search
   - [ ] Test pagination

3. **Performance Tests**:
   - [ ] Dashboard loads < 2s with 100+ sessions
   - [ ] Search returns results < 500ms
   - [ ] Session creation < 1s

4. **User Acceptance Tests**:
   - [ ] All UC criteria from PRD are met
   - [ ] Mobile responsive design works
   - [ ] Accessibility standards met

### Manual Testing Script

```bash
# 1. Run tests
python manage.py test apps.review_manager -v 2

# 2. Check code quality
flake8 apps/review_manager/ --max-line-length=120
mypy apps/review_manager/

# 3. Run development server
python manage.py runserver

# 4. Test URLs:
# - http://localhost:8000/ (Dashboard)
# - http://localhost:8000/sessions/create/ (Create session)
# - http://localhost:8000/api/review-manager/sessions/ (API)
```

## Known Issues & Solutions

1. **Navigation URLs for other apps**: The SessionNavigationMixin references URLs from other apps that don't exist yet. Solution: Comment out those entries temporarily or create placeholder views.

2. **Static files**: Ensure STATICFILES_DIRS includes app-specific static directories.

3. **Template tags**: Create empty `__init__.py` in templatetags directory.

## Success Metrics

1. All user acceptance criteria pass
2. 90%+ test coverage
3. Performance benchmarks met
4. No security vulnerabilities
5. Accessibility audit passes

## Next Steps

1. Create the directory structure
2. Implement views and forms
3. Create templates
4. Add static files
5. Write tests
6. Integration testing
7. Performance optimization