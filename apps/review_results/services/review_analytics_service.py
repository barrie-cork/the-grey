"""
Review analytics service for review_results slice.
Business capability: Review data export, validation, and analytics.
"""

from typing import Dict, Any, List
from django.utils import timezone

from apps.core.logging import ServiceLoggerMixin


class ReviewAnalyticsService(ServiceLoggerMixin):
    """Service for review analytics, export, and validation."""
    
    def export_review_data(self, session_id: str, format_type: str = 'csv') -> Dict[str, Any]:
        """
        Export review data in various formats.
        
        Args:
            session_id: UUID of the SearchSession
            format_type: Export format ('csv', 'json', 'excel')
            
        Returns:
            Dictionary with export data and metadata
        """
        from apps.results_manager.models import ProcessedResult
        
        results = ProcessedResult.objects.filter(session_id=session_id)
        export_data = self._build_export_data(results)
        summary = self._generate_export_summary(session_id, export_data)
        
        return {
            'session_id': session_id,
            'export_format': format_type,
            'export_timestamp': timezone.now().isoformat(),
            'results': export_data,
            'summary': summary
        }
    
    def _build_export_data(self, results) -> List[Dict[str, Any]]:
        """Build export data from results with tag information."""
        from ..models import ReviewTagAssignment
        
        export_data = []
        for result in results:
            assignments = ReviewTagAssignment.objects.filter(result=result)
            tags = [assignment.tag.name for assignment in assignments]
            
            result_data = {
                'id': str(result.id),
                'title': result.title,
                'url': result.url,
                'publication_year': result.publication_year,
                'document_type': result.document_type,
                'relevance_score': result.relevance_score,
                'has_full_text': result.has_full_text,
                'is_reviewed': len(assignments) > 0,
                'tags': tags,
                'tag_count': len(tags),
                'review_notes': '; '.join([a.notes for a in assignments if a.notes]),
                'domain': self._safe_get_display_url(result),
                'processed_at': result.processed_at.isoformat() if result.processed_at else None
            }
            export_data.append(result_data)
        
        return export_data
    
    def _safe_get_display_url(self, result) -> str:
        """Safely get display URL from result object."""
        try:
            if hasattr(result, 'get_display_url') and callable(getattr(result, 'get_display_url')):
                return result.get_display_url()
            else:
                # Fallback to extracting domain from URL
                from urllib.parse import urlparse
                return urlparse(result.url).netloc if result.url else ''
        except Exception:
            # If any error occurs, return the raw URL or empty string
            return getattr(result, 'url', '')
    
    def _generate_export_summary(self, session_id: str, export_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary statistics for export data."""
        from .review_progress_service import ReviewProgressService
        from .tagging_management_service import TaggingManagementService
        
        progress_service = ReviewProgressService()
        tagging_service = TaggingManagementService()
        
        progress = progress_service.calculate_review_progress(session_id)
        tag_stats = tagging_service.get_tag_usage_statistics(session_id)
        
        return {
            'total_results': len(export_data),
            'reviewed_results': len([r for r in export_data if r['is_reviewed']]),
            'review_progress': progress,
            'tag_statistics': tag_stats
        }
    
    def validate_review_completeness(self, session_id: str) -> Dict[str, Any]:
        """
        Validate that the review is complete and ready for reporting.
        
        Args:
            session_id: UUID of the SearchSession
            
        Returns:
            Dictionary with validation results
        """
        from apps.results_manager.models import ProcessedResult
        from ..models import ReviewTagAssignment
        from .tagging_management_service import TaggingManagementService
        
        results = ProcessedResult.objects.filter(session_id=session_id)
        total_results = results.count()
        
        validation_results = {
            'is_complete': False,
            'total_results': total_results,
            'reviewed_results': 0,
            'missing_reviews': 0,
            'issues': [],
            'recommendations': []
        }
        
        if total_results == 0:
            validation_results['issues'].append('No results to review')
            return validation_results
        
        # Check review coverage
        reviewed_result_ids = ReviewTagAssignment.objects.filter(
            result__session_id=session_id
        ).values_list('result_id', flat=True).distinct()
        
        reviewed_count = len(reviewed_result_ids)
        missing_count = total_results - reviewed_count
        
        validation_results.update({
            'reviewed_results': reviewed_count,
            'missing_reviews': missing_count
        })
        
        # Validation checks
        if missing_count > 0:
            validation_results['issues'].append(f'{missing_count} results have not been reviewed')
            validation_results['recommendations'].append('Complete review of all results before generating final report')
        
        # Check for reasonable distribution of decisions
        tagging_service = TaggingManagementService()
        tag_stats = tagging_service.get_tag_usage_statistics(session_id)
        include_count = tag_stats['tag_counts'].get('Include', 0)
        exclude_count = tag_stats['tag_counts'].get('Exclude', 0)
        
        if include_count == 0:
            validation_results['issues'].append('No results have been marked for inclusion')
            validation_results['recommendations'].append('Review tagging criteria - at least some results should typically be included')
        
        if exclude_count == 0 and reviewed_count > 10:
            validation_results['recommendations'].append('Consider if exclusion criteria are appropriate - some results are typically excluded in systematic reviews')
        
        # Overall completeness
        validation_results['is_complete'] = (
            missing_count == 0 and
            include_count > 0 and
            len(validation_results['issues']) == 0
        )
        
        return validation_results
    
    def generate_review_quality_metrics(self, session_id: str) -> Dict[str, Any]:
        """
        Generate metrics about review quality and consistency.
        
        Args:
            session_id: UUID of the SearchSession
            
        Returns:
            Dictionary with quality metrics
        """
        from apps.results_manager.models import ProcessedResult
        from ..models import ReviewTagAssignment
        from .tagging_management_service import TaggingManagementService
        
        results = ProcessedResult.objects.filter(session_id=session_id)
        assignments = ReviewTagAssignment.objects.filter(result__session_id=session_id)
        
        if not assignments.exists():
            return {'total_results': 0, 'quality_score': 0}
        
        tagging_service = TaggingManagementService()
        quality_scores = self._calculate_quality_scores(results, assignments, tagging_service, session_id)
        
        return {
            'session_id': session_id,
            'overall_quality_score': round(quality_scores['overall'], 1),
            'metrics': {
                'coverage_score': round(quality_scores['coverage'], 1),
                'balance_score': round(quality_scores['balance'], 1),
                'consistency_score': round(quality_scores['consistency'], 1),
                'notes_quality_score': round(quality_scores['notes'], 1)
            },
            'statistics': quality_scores['statistics'],
            'recommendations': self._generate_quality_recommendations(
                quality_scores['coverage'], quality_scores['balance'], 
                quality_scores['consistency'], quality_scores['notes']
            )
        }
    
    def _calculate_quality_scores(self, results, assignments, tagging_service, session_id: str) -> Dict[str, Any]:
        """Calculate individual quality scores and statistics."""
        consistency_analysis = tagging_service.get_tag_consistency_analysis(session_id)
        
        total_results = results.count()
        reviewed_results = assignments.values('result_id').distinct().count()
        
        # Review coverage
        coverage_score = (reviewed_results / total_results) * 100 if total_results > 0 else 0
        
        # Tag distribution balance
        balance_score = self._calculate_balance_score(tagging_service, session_id)
        
        # Consistency score from inter-reviewer agreement
        consistency_score = consistency_analysis.get('agreement_rate', 0)
        
        # Notes quality
        assignments_with_notes = assignments.exclude(notes='').count()
        notes_score = (assignments_with_notes / assignments.count()) * 100 if assignments.count() > 0 else 0
        
        # Overall quality score
        overall_score = (
            coverage_score * 0.4 + balance_score * 0.2 + consistency_score * 0.2 + notes_score * 0.2
        )
        
        tag_stats = tagging_service.get_tag_usage_statistics(session_id)
        include_count = tag_stats['tag_counts'].get('Include', 0)
        exclude_count = tag_stats['tag_counts'].get('Exclude', 0)
        
        return {
            'overall': overall_score,
            'coverage': coverage_score,
            'balance': balance_score,
            'consistency': consistency_score,
            'notes': notes_score,
            'statistics': {
                'total_results': total_results,
                'reviewed_results': reviewed_results,
                'inclusion_rate': round((include_count / max(include_count + exclude_count, 1)) * 100, 1),
                'assignments_with_notes': assignments_with_notes,
                'inter_reviewer_agreement': consistency_analysis.get('agreement_rate', 0)
            }
        }
    
    def _calculate_balance_score(self, tagging_service, session_id: str) -> float:
        """Calculate tag distribution balance score."""
        tag_stats = tagging_service.get_tag_usage_statistics(session_id)
        include_count = tag_stats['tag_counts'].get('Include', 0)
        exclude_count = tag_stats['tag_counts'].get('Exclude', 0)
        
        if include_count + exclude_count > 0:
            inclusion_rate = include_count / (include_count + exclude_count)
            # Ideal inclusion rate is context-dependent, but 10-30% is often reasonable
            balance_score = 100 - abs(20 - (inclusion_rate * 100)) * 2
            return max(0, min(100, balance_score))
        
        return 0
    
    def _generate_quality_recommendations(self, coverage: float, balance: float, 
                                        consistency: float, notes: float) -> List[str]:
        """Generate recommendations based on quality metrics."""
        recommendations = []
        
        if coverage < 90:
            recommendations.append(f'Review coverage is {coverage:.1f}% - complete review of all results')
        
        if balance < 50:
            recommendations.append('Review inclusion/exclusion balance - criteria may be too strict or permissive')
        
        if consistency < 70:
            recommendations.append('Low inter-reviewer agreement - consider clarifying review criteria')
        
        if notes < 30:
            recommendations.append('Consider adding more detailed notes to tag assignments for transparency')
        
        if not recommendations:
            recommendations.append('Review quality metrics look good - maintain current standards')
        
        return recommendations
    
    def generate_reviewer_performance_report(self, session_id: str) -> Dict[str, Any]:
        """
        Generate report on individual reviewer performance.
        
        Args:
            session_id: UUID of the SearchSession
            
        Returns:
            Dictionary with reviewer performance data
        """
        from ..models import ReviewTagAssignment
        from django.db.models import Count
        
        assignments = ReviewTagAssignment.objects.filter(
            result__session_id=session_id
        ).select_related('assigned_by')
        
        if not assignments.exists():
            return {'total_reviewers': 0}
        
        # Group by reviewer
        reviewer_stats = assignments.values('assigned_by__username').annotate(
            review_count=Count('id'),
            unique_results=Count('result_id', distinct=True)
        )
        
        reviewer_performance = []
        
        for stats in reviewer_stats:
            username = stats['assigned_by__username']
            user_assignments = assignments.filter(assigned_by__username=username)
            
            # Calculate reviewer-specific metrics
            include_count = user_assignments.filter(tag__name='Include').count()
            exclude_count = user_assignments.filter(tag__name='Exclude').count()
            notes_count = user_assignments.exclude(notes='').count()
            
            inclusion_rate = (include_count / max(include_count + exclude_count, 1)) * 100
            notes_rate = (notes_count / stats['review_count']) * 100
            
            reviewer_performance.append({
                'username': username,
                'total_assignments': stats['review_count'],
                'unique_results_reviewed': stats['unique_results'],
                'inclusion_rate': round(inclusion_rate, 1),
                'notes_rate': round(notes_rate, 1),
                'include_count': include_count,
                'exclude_count': exclude_count
            })
        
        # Sort by review count
        reviewer_performance.sort(key=lambda x: x['total_assignments'], reverse=True)
        
        return {
            'session_id': session_id,
            'total_reviewers': len(reviewer_performance),
            'reviewer_performance': reviewer_performance,
            'summary': {
                'most_active_reviewer': reviewer_performance[0]['username'] if reviewer_performance else None,
                'avg_inclusion_rate': round(sum(r['inclusion_rate'] for r in reviewer_performance) / len(reviewer_performance), 1) if reviewer_performance else 0,
                'avg_notes_rate': round(sum(r['notes_rate'] for r in reviewer_performance) / len(reviewer_performance), 1) if reviewer_performance else 0
            }
        }