"""
Deduplication service for results_manager slice.
Business capability: Result deduplication and similarity detection.
"""
import re
from difflib import SequenceMatcher
from typing import Dict, List, Any, Set
from urllib.parse import urlparse, parse_qs

from django.db.models import QuerySet

from apps.core.logging import ServiceLoggerMixin
from apps.results_manager.constants import DeduplicationConstants


class DeduplicationService(ServiceLoggerMixin):
    """Service for handling result deduplication and similarity detection."""
    
    def normalize_url(self, url: str) -> str:
        """
        Normalize URL for deduplication purposes.
        
        Args:
            url: Original URL
            
        Returns:
            Normalized URL string
        """
        if not url:
            return ""
        
        parsed = urlparse(url.lower().strip())
        
        # Remove common tracking parameters
        tracking_params = DeduplicationConstants.TRACKING_PARAMS
        
        # Parse query parameters and remove tracking ones
        query_params = parse_qs(parsed.query)
        clean_params = {k: v for k, v in query_params.items() if k not in tracking_params}
        
        # Rebuild query string
        clean_query = '&'.join([f"{k}={v[0]}" for k, v in clean_params.items()])
        
        # Normalize common patterns
        path = parsed.path.rstrip('/')
        if path == '':
            path = DeduplicationConstants.DEFAULT_PATH
        
        # Remove www prefix
        netloc = parsed.netloc
        if netloc.startswith(DeduplicationConstants.WWW_PREFIX):
            netloc = netloc[len(DeduplicationConstants.WWW_PREFIX):]
        
        # Rebuild URL
        normalized = f"{parsed.scheme}://{netloc}{path}"
        if clean_query:
            normalized += f"?{clean_query}"
        
        return normalized
    
    def calculate_similarity_score(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity score between two strings.
        
        Args:
            text1: First text string
            text2: Second text string
            
        Returns:
            Similarity score between 0 and 1
        """
        if not text1 or not text2:
            return 0.0
        
        # Basic string similarity
        similarity = SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
        
        # Boost score for exact matches in key phrases
        text1_words = set(text1.lower().split())
        text2_words = set(text2.lower().split())
        
        if len(text1_words) > 0 and len(text2_words) > 0:
            word_overlap = len(text1_words & text2_words) / len(text1_words | text2_words)
            similarity = (similarity + word_overlap) / 2
        
        return similarity
    
    def extract_title_keywords(self, title: str) -> Set[str]:
        """
        Extract meaningful keywords from a title.
        
        Args:
            title: Document title
            
        Returns:
            Set of normalized keywords
        """
        if not title:
            return set()
        
        # Clean and tokenize
        clean_title = re.sub(r'[^\w\s]', ' ', title.lower())
        words = [word.strip() for word in clean_title.split() 
                if len(word.strip()) > DeduplicationConstants.MIN_WORD_LENGTH]
        
        # Filter out stop words and return meaningful keywords
        keywords = {word for word in words if word not in DeduplicationConstants.STOP_WORDS}
        
        return keywords
    
    def detect_duplicates(self, results: QuerySet, similarity_threshold: float = DeduplicationConstants.DEFAULT_SIMILARITY_THRESHOLD) -> List[Dict[str, Any]]:
        """
        Detect potential duplicates among results using multiple methods.
        
        Args:
            results: QuerySet of ProcessedResult instances
            similarity_threshold: Minimum similarity score to consider duplicates
            
        Returns:
            List of duplicate groups with metadata
        """
        detector = DuplicateDetector(similarity_threshold, self)
        return detector.process_results(results)
    
    def check_duplicate_methods(self, result1, result2) -> Dict[str, Any]:
        """
        Check for duplicates using multiple methods.
        
        Args:
            result1: First ProcessedResult instance
            result2: Second ProcessedResult instance
            
        Returns:
            Dictionary with duplicate check results
        """
        # Exact URL match
        if self.normalize_url(result1.url) == self.normalize_url(result2.url):
            return {
                'is_duplicate': True,
                'method': 'exact_url',
                'confidence': DeduplicationConstants.EXACT_URL_CONFIDENCE
            }
        
        # Title similarity
        title_similarity = self.calculate_similarity_score(result1.title, result2.title)
        if title_similarity >= DeduplicationConstants.TITLE_SIMILARITY_THRESHOLD:
            return {
                'is_duplicate': True,
                'method': 'title_match',
                'confidence': title_similarity
            }
        
        # Domain + title keyword overlap
        domain1 = urlparse(result1.url).netloc
        domain2 = urlparse(result2.url).netloc
        
        if domain1 == domain2:
            keywords1 = self.extract_title_keywords(result1.title)
            keywords2 = self.extract_title_keywords(result2.title)
            
            if keywords1 and keywords2:
                overlap = len(keywords1 & keywords2) / len(keywords1 | keywords2)
                if overlap >= DeduplicationConstants.FUZZY_MATCH_THRESHOLD:
                    return {
                        'is_duplicate': True,
                        'method': 'fuzzy_match',
                        'confidence': overlap
                    }
        
        # Content hash (if snippets are similar enough)
        if result1.snippet and result2.snippet:
            snippet_similarity = self.calculate_similarity_score(result1.snippet, result2.snippet)
            if snippet_similarity >= DeduplicationConstants.CONTENT_HASH_THRESHOLD:
                return {
                    'is_duplicate': True,
                    'method': 'content_hash',
                    'confidence': snippet_similarity
                }
        
        return {
            'is_duplicate': False,
            'method': 'none',
            'confidence': 0.0
        }


class DuplicateDetector:
    """Handles the logic for detecting duplicates among results."""
    
    def __init__(self, threshold: float, service: 'DeduplicationService'):
        self.threshold = threshold
        self.service = service
    
    def process_results(self, results: QuerySet) -> List[Dict[str, Any]]:
        """Process results to find duplicate groups."""
        duplicate_groups = []
        processed_ids = set()
        results_list = list(results)
        
        for i, result1 in enumerate(results_list):
            if result1.id in processed_ids:
                continue
            
            group = self._create_empty_group(result1)
            
            for result2 in results_list[i+1:]:
                if result2.id in processed_ids:
                    continue
                
                similarity_info = self._compare_results(result1, result2)
                
                if self._is_duplicate_match(similarity_info):
                    self._add_to_group(group, result2, similarity_info)
                    processed_ids.add(result2.id)
            
            if group['duplicates']:
                processed_ids.add(result1.id)
                duplicate_groups.append(group)
        
        return duplicate_groups
    
    def _create_empty_group(self, canonical_result) -> Dict[str, Any]:
        """Create an empty duplicate group."""
        return {
            'canonical_result': canonical_result,
            'duplicates': [],
            'similarity_type': 'none',
            'confidence': 0.0
        }
    
    def _compare_results(self, result1, result2) -> Dict[str, Any]:
        """Compare two results using the service's comparison methods."""
        return self.service.check_duplicate_methods(result1, result2)
    
    def _is_duplicate_match(self, similarity_info: Dict[str, Any]) -> bool:
        """Check if similarity meets threshold for duplicate match."""
        return (similarity_info['is_duplicate'] and 
                similarity_info['confidence'] >= self.threshold)
    
    def _add_to_group(self, group: Dict[str, Any], result, similarity_info: Dict[str, Any]) -> None:
        """Add a result to the duplicate group."""
        group['duplicates'].append(result)
        
        # Use the highest confidence similarity type
        if similarity_info['confidence'] > group['confidence']:
            group['similarity_type'] = similarity_info['method']
            group['confidence'] = similarity_info['confidence']