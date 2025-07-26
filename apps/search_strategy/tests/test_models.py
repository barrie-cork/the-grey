"""
Tests for search_strategy models.

Tests for SearchQuery and QueryTemplate models including
PIC framework validation, query generation, and template functionality.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from datetime import date

from apps.review_manager.models import SearchSession
from ..models import SearchQuery, QueryTemplate

User = get_user_model()


class SearchQueryModelTests(TestCase):
    """Test cases for SearchQuery model."""
    
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
    
    def test_query_creation(self):
        """Test creating a search query."""
        query = SearchQuery.objects.create(
            session=self.session,
            population='elderly adults',
            interest='digital health interventions',
            context='healthcare settings',
            search_engines=['google']
        )
        
        self.assertEqual(query.population, 'elderly adults')
        self.assertEqual(query.interest, 'digital health interventions')
        self.assertEqual(query.context, 'healthcare settings')
        self.assertTrue(query.is_active)
        self.assertTrue(query.is_primary)
    
    def test_query_string_generation(self):
        """Test automatic query string generation."""
        query = SearchQuery.objects.create(
            session=self.session,
            population='students',
            interest='online learning',
            context='higher education',
            search_engines=['google']
        )
        
        # Check that query string was auto-generated
        self.assertIn('students', query.query_string)
        self.assertIn('online learning', query.query_string)
        self.assertIn('higher education', query.query_string)
        self.assertIn('AND', query.query_string)
    
    def test_pic_validation(self):
        """Test PIC framework validation."""
        query = SearchQuery(
            session=self.session,
            population='',
            interest='',
            context='',
            search_engines=['google']
        )
        
        with self.assertRaises(ValidationError):
            query.full_clean()
    
    def test_date_range_validation(self):
        """Test date range validation."""
        query = SearchQuery(
            session=self.session,
            population='test population',
            date_from=date(2023, 12, 31),
            date_to=date(2023, 1, 1),
            search_engines=['google']
        )
        
        with self.assertRaises(ValidationError):
            query.full_clean()


class QueryTemplateModelTests(TestCase):
    """Test cases for QueryTemplate model."""
    
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
    
    def test_template_creation(self):
        """Test creating a query template."""
        template = QueryTemplate.objects.create(
            name='Healthcare Research Template',
            description='Template for healthcare research queries',
            category='Healthcare',
            created_by=self.user,
            population_template='{age_group} with {condition}',
            interest_template='{intervention} interventions',
            context_template='{setting} settings'
        )
        
        self.assertEqual(template.name, 'Healthcare Research Template')
        self.assertEqual(template.usage_count, 0)
        self.assertFalse(template.is_public)
    
    def test_create_query_from_template(self):
        """Test creating a query from a template."""
        template = QueryTemplate.objects.create(
            name='Test Template',
            created_by=self.user,
            population_template='{age_group} patients',
            interest_template='{treatment} therapy',
            context_template='{location} clinics',
            default_keywords=['research', 'study'],
            default_engines=['google']
        )
        
        query = template.create_query(
            session=self.session,
            age_group='elderly',
            treatment='physical',
            location='urban'
        )
        
        self.assertEqual(query.population, 'elderly patients')
        self.assertEqual(query.interest, 'physical therapy')
        self.assertEqual(query.context, 'urban clinics')
        self.assertEqual(query.include_keywords, ['research', 'study'])
        self.assertEqual(query.search_engines, ['google'])
        
        # Check usage count was incremented
        template.refresh_from_db()
        self.assertEqual(template.usage_count, 1)