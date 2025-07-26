"""
Metadata extraction service for results_manager slice.
Business capability: Document metadata extraction and enrichment.
"""

import re
from datetime import datetime
from typing import Dict, Any
from urllib.parse import urlparse

from apps.core.logging import ServiceLoggerMixin


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
        metadata = self._initialize_metadata()
        text_to_analyze = f"{title} {snippet}".lower()
        domain = urlparse(url).netloc.lower()
        
        self._detect_document_type(metadata, text_to_analyze, url)
        self._detect_academic_source(metadata, text_to_analyze, domain)
        self._detect_authors(metadata, title, snippet)
        self._extract_publication_year(metadata, text_to_analyze)
        self._extract_organization(metadata, domain)
        self._detect_subject_areas(metadata, text_to_analyze)
        
        return metadata
    
    def _initialize_metadata(self) -> Dict[str, Any]:
        """Initialize metadata structure with default values."""
        return {
            'document_type': 'unknown',
            'is_academic': False,
            'has_authors': False,
            'publication_year': None,
            'language': 'en',
            'organization': '',
            'subject_areas': [],
            'confidence_scores': {}
        }
    
    def _detect_document_type(self, metadata: Dict[str, Any], text: str, url: str) -> None:
        """Detect document type from text and URL."""
        if '.pdf' in url.lower() or 'pdf' in text:
            metadata['document_type'] = 'pdf'
            metadata['confidence_scores']['document_type'] = 0.9
        elif any(term in text for term in ['report', 'white paper', 'policy']):
            metadata['document_type'] = 'report'
            metadata['confidence_scores']['document_type'] = 0.7
        elif any(term in text for term in ['thesis', 'dissertation']):
            metadata['document_type'] = 'thesis'
            metadata['confidence_scores']['document_type'] = 0.8
        elif any(term in text for term in ['working paper', 'discussion paper']):
            metadata['document_type'] = 'working_paper'
            metadata['confidence_scores']['document_type'] = 0.7
    
    def _detect_academic_source(self, metadata: Dict[str, Any], text: str, domain: str) -> None:
        """Detect if source is academic."""
        academic_indicators = ['.edu', '.ac.', 'university', 'college', 'research', 'journal', 'academic']
        academic_score = sum(1 for indicator in academic_indicators if indicator in domain or indicator in text)
        
        if academic_score >= 2:
            metadata['is_academic'] = True
            metadata['confidence_scores']['is_academic'] = min(1.0, academic_score / 4)
    
    def _detect_authors(self, metadata: Dict[str, Any], title: str, snippet: str) -> None:
        """Detect presence of authors in text."""
        author_patterns = [
            r'by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)',
            r'author[s]?[:\s]+([A-Z][a-z]+)',
            r'([A-Z][a-z]+,\s+[A-Z]\.)',
        ]
        
        for pattern in author_patterns:
            if re.search(pattern, title + " " + snippet):
                metadata['has_authors'] = True
                metadata['confidence_scores']['has_authors'] = 0.8
                break
    
    def _extract_publication_year(self, metadata: Dict[str, Any], text: str) -> None:
        """Extract publication year from text."""
        year_pattern = r'\b(19|20)\d{2}\b'
        years = re.findall(year_pattern, text)
        if years:
            current_year = datetime.now().year
            valid_years = [int(y) for y in years if 1980 <= int(y) <= current_year]
            if valid_years:
                metadata['publication_year'] = max(valid_years)
                metadata['confidence_scores']['publication_year'] = 0.7
    
    def _extract_organization(self, metadata: Dict[str, Any], domain: str) -> None:
        """Extract organization from domain."""
        if '.gov' in domain:
            org_match = re.search(r'([a-z]+)\.gov', domain)
            if org_match:
                metadata['organization'] = org_match.group(1).upper()
                metadata['confidence_scores']['organization'] = 0.9
        elif '.org' in domain:
            org_match = re.search(r'([a-z]+)\.org', domain)
            if org_match:
                metadata['organization'] = org_match.group(1).title()
                metadata['confidence_scores']['organization'] = 0.7
    
    def _detect_subject_areas(self, metadata: Dict[str, Any], text: str) -> None:
        """Detect subject areas from text."""
        subject_keywords = {
            'healthcare': ['health', 'medical', 'clinical', 'patient', 'treatment'],
            'education': ['education', 'learning', 'student', 'academic', 'school'],
            'technology': ['technology', 'digital', 'software', 'computer', 'internet'],
            'policy': ['policy', 'government', 'regulation', 'law', 'legislation'],
            'economics': ['economic', 'financial', 'market', 'business', 'economy'],
            'environment': ['environment', 'climate', 'sustainability', 'green', 'conservation']
        }
        
        for subject, keywords in subject_keywords.items():
            matches = sum(1 for keyword in keywords if keyword in text)
            if matches >= 2:
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
        if any(pattern in domain for pattern in ['eprints', 'repository', 'repo', 'dspace']):
            enriched['source_type'] = 'institutional_repository'
            enriched['confidence_scores']['source_type'] = 0.8
        
        # Detect preprint servers
        if any(pattern in domain for pattern in ['arxiv', 'biorxiv', 'medrxiv', 'preprint']):
            enriched['source_type'] = 'preprint_server'
            enriched['confidence_scores']['source_type'] = 0.9
        
        # Detect government sources
        if '.gov' in domain:
            enriched['source_type'] = 'government'
            enriched['confidence_scores']['source_type'] = 0.95
        
        # Detect NGO/nonprofit sources
        if '.org' in domain and not any(academic in domain for academic in ['.edu', '.ac.']):
            enriched['source_type'] = 'nonprofit_organization'
            enriched['confidence_scores']['source_type'] = 0.7
        
        return enriched