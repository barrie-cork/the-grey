"""
Signals for cross-slice communication in the review_manager app.
VSA-compliant event-driven communication.
"""

from typing import Any, Dict

from django.dispatch import Signal, receiver

# Session lifecycle signals
session_created = Signal()
session_status_changed = Signal()
session_deleted = Signal()

# Session data access signals for other slices
session_data_requested = Signal()


def get_session_data(session_id: str) -> Dict[str, Any]:
    """
    Internal API for controlled cross-slice data access.
    Returns session data without exposing internal models.
    """
    from .models import SearchSession

    try:
        session = SearchSession.objects.get(id=session_id)
        return {
            "id": str(session.id),
            "title": session.title,
            "status": session.status,
            "owner_id": str(session.owner.id),
            "created_at": session.created_at.isoformat(),
            "total_queries": session.total_queries,
            "total_results": session.total_results,
            "reviewed_results": session.reviewed_results,
            "included_results": session.included_results,
        }
    except SearchSession.DoesNotExist:
        return {}


def get_sessions_by_status(user_id: str, status: str = None) -> list:
    """
    Internal API to get sessions without exposing models.
    """
    from django.contrib.auth import get_user_model

    from .models import SearchSession

    User = get_user_model()

    try:
        user = User.objects.get(id=user_id)
        sessions = SearchSession.objects.filter(owner=user)

        if status:
            sessions = sessions.filter(status=status)

        return [
            {
                "id": str(session.id),
                "title": session.title,
                "status": session.status,
                "created_at": session.created_at.isoformat(),
                "total_results": session.total_results,
            }
            for session in sessions
        ]
    except Exception:
        return []


@receiver(session_status_changed)
def handle_status_change_request(
    sender, session_id, requested_status, reason, **kwargs
):
    """
    Handle status change requests from other slices.
    """
    from .models import SearchSession
    from .utils import transition_session_status

    try:
        session = SearchSession.objects.get(id=session_id)
        success, error = transition_session_status(
            session, requested_status, description=reason
        )

        if success and requested_status == "ready_to_execute":
            # Update query count from search_strategy slice
            from apps.search_strategy.signals import get_query_count

            session.total_queries = get_query_count(session_id)
            session.save(update_fields=["total_queries", "updated_at"])

    except SearchSession.DoesNotExist:
        pass
