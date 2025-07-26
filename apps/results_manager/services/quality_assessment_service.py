"""
Quality assessment service for results_manager slice.
Business capability: Result quality assessment and relevance scoring.
"""

from typing import List

from apps.core.logging import ServiceLoggerMixin


class QualityAssessmentService(ServiceLoggerMixin):
    """Service for assessing result quality and calculating relevance scores."""
    
    def calculate_relevance_score(self, result, query_terms: List[str]) -> float:
        """
        Calculate relevance score for a result based on query terms.
        
        Args:
            result: ProcessedResult instance
            query_terms: List of search terms from the original query
            
        Returns:
            Relevance score between 0 and 1
        """
        if not query_terms:
            return 0.5  # Default score if no query terms
        
        score = 0.0
        total_weight = 0
        
        # Title matching (highest weight)
        if result.title:
            title_matches = sum(1 for term in query_terms if term.lower() in result.title.lower())
            title_score = title_matches / len(query_terms)
            score += title_score * 0.4
            total_weight += 0.4
        
        # Snippet matching
        if result.snippet:
            snippet_matches = sum(1 for term in query_terms if term.lower() in result.snippet.lower())
            snippet_score = snippet_matches / len(query_terms)
            score += snippet_score * 0.3
            total_weight += 0.3
        
        # URL matching (domain relevance)
        if result.url:
            url_matches = sum(1 for term in query_terms if term.lower() in result.url.lower())
            url_score = url_matches / len(query_terms)
            score += url_score * 0.1
            total_weight += 0.1
        
        # Publication recency (newer = slightly higher score)
        if result.publication_year:
            current_year = 2024  # This should be dynamic
            years_old = max(0, current_year - result.publication_year)
            recency_score = max(0, 1 - (years_old / 20))  # Decay over 20 years
            score += recency_score * 0.1
            total_weight += 0.1
        
        # Quality indicators
        quality_bonus = 0
        if result.has_full_text:
            quality_bonus += 0.05
        if result.is_pdf:
            quality_bonus += 0.03
        if result.quality_indicators.get('peer_reviewed'):
            quality_bonus += 0.07
        if result.quality_indicators.get('has_doi'):
            quality_bonus += 0.05
        
        score += quality_bonus
        total_weight += 0.2
        
        # Normalize by total weight
        if total_weight > 0:
            score = score / total_weight
        
        return min(1.0, max(0.0, score))
    
    def assess_document_quality(self, result) -> dict:
        """
        Assess overall document quality indicators.
        
        Args:
            result: ProcessedResult instance
            
        Returns:
            Dictionary with quality assessment
        """
        quality = {
            'overall_score': 0.0,
            'quality_factors': [],
            'concerns': []
        }
        
        score = 0.0
        max_score = 100
        
        # Full text availability
        if result.has_full_text:
            score += 20
            quality['quality_factors'].append('Full text available')
        else:
            quality['concerns'].append('No full text available')
        
        # PDF format (generally higher quality for academic content)
        if result.is_pdf:
            score += 15
            quality['quality_factors'].append('PDF format')
        
        # Academic indicators
        if result.quality_indicators.get('peer_reviewed'):
            score += 25
            quality['quality_factors'].append('Peer reviewed')
        
        if result.quality_indicators.get('has_doi'):
            score += 15
            quality['quality_factors'].append('Has DOI')
        
        # Publication year recency
        if result.publication_year:
            if result.publication_year >= 2020:
                score += 15
                quality['quality_factors'].append('Recent publication')
            elif result.publication_year >= 2010:
                score += 10
                quality['quality_factors'].append('Moderately recent')
            else:
                quality['concerns'].append('Older publication')
        else:
            quality['concerns'].append('No publication date')
        
        # Title and snippet quality
        if result.title and len(result.title) >= 20:
            score += 5
        else:
            quality['concerns'].append('Poor or missing title')
        
        if result.snippet and len(result.snippet) >= 50:
            score += 5
        else:
            quality['concerns'].append('Poor or missing snippet')
        
        quality['overall_score'] = min(1.0, score / max_score)
        
        return quality