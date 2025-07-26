"""
Quality assessment service for results_manager slice.
Business capability: Result quality assessment and relevance scoring.
"""
from datetime import datetime
from typing import List, Dict, Any

from apps.core.logging import ServiceLoggerMixin
from apps.results_manager.constants import QualityConstants


class QualityAssessmentService(ServiceLoggerMixin):
    """Service for assessing result quality and calculating relevance scores."""
    
    def calculate_relevance_score(self, result, query_terms: List[str]) -> float:
        """
        DEPRECATED: Calculate relevance score for a result based on query terms.
        This method is deprecated in the simplified approach and returns a basic quality indicator.
        
        Args:
            result: ProcessedResult instance
            query_terms: List of search terms from the original query
            
        Returns:
            Basic quality score between 0 and 1
        """
        import warnings
        warnings.warn(
            "calculate_relevance_score is deprecated. Use simplified quality indicators instead.",
            DeprecationWarning,
            stacklevel=2
        )
        # Simplified quality score based on basic indicators
        score = 0.5  # Base score
        
        if result.has_full_text:
            score += 0.3
        
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
        max_score = QualityConstants.MAX_QUALITY_SCORE
        
        # Full text availability
        if result.has_full_text:
            score += QualityConstants.QUALITY_SCORES['full_text_available']
            quality['quality_factors'].append('Full text available')
        else:
            quality['concerns'].append('No full text available')
        
        # PDF format (generally higher quality for academic content)
        if result.is_pdf:
            score += QualityConstants.QUALITY_SCORES['pdf_format']
            quality['quality_factors'].append('PDF format')
        
        # Academic indicators removed - simplified approach
        
        # Publication year recency
        if result.publication_year:
            if result.publication_year >= QualityConstants.RECENT_PUBLICATION_THRESHOLD:
                score += QualityConstants.QUALITY_SCORES['recent_publication']
                quality['quality_factors'].append('Recent publication')
            elif result.publication_year >= QualityConstants.MODERATELY_RECENT_THRESHOLD:
                score += QualityConstants.QUALITY_SCORES['moderately_recent']
                quality['quality_factors'].append('Moderately recent')
            else:
                quality['concerns'].append('Older publication')
        else:
            quality['concerns'].append('No publication date')
        
        # Title and snippet quality
        if result.title and len(result.title) >= QualityConstants.MIN_TITLE_LENGTH:
            score += QualityConstants.QUALITY_SCORES['good_title']
        else:
            quality['concerns'].append('Poor or missing title')
        
        if result.snippet and len(result.snippet) >= QualityConstants.MIN_SNIPPET_LENGTH:
            score += QualityConstants.QUALITY_SCORES['good_snippet']
        else:
            quality['concerns'].append('Poor or missing snippet')
        
        quality['overall_score'] = min(QualityConstants.MAX_SCORE, score / max_score)
        
        return quality