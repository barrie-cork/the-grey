"""
Utility functions for the review_manager app.

This module contains helper functions for session management, workflow state transitions,
progress calculations, and other common operations related to SearchSession management.
"""

from typing import Any, Dict, List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, QuerySet

from .models import SearchSession, SessionActivity

User = get_user_model()


def get_session_statistics(user: User) -> Dict[str, Any]:
    """
    Get comprehensive statistics for a user's search sessions.

    Args:
        user: The user to get statistics for

    Returns:
        Dictionary containing session statistics
    """
    sessions = SearchSession.objects.filter(owner=user)

    total_sessions = sessions.count()
    status_counts = sessions.values("status").annotate(count=Count("status"))

    # Calculate progress metrics
    total_results = sum(session.total_results for session in sessions)
    total_reviewed = sum(session.reviewed_results for session in sessions)
    total_included = sum(session.included_results for session in sessions)

    return {
        "total_sessions": total_sessions,
        "status_distribution": {
            item["status"]: item["count"] for item in status_counts
        },
        "total_results_found": total_results,
        "total_results_reviewed": total_reviewed,
        "total_results_included": total_included,
        "overall_inclusion_rate": (
            round((total_included / total_reviewed * 100), 1)
            if total_reviewed > 0
            else 0
        ),
        "active_sessions": sessions.exclude(
            status__in=["completed", "archived"]
        ).count(),
        "completed_sessions": sessions.filter(status="completed").count(),
    }


def validate_status_transition(
    session: SearchSession, new_status: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate if a status transition is allowed and return validation result.

    Args:
        session: The SearchSession instance
        new_status: The desired new status

    Returns:
        Tuple of (is_valid, error_message)
    """
    if session.status == new_status:
        return True, None

    if session.can_transition_to(new_status):
        return True, None

    allowed_transitions = session.get_allowed_transitions()
    error_msg = (
        f"Cannot transition from '{session.get_status_display()}' to '{dict(SearchSession.STATUS_CHOICES)[new_status]}'. "
        f"Allowed transitions: {', '.join([dict(SearchSession.STATUS_CHOICES)[status] for status in allowed_transitions])}"
    )

    return False, error_msg


def transition_session_status(
    session: SearchSession,
    new_status: str,
    user: Optional[User] = None,
    description: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Safely transition a session to a new status with activity logging.

    Args:
        session: The SearchSession instance
        new_status: The desired new status
        user: User performing the transition (defaults to session owner)
        description: Custom description for the activity log

    Returns:
        Tuple of (success, error_message)
    """
    is_valid, error_msg = validate_status_transition(session, new_status)
    if not is_valid:
        return False, error_msg

    old_status = session.status
    session.status = new_status

    try:
        session.save()

        # Log the activity
        if not description:
            description = f"Status changed from {dict(SearchSession.STATUS_CHOICES)[old_status]} to {dict(SearchSession.STATUS_CHOICES)[new_status]}"

        SessionActivity.log_activity(
            session=session,
            activity_type="status_changed",
            description=description,
            user=user,
            metadata={"old_status": old_status, "new_status": new_status},
        )

        return True, None

    except Exception as e:
        return False, str(e)


def get_sessions_by_status(user: User, status: Optional[str] = None) -> QuerySet:
    """
    Get user's sessions filtered by status with optimized queries.

    Args:
        user: The user to get sessions for
        status: Optional status filter

    Returns:
        QuerySet of SearchSession instances
    """
    sessions = SearchSession.objects.filter(owner=user).select_related("owner")

    if status:
        sessions = sessions.filter(status=status)

    return sessions.order_by("-updated_at")


def get_recent_activities(session: SearchSession, limit: int = 10) -> QuerySet:
    """
    Get recent activities for a session with user information.

    Args:
        session: The SearchSession instance
        limit: Maximum number of activities to return

    Returns:
        QuerySet of SessionActivity instances
    """
    return (
        SessionActivity.objects.filter(session=session)
        .select_related("user")
        .order_by("-created_at")[:limit]
    )


def calculate_workflow_progress(session: SearchSession) -> Dict[str, Any]:
    """
    Calculate detailed workflow progress information.

    Args:
        session: The SearchSession instance

    Returns:
        Dictionary containing progress information
    """
    status_order = [
        status[0] for status in SearchSession.STATUS_CHOICES if status[0] != "archived"
    ]
    current_index = (
        status_order.index(session.status) if session.status in status_order else 0
    )
    total_steps = len(status_order)

    return {
        "current_step": current_index + 1,
        "total_steps": total_steps,
        "percentage": (
            round((current_index / (total_steps - 1)) * 100, 1)
            if total_steps > 1
            else 0
        ),
        "status_display": session.get_status_display(),
        "next_statuses": [
            dict(SearchSession.STATUS_CHOICES)[status]
            for status in session.get_allowed_transitions()
        ],
        "is_complete": session.status == "completed",
        "is_archived": session.status == "archived",
    }


def get_dashboard_summary(user: User) -> Dict[str, Any]:
    """
    Get summary data for the user's dashboard.

    Args:
        user: The user to get dashboard data for

    Returns:
        Dictionary containing dashboard summary
    """
    sessions = SearchSession.objects.filter(owner=user)

    # Get sessions by status
    draft_sessions = sessions.filter(status="draft").count()
    active_sessions = sessions.exclude(
        status__in=["completed", "archived", "draft"]
    ).count()
    completed_sessions = sessions.filter(status="completed").count()

    # Get recent sessions
    recent_sessions = sessions.order_by("-updated_at")[:5]

    # Calculate totals
    total_results = sessions.aggregate(total=Count("total_results"))["total"] or 0

    return {
        "total_sessions": sessions.count(),
        "draft_sessions": draft_sessions,
        "active_sessions": active_sessions,
        "completed_sessions": completed_sessions,
        "recent_sessions": recent_sessions,
        "total_results_across_sessions": sum(s.total_results for s in sessions),
        "requires_attention": sessions.filter(
            Q(status="ready_to_execute") | Q(status="ready_for_review")
        ).count(),
    }


def bulk_update_session_tags(
    sessions: List[SearchSession],
    tags_to_add: List[str],
    tags_to_remove: List[str] = None,
) -> int:
    """
    Bulk update tags for multiple sessions.

    Args:
        sessions: List of SearchSession instances
        tags_to_add: List of tags to add
        tags_to_remove: List of tags to remove (optional)

    Returns:
        Number of sessions updated
    """
    updated_count = 0
    tags_to_remove = tags_to_remove or []

    for session in sessions:
        current_tags = set(session.tags)
        current_tags.update(tags_to_add)
        current_tags.difference_update(tags_to_remove)

        session.tags = list(current_tags)
        session.save(update_fields=["tags", "updated_at"])
        updated_count += 1

    return updated_count


def get_sessions_needing_attention(user: User) -> QuerySet:
    """
    Get sessions that need user attention (ready for next action).

    Args:
        user: The user to get sessions for

    Returns:
        QuerySet of SearchSession instances needing attention
    """
    attention_statuses = ["ready_to_execute", "ready_for_review"]
    return SearchSession.objects.filter(
        owner=user, status__in=attention_statuses
    ).order_by("updated_at")
