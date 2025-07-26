"""
URL configuration for the SERP execution module.
"""

from django.urls import path
from . import views

app_name = 'serp_execution'

urlpatterns = [
    # Main views
    path(
        'session/<uuid:session_id>/execute/',
        views.ExecuteSearchView.as_view(),
        name='execute_search'
    ),
    path(
        'session/<uuid:session_id>/status/',
        views.SearchExecutionStatusView.as_view(),
        name='execution_status'
    ),
    path(
        'execution/<uuid:execution_id>/recover/',
        views.ErrorRecoveryView.as_view(),
        name='error_recovery'
    ),
    
    # AJAX API endpoints
    path(
        'api/execution/<uuid:execution_id>/status/',
        views.execution_status_api,
        name='execution_status_api'
    ),
    path(
        'api/session/<uuid:session_id>/progress/',
        views.session_progress_api,
        name='session_progress_api'
    ),
    path(
        'api/execution/<uuid:execution_id>/retry/',
        views.retry_execution_api,
        name='retry_execution_api'
    ),
]