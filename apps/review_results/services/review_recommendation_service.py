"""
Review recommendation service for review_results slice.
Business capability: Result prioritization and review recommendations.
"""

from typing import List, Dict, Any
from django.db.models import QuerySet
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class ReviewRecommendationService:
    """Service for providing intelligent review recommendations."""
    
    def get_review_recommendations(self, session_id: str, user: User, limit: int = 10) -> QuerySet:
        """
        Get recommended results for review based on various factors.
        
        Args:
            session_id: UUID of the SearchSession
            user: User requesting recommendations
            limit: Maximum number of recommendations
            
        Returns:
            QuerySet of recommended ProcessedResult instances
        """
        from apps.results_manager.models import ProcessedResult
        from ..models import ReviewTagAssignment
        
        # Get unreviewed results
        reviewed_result_ids = ReviewTagAssignment.objects.filter(
            result__session_id=session_id
        ).values_list('result_id', flat=True)
        
        unreviewed = ProcessedResult.objects.filter(
            session_id=session_id
        ).exclude(id__in=reviewed_result_ids)
        
        # Priority factors:
        # 1. High relevance score
        # 2. Academic sources
        # 3. Has full text
        # 4. Recent publications
        # 5. No duplicates
        
        recommendations = unreviewed.extra(
            select={
                'recommendation_score': """
                    COALESCE(relevance_score, 0) * 50 +
                    CASE WHEN quality_indicators ? 'peer_reviewed' THEN 20 ELSE 0 END +
                    CASE WHEN has_full_text THEN 15 ELSE 0 END +
                    CASE WHEN duplicate_group_id IS NULL THEN 10 ELSE 0 END +
                    CASE WHEN publication_year >= 2020 THEN 5 ELSE 0 END
                """
            }
        ).order_by('-recommendation_score', '-publication_year')
        
        return recommendations[:limit]
    
    def get_personalized_recommendations(self, session_id: str, user: User, limit: int = 10) -> QuerySet:
        """
        Get personalized recommendations based on user's review history.
        
        Args:
            session_id: UUID of the SearchSession
            user: User requesting recommendations
            limit: Maximum number of recommendations
            
        Returns:
            QuerySet of personalized recommendations
        """
        from apps.results_manager.models import ProcessedResult
        from ..models import ReviewTagAssignment
        
        # Get user's review history to understand preferences
        user_assignments = ReviewTagAssignment.objects.filter(
            assigned_by=user,
            result__session_id=session_id
        )
        
        # Analyze user's inclusion patterns
        included_results = user_assignments.filter(tag__name='Include')
        avg_relevance = included_results.aggregate(
            avg_relevance=models.Avg('result__relevance_score')
        )['avg_relevance'] or 0.5
        
        # Get unreviewed results
        reviewed_result_ids = ReviewTagAssignment.objects.filter(
            result__session_id=session_id
        ).values_list('result_id', flat=True)
        
        unreviewed = ProcessedResult.objects.filter(
            session_id=session_id
        ).exclude(id__in=reviewed_result_ids)
        
        # Personalized scoring based on user preferences
        personalized = unreviewed.extra(
            select={
                'personalized_score': f"""
                    COALESCE(relevance_score, 0) * 40 +
                    CASE WHEN relevance_score >= {avg_relevance} THEN 20 ELSE 0 END +
                    CASE WHEN has_full_text THEN 15 ELSE 0 END +
                    CASE WHEN quality_indicators ? 'peer_reviewed' THEN 15 ELSE 0 END +
                    CASE WHEN duplicate_group_id IS NULL THEN 10 ELSE 0 END
                """
            }
        ).order_by('-personalized_score', '-publication_year')
        
        return personalized[:limit]
    
    def get_similar_results(self, result_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find results similar to the given result for comparison during review.
        
        Args:
            result_id: UUID of the ProcessedResult
            limit: Maximum number of similar results to return
            
        Returns:
            List of similar result information
        """
        from apps.results_manager.models import ProcessedResult
        from apps.results_manager.utils import calculate_similarity_score, extract_title_keywords
        
        try:
            target_result = ProcessedResult.objects.get(id=result_id)
        except ProcessedResult.DoesNotExist:
            return []
        
        # Get other results from the same session
        other_results = ProcessedResult.objects.filter(
            session=target_result.session
        ).exclude(id=result_id)
        
        similarities = []
        target_keywords = extract_title_keywords(target_result.title)
        
        for result in other_results:
            # Calculate similarity based on multiple factors
            title_similarity = calculate_similarity_score(target_result.title, result.title)
            
            # Keyword overlap
            result_keywords = extract_title_keywords(result.title)
            keyword_overlap = 0
            if target_keywords and result_keywords:
                keyword_overlap = len(target_keywords & result_keywords) / len(target_keywords | result_keywords)
            
            # Domain similarity
            domain_match = target_result.get_display_url() == result.get_display_url()
            
            # Publication year proximity
            year_similarity = 0
            if target_result.publication_year and result.publication_year:
                year_diff = abs(target_result.publication_year - result.publication_year)
                year_similarity = max(0, 1 - (year_diff / 10))  # Decay over 10 years
            
            # Combined similarity score
            combined_score = (
                title_similarity * 0.4 +
                keyword_overlap * 0.3 +
                (1.0 if domain_match else 0.0) * 0.2 +
                year_similarity * 0.1
            )
            
            if combined_score > 0.3:  # Minimum similarity threshold
                similarities.append({
                    'result': result,
                    'similarity_score': combined_score,
                    'title_similarity': title_similarity,
                    'keyword_overlap': keyword_overlap,
                    'domain_match': domain_match,
                    'year_proximity': year_similarity
                })
        
        # Sort by similarity and return top results
        similarities.sort(key=lambda x: x['similarity_score'], reverse=True)
        return similarities[:limit]
    
    def get_batch_recommendations(self, session_id: str, batch_size: int = 20) -> Dict[str, Any]:
        """
        Get a balanced batch of results for efficient review sessions.
        
        Args:
            session_id: UUID of the SearchSession
            batch_size: Number of results in the batch
            
        Returns:
            Dictionary with batch recommendations
        """
        from apps.results_manager.models import ProcessedResult
        from ..models import ReviewTagAssignment
        
        # Get unreviewed results
        reviewed_result_ids = ReviewTagAssignment.objects.filter(
            result__session_id=session_id
        ).values_list('result_id', flat=True)
        
        unreviewed = ProcessedResult.objects.filter(
            session_id=session_id
        ).exclude(id__in=reviewed_result_ids)
        
        if not unreviewed.exists():
            return {
                'batch': [],
                'batch_characteristics': {},
                'recommendation': 'All results have been reviewed'
            }
        
        # Create a balanced batch:
        # - High priority items (top relevance)
        # - Medium priority items (diverse sources)
        # - Some random items for unbiased sampling
        
        high_priority = unreviewed.filter(relevance_score__gte=0.7).order_by('-relevance_score')[:batch_size//2]
        medium_priority = unreviewed.filter(
            relevance_score__lt=0.7,
            relevance_score__gte=0.4
        ).order_by('?')[:batch_size//3]  # Random sampling
        
        remaining_slots = batch_size - high_priority.count() - medium_priority.count()
        random_sample = unreviewed.exclude(
            id__in=list(high_priority.values_list('id', flat=True)) + 
                   list(medium_priority.values_list('id', flat=True))
        ).order_by('?')[:remaining_slots]
        
        # Combine into final batch
        batch_results = list(high_priority) + list(medium_priority) + list(random_sample)
        
        # Calculate batch characteristics
        characteristics = {
            'total_results': len(batch_results),
            'high_relevance_count': len([r for r in batch_results if r.relevance_score >= 0.7]),
            'has_full_text_count': len([r for r in batch_results if r.has_full_text]),
            'academic_count': len([r for r in batch_results if r.quality_indicators.get('peer_reviewed')]),
            'avg_relevance': round(sum(r.relevance_score or 0 for r in batch_results) / len(batch_results), 3),
            'document_types': {}
        }
        
        # Document type distribution
        for result in batch_results:
            doc_type = result.document_type or 'unknown'
            characteristics['document_types'][doc_type] = characteristics['document_types'].get(doc_type, 0) + 1
        
        return {
            'batch': batch_results,
            'batch_characteristics': characteristics,
            'recommendation': f'Balanced batch of {len(batch_results)} results ready for review'
        }