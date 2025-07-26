"""
Tagging management service for review_results slice.
Business capability: Tag management, bulk operations, and tagging analytics.
"""

from typing import Any, Dict, List

from django.contrib.auth import get_user_model
from django.db.models import Count

User = get_user_model()

from apps.core.logging import ServiceLoggerMixin


class TaggingManagementService(ServiceLoggerMixin):
    """Service for managing tags and tagging operations."""

    def get_tag_usage_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        Get statistics on tag usage for a session.

        Args:
            session_id: UUID of the SearchSession

        Returns:
            Dictionary with tag usage statistics
        """
        from ..models import ReviewTagAssignment

        assignments = ReviewTagAssignment.objects.filter(result__session_id=session_id)

        if not assignments.exists():
            return {
                "total_assignments": 0,
                "unique_tags_used": 0,
                "tag_counts": {},
                "most_used_tag": None,
                "tag_type_distribution": {},
            }

        total_assignments = assignments.count()

        # Tag counts
        tag_counts = (
            assignments.values("tag__name")
            .annotate(count=Count("tag__name"))
            .order_by("-count")
        )

        tag_count_dict = {item["tag__name"]: item["count"] for item in tag_counts}
        most_used_tag = tag_counts[0]["tag__name"] if tag_counts else None

        # Tag type distribution
        type_counts = assignments.values("tag__tag_type").annotate(
            count=Count("tag__tag_type")
        )
        tag_type_distribution = {
            item["tag__tag_type"]: item["count"] for item in type_counts
        }

        return {
            "total_assignments": total_assignments,
            "unique_tags_used": len(tag_count_dict),
            "tag_counts": tag_count_dict,
            "most_used_tag": most_used_tag,
            "tag_type_distribution": tag_type_distribution,
        }

    def bulk_tag_results(
        self, result_ids: List[str], tag_ids: List[str], user: User, notes: str = ""
    ) -> int:
        """
        Apply tags to multiple results in bulk.

        Args:
            result_ids: List of ProcessedResult UUIDs
            tag_ids: List of ReviewTag UUIDs
            user: User performing the tagging
            notes: Optional notes for all assignments

        Returns:
            Number of tag assignments created
        """
        from apps.results_manager.models import ProcessedResult

        from ..models import ReviewTag, ReviewTagAssignment

        # Validate inputs
        valid_results = ProcessedResult.objects.filter(id__in=result_ids)
        valid_tags = ReviewTag.objects.filter(id__in=tag_ids)

        assignments_created = 0

        for result in valid_results:
            for tag in valid_tags:
                # Check if assignment already exists
                if not ReviewTagAssignment.objects.filter(
                    result=result, tag=tag
                ).exists():
                    ReviewTagAssignment.objects.create(
                        result=result, tag=tag, assigned_by=user, notes=notes
                    )
                    assignments_created += 1

        return assignments_created

    def bulk_remove_tags(
        self, result_ids: List[str], tag_ids: List[str], user: User
    ) -> int:
        """
        Remove tags from multiple results in bulk.

        Args:
            result_ids: List of ProcessedResult UUIDs
            tag_ids: List of ReviewTag UUIDs
            user: User performing the operation

        Returns:
            Number of tag assignments removed
        """
        from ..models import ReviewTagAssignment

        assignments_to_remove = ReviewTagAssignment.objects.filter(
            result_id__in=result_ids, tag_id__in=tag_ids
        )

        # Only allow removal of assignments made by the same user (or admin)
        if not user.is_staff:
            assignments_to_remove = assignments_to_remove.filter(assigned_by=user)

        count = assignments_to_remove.count()
        assignments_to_remove.delete()

        return count

    def get_tag_consistency_analysis(self, session_id: str) -> Dict[str, Any]:
        """
        Analyze consistency of tagging across reviewers.

        Args:
            session_id: UUID of the SearchSession

        Returns:
            Dictionary with consistency analysis
        """
        from ..models import ReviewTagAssignment

        assignments = ReviewTagAssignment.objects.filter(
            result__session_id=session_id
        ).select_related("tag", "assigned_by")

        result_reviews = self._group_assignments_by_result(assignments)
        conflicts, consistent_reviews = self._analyze_review_conflicts(result_reviews)
        agreement_rate = self._calculate_agreement_rate(
            result_reviews, consistent_reviews
        )

        return {
            "session_id": session_id,
            "total_results_reviewed": len(result_reviews),
            "multi_reviewed_results": len(
                [r for r in result_reviews.values() if len(r) > 1]
            ),
            "consistent_reviews": consistent_reviews,
            "conflicts_found": len(conflicts),
            "agreement_rate": agreement_rate,
            "conflicts": conflicts[:10],  # Limit to first 10 conflicts for display
        }

    def _group_assignments_by_result(self, assignments) -> Dict[str, List]:
        """Group assignments by result ID."""
        result_reviews = {}
        for assignment in assignments:
            result_id = str(assignment.result_id)
            if result_id not in result_reviews:
                result_reviews[result_id] = []
            result_reviews[result_id].append(assignment)
        return result_reviews

    def _analyze_review_conflicts(self, result_reviews: Dict[str, List]) -> tuple:
        """Analyze conflicts in review decisions."""
        conflicts = []
        consistent_reviews = 0

        for result_id, reviews in result_reviews.items():
            if len(reviews) > 1:
                decision_tags = [
                    r.tag.name for r in reviews if r.tag.tag_type == "decision"
                ]
                if len(set(decision_tags)) > 1:
                    conflicts.append(
                        {
                            "result_id": result_id,
                            "conflicting_tags": list(set(decision_tags)),
                            "reviewers": [r.assigned_by.username for r in reviews],
                            "assignments": reviews,
                        }
                    )
                else:
                    consistent_reviews += 1

        return conflicts, consistent_reviews

    def _calculate_agreement_rate(
        self, result_reviews: Dict[str, List], consistent_reviews: int
    ) -> float:
        """Calculate inter-reviewer agreement rate."""
        total_multi_reviewed = len([r for r in result_reviews.values() if len(r) > 1])
        if total_multi_reviewed > 0:
            return round((consistent_reviews / total_multi_reviewed) * 100, 1)
        return 0

    def suggest_tags_for_result(self, result_id: str) -> List[Dict[str, Any]]:
        """
        Suggest appropriate tags for a result based on similar results.

        Args:
            result_id: UUID of the ProcessedResult

        Returns:
            List of suggested tags with confidence scores
        """
        from apps.results_manager.models import ProcessedResult

        from ..models import ReviewTagAssignment

        try:
            target_result = ProcessedResult.objects.get(id=result_id)
        except ProcessedResult.DoesNotExist:
            return []

        # Find similar results that have been tagged - simplified approach
        similar_results = ProcessedResult.objects.filter(
            session_id=target_result.session_id,
            document_type=target_result.document_type,
        ).exclude(id=result_id)

        # Further filter by publication year if available
        if target_result.publication_year:
            similar_results = similar_results.filter(
                publication_year__gte=target_result.publication_year - 2,
                publication_year__lte=target_result.publication_year + 2,
            )

        # Get tags from similar results
        similar_assignments = ReviewTagAssignment.objects.filter(
            result__in=similar_results
        ).select_related("tag")

        # Count tag occurrences
        tag_suggestions = {}
        for assignment in similar_assignments:
            tag_name = assignment.tag.name
            if tag_name not in tag_suggestions:
                tag_suggestions[tag_name] = {
                    "tag": assignment.tag,
                    "count": 0,
                    "confidence": 0.0,
                }
            tag_suggestions[tag_name]["count"] += 1

        # Calculate confidence scores
        total_similar = similar_results.count()
        suggestions = []

        for tag_name, data in tag_suggestions.items():
            confidence = data["count"] / max(total_similar, 1)
            suggestions.append(
                {
                    "tag": data["tag"],
                    "confidence": round(confidence, 3),
                    "supporting_results": data["count"],
                    "reasoning": f"Applied to {data['count']} similar results",
                }
            )

        # Sort by confidence
        suggestions.sort(key=lambda x: x["confidence"], reverse=True)

        return suggestions[:5]  # Top 5 suggestions

    def create_custom_tag(
        self, name: str, tag_type: str, description: str, user: User
    ) -> Dict[str, Any]:
        """
        Create a custom tag for a session.

        Args:
            name: Tag name
            tag_type: Type of tag ('decision', 'quality', 'category', 'custom')
            description: Tag description
            user: User creating the tag

        Returns:
            Dictionary with creation result
        """
        from ..models import ReviewTag

        # Check if tag already exists
        if ReviewTag.objects.filter(name=name).exists():
            return {
                "success": False,
                "error": f'Tag "{name}" already exists',
                "tag": None,
            }

        # Validate tag type
        valid_types = ["decision", "quality", "category", "custom"]
        if tag_type not in valid_types:
            return {
                "success": False,
                "error": f'Invalid tag type. Must be one of: {", ".join(valid_types)}',
                "tag": None,
            }

        # Create the tag
        tag = ReviewTag.objects.create(
            name=name, tag_type=tag_type, description=description, created_by=user
        )

        return {"success": True, "error": None, "tag": tag}
