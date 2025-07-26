"""
Content analysis and classification service for serp_execution slice.
Business capability: Analyzing and classifying search result content.
"""

import re
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse
from datetime import datetime
from dateutil import parser as date_parser

from apps.core.logging import ServiceLoggerMixin


class ContentAnalysisService(ServiceLoggerMixin):
    """Service for analyzing and classifying search result content."""
    
    # Academic source patterns
    ACADEMIC_DOMAINS = [
        r'\.edu(\.[a-z]{2})?',
        r'\.ac\.[a-z]{2}',
        r'scholar\.google',
        r'pubmed',
        r'arxiv\.org',
        r'researchgate\.net',
        r'academia\.edu',
    ]
    
    # Government source patterns
    GOVERNMENT_DOMAINS = [
        r'\.gov(\.[a-z]{2})?',
        r'\.mil(\.[a-z]{2})?',
        r'\.int',
    ]
    
    # File type patterns
    FILE_TYPE_PATTERNS = {
        'pdf': [r'\.pdf(\?|$)', r'filetype:pdf'],
        'doc': [r'\.docx?(\?|$)', r'filetype:doc'],
        'ppt': [r'\.pptx?(\?|$)', r'filetype:ppt'],
        'xls': [r'\.xlsx?(\?|$)', r'filetype:xls'],
    }
    
    def detect_content_type(self, url: str, title: str, snippet: str) -> Dict[str, Any]:
        """
        Detect the type and characteristics of search result content.
        
        Args:
            url: Result URL
            title: Result title
            snippet: Result snippet
            
        Returns:
            Dictionary with content characteristics
        """
        content_info = {
            'is_pdf': False,
            'is_academic': False,
            'is_government': False,
            'is_news': False,
            'document_type': 'webpage',
            'confidence_score': 0.0,
            'file_type': None,
            'source_type': 'unknown'
        }
        
        url_lower = url.lower()
        domain = urlparse(url).netloc.lower()
        combined_text = f"{title} {snippet}".lower()
        
        # File type detection
        file_type = self._detect_file_type(url_lower)
        if file_type:
            content_info['document_type'] = file_type
            content_info['file_type'] = file_type
            content_info['is_pdf'] = (file_type == 'pdf')
            content_info['confidence_score'] += 0.3
        
        # Academic source detection
        if self._is_academic_source(domain, combined_text):
            content_info['is_academic'] = True
            content_info['source_type'] = 'academic'
            content_info['confidence_score'] += 0.4
        
        # Government source detection
        if self._is_government_source(domain):
            content_info['is_government'] = True
            content_info['source_type'] = 'government'
            content_info['confidence_score'] += 0.4
        
        # News source detection
        if self._is_news_source(domain, combined_text):
            content_info['is_news'] = True
            content_info['source_type'] = 'news'
            content_info['confidence_score'] += 0.3
        
        return content_info
    
    def extract_publication_date(self, title: str, snippet: str, url: str) -> Optional[datetime]:
        """
        Extract publication date from title, snippet, or URL.
        
        Args:
            title: Result title
            snippet: Result snippet
            url: Result URL
            
        Returns:
            Extracted publication date or None
        """
        combined_text = f"{title} {snippet} {url}"
        
        # Date patterns to search for
        date_patterns = [
            # ISO format: 2024-01-15
            r'(\d{4}-\d{1,2}-\d{1,2})',
            # US format: 01/15/2024 or 1/15/2024
            r'(\d{1,2}/\d{1,2}/\d{4})',
            # EU format: 15.01.2024
            r'(\d{1,2}\.\d{1,2}\.\d{4})',
            # Month name: January 15, 2024 or Jan 15, 2024
            r'([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})',
            # Month year: January 2024
            r'([A-Za-z]{3,9}\s+\d{4})',
            # Published: or Date: followed by date
            r'(?:Published|Date|Updated):\s*([^<>\n]+\d{4})'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            for match in matches:
                try:
                    parsed_date = date_parser.parse(match, fuzzy=True)
                    # Validate reasonable date range (not in future, not too old)
                    current_year = datetime.now().year
                    if 1990 <= parsed_date.year <= current_year:
                        return parsed_date
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def analyze_content_quality(self, title: str, snippet: str, url: str) -> Dict[str, Any]:
        """
        Analyze the quality indicators of search result content.
        """
        quality_indicators = {
            'title_quality': self._assess_title_quality(title),
            'snippet_quality': self._assess_snippet_quality(snippet),
            'url_quality': self._assess_url_quality(url),
            'overall_score': 0.0,
            'quality_flags': []
        }
        
        # Calculate overall quality score
        scores = [
            quality_indicators['title_quality'],
            quality_indicators['snippet_quality'],
            quality_indicators['url_quality']
        ]
        quality_indicators['overall_score'] = sum(scores) / len(scores)
        
        # Add quality flags
        if quality_indicators['title_quality'] < 0.3:
            quality_indicators['quality_flags'].append('poor_title')
        if quality_indicators['snippet_quality'] < 0.3:
            quality_indicators['quality_flags'].append('poor_snippet')
        if quality_indicators['url_quality'] < 0.3:
            quality_indicators['quality_flags'].append('suspicious_url')
        
        return quality_indicators
    
    def _detect_file_type(self, url: str) -> Optional[str]:
        """Detect file type from URL."""
        for file_type, patterns in self.FILE_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return file_type
        return None
    
    def _is_academic_source(self, domain: str, text: str) -> bool:
        """Check if source appears to be academic."""
        # Check domain patterns
        for pattern in self.ACADEMIC_DOMAINS:
            if re.search(pattern, domain):
                return True
        
        # Check text content for academic keywords
        academic_keywords = [
            'journal', 'research', 'study', 'academic', 'university',
            'paper', 'publication', 'peer review', 'citation', 'doi'
        ]
        
        keyword_count = sum(1 for keyword in academic_keywords if keyword in text)
        return keyword_count >= 2
    
    def _is_government_source(self, domain: str) -> bool:
        """Check if source is from government domain."""
        for pattern in self.GOVERNMENT_DOMAINS:
            if re.search(pattern, domain):
                return True
        return False
    
    def _is_news_source(self, domain: str, text: str) -> bool:
        """Check if source appears to be news."""
        news_domains = ['news', 'times', 'post', 'herald', 'tribune', 'guardian', 'bbc', 'cnn']
        news_keywords = ['breaking', 'reported', 'according to', 'journalist', 'editor']
        
        domain_match = any(news_domain in domain for news_domain in news_domains)
        keyword_match = any(keyword in text for keyword in news_keywords)
        
        return domain_match or keyword_match
    
    def _assess_title_quality(self, title: str) -> float:
        """Assess title quality (0-1 score)."""
        if not title or len(title.strip()) < 5:
            return 0.0
        
        score = 0.5  # Base score
        
        # Length indicators
        if 20 <= len(title) <= 100:
            score += 0.2
        
        # Capitalization
        if title.istitle() or (title[0].isupper() and not title.isupper()):
            score += 0.1
        
        # No excessive punctuation
        punct_ratio = sum(1 for c in title if c in '!?.,;:') / len(title)
        if punct_ratio < 0.1:
            score += 0.1
        
        # Contains meaningful words
        word_count = len(title.split())
        if word_count >= 3:
            score += 0.1
        
        return min(score, 1.0)
    
    def _assess_snippet_quality(self, snippet: str) -> float:
        """Assess snippet quality (0-1 score)."""
        if not snippet or len(snippet.strip()) < 10:
            return 0.0
        
        score = 0.3  # Base score
        
        # Length indicators
        if 50 <= len(snippet) <= 300:
            score += 0.3
        
        # Sentence structure
        sentences = snippet.split('.')
        if len(sentences) >= 2:
            score += 0.2
        
        # Contains useful information indicators
        info_words = ['the', 'and', 'of', 'in', 'to', 'for', 'with', 'on']
        info_ratio = sum(1 for word in snippet.lower().split() if word in info_words) / len(snippet.split())
        if 0.1 <= info_ratio <= 0.5:
            score += 0.2
        
        return min(score, 1.0)
    
    def _assess_url_quality(self, url: str) -> float:
        """Assess URL quality (0-1 score)."""
        if not url:
            return 0.0
        
        score = 0.5  # Base score
        
        try:
            parsed = urlparse(url)
            
            # HTTPS
            if parsed.scheme == 'https':
                score += 0.2
            
            # Reasonable domain
            if parsed.netloc and '.' in parsed.netloc:
                score += 0.2
            
            # Not too many parameters
            if len(parsed.query) < 100:
                score += 0.1
            
        except Exception:
            score = 0.1
        
        return min(score, 1.0)