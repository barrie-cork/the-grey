"""
URL configuration for results_manager app.

This module defines the URL patterns for the Results Manager views and API endpoints.
"""

from django.urls import path

from . import views

app_name = "results_manager"

urlpatterns = [
    # Main views
    path(
        "results/<uuid:session_id>/",
        views.ResultsOverviewView.as_view(),
        name="results_overview",
    ),
    path(
        "processing/<uuid:session_id>/",
        views.ProcessingStatusView.as_view(),
        name="processing_status",
    ),
    path(
        "start-processing/<uuid:session_id>/",
        views.StartProcessingView.as_view(),
        name="start_processing",
    ),
    # API endpoints
    path(
        "api/processing-status/<uuid:session_id>/",
        views.ProcessingStatusAPIView.as_view(),
        name="api_processing_status",
    ),
    path(
        "api/results/<uuid:session_id>/",
        views.ResultsFilterAPIView.as_view(),
        name="api_results_filter",
    ),
]
