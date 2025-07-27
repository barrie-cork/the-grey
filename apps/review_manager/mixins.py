from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse


class UserOwnerMixin(UserPassesTestMixin):
    """Mixin to ensure user owns the session."""

    def test_func(self):
        session = self.get_object()
        return session.owner == self.request.user

    def handle_no_permission(self):
        messages.error(
            self.request, "You don't have permission to access this session."
        )
        return redirect("review_manager:dashboard")


class SessionNavigationMixin:
    """Mixin for smart session navigation based on status."""

    def get_session_next_url(self, session):
        """Determine where to send user when they click on a session."""
        navigation_map = {
            "draft": {
                "url": reverse(
                    "search_strategy:strategy_form", kwargs={"session_id": session.id}
                ),
                "text": "Define Search Strategy",
                "icon": "bi-search",
                "help": "Define your Population, Interest, and Context terms",
            },
            "defining_search": {
                "url": reverse(
                    "search_strategy:strategy_form", kwargs={"session_id": session.id}
                ),
                "text": "Complete Strategy",
                "icon": "bi-pencil",
                "help": "Finish defining your search strategy",
            },
            "ready_to_execute": {
                "url": reverse(
                    "serp_execution:execute_search", kwargs={"session_id": session.id}
                ),
                "text": "Execute Searches",
                "icon": "bi-play-circle",
                "help": "Run searches across selected sources",
            },
            "executing": {
                "url": reverse(
                    "serp_execution:execution_status", kwargs={"session_id": session.id}
                ),
                "text": "View Progress",
                "icon": "bi-hourglass-split",
                "help": "Monitor search execution progress",
            },
            "processing_results": {
                "url": reverse(
                    "serp_execution:execution_status", kwargs={"session_id": session.id}
                ),
                "text": "Processing Results",
                "icon": "bi-gear-wide-connected",
                "help": "Results are being processed",
            },
            "ready_for_review": {
                "url": f"/review-results/overview/{session.id}/",  # Placeholder URL
                "text": "Start Review",
                "icon": "bi-journal-check",
                "help": f"{session.total_results} results ready for review",
            },
            "under_review": {
                "url": f"/review-results/overview/{session.id}/",  # Placeholder URL
                "text": "Continue Review",
                "icon": "bi-journal-bookmark",
                "help": f"{session.reviewed_results} of {session.total_results} reviewed",
            },
            "completed": {
                "url": f"/reporting/summary/{session.id}/",  # Placeholder URL
                "text": "View Report",
                "icon": "bi-file-earmark-text",
                "help": "Access final report and export options",
            },
            "archived": {
                "url": f"/reporting/summary/{session.id}/",  # Placeholder URL
                "text": "View Archived",
                "icon": "bi-archive",
                "help": "Access archived review report",
            },
        }

        return navigation_map.get(
            session.status,
            {
                "url": reverse(
                    "review_manager:session_detail", kwargs={"session_id": session.id}
                ),
                "text": "View Details",
                "icon": "bi-info-circle",
                "help": "View session information",
            },
        )

    def get_status_explanation(self, status):
        """Get user-friendly explanation of session status."""
        explanations = {
            "draft": "Your session is created but needs a search strategy.",
            "defining_search": "You are defining the search strategy for this review.",
            "ready_to_execute": "Your search strategy is defined. Ready to execute searches.",
            "executing": "Searches are currently running across selected sources.",
            "processing_results": "Search results are being processed and deduplicated.",
            "ready_for_review": "Results are ready for your review.",
            "under_review": "You are actively reviewing the search results.",
            "completed": "Your review is complete and ready for reporting.",
            "archived": "This session has been archived but remains accessible.",
        }
        return explanations.get(status, "Session status unknown.")
