"""
URL configuration for review_results app.

This module defines the URL patterns for the Review Results views.
For now, it redirects to the results_manager for the main functionality.
"""

from django.urls import path
from django.shortcuts import redirect

app_name = 'review_results'

def redirect_to_results_manager(request, session_id):
    """Redirect review-results URLs to results-manager for now."""
    return redirect('results_manager:results_overview', session_id=session_id)

urlpatterns = [
    # Redirect review-results overview to results-manager
    path(
        'overview/<uuid:session_id>/',
        redirect_to_results_manager,
        name='overview'
    ),
]