"""
Deduplication service for results_manager slice.
Business capability: Result deduplication and similarity detection.
"""

import re
from typing import Dict, List, Any, Set
from urllib.parse import urlparse, parse_qs
from django.db.models import QuerySet
from difflib import SequenceMatcher


class DeduplicationService:
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
        tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term',
            'gclid', 'fbclid', 'msclkid', '_ga', 'ref', 'source'
        }
        
        # Parse query parameters and remove tracking ones
        query_params = parse_qs(parsed.query)
        clean_params = {k: v for k, v in query_params.items() if k not in tracking_params}
        
        # Rebuild query string
        clean_query = '&'.join([f"{k}={v[0]}" for k, v in clean_params.items()])
        
        # Normalize common patterns
        path = parsed.path.rstrip('/')
        if path == '':
            path = '/'
        
        # Remove www prefix
        netloc = parsed.netloc
        if netloc.startswith('www.'):
            netloc = netloc[4:]
        
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
        
        # Remove common stop words
        stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'were', 'will', 'with', 'this', 'these', 'they', 'been'
        }
        
        # Clean and tokenize
        clean_title = re.sub(r'[^\w\s]', ' ', title.lower())
        words = [word.strip() for word in clean_title.split() if len(word.strip()) > 2]
        
        # Filter out stop words and return meaningful keywords
        keywords = {word for word in words if word not in stop_words}
        
        return keywords
    
    def detect_duplicates(self, results: QuerySet, similarity_threshold: float = 0.85) -> List[Dict[str, Any]]:
        """
        Detect potential duplicates among results using multiple methods.
        
        Args:
            results: QuerySet of ProcessedResult instances
            similarity_threshold: Minimum similarity score to consider duplicates
            
        Returns:
            List of duplicate groups with metadata
        """
        duplicate_groups = []
        processed_ids = set()
        
        results_list = list(results)
        
        for i, result1 in enumerate(results_list):
            if result1.id in processed_ids:
                continue
            
            group = {
                'canonical_result': result1,
                'duplicates': [],
                'similarity_type': 'none',
                'confidence': 0.0
            }
            
            for j, result2 in enumerate(results_list[i+1:], i+1):
                if result2.id in processed_ids:
                    continue
                
                # Check for various types of duplicates
                similarity_info = self.check_duplicate_methods(result1, result2)
                
                if similarity_info['is_duplicate'] and similarity_info['confidence'] >= similarity_threshold:
                    group['duplicates'].append(result2)
                    processed_ids.add(result2.id)
                    
                    # Use the highest confidence similarity type
                    if similarity_info['confidence'] > group['confidence']:
                        group['similarity_type'] = similarity_info['method']
                        group['confidence'] = similarity_info['confidence']
            
            if group['duplicates']:
                processed_ids.add(result1.id)
                duplicate_groups.append(group)
        
        return duplicate_groups
    
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
                'confidence': 1.0
            }
        
        # Title similarity
        title_similarity = self.calculate_similarity_score(result1.title, result2.title)
        if title_similarity >= 0.9:
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
                if overlap >= 0.7:
                    return {
                        'is_duplicate': True,
                        'method': 'fuzzy_match',
                        'confidence': overlap
                    }
        
        # Content hash (if snippets are similar enough)
        if result1.snippet and result2.snippet:
            snippet_similarity = self.calculate_similarity_score(result1.snippet, result2.snippet)
            if snippet_similarity >= 0.8:
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