"""
Internal API for results_manager slice.
VSA-compliant data access without exposing models.
"""

from typing import Any, Dict, List


def get_processed_results_data(session_id: str) -> List[Dict[str, Any]]:
    """
    Get processed results data for a session without exposing models.
    """
    from .models import ProcessedResult

    results = ProcessedResult.objects.filter(session_id=session_id)

    return [
        {
            "id": str(result.id),
            "title": result.title,
            "url": result.url,
            "snippet": result.snippet,
            "document_type": result.document_type,
            "is_pdf": result.is_pdf,
            "has_full_text": result.has_full_text,  # Simplified quality indicator
            "publication_date": (
                result.publication_date.isoformat() if result.publication_date else None
            ),
            "is_duplicate": result.duplicate_group_id is not None,
        }
        for result in results
    ]


def get_processed_results_count(session_id: str) -> int:
    """Get count of processed results for a session."""
    from .models import ProcessedResult

    return ProcessedResult.objects.filter(session_id=session_id).count()


def get_duplicate_groups_data(session_id: str) -> List[Dict[str, Any]]:
    """Get duplicate group data for a session."""
    from .models import DuplicateGroup

    groups = DuplicateGroup.objects.filter(session_id=session_id)

    return [
        {
            "id": str(group.id),
            "canonical_url": group.canonical_url,
            "result_count": group.result_count,
            "similarity_type": group.similarity_type,
        }
        for group in groups
    ]


def get_deduplication_stats(session_id: str) -> Dict[str, Any]:
    """Get deduplication statistics for a session."""
    from .models import DuplicateGroup, ProcessedResult

    total_results = ProcessedResult.objects.filter(session_id=session_id).count()
    duplicate_groups = DuplicateGroup.objects.filter(session_id=session_id).count()
    duplicated_results = ProcessedResult.objects.filter(
        session_id=session_id, duplicate_group__isnull=False
    ).count()

    unique_results = total_results - duplicated_results + duplicate_groups

    return {
        "total_results": total_results,
        "duplicate_groups": duplicate_groups,
        "duplicated_results": duplicated_results,
        "unique_results": unique_results,
        "deduplication_rate": (
            round((duplicated_results / total_results * 100), 1)
            if total_results > 0
            else 0
        ),
    }
