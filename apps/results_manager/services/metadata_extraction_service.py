"""
Metadata extraction service for results_manager slice.
Business capability: Document metadata extraction and enrichment.
"""
import re
from datetime import datetime
from typing import Dict, Any, List, Set
from urllib.parse import urlparse

from apps.core.logging import ServiceLoggerMixin
from apps.results_manager.constants import MetadataConstants


class MetadataExtractionService(ServiceLoggerMixin):
    """Service for extracting and enriching document metadata."""
    
    def extract_document_metadata(self, title: str, snippet: str, url: str) -> Dict[str, Any]:
        """
        Extract document metadata from title, snippet, and URL.
        
        Args:
            title: Document title
            snippet: Document snippet
            url: Document URL
            
        Returns:
            Dictionary with extracted metadata
        """
        self.log_info("Starting metadata extraction", url=url, title_length=len(title))
        
        try:
            metadata = self._initialize_metadata()
            text_to_analyze = f"{title} {snippet}".lower()
            domain = urlparse(url).netloc.lower()
            
            self._detect_document_type(metadata, text_to_analyze, url)
            self._detect_academic_source(metadata, text_to_analyze, domain)
            self._detect_authors(metadata, title, snippet)
            self._extract_publication_year(metadata, text_to_analyze)
            self._extract_organization(metadata, domain)
            self._detect_subject_areas(metadata, text_to_analyze)
            
            self.log_debug(
                "Metadata extraction completed",
                url=url,
                document_type=metadata.get('document_type'),
                has_authors=metadata.get('has_authors'),
                publication_year=metadata.get('publication_year'),
                subject_areas=metadata.get('subject_areas')
            )
            
            return metadata
            
        except Exception as e:
            self.log_error("Failed to extract metadata", error=e, url=url)
            raise
    
    def _initialize_metadata(self) -> Dict[str, Any]:
        """Initialize metadata structure with default values."""
        return {
            'document_type': MetadataConstants.DEFAULT_DOCUMENT_TYPE,
            'is_academic': MetadataConstants.DEFAULT_IS_ACADEMIC,
            'has_authors': MetadataConstants.DEFAULT_HAS_AUTHORS,
            'publication_year': None,
            'language': MetadataConstants.DEFAULT_LANGUAGE,
            'organization': MetadataConstants.DEFAULT_ORGANIZATION,
            'subject_areas': [],
            'confidence_scores': {}
        }
    
    def _detect_document_type(self, metadata: Dict[str, Any], text: str, url: str) -> None:
        """Detect document type from text and URL."""
        if '.pdf' in url.lower() or 'pdf' in text:
            metadata['document_type'] = 'pdf'
            metadata['confidence_scores']['document_type'] = MetadataConstants.CONFIDENCE_SCORES['pdf_detection']
        elif any(term in text for term in MetadataConstants.DOCUMENT_TYPE_KEYWORDS['report']):
            metadata['document_type'] = 'report'
            metadata['confidence_scores']['document_type'] = MetadataConstants.CONFIDENCE_SCORES['report_detection']
        elif any(term in text for term in MetadataConstants.DOCUMENT_TYPE_KEYWORDS['thesis']):
            metadata['document_type'] = 'thesis'
            metadata['confidence_scores']['document_type'] = MetadataConstants.CONFIDENCE_SCORES['thesis_detection']
        elif any(term in text for term in MetadataConstants.DOCUMENT_TYPE_KEYWORDS['working_paper']):
            metadata['document_type'] = 'working_paper'
            metadata['confidence_scores']['document_type'] = MetadataConstants.CONFIDENCE_SCORES['working_paper_detection']
    
    def _detect_academic_source(self, metadata: Dict[str, Any], text: str, domain: str) -> None:
        """Detect if source is academic."""
        academic_score = sum(1 for indicator in MetadataConstants.ACADEMIC_INDICATORS 
                           if indicator in domain or indicator in text)
        
        if academic_score >= MetadataConstants.ACADEMIC_SCORE_THRESHOLD:
            metadata['is_academic'] = True
            metadata['confidence_scores']['is_academic'] = min(
                1.0, academic_score / MetadataConstants.ACADEMIC_SCORE_MAX_WEIGHT
            )
    
    def _detect_authors(self, metadata: Dict[str, Any], title: str, snippet: str) -> None:
        """Detect presence of authors in text."""
        for pattern in MetadataConstants.AUTHOR_PATTERNS:
            if re.search(pattern, title + " " + snippet):
                metadata['has_authors'] = True
                metadata['confidence_scores']['has_authors'] = MetadataConstants.CONFIDENCE_SCORES['author_detection']
                break
    
    def _extract_publication_year(self, metadata: Dict[str, Any], text: str) -> None:
        """Extract publication year from text."""
        years = re.findall(MetadataConstants.YEAR_PATTERN, text)
        if years:
            current_year = datetime.now().year
            valid_years = [int(y) for y in years 
                          if MetadataConstants.MIN_PUBLICATION_YEAR <= int(y) <= current_year]
            if valid_years:
                metadata['publication_year'] = max(valid_years)
                metadata['confidence_scores']['publication_year'] = MetadataConstants.CONFIDENCE_SCORES['publication_year']
    
    def _extract_organization(self, metadata: Dict[str, Any], domain: str) -> None:
        """Extract organization from domain."""
        if '.gov' in domain:
            org_match = re.search(r'([a-z]+)\.gov', domain)
            if org_match:
                metadata['organization'] = org_match.group(1).upper()
                metadata['confidence_scores']['organization'] = MetadataConstants.CONFIDENCE_SCORES['government_org']
        elif '.org' in domain:
            org_match = re.search(r'([a-z]+)\.org', domain)
            if org_match:
                metadata['organization'] = org_match.group(1).title()
                metadata['confidence_scores']['organization'] = MetadataConstants.CONFIDENCE_SCORES['nonprofit_org']
    
    def _detect_subject_areas(self, metadata: Dict[str, Any], text: str) -> None:
        """Detect subject areas from text."""
        for subject, keywords in MetadataConstants.SUBJECT_KEYWORDS.items():
            matches = sum(1 for keyword in keywords if keyword in text)
            if matches >= MetadataConstants.MIN_SUBJECT_MATCHES:
                metadata['subject_areas'].append(subject)
                metadata['confidence_scores'][f'subject_{subject}'] = min(1.0, matches / len(keywords))
    
    def enrich_metadata_with_external_sources(self, metadata: Dict[str, Any], url: str) -> Dict[str, Any]:
        """
        Enrich metadata with information from external sources or URL analysis.
        
        Args:
            metadata: Existing metadata dictionary
            url: Document URL
            
        Returns:
            Enriched metadata dictionary
        """
        enriched = metadata.copy()
        
        # Additional URL-based enrichment
        domain = urlparse(url).netloc.lower()
        
        # Detect institutional repositories
        if any(pattern in domain for pattern in MetadataConstants.REPOSITORY_PATTERNS):
            enriched['source_type'] = 'institutional_repository'
            enriched['confidence_scores']['source_type'] = MetadataConstants.CONFIDENCE_SCORES['institutional_repo']
        
        # Detect preprint servers
        if any(pattern in domain for pattern in MetadataConstants.PREPRINT_PATTERNS):
            enriched['source_type'] = 'preprint_server'
            enriched['confidence_scores']['source_type'] = MetadataConstants.CONFIDENCE_SCORES['preprint_server']
        
        # Detect government sources
        if '.gov' in domain:
            enriched['source_type'] = 'government'
            enriched['confidence_scores']['source_type'] = MetadataConstants.CONFIDENCE_SCORES['government_source']
        
        # Detect NGO/nonprofit sources
        if '.org' in domain and not any(academic in domain for academic in ['.edu', '.ac.']):
            enriched['source_type'] = 'nonprofit_organization'
            enriched['confidence_scores']['source_type'] = MetadataConstants.CONFIDENCE_SCORES['nonprofit_source']
        
        return enriched