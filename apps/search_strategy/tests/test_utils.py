"""
Tests for search_strategy utility functions.

Tests for PIC framework validation, query optimization, template suggestions,
and other utility functions.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.review_manager.models import SearchSession
from ..models import SearchQuery, QueryTemplate
from ..utils import (
    validate_pic_framework,
    generate_query_variations,
    optimize_query_string,
    calculate_query_complexity,
    get_template_suggestions
)

User = get_user_model()


class UtilityFunctionTests(TestCase):
    """Test cases for utility functions."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.session = SearchSession.objects.create(
            title='Test Session',
            owner=self.user
        )
    
    def test_validate_pic_framework(self):
        """Test PIC framework validation."""
        # Valid PIC components
        is_valid, errors = validate_pic_framework(
            population='elderly adults',
            interest='digital health',
            context='primary care'
        )
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Invalid - all empty
        is_valid, errors = validate_pic_framework('', '', '')
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        
        # Invalid - too short
        is_valid, errors = validate_pic_framework('ab', '', '')
        self.assertFalse(is_valid)
        self.assertIn('at least', errors[0])
    
    def test_generate_query_variations(self):
        """Test query variation generation."""
        query = SearchQuery.objects.create(
            session=self.session,
            population='elderly adults',
            interest='digital health interventions',
            context='healthcare settings',
            include_keywords=['mobile', 'app'],
            search_engines=['google']
        )
        
        variations = generate_query_variations(query, 3)
        
        self.assertEqual(len(variations), 3)
        
        # Check variation types
        variation_types = [v['variation_type'] for v in variations]
        self.assertIn('Broader Search', variation_types)
        self.assertIn('Narrower Search', variation_types)
        self.assertIn('Alternative Terms', variation_types)
    
    def test_optimize_query_string(self):
        """Test query string optimization."""
        # Test with a long query
        long_query = 'elderly adults with chronic conditions using digital health interventions in primary care settings with mobile applications'
        analysis = optimize_query_string(long_query)
        
        self.assertIn('original_query', analysis)
        self.assertIn('word_count', analysis)
        self.assertIn('suggestions', analysis)
        self.assertGreater(analysis['word_count'], 10)
        
        # Should suggest shortening
        suggestions_text = ' '.join(analysis['suggestions'])
        self.assertIn('shortening', suggestions_text.lower())
    
    def test_calculate_query_complexity(self):
        """Test query complexity calculation."""
        # Simple query
        simple_query = SearchQuery.objects.create(
            session=self.session,
            population='students',
            interest='online learning',
            context='universities',
            search_engines=['google']
        )
        
        complexity = calculate_query_complexity(simple_query)
        self.assertIn('score', complexity)
        self.assertIn('level', complexity)
        self.assertEqual(complexity['level'], 'Simple')
        
        # Complex query
        complex_query = SearchQuery.objects.create(
            session=self.session,
            population='elderly adults with multiple chronic conditions',
            interest='complex digital health interventions and telemedicine solutions',
            context='rural healthcare settings with limited internet access',
            include_keywords=['mobile', 'app', 'telemedicine', 'remote monitoring'],
            exclude_keywords=['pediatric', 'children'],
            search_engines=['google', 'bing', 'duckduckgo'],
            languages=['en', 'es', 'fr'],
            document_types=['pdf', 'doc', 'report']
        )
        
        complexity = calculate_query_complexity(complex_query)
        self.assertIn(complexity['level'], ['Complex', 'Very Complex'])
        self.assertGreater(complexity['score'], 20)
    
    def test_get_template_suggestions(self):
        """Test template suggestion functionality."""
        # Create a template
        template = QueryTemplate.objects.create(
            name='Healthcare Template',
            description='For healthcare research',
            category='Healthcare',
            created_by=self.user,
            is_public=True,
            population_template='elderly patients',
            interest_template='digital health',
            context_template='healthcare settings'
        )
        
        # Get suggestions
        suggestions = get_template_suggestions(
            population='elderly adults',
            interest='digital interventions',
            context='medical settings',
            user=self.user
        )
        
        self.assertIn(template, suggestions)