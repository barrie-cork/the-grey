"""
Simple progress tracking for review completion.
"""

from typing import Any, Dict


class SimpleReviewProgressService:
    """Simple progress tracking for review completion."""

    def get_progress_summary(self, session_id: str) -> Dict[str, Any]:
        """Get basic progress statistics."""
        from apps.results_manager.models import ProcessedResult

        from ..models import SimpleReviewDecision

        total_results = ProcessedResult.objects.filter(session_id=session_id).count()
        decisions = SimpleReviewDecision.objects.filter(result__session_id=session_id)

        reviewed_count = decisions.exclude(decision="pending").count()
        include_count = decisions.filter(decision="include").count()
        exclude_count = decisions.filter(decision="exclude").count()
        maybe_count = decisions.filter(decision="maybe").count()
        pending_count = total_results - reviewed_count

        return {
            "total_results": total_results,
            "reviewed_count": reviewed_count,
            "pending_count": pending_count,
            "include_count": include_count,
            "exclude_count": exclude_count,
            "maybe_count": maybe_count,
            "completion_percentage": (
                round((reviewed_count / total_results * 100), 1)
                if total_results > 0
                else 0
            ),
        }
