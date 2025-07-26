"""
Tests for MetadataExtractionService.

Tests document metadata extraction and enrichment functionality.
"""

import re
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.results_manager.services.metadata_extraction_service import MetadataExtractionService


User = get_user_model()


class TestMetadataExtractionService(TestCase):
    """Test cases for MetadataExtractionService."""
    
    def setUp(self):
        """Set up test data."""
        self.service = MetadataExtractionService()
    
    def test_extract_document_metadata_basic(self):
        """Test basic metadata extraction."""
        title = "Effects of Artificial Intelligence on Healthcare Outcomes: A Systematic Review"
        snippet = "This systematic review examines the impact of AI technologies on patient care outcomes published between 2020-2024."
        url = "https://journal.medical.edu/articles/ai-healthcare-review.pdf"
        
        metadata = self.service.extract_document_metadata(title, snippet, url)
        
        self.assertIsInstance(metadata, dict)
        self.assertIn('document_type', metadata)
        self.assertIn('is_academic', metadata)
        self.assertIn('has_authors', metadata)
        self.assertIn('publication_year', metadata)
        self.assertIn('subject_areas', metadata)
        
        # Check specific extractions
        self.assertEqual(metadata['document_type'], 'pdf')
        self.assertTrue(metadata['is_academic'])
        self.assertIn('healthcare', metadata['subject_areas'])
    
    def test_detect_document_type(self):
        """Test document type detection."""
        test_cases = [
            ('file.pdf', 'https://example.com/doc.pdf', 'pdf'),
            ('Report on Climate Change', 'https://example.com/report', 'report'),
            ('PhD Thesis: Machine Learning', 'https://example.com/thesis', 'thesis'),
            ('Working Paper #123', 'https://example.com/wp', 'working_paper'),
            ('Random Title', 'https://example.com/page', 'unknown')
        ]
        
        for title, url, expected_type in test_cases:
            metadata = self.service.extract_document_metadata(
                title, 
                'Generic snippet text', 
                url
            )
            self.assertEqual(
                metadata['document_type'], 
                expected_type,
                f"Failed for title: {title}"
            )
    
    def test_detect_academic_source(self):
        """Test academic source detection."""
        academic_cases = [
            ('https://university.edu/paper', True),
            ('https://journal.ac.uk/article', True),
            ('https://research.institute.org', True),
            ('https://blog.com/post', False),
            ('https://news.site.com/article', False)
        ]
        
        for url, expected_academic in academic_cases:
            metadata = self.service.extract_document_metadata(
                'Test Title',
                'Test snippet with research content',
                url
            )
            self.assertEqual(
                metadata['is_academic'],
                expected_academic,
                f"Failed for URL: {url}"
            )
    
    def test_detect_authors(self):
        """Test author detection in text."""
        test_cases = [
            (
                "Study by John Smith and Jane Doe",
                "This research was conducted...",
                True
            ),
            (
                "Machine Learning Applications",
                "Authors: Smith, J., Doe, J., Johnson, K.",
                True
            ),
            (
                "Anonymous Report",
                "No author information available",
                False
            )
        ]
        
        for title, snippet, expected_has_authors in test_cases:
            metadata = self.service.extract_document_metadata(
                title,
                snippet,
                'https://example.com'
            )
            self.assertEqual(
                metadata['has_authors'],
                expected_has_authors,
                f"Failed for title: {title}"
            )
    
    @patch('apps.results_manager.services.metadata_extraction_service.datetime')
    def test_extract_publication_year(self, mock_datetime):
        """Test publication year extraction with current year validation."""
        # Mock current year as 2025
        mock_datetime.now.return_value.year = 2025
        
        test_cases = [
            ("Published in 2023", 2023),
            ("Study from 1995 revisited", 1995),
            ("Results (2024)", 2024),
            ("Historic data from 1970", None),  # Too old (before 1980)
            ("Future projections for 2030", None),  # Future year
            ("No year mentioned", None)
        ]
        
        for text, expected_year in test_cases:
            metadata = self.service.extract_document_metadata(
                text,
                text,
                'https://example.com'
            )
            self.assertEqual(
                metadata['publication_year'],
                expected_year,
                f"Failed for text: {text}"
            )
    
    def test_extract_organization(self):
        """Test organization extraction from domain."""
        test_cases = [
            ('https://cdc.gov/report', 'CDC'),
            ('https://who.org/guidelines', 'Who'),
            ('https://example.com/page', ''),
            ('https://research.microsoft.com', ''),
        ]
        
        for url, expected_org in test_cases:
            metadata = self.service.extract_document_metadata(
                'Test Title',
                'Test snippet',
                url
            )
            self.assertEqual(
                metadata['organization'],
                expected_org,
                f"Failed for URL: {url}"
            )
    
    def test_detect_subject_areas(self):
        """Test subject area detection."""
        test_texts = [
            (
                "Healthcare AI: Using machine learning for patient diagnosis",
                ['healthcare', 'technology']
            ),
            (
                "Government policy on climate change and environmental sustainability",
                ['policy', 'environment']
            ),
            (
                "Economic impact of digital transformation in business markets",
                ['economics', 'technology']
            ),
            (
                "Educational technology for student learning outcomes",
                ['education', 'technology']
            )
        ]
        
        for text, expected_subjects in test_texts:
            metadata = self.service.extract_document_metadata(
                text,
                text,
                'https://example.com'
            )
            
            for subject in expected_subjects:
                self.assertIn(
                    subject,
                    metadata['subject_areas'],
                    f"Missing {subject} for text: {text}"
                )
    
    def test_confidence_scores(self):
        """Test that confidence scores are generated."""
        metadata = self.service.extract_document_metadata(
            "Research Report: AI in Healthcare by Dr. Smith (2023)",
            "This academic study examines artificial intelligence applications...",
            "https://university.edu/research/ai-healthcare.pdf"
        )
        
        self.assertIn('confidence_scores', metadata)
        scores = metadata['confidence_scores']
        
        # Check some confidence scores exist and are valid
        self.assertIn('document_type', scores)
        self.assertIn('is_academic', scores)
        
        # Scores should be between 0 and 1
        for score in scores.values():
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 1)
    
    def test_enrich_metadata_with_external_sources(self):
        """Test metadata enrichment with URL analysis."""
        base_metadata = {
            'document_type': 'unknown',
            'is_academic': False,
            'confidence_scores': {}
        }
        
        test_cases = [
            ('https://arxiv.org/abs/2024.12345', 'preprint_server'),
            ('https://repository.university.edu/handle/123', 'institutional_repository'),
            ('https://www.nih.gov/research/paper', 'government'),
            ('https://nonprofit.org/report', 'nonprofit_organization')
        ]
        
        for url, expected_source_type in test_cases:
            enriched = self.service.enrich_metadata_with_external_sources(
                base_metadata.copy(),
                url
            )
            
            self.assertEqual(
                enriched['source_type'],
                expected_source_type,
                f"Failed for URL: {url}"
            )
            self.assertIn('source_type', enriched['confidence_scores'])
    
    def test_complex_document_analysis(self):
        """Test extraction with complex, realistic document."""
        title = "Smith, J., Doe, A., & Johnson, K. (2024). Systematic Review: Machine Learning Applications in Clinical Decision Support Systems. Journal of Medical AI, 15(3), 234-256."
        
        snippet = """This systematic review examines the current state of machine learning 
        applications in healthcare settings, specifically focusing on clinical decision 
        support systems. We analyzed 150 studies published between 2020 and 2024, 
        finding significant improvements in diagnostic accuracy. The review was conducted 
        following PRISMA guidelines. Keywords: artificial intelligence, healthcare, 
        clinical outcomes, decision support."""
        
        url = "https://journal.medical.university.edu/jmai/vol15/issue3/ml-clinical-review.pdf"
        
        metadata = self.service.extract_document_metadata(title, snippet, url)
        
        # Comprehensive checks
        self.assertEqual(metadata['document_type'], 'pdf')
        self.assertTrue(metadata['is_academic'])
        self.assertTrue(metadata['has_authors'])
        self.assertEqual(metadata['publication_year'], 2024)
        self.assertIn('healthcare', metadata['subject_areas'])
        self.assertIn('technology', metadata['subject_areas'])
        
        # High confidence scores for clear indicators
        self.assertGreater(metadata['confidence_scores']['document_type'], 0.8)
        self.assertGreater(metadata['confidence_scores']['is_academic'], 0.8)
    
    def test_edge_cases(self):
        """Test edge cases and unusual inputs."""
        # Empty inputs
        metadata = self.service.extract_document_metadata('', '', '')
        self.assertEqual(metadata['document_type'], 'unknown')
        self.assertFalse(metadata['is_academic'])
        
        # Very long inputs
        long_title = 'A' * 500
        long_snippet = 'B' * 1000
        metadata = self.service.extract_document_metadata(
            long_title,
            long_snippet,
            'https://example.com'
        )
        self.assertIsInstance(metadata, dict)
        
        # Special characters
        special_title = "Study@#$%^&*() with special chars"
        metadata = self.service.extract_document_metadata(
            special_title,
            'Normal snippet',
            'https://example.com'
        )
        self.assertIsInstance(metadata, dict)
    
    def test_year_boundary_validation(self):
        """Test year validation at boundary conditions."""
        current_year = datetime.now().year
        
        test_years = [
            (f"Published in {current_year}", current_year),  # Current year
            (f"Study from {current_year + 1}", None),  # Future year
            ("Research from 1980", 1980),  # Minimum valid year
            ("Data from 1979", None),  # Below minimum
        ]
        
        for text, expected_year in test_years:
            metadata = self.service.extract_document_metadata(
                text,
                text,
                'https://example.com'
            )
            self.assertEqual(
                metadata['publication_year'],
                expected_year,
                f"Failed for text: {text}"
            )
    
    def test_logging_in_extraction(self):
        """Test that extraction operations are properly logged."""
        with self.assertLogs('apps.results_manager.services.metadata_extraction_service', level='INFO') as cm:
            self.service.extract_document_metadata(
                'Test Title',
                'Test snippet',
                'https://example.com/test'
            )
        
        self.assertTrue(any('Starting metadata extraction' in msg for msg in cm.output))
        self.assertTrue(any('Metadata extraction completed' in msg for msg in cm.output))