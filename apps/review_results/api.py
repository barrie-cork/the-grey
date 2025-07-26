"""
Internal API for review_results slice.
VSA-compliant data access without exposing models.
"""

from typing import Dict, List, Any


def get_review_assignments_data(session_id: str) -> List[Dict[str, Any]]:
    """
    Get review tag assignments for a session without exposing models.
    """
    from .models import ReviewTagAssignment
    
    assignments = ReviewTagAssignment.objects.filter(
        result__session_id=session_id
    ).select_related('tag', 'result')
    
    return [
        {
            'id': str(assignment.id),
            'result_id': str(assignment.result.id),
            'tag_name': assignment.tag.name,
            'tag_type': assignment.tag.tag_type,
            'notes': assignment.notes,
            'assigned_at': assignment.created_at.isoformat(),
            'assigned_by': str(assignment.assigned_by.id) if assignment.assigned_by else None,
        }
        for assignment in assignments
    ]


def get_tag_counts(session_id: str) -> Dict[str, int]:
    """Get tag usage counts for a session."""
    from .models import ReviewTagAssignment
    from django.db.models import Count
    
    tag_counts = ReviewTagAssignment.objects.filter(
        result__session_id=session_id
    ).values('tag__name').annotate(count=Count('tag__name'))
    
    return {item['tag__name']: item['count'] for item in tag_counts}


def get_review_progress_stats(session_id: str) -> Dict[str, Any]:
    """Get review progress statistics for a session."""
    from .models import ReviewTagAssignment
    from apps.results_manager.api import get_processed_results_count
    
    total_results = get_processed_results_count(session_id)
    
    reviewed_result_ids = ReviewTagAssignment.objects.filter(
        result__session_id=session_id
    ).values_list('result_id', flat=True).distinct()
    
    reviewed_count = len(reviewed_result_ids)
    pending_count = total_results - reviewed_count
    
    include_count = ReviewTagAssignment.objects.filter(
        result__session_id=session_id,
        tag__name='Include'
    ).count()
    
    exclude_count = ReviewTagAssignment.objects.filter(
        result__session_id=session_id,
        tag__name='Exclude'
    ).count()
    
    return {
        'total_results': total_results,
        'reviewed_results': reviewed_count,
        'pending_results': pending_count,
        'completion_percentage': round((reviewed_count / total_results * 100), 1) if total_results > 0 else 0,
        'included_results': include_count,
        'excluded_results': exclude_count,
    }