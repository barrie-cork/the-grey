"""
Result processor service for handling raw search results.
Extracts metadata, detects file types, and prepares data for storage.
"""

import re
import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from dateutil import parser as date_parser
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


class ResultProcessor:
    """
    Service for processing raw search results from Serper API.
    Handles metadata extraction, deduplication, and normalization.
    """
    
    # Patterns for detecting academic sources
    ACADEMIC_PATTERNS = [
        r'\.edu(\.[a-z]{2})?(/|$)',
        r'\.ac\.[a-z]{2}(/|$)',
        r'\.gov(\.[a-z]{2})?(/|$)',
        r'\.org(/|$)',
        r'scholar\.google',
        r'researchgate\.net',
        r'academia\.edu',
        r'arxiv\.org',
        r'pubmed',
        r'sciencedirect',
        r'springer',
        r'wiley',
        r'tandfonline',
        r'sage',
        r'jstor',
        r'ssrn\.com',
        r'repository',
        r'thesis',
        r'dissertation'
    ]
    
    # Patterns for detecting dates
    DATE_PATTERNS = [
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
        # Year only in parentheses or after dash
        r'[\(\-]\s*(\d{4})\s*[\)\-]',
        # Copyright year
        r'©\s*(\d{4})',
        # Published: or Date: followed by date
        r'(?:Published|Date|Updated):\s*([^<>\n]+\d{4})'
    ]
    
    # File type indicators
    FILE_TYPE_INDICATORS = {
        'pdf': ['.pdf', 'application/pdf', 'PDF'],
        'doc': ['.doc', 'application/msword', 'Word Document'],
        'docx': ['.docx', 'application/vnd.openxmlformats', 'Word Document'],
        'ppt': ['.ppt', 'application/vnd.ms-powerpoint', 'PowerPoint'],
        'pptx': ['.pptx', 'application/vnd.openxmlformats.*presentation', 'PowerPoint'],
        'xls': ['.xls', 'application/vnd.ms-excel', 'Excel'],
        'xlsx': ['.xlsx', 'application/vnd.openxmlformats.*spreadsheet', 'Excel'],
        'txt': ['.txt', 'text/plain', 'Text File'],
        'rtf': ['.rtf', 'application/rtf', 'Rich Text'],
        'odt': ['.odt', 'application/vnd.oasis', 'OpenDocument Text'],
        'html': ['.html', '.htm', 'text/html', 'Web Page']
    }
    
    # Language detection patterns (basic)
    LANGUAGE_INDICATORS = {
        'en': ['the', 'and', 'or', 'for', 'with', 'this', 'that'],
        'es': ['el', 'la', 'de', 'que', 'para', 'con'],
        'fr': ['le', 'la', 'de', 'et', 'pour', 'avec'],
        'de': ['der', 'die', 'das', 'und', 'für', 'mit'],
        'pt': ['o', 'a', 'de', 'para', 'com', 'por'],
        'it': ['il', 'la', 'di', 'e', 'per', 'con'],
        'nl': ['de', 'het', 'van', 'en', 'voor', 'met'],
        'ru': ['и', 'в', 'на', 'с', 'для', 'по'],
        'zh': ['的', '和', '在', '是', '有', '个'],
        'ja': ['の', 'に', 'は', 'を', 'と', 'が']
    }
    
    def __init__(self):
        """Initialize the result processor."""
        self.processed_urls = set()
        self.dedup_cache = {}
    
    def process_search_results(
        self,
        execution_id: str,
        raw_results: List[Dict[str, Any]],
        batch_size: int = 50
    ) -> Tuple[int, int, List[str]]:
        """
        Process a batch of raw search results.
        
        Args:
            execution_id: ID of the SearchExecution
            raw_results: List of raw result dictionaries from Serper
            batch_size: Number of results to process in each batch
            
        Returns:
            Tuple of (processed_count, duplicate_count, error_messages)
        """
        from apps.serp_execution.models import SearchExecution, RawSearchResult
        
        processed_count = 0
        duplicate_count = 0
        errors = []
        
        try:
            execution = SearchExecution.objects.get(id=execution_id)
        except SearchExecution.DoesNotExist:
            logger.error(f"SearchExecution {execution_id} not found")
            return 0, 0, ["SearchExecution not found"]
        
        # Process in batches for better performance
        for i in range(0, len(raw_results), batch_size):
            batch = raw_results[i:i + batch_size]
            
            try:
                with transaction.atomic():
                    batch_processed, batch_duplicates, batch_errors = self._process_batch(
                        execution, batch, starting_position=i + 1
                    )
                    processed_count += batch_processed
                    duplicate_count += batch_duplicates
                    errors.extend(batch_errors)
                    
            except Exception as e:
                error_msg = f"Error processing batch {i//batch_size + 1}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        logger.info(f"Processed {processed_count} results, found {duplicate_count} duplicates")
        return processed_count, duplicate_count, errors
    
    def _process_batch(
        self,
        execution: 'SearchExecution',
        results: List[Dict[str, Any]],
        starting_position: int
    ) -> Tuple[int, int, List[str]]:
        """
        Process a batch of results.
        
        Args:
            execution: SearchExecution instance
            results: List of result dictionaries
            starting_position: Starting position number for this batch
            
        Returns:
            Tuple of (processed_count, duplicate_count, error_messages)
        """
        from apps.serp_execution.models import RawSearchResult
        
        processed = 0
        duplicates = 0
        errors = []
        results_to_create = []
        
        for idx, result in enumerate(results):
            position = starting_position + idx
            
            try:
                # Extract basic fields
                title = result.get('title', '').strip()
                link = result.get('link', '').strip()
                snippet = result.get('snippet', '').strip()
                
                if not title or not link:
                    errors.append(f"Missing required fields at position {position}")
                    continue
                
                # Check for duplicates
                if self._is_duplicate(execution, link):
                    duplicates += 1
                    continue
                
                # Extract metadata
                metadata = self._extract_metadata(result)
                
                # Create RawSearchResult object (not saved yet)
                raw_result = RawSearchResult(
                    execution=execution,
                    position=position,
                    title=title[:1024],  # Ensure it fits in TextField
                    link=link[:2048],  # URL max length
                    snippet=snippet,
                    display_link=result.get('displayLink', '')[:255],
                    source=metadata['source'][:255],
                    raw_data=result,
                    has_pdf=metadata['has_pdf'],
                    has_date=metadata['has_date'],
                    detected_date=metadata['detected_date'],
                    is_academic=metadata['is_academic'],
                    language_code=metadata['language_code'][:10]
                )
                
                results_to_create.append(raw_result)
                processed += 1
                
            except Exception as e:
                error_msg = f"Error processing result at position {position}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Bulk create all results
        if results_to_create:
            RawSearchResult.objects.bulk_create(results_to_create)
            
            # Add URLs to dedup cache
            for result in results_to_create:
                self.processed_urls.add(result.link)
        
        return processed, duplicates, errors
    
    def _is_duplicate(self, execution: 'SearchExecution', url: str) -> bool:
        """
        Check if URL is a duplicate within this session.
        
        Args:
            execution: SearchExecution instance
            url: URL to check
            
        Returns:
            True if duplicate, False otherwise
        """
        # Normalize URL for comparison
        normalized_url = self._normalize_url(url)
        
        # Check in-memory cache first
        if normalized_url in self.processed_urls:
            return True
        
        # Check database for duplicates in same session
        from apps.serp_execution.models import RawSearchResult
        
        session_id = execution.query.session_id
        exists = RawSearchResult.objects.filter(
            execution__query__session_id=session_id,
            link__icontains=normalized_url
        ).exists()
        
        return exists
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL for deduplication comparison.
        
        Args:
            url: URL to normalize
            
        Returns:
            Normalized URL
        """
        # Parse URL
        parsed = urlparse(url.lower())
        
        # Remove www. prefix
        netloc = parsed.netloc.replace('www.', '')
        
        # Remove trailing slash from path
        path = parsed.path.rstrip('/')
        
        # Remove common tracking parameters
        if parsed.query:
            params = parse_qs(parsed.query)
            # Remove common tracking params
            tracking_params = ['utm_source', 'utm_medium', 'utm_campaign', 
                             'utm_content', 'utm_term', 'fbclid', 'gclid']
            for param in tracking_params:
                params.pop(param, None)
            
            # Reconstruct query string
            query_parts = []
            for key, values in sorted(params.items()):
                for value in values:
                    query_parts.append(f"{key}={value}")
            query = '&'.join(query_parts)
        else:
            query = ''
        
        # Reconstruct normalized URL
        normalized = f"{parsed.scheme}://{netloc}{path}"
        if query:
            normalized += f"?{query}"
        
        return normalized
    
    def _extract_metadata(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from a search result.
        
        Args:
            result: Raw result dictionary
            
        Returns:
            Dictionary of extracted metadata
        """
        metadata = {
            'source': '',
            'has_pdf': False,
            'has_date': False,
            'detected_date': None,
            'is_academic': False,
            'language_code': 'en',  # Default to English
            'file_type': None,
            'domain': ''
        }
        
        # Extract source/domain
        url = result.get('link', '')
        if url:
            parsed = urlparse(url)
            metadata['domain'] = parsed.netloc
            metadata['source'] = parsed.netloc.replace('www.', '')
        
        # Detect file type
        file_type = self._detect_file_type(result)
        if file_type:
            metadata['file_type'] = file_type
            metadata['has_pdf'] = (file_type == 'pdf')
        
        # Detect if academic
        metadata['is_academic'] = self._is_academic_source(url, result)
        
        # Extract date
        date_found, extracted_date = self._extract_date(result)
        metadata['has_date'] = date_found
        metadata['detected_date'] = extracted_date
        
        # Detect language (basic)
        metadata['language_code'] = self._detect_language(result)
        
        return metadata
    
    def _detect_file_type(self, result: Dict[str, Any]) -> Optional[str]:
        """
        Detect file type from result.
        
        Args:
            result: Result dictionary
            
        Returns:
            File type string or None
        """
        # Check URL
        url = result.get('link', '').lower()
        
        # Check title and snippet
        title = result.get('title', '').lower()
        snippet = result.get('snippet', '').lower()
        
        # Check mime type if available
        mime_type = result.get('mimeType', '').lower()
        
        # Check each file type
        for file_type, indicators in self.FILE_TYPE_INDICATORS.items():
            for indicator in indicators:
                if (indicator in url or 
                    indicator in title or 
                    indicator in snippet or
                    (mime_type and indicator in mime_type)):
                    return file_type
        
        # Check for [PDF] or similar markers in title
        if re.search(r'\[(PDF|DOC|DOCX|PPT|PPTX)\]', title, re.IGNORECASE):
            match = re.search(r'\[(PDF|DOC|DOCX|PPT|PPTX)\]', title, re.IGNORECASE)
            return match.group(1).lower()
        
        return None
    
    def _is_academic_source(self, url: str, result: Dict[str, Any]) -> bool:
        """
        Determine if result is from an academic source.
        
        Args:
            url: Result URL
            result: Result dictionary
            
        Returns:
            True if academic source, False otherwise
        """
        url_lower = url.lower()
        title_lower = result.get('title', '').lower()
        snippet_lower = result.get('snippet', '').lower()
        
        # Check URL patterns
        for pattern in self.ACADEMIC_PATTERNS:
            if re.search(pattern, url_lower):
                return True
        
        # Check for academic keywords in title/snippet
        academic_keywords = [
            'research', 'study', 'journal', 'paper', 'thesis', 
            'dissertation', 'conference', 'proceedings', 'abstract',
            'methodology', 'findings', 'results', 'conclusion',
            'university', 'institute', 'department', 'faculty',
            'peer review', 'citation', 'bibliography', 'references'
        ]
        
        text_to_check = f"{title_lower} {snippet_lower}"
        academic_keyword_count = sum(1 for keyword in academic_keywords 
                                   if keyword in text_to_check)
        
        # If multiple academic keywords found, likely academic
        return academic_keyword_count >= 2
    
    def _extract_date(self, result: Dict[str, Any]) -> Tuple[bool, Optional[date]]:
        """
        Extract publication date from result.
        
        Args:
            result: Result dictionary
            
        Returns:
            Tuple of (date_found, extracted_date)
        """
        # Check multiple fields for dates
        text_to_search = ' '.join([
            result.get('title', ''),
            result.get('snippet', ''),
            result.get('date', ''),  # Sometimes Serper provides this
            str(result.get('publicationDate', '')),
            str(result.get('datePublished', ''))
        ])
        
        # Try each date pattern
        for pattern in self.DATE_PATTERNS:
            matches = re.findall(pattern, text_to_search)
            
            for match in matches:
                try:
                    # Try to parse the date
                    parsed_date = date_parser.parse(match, fuzzy=True)
                    
                    # Sanity check - not future dates, not too old
                    current_year = timezone.now().year
                    if 1990 <= parsed_date.year <= current_year:
                        return True, parsed_date.date()
                        
                except (ValueError, TypeError):
                    continue
        
        # Try to extract just a year
        year_match = re.search(r'\b(19[9-9]\d|20[0-2]\d)\b', text_to_search)
        if year_match:
            year = int(year_match.group(1))
            current_year = timezone.now().year
            if 1990 <= year <= current_year:
                # Return January 1st of that year
                return True, date(year, 1, 1)
        
        return False, None
    
    def _detect_language(self, result: Dict[str, Any]) -> str:
        """
        Detect language of result (basic implementation).
        
        Args:
            result: Result dictionary
            
        Returns:
            Language code (default 'en')
        """
        # Check if language is provided
        if 'language' in result:
            return result['language'][:2]
        
        # Basic language detection from title and snippet
        text = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
        words = text.split()
        
        if not words:
            return 'en'
        
        # Count language indicators
        language_scores = {}
        
        for lang, indicators in self.LANGUAGE_INDICATORS.items():
            score = sum(1 for word in words if word in indicators)
            if score > 0:
                language_scores[lang] = score
        
        # Return language with highest score, default to English
        if language_scores:
            return max(language_scores, key=language_scores.get)
        
        return 'en'
    
    def prepare_for_processing_pipeline(
        self,
        raw_result_id: str
    ) -> Dict[str, Any]:
        """
        Prepare a raw result for the processing pipeline.
        
        Args:
            raw_result_id: ID of the RawSearchResult
            
        Returns:
            Dictionary of prepared data for processing
        """
        from apps.serp_execution.models import RawSearchResult
        
        try:
            raw_result = RawSearchResult.objects.get(id=raw_result_id)
        except RawSearchResult.DoesNotExist:
            logger.error(f"RawSearchResult {raw_result_id} not found")
            return {}
        
        # Extract key terms from title and snippet
        key_terms = self._extract_key_terms(raw_result.title, raw_result.snippet)
        
        # Prepare data for ProcessedResult
        prepared_data = {
            'raw_result_id': raw_result.id,
            'session_id': raw_result.execution.query.session_id,
            'title': raw_result.title,
            'url': raw_result.link,
            'snippet': raw_result.snippet,
            'source_domain': raw_result.get_domain(),
            'publication_date': raw_result.detected_date,
            'document_type': self._infer_document_type(raw_result),
            'is_pdf': raw_result.has_pdf,
            'is_academic': raw_result.is_academic,
            'language': raw_result.language_code,
            'key_terms': key_terms,
            'relevance_score': 0.0,  # Will be calculated by processing pipeline
            'quality_indicators': self._extract_quality_indicators(raw_result),
            'needs_manual_review': self._needs_manual_review(raw_result)
        }
        
        return prepared_data
    
    def _extract_key_terms(self, title: str, snippet: str) -> List[str]:
        """Extract key terms from title and snippet."""
        text = f"{title} {snippet}".lower()
        
        # Remove common words and punctuation
        words = re.findall(r'\b\w+\b', text)
        
        # Filter out stop words and short words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 
                     'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as',
                     'is', 'was', 'are', 'were', 'been', 'be', 'have',
                     'has', 'had', 'do', 'does', 'did', 'will', 'would',
                     'should', 'could', 'may', 'might', 'must', 'shall',
                     'can', 'this', 'that', 'these', 'those', 'i', 'you',
                     'he', 'she', 'it', 'we', 'they', 'them', 'their'}
        
        filtered_words = [w for w in words 
                         if len(w) > 2 and w not in stop_words]
        
        # Count frequencies
        word_freq = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Return top 10 most frequent terms
        sorted_terms = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [term[0] for term in sorted_terms[:10]]
    
    def _infer_document_type(self, raw_result: 'RawSearchResult') -> str:
        """Infer document type from various indicators."""
        title_lower = raw_result.title.lower()
        url_lower = raw_result.link.lower()
        
        # Check for specific document types
        if 'thesis' in title_lower or 'dissertation' in title_lower:
            return 'thesis'
        elif 'report' in title_lower:
            return 'report'
        elif 'policy' in title_lower or 'white paper' in title_lower:
            return 'policy'
        elif 'conference' in title_lower or 'proceedings' in title_lower:
            return 'conference'
        elif 'working paper' in title_lower:
            return 'working_paper'
        elif 'preprint' in title_lower or 'arxiv' in url_lower:
            return 'preprint'
        elif raw_result.has_pdf:
            return 'document'
        else:
            return 'webpage'
    
    def _extract_quality_indicators(self, raw_result: 'RawSearchResult') -> Dict[str, Any]:
        """Extract quality indicators for the result."""
        indicators = {
            'has_abstract': 'abstract' in raw_result.snippet.lower(),
            'has_methodology': any(term in raw_result.snippet.lower() 
                                 for term in ['method', 'methodology', 'approach']),
            'has_references': any(term in raw_result.snippet.lower() 
                                for term in ['references', 'bibliography', 'citation']),
            'from_known_repository': any(repo in raw_result.link.lower() 
                                       for repo in ['repository', 'arxiv', 'ssrn', 'researchgate']),
            'recent_publication': False
        }
        
        # Check if recent (within last 5 years)
        if raw_result.detected_date:
            years_old = (timezone.now().date() - raw_result.detected_date).days / 365
            indicators['recent_publication'] = years_old <= 5
        
        return indicators
    
    def _needs_manual_review(self, raw_result: 'RawSearchResult') -> bool:
        """Determine if result needs manual review."""
        # Needs review if:
        # - No date detected but appears academic
        # - Very short snippet
        # - Potentially duplicate content
        # - Unclear document type
        
        if raw_result.is_academic and not raw_result.has_date:
            return True
        
        if len(raw_result.snippet) < 50:
            return True
        
        return False