"""
PRISMA reporting service for reporting slice.
Business capability: PRISMA-compliant report generation and flow diagram data.
"""

from datetime import datetime
from typing import Any, Dict

from django.utils import timezone

from apps.core.logging import ServiceLoggerMixin
from apps.reporting.constants import PRISMAConstants
from apps.results_manager.api import get_deduplication_stats
from apps.review_manager.models import SearchSession, SessionActivity
from apps.review_manager.signals import get_session_data
from apps.review_results.api import get_review_progress_stats
from apps.review_results.models import SimpleReviewDecision
from apps.search_strategy.signals import get_session_queries_data
from apps.serp_execution.api import get_raw_results_count, get_session_executions_data


class PrismaReportingService(ServiceLoggerMixin):
    """Service for generating PRISMA-compliant reports and flow diagrams."""

    def generate_prisma_flow_data(self, session_id: str) -> Dict[str, Any]:
        """
        Generate data for PRISMA flow diagram.

        Args:
            session_id: UUID of the SearchSession

        Returns:
            Dictionary with PRISMA flow data
        """
        # Get session data using internal API
        session_data = get_session_data(session_id)
        if not session_data:
            return {}

        # Stage 1: Identification - Get data from respective slices
        queries_data = get_session_queries_data(session_id)
        executions_data = get_session_executions_data(session_id)
        raw_results_count = get_raw_results_count(session_id)

        # Stage 2: Screening/Deduplication
        dedup_stats = get_deduplication_stats(session_id)

        # Stage 3: Eligibility/Review
        review_stats = get_review_progress_stats(session_id)

        # Generate flow data using API responses
        search_engines = set()
        for query in queries_data:
            if query.get("search_engines"):
                search_engines.update(query["search_engines"])

        flow_data = {
            "raw_search_results": raw_results_count,
            "duplicates_removed": dedup_stats["duplicated_results"],
            "processed_results": dedup_stats["unique_results"],
            "results_included": review_stats["included_results"],
            "results_excluded": review_stats["excluded_results"],
            "results_maybe": review_stats.get("maybe_results", 0),
            "results_pending": review_stats["pending_results"],
            "session_metadata": {
                "session_id": session_id,
                "title": session_data["title"],
                "created_date": session_data["created_at"][:10],
            },
        }


        return flow_data

    def calculate_review_period_from_data(
        self, session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate review period from session data.

        Args:
            session_data: Session data dictionary

        Returns:
            Dictionary with start_date, end_date, and duration_days
        """
        created_date = datetime.fromisoformat(
            session_data["created_at"].replace("Z", "+00:00")
        )

        return {
            "start_date": created_date.date().isoformat(),
            "end_date": created_date.date().isoformat(),  # Use same for now
            "duration_days": 1,
        }

    def get_exclusion_reasons(self, session_id: str) -> Dict[str, int]:
        """
        Get exclusion reasons and their counts.

        Args:
            session_id: UUID of the SearchSession

        Returns:
            Dictionary mapping exclusion reasons to counts
        """
        # Get excluded decisions with reasons
        excluded_decisions = SimpleReviewDecision.objects.filter(
            session_id=session_id, decision="exclude"
        )

        reasons = {}
        for decision in excluded_decisions:
            # Use exclusion_reason field first, fall back to notes
            reason = decision.exclusion_reason or decision.notes.strip()
            if reason:
                # Get display name for choice field
                if decision.exclusion_reason:
                    standardized_reason = decision.get_exclusion_reason_display()
                else:
                    # Clean up reason from notes
                    reason = reason.lower()
                    # Map to standardized reasons
                    if "not relevant" in reason or "irrelevant" in reason:
                        standardized_reason = PRISMAConstants.STANDARD_EXCLUSION_REASONS[
                            "not_relevant"
                        ]
                    elif "no full text" in reason or "full text unavailable" in reason:
                        standardized_reason = PRISMAConstants.STANDARD_EXCLUSION_REASONS[
                            "no_full_text"
                        ]
                    elif "duplicate" in reason:
                        standardized_reason = PRISMAConstants.STANDARD_EXCLUSION_REASONS[
                            "duplicate"
                        ]
                    elif "wrong document type" in reason or "document type" in reason:
                        standardized_reason = PRISMAConstants.STANDARD_EXCLUSION_REASONS[
                            "wrong_document_type"
                        ]
                    elif "language" in reason:
                        standardized_reason = PRISMAConstants.STANDARD_EXCLUSION_REASONS[
                            "language"
                        ]
                    else:
                        standardized_reason = reason.title()

                reasons[standardized_reason] = reasons.get(standardized_reason, 0) + 1

        return reasons

    def calculate_review_period(self, session) -> Dict[str, Any]:
        """
        Calculate the time period of the systematic review.

        Args:
            session: SearchSession instance

        Returns:
            Dictionary with review period information
        """
        period_info = {
            "start_date": session.created_at.date(),
            "end_date": (
                session.completed_at.date()
                if session.completed_at
                else timezone.now().date()
            ),
            "duration_days": 0,
            "phases": [],
        }

        if session.completed_at:
            duration = session.completed_at.date() - session.created_at.date()
            period_info["duration_days"] = duration.days

        # Calculate phase durations based on status changes
        activities = SessionActivity.objects.filter(
            session=session, activity_type="status_changed"
        ).order_by("created_at")

        phase_start = session.created_at
        for activity in activities:
            if activity.metadata and "new_status" in activity.metadata:
                phase_duration = (activity.created_at - phase_start).days
                period_info["phases"].append(
                    {
                        "status": activity.metadata.get("old_status", "draft"),
                        "duration_days": phase_duration,
                        "end_date": activity.created_at.date(),
                    }
                )
                phase_start = activity.created_at

        return period_info

    def export_prisma_checklist(self, session_id: str) -> Dict[str, Any]:
        """
        Generate PRISMA checklist with completion status.

        Args:
            session_id: UUID of the SearchSession

        Returns:
            Dictionary with PRISMA checklist data
        """
        try:
            session = SearchSession.objects.get(id=session_id)
        except SearchSession.DoesNotExist:
            return {}

        # PRISMA 2020 checklist items
        checklist_items = [
            {
                "section": "Title",
                "item": 1,
                "description": "Identify the report as a systematic review.",
                "completed": bool(
                    session.title and "systematic" in session.title.lower()
                ),
                "evidence": session.title if session.title else None,
            },
            {
                "section": "Abstract",
                "item": 2,
                "description": "See the PRISMA 2020 for Abstracts checklist.",
                "completed": bool(session.description),
                "evidence": session.description if session.description else None,
            },
            {
                "section": "Rationale",
                "item": 3,
                "description": "Describe the rationale for the review in the context of existing knowledge.",
                "completed": bool(
                    session.description
                    and len(session.description)
                    > PRISMAConstants.MIN_DESCRIPTION_LENGTH
                ),
                "evidence": "Description provided" if session.description else None,
            },
            {
                "section": "Objectives",
                "item": 4,
                "description": "Provide an explicit statement of the objective(s) or question(s) the review addresses.",
                "completed": bool(session.description),
                "evidence": (
                    "Objectives in description" if session.description else None
                ),
            },
            # Note: This is a simplified version. A full implementation would include all PRISMA items
        ]

        # Calculate completion statistics
        completed_items = sum(1 for item in checklist_items if item["completed"])
        total_items = len(checklist_items)
        completion_percentage = round(
            completed_items / total_items * PRISMAConstants.PERCENTAGE_MULTIPLIER, 1
        )

        return {
            "session_id": session_id,
            "checklist_items": checklist_items,
            "completion_summary": {
                "completed_items": completed_items,
                "total_items": total_items,
                "completion_percentage": completion_percentage,
            },
            "generated_at": timezone.now().isoformat(),
        }
