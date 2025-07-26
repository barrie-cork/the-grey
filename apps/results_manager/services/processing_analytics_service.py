"""
Processing analytics service for results_manager slice.
Business capability: Processing statistics, result prioritization, and export functionality.
"""

from typing import Dict, Any
from django.db.models import QuerySet, Count, Avg
from django.utils import timezone


class ProcessingAnalyticsService:
    """Service for processing analytics, statistics, and result prioritization."""
    
    def get_processing_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        Get processing statistics for a session.
        
        Args:
            session_id: UUID of the SearchSession
            
        Returns:
            Dictionary with processing statistics
        """
        from ..models import ProcessedResult, DuplicateGroup
        
        results = ProcessedResult.objects.filter(session_id=session_id)
        
        if not results.exists():
            return self._empty_statistics()
        
        total_results = results.count()
        duplicate_groups = DuplicateGroup.objects.filter(session_id=session_id).count()
        unique_results = total_results - results.filter(duplicate_group__isnull=False).count() + duplicate_groups
        
        # Document type distribution
        doc_types = results.values('document_type').annotate(count=Count('document_type'))
        document_types = {item['document_type'] or 'unknown': item['count'] for item in doc_types}
        
        # Publication year distribution
        years = results.exclude(publication_year__isnull=True).values('publication_year').annotate(count=Count('publication_year'))
        publication_years = {item['publication_year']: item['count'] for item in years}
        
        # Other metrics
        has_full_text_count = results.filter(has_full_text=True).count()
        academic_results = results.filter(quality_indicators__has_key='peer_reviewed').count()
        
        # Average relevance score
        avg_relevance = results.aggregate(avg=Avg('relevance_score'))['avg'] or 0
        
        return {
            'total_results': total_results,
            'processed_results': total_results,
            'duplicate_groups': duplicate_groups,
            'unique_results': unique_results,
            'average_relevance': round(avg_relevance, 3),
            'document_types': document_types,
            'publication_years': dict(sorted(publication_years.items(), reverse=True)),
            'has_full_text_count': has_full_text_count,
            'academic_results': academic_results,
            'full_text_percentage': round((has_full_text_count / total_results * 100), 1) if total_results > 0 else 0,
            'academic_percentage': round((academic_results / total_results * 100), 1) if total_results > 0 else 0
        }
    
    def prioritize_results_for_review(self, session_id: str, limit: int = 50) -> QuerySet:
        """
        Get prioritized results for manual review.
        
        Args:
            session_id: UUID of the SearchSession
            limit: Maximum number of results to return
            
        Returns:
            QuerySet of prioritized ProcessedResult instances
        """
        from ..models import ProcessedResult
        
        results = ProcessedResult.objects.filter(
            session_id=session_id,
            is_reviewed=False
        )
        
        # Priority scoring factors:
        # 1. High relevance score
        # 2. Has full text
        # 3. Academic sources
        # 4. Recent publications
        # 5. Not duplicates
        
        # Calculate priority scores and order results
        prioritized = results.extra(
            select={
                'priority_score': """
                    COALESCE(relevance_score, 0) * 40 +
                    CASE WHEN has_full_text THEN 20 ELSE 0 END +
                    CASE WHEN duplicate_group_id IS NULL THEN 15 ELSE 0 END +
                    CASE WHEN publication_year >= 2020 THEN 10 ELSE 0 END +
                    CASE WHEN publication_year >= 2015 THEN 5 ELSE 0 END +
                    CASE WHEN quality_indicators ? 'peer_reviewed' THEN 10 ELSE 0 END
                """
            }
        ).order_by('-priority_score', '-publication_year')
        
        return prioritized[:limit]
    
    def export_results_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Export a comprehensive summary of processed results.
        
        Args:
            session_id: UUID of the SearchSession
            
        Returns:
            Dictionary with exportable results summary
        """
        from ..models import ProcessedResult
        
        results = ProcessedResult.objects.filter(session_id=session_id)
        stats = self.get_processing_statistics(session_id)
        
        # Get sample results for each document type
        sample_results = {}
        for doc_type in stats['document_types'].keys():
            samples = results.filter(document_type=doc_type).order_by('-relevance_score')[:3]
            sample_results[doc_type] = [
                {
                    'title': result.title,
                    'url': result.url,
                    'publication_year': result.publication_year,
                    'relevance_score': result.relevance_score
                } for result in samples
            ]
        
        return {
            'session_id': session_id,
            'statistics': stats,
            'sample_results': sample_results,
            'export_timestamp': timezone.now().isoformat(),
            'processing_summary': {
                'deduplication_performed': stats['duplicate_groups'] > 0,
                'quality_assessment_complete': stats['average_relevance'] > 0,
                'metadata_extraction_complete': True
            }
        }
    
    def get_quality_distribution(self, session_id: str) -> Dict[str, Any]:
        """
        Get distribution of quality indicators across results.
        
        Args:
            session_id: UUID of the SearchSession
            
        Returns:
            Dictionary with quality metrics distribution
        """
        from ..models import ProcessedResult
        
        results = ProcessedResult.objects.filter(session_id=session_id)
        
        if not results.exists():
            return {'total_results': 0}
        
        total = results.count()
        
        # Relevance score distribution
        high_relevance = results.filter(relevance_score__gte=0.8).count()
        medium_relevance = results.filter(relevance_score__gte=0.5, relevance_score__lt=0.8).count()
        low_relevance = results.filter(relevance_score__lt=0.5).count()
        
        return {
            'total_results': total,
            'relevance_distribution': {
                'high': {'count': high_relevance, 'percentage': round(high_relevance / total * 100, 1)},
                'medium': {'count': medium_relevance, 'percentage': round(medium_relevance / total * 100, 1)},
                'low': {'count': low_relevance, 'percentage': round(low_relevance / total * 100, 1)}
            },
            'quality_indicators': {
                'has_full_text': results.filter(has_full_text=True).count(),
                'is_pdf': results.filter(is_pdf=True).count(),
                'has_doi': results.filter(quality_indicators__has_key='has_doi').count(),
                'peer_reviewed': results.filter(quality_indicators__has_key='peer_reviewed').count()
            }
        }
    
    def _empty_statistics(self) -> Dict[str, Any]:
        """Return empty statistics structure."""
        return {
            'total_results': 0,
            'processed_results': 0,
            'duplicate_groups': 0,
            'unique_results': 0,
            'average_relevance': 0,
            'document_types': {},
            'publication_years': {},
            'has_full_text_count': 0,
            'academic_results': 0,
            'full_text_percentage': 0,
            'academic_percentage': 0
        }