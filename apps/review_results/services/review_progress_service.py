"""
Review progress tracking service for review_results slice.
Business capability: Review progress tracking and velocity calculation.
"""

from typing import Dict, Any
from django.db.models import Count
from django.utils import timezone

from apps.core.logging import ServiceLoggerMixin


class ReviewProgressService(ServiceLoggerMixin):
    """Service for tracking review progress and calculating velocity metrics."""
    
    def calculate_review_progress(self, session_id: str) -> Dict[str, Any]:
        """
        Calculate review progress for a session.
        
        Args:
            session_id: UUID of the SearchSession
            
        Returns:
            Dictionary with review progress information
        """
        from apps.results_manager.models import ProcessedResult
        from ..models import ReviewTagAssignment
        
        results = ProcessedResult.objects.filter(session_id=session_id)
        total_results = results.count()
        
        if total_results == 0:
            return {
                'total_results': 0,
                'reviewed_results': 0,
                'pending_results': 0,
                'completion_percentage': 0,
                'tag_distribution': {},
                'review_velocity': 0
            }
        
        # Count reviewed results (those with tag assignments)
        reviewed_result_ids = ReviewTagAssignment.objects.filter(
            result__session_id=session_id
        ).values_list('result_id', flat=True).distinct()
        
        reviewed_count = len(reviewed_result_ids)
        pending_count = total_results - reviewed_count
        completion_percentage = round((reviewed_count / total_results) * 100, 1)
        
        # Tag distribution
        tag_counts = ReviewTagAssignment.objects.filter(
            result__session_id=session_id
        ).values('tag__name').annotate(count=Count('tag__name'))
        
        tag_distribution = {item['tag__name']: item['count'] for item in tag_counts}
        
        return {
            'total_results': total_results,
            'reviewed_results': reviewed_count,
            'pending_results': pending_count,
            'completion_percentage': completion_percentage,
            'tag_distribution': tag_distribution,
            'review_velocity': self.calculate_review_velocity(session_id)
        }
    
    def calculate_review_velocity(self, session_id: str) -> float:
        """
        Calculate review velocity (results reviewed per day).
        
        Args:
            session_id: UUID of the SearchSession
            
        Returns:
            Average results reviewed per day
        """
        from ..models import ReviewTagAssignment
        
        # Get assignments from the last 7 days
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)
        recent_assignments = ReviewTagAssignment.objects.filter(
            result__session_id=session_id,
            created_at__gte=seven_days_ago
        )
        
        if not recent_assignments.exists():
            return 0.0
        
        # Count unique results reviewed in the last 7 days
        unique_results = recent_assignments.values('result_id').distinct().count()
        
        return round(unique_results / 7, 1)
    
    def get_review_timeline(self, session_id: str) -> Dict[str, Any]:
        """
        Get timeline of review activities for a session.
        
        Args:
            session_id: UUID of the SearchSession
            
        Returns:
            Dictionary with review timeline data
        """
        from ..models import ReviewTagAssignment
        from django.db.models import TruncDate
        
        assignments = ReviewTagAssignment.objects.filter(
            result__session_id=session_id
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        timeline = []
        for item in assignments:
            timeline.append({
                'date': item['date'].isoformat(),
                'reviews_completed': item['count']
            })
        
        return {
            'session_id': session_id,
            'timeline': timeline,
            'total_review_days': len(timeline)
        }
    
    def estimate_completion_time(self, session_id: str) -> Dict[str, Any]:
        """
        Estimate time to complete review based on current velocity.
        
        Args:
            session_id: UUID of the SearchSession
            
        Returns:
            Dictionary with completion estimates
        """
        progress = self.calculate_review_progress(session_id)
        velocity = progress['review_velocity']
        pending = progress['pending_results']
        
        if velocity <= 0:
            return {
                'estimated_days': None,
                'estimated_completion_date': None,
                'confidence': 'low',
                'recommendation': 'Start reviewing to establish velocity baseline'
            }
        
        estimated_days = round(pending / velocity, 1)
        estimated_completion = timezone.now() + timezone.timedelta(days=estimated_days)
        
        # Determine confidence based on review history
        confidence = 'low'
        if progress['reviewed_results'] > 20:
            confidence = 'medium'
        if progress['reviewed_results'] > 50:
            confidence = 'high'
        
        return {
            'estimated_days': estimated_days,
            'estimated_completion_date': estimated_completion.date().isoformat(),
            'confidence': confidence,
            'current_velocity': velocity,
            'remaining_results': pending,
            'recommendation': self._get_velocity_recommendation(velocity, pending)
        }
    
    def _get_velocity_recommendation(self, velocity: float, pending: int) -> str:
        """Get recommendation based on current velocity."""
        if velocity < 5 and pending > 100:
            return 'Consider increasing review pace or involving additional reviewers'
        elif velocity > 20:
            return 'Excellent review pace - maintain current momentum'
        elif velocity > 10:
            return 'Good review pace - on track for completion'
        else:
            return 'Consider establishing a regular review schedule'