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
        Calculate relevance score for a result based on query terms.
        
        Args:
            result: ProcessedResult instance
            query_terms: List of search terms from the original query
            
        Returns:
            Relevance score between 0 and 1
        """
        if not query_terms:
            return QualityConstants.DEFAULT_RELEVANCE_SCORE  # Default score if no query terms
        
        score = 0.0
        total_weight = 0
        
        # Title matching (highest weight)
        if result.title:
            title_matches = sum(1 for term in query_terms if term.lower() in result.title.lower())
            title_score = title_matches / len(query_terms)
            score += title_score * QualityConstants.RELEVANCE_WEIGHTS['title']
            total_weight += QualityConstants.RELEVANCE_WEIGHTS['title']
        
        # Snippet matching
        if result.snippet:
            snippet_matches = sum(1 for term in query_terms if term.lower() in result.snippet.lower())
            snippet_score = snippet_matches / len(query_terms)
            score += snippet_score * QualityConstants.RELEVANCE_WEIGHTS['snippet']
            total_weight += QualityConstants.RELEVANCE_WEIGHTS['snippet']
        
        # URL matching (domain relevance)
        if result.url:
            url_matches = sum(1 for term in query_terms if term.lower() in result.url.lower())
            url_score = url_matches / len(query_terms)
            score += url_score * QualityConstants.RELEVANCE_WEIGHTS['url']
            total_weight += QualityConstants.RELEVANCE_WEIGHTS['url']
        
        # Publication recency (newer = slightly higher score)
        if result.publication_year:
            current_year = datetime.now().year
            years_old = max(0, current_year - result.publication_year)
            recency_score = max(0, 1 - (years_old / QualityConstants.RECENCY_DECAY_YEARS))
            score += recency_score * QualityConstants.RELEVANCE_WEIGHTS['recency']
            total_weight += QualityConstants.RELEVANCE_WEIGHTS['recency']
        
        # Quality indicators
        quality_bonus = 0
        if result.has_full_text:
            quality_bonus += QualityConstants.QUALITY_BONUSES['has_full_text']
        if result.is_pdf:
            quality_bonus += QualityConstants.QUALITY_BONUSES['is_pdf']
        if result.quality_indicators.get('peer_reviewed'):
            quality_bonus += QualityConstants.QUALITY_BONUSES['peer_reviewed']
        if result.quality_indicators.get('has_doi'):
            quality_bonus += QualityConstants.QUALITY_BONUSES['has_doi']
        
        score += quality_bonus
        total_weight += QualityConstants.RELEVANCE_WEIGHTS['quality_indicators']
        
        # Normalize by total weight
        if total_weight > 0:
            score = score / total_weight
        
        return min(QualityConstants.MAX_SCORE, max(QualityConstants.MIN_SCORE, score))
    
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
        
        # Academic indicators
        if result.quality_indicators.get('peer_reviewed'):
            score += QualityConstants.QUALITY_SCORES['peer_reviewed']
            quality['quality_factors'].append('Peer reviewed')
        
        if result.quality_indicators.get('has_doi'):
            score += QualityConstants.QUALITY_SCORES['has_doi']
            quality['quality_factors'].append('Has DOI')
        
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