"""
Internal API for review_results slice.
VSA-compliant data access without exposing models.
"""

from typing import Any, Dict, List


def get_review_decisions_data(session_id: str) -> List[Dict[str, Any]]:
    """
    Get review decisions for a session without exposing models.
    """
    from .models import SimpleReviewDecision

    decisions = SimpleReviewDecision.objects.filter(
        session_id=session_id
    ).select_related("result", "reviewer")

    return [
        {
            "id": str(decision.id),
            "result_id": str(decision.result.id),
            "decision": decision.decision,
            "decision_display": decision.get_decision_display(),
            "exclusion_reason": decision.exclusion_reason,
            "exclusion_reason_display": (
                decision.get_exclusion_reason_display()
                if decision.exclusion_reason
                else ""
            ),
            "notes": decision.notes,
            "reviewed_at": decision.reviewed_at.isoformat(),
            "reviewer_id": str(decision.reviewer.id) if decision.reviewer else None,
        }
        for decision in decisions
    ]


def get_decision_counts(session_id: str) -> Dict[str, int]:
    """Get decision counts for a session."""
    from django.db.models import Count

    from .models import SimpleReviewDecision

    decision_counts = (
        SimpleReviewDecision.objects.filter(session_id=session_id)
        .values("decision")
        .annotate(count=Count("decision"))
    )

    return {item["decision"]: item["count"] for item in decision_counts}


def get_review_progress_stats(session_id: str) -> Dict[str, Any]:
    """Get review progress statistics for a session."""
    from apps.results_manager.api import get_processed_results_count

    from .models import SimpleReviewDecision

    total_results = get_processed_results_count(session_id)

    decisions = SimpleReviewDecision.objects.filter(session_id=session_id)

    reviewed_count = decisions.exclude(decision="pending").count()
    pending_count = total_results - reviewed_count

    include_count = decisions.filter(decision="include").count()
    exclude_count = decisions.filter(decision="exclude").count()
    maybe_count = decisions.filter(decision="maybe").count()

    return {
        "total_results": total_results,
        "reviewed_results": reviewed_count,
        "pending_results": pending_count,
        "completion_percentage": (
            round((reviewed_count / total_results * 100), 1) if total_results > 0 else 0
        ),
        "included_results": include_count,
        "excluded_results": exclude_count,
        "maybe_results": maybe_count,
    }
