"""
Tests for SearchStrategyReportingService.

Tests search strategy documentation and reporting.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.review_manager.models import SearchSession
from apps.search_strategy.models import (
    SearchQuery, Population, Interest, Context, 
    ContextOrganization, SearchQueryVersion
)
from apps.reporting.services.search_strategy_reporting_service import SearchStrategyReportingService


User = get_user_model()


class TestSearchStrategyReportingService(TestCase):
    """Test cases for SearchStrategyReportingService."""
    
    def setUp(self):
        """Set up test data."""
        self.service = SearchStrategyReportingService()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test session
        self.session = SearchSession.objects.create(
            title='Healthcare AI Review',
            description='Systematic review of AI in healthcare',
            owner=self.user,
            status='ready_to_execute'
        )
        
        # Create PIC components
        self.population = Population.objects.create(
            session=self.session,
            description='Healthcare providers and patients',
            inclusion_criteria='Adults over 18 years',
            exclusion_criteria='Pediatric populations',
            geographic_scope='Global',
            time_period='2020-2025'
        )
        
        self.interest = Interest.objects.create(
            session=self.session,
            primary_focus='Artificial Intelligence applications',
            secondary_aspects='Machine learning, Deep learning',
            specific_outcomes='Clinical outcomes, Patient satisfaction',
            excluded_topics='Non-clinical applications'
        )
        
        self.context = Context.objects.create(
            session=self.session,
            setting='Hospital and clinical settings',
            constraints='English language only',
            special_considerations='Focus on peer-reviewed sources'
        )
        
        # Create organizations
        self.org1 = ContextOrganization.objects.create(
            context=self.context,
            name='World Health Organization',
            abbreviation='WHO',
            url='https://www.who.int',
            relevance='High'
        )
        
        self.org2 = ContextOrganization.objects.create(
            context=self.context,
            name='National Institutes of Health',
            abbreviation='NIH',
            url='https://www.nih.gov',
            relevance='High'
        )
        
        # Create search queries
        self.query1 = SearchQuery.objects.create(
            session=self.session,
            query_string='("artificial intelligence" OR "AI") AND "healthcare" AND "clinical outcomes"',
            search_type='standard',
            target_results=100,
            priority='high'
        )
        
        self.query2 = SearchQuery.objects.create(
            session=self.session,
            query_string='("machine learning" OR "deep learning") AND "patient care" AND "hospital"',
            search_type='academic',
            target_results=50,
            priority='medium'
        )
        
        # Create query versions
        SearchQueryVersion.objects.create(
            query=self.query1,
            version_number=1,
            query_string='initial query version',
            modified_by=self.user,
            change_reason='Initial creation'
        )
        
        SearchQueryVersion.objects.create(
            query=self.query1,
            version_number=2,
            query_string=self.query1.query_string,
            modified_by=self.user,
            change_reason='Added clinical outcomes'
        )
    
    def test_generate_search_strategy_report(self):
        """Test generation of comprehensive search strategy report."""
        report = self.service.generate_search_strategy_report(str(self.session.id))
        
        self.assertIsInstance(report, dict)
        
        # Check main sections
        self.assertIn('session_info', report)
        self.assertIn('pic_framework', report)
        self.assertIn('search_queries', report)
        self.assertIn('organizations', report)
        self.assertIn('search_evolution', report)
        self.assertIn('methodology', report)
        
        # Check session info
        session_info = report['session_info']
        self.assertEqual(session_info['title'], 'Healthcare AI Review')
        self.assertEqual(session_info['status'], 'ready_to_execute')
        
        # Check PIC framework
        pic = report['pic_framework']
        self.assertIn('population', pic)
        self.assertIn('interest', pic)
        self.assertIn('context', pic)
        self.assertEqual(pic['population']['description'], 'Healthcare providers and patients')
    
    def test_document_pic_framework(self):
        """Test documentation of PIC framework."""
        pic_doc = self.service.document_pic_framework(str(self.session.id))
        
        self.assertIsInstance(pic_doc, dict)
        
        # Check population documentation
        population = pic_doc['population']
        self.assertIn('description', population)
        self.assertIn('inclusion_criteria', population)
        self.assertIn('exclusion_criteria', population)
        self.assertIn('scope', population)
        
        # Check interest documentation
        interest = pic_doc['interest']
        self.assertIn('primary_focus', interest)
        self.assertIn('secondary_aspects', interest)
        self.assertIn('outcomes', interest)
        
        # Check context documentation
        context = pic_doc['context']
        self.assertIn('setting', context)
        self.assertIn('constraints', context)
        self.assertIn('organizations', context)
        self.assertEqual(len(context['organizations']), 2)
    
    def test_generate_query_documentation(self):
        """Test generation of query documentation."""
        query_doc = self.service.generate_query_documentation(str(self.session.id))
        
        self.assertIsInstance(query_doc, list)
        self.assertEqual(len(query_doc), 2)
        
        # Check query structure
        for query in query_doc:
            self.assertIn('query_id', query)
            self.assertIn('query_string', query)
            self.assertIn('type', query)
            self.assertIn('priority', query)
            self.assertIn('target_results', query)
            self.assertIn('boolean_operators', query)
            self.assertIn('search_terms', query)
            self.assertIn('version_history', query)
        
        # Check boolean operator analysis
        query1_doc = query_doc[0]
        self.assertIn('AND', query1_doc['boolean_operators'])
        self.assertIn('OR', query1_doc['boolean_operators'])
        self.assertEqual(query1_doc['boolean_operators']['AND'], 2)
        self.assertEqual(query1_doc['boolean_operators']['OR'], 1)
    
    def test_analyze_search_evolution(self):
        """Test analysis of search strategy evolution."""
        evolution = self.service.analyze_search_evolution(str(self.session.id))
        
        self.assertIsInstance(evolution, dict)
        self.assertIn('total_versions', evolution)
        self.assertIn('queries_modified', evolution)
        self.assertIn('modification_timeline', evolution)
        self.assertIn('change_patterns', evolution)
        
        self.assertEqual(evolution['total_versions'], 2)
        self.assertEqual(evolution['queries_modified'], 1)
        
        # Check modification timeline
        timeline = evolution['modification_timeline']
        self.assertIsInstance(timeline, list)
        self.assertTrue(len(timeline) > 0)
    
    def test_generate_search_string_examples(self):
        """Test generation of search string examples."""
        examples = self.service.generate_search_string_examples(str(self.session.id))
        
        self.assertIsInstance(examples, dict)
        self.assertIn('google_scholar', examples)
        self.assertIn('pubmed', examples)
        self.assertIn('general_search', examples)
        
        # Check format adaptation
        google_scholar = examples['google_scholar']
        self.assertIsInstance(google_scholar, list)
        self.assertTrue(all(isinstance(s, str) for s in google_scholar))
    
    def test_calculate_search_complexity_metrics(self):
        """Test calculation of search complexity metrics."""
        metrics = self.service.calculate_search_complexity_metrics(str(self.session.id))
        
        self.assertIsInstance(metrics, dict)
        self.assertIn('total_queries', metrics)
        self.assertIn('average_query_length', metrics)
        self.assertIn('total_search_terms', metrics)
        self.assertIn('unique_search_terms', metrics)
        self.assertIn('boolean_complexity', metrics)
        self.assertIn('complexity_score', metrics)
        
        self.assertEqual(metrics['total_queries'], 2)
        self.assertGreater(metrics['average_query_length'], 0)
        self.assertGreater(metrics['total_search_terms'], 0)
        
        # Check complexity score is normalized
        self.assertGreaterEqual(metrics['complexity_score'], 0)
        self.assertLessEqual(metrics['complexity_score'], 100)
    
    def test_generate_reproducibility_checklist(self):
        """Test generation of reproducibility checklist."""
        checklist = self.service.generate_reproducibility_checklist(str(self.session.id))
        
        self.assertIsInstance(checklist, list)
        
        for item in checklist:
            self.assertIn('category', item)
            self.assertIn('item', item)
            self.assertIn('documented', item)
            self.assertIn('details', item)
            self.assertIsInstance(item['documented'], bool)
        
        # Check key categories
        categories = {item['category'] for item in checklist}
        self.assertIn('Search Strategy', categories)
        self.assertIn('Databases', categories)
        self.assertIn('Inclusion Criteria', categories)
        self.assertIn('Time Period', categories)
    
    def test_export_search_strategy_template(self):
        """Test export of search strategy as reusable template."""
        template = self.service.export_search_strategy_template(str(self.session.id))
        
        self.assertIsInstance(template, dict)
        self.assertIn('template_name', template)
        self.assertIn('description', template)
        self.assertIn('pic_framework', template)
        self.assertIn('query_patterns', template)
        self.assertIn('organizations', template)
        self.assertIn('metadata', template)
        
        # Check metadata
        metadata = template['metadata']
        self.assertIn('created_date', metadata)
        self.assertIn('created_by', metadata)
        self.assertIn('domain', metadata)
        self.assertIn('keywords', metadata)
    
    def test_compare_search_strategies(self):
        """Test comparison of multiple search strategies."""
        # Create another session for comparison
        session2 = SearchSession.objects.create(
            title='AI in Education Review',
            description='Review of AI in education',
            owner=self.user,
            status='defining_search'
        )
        
        SearchQuery.objects.create(
            session=session2,
            query_string='("artificial intelligence") AND "education"',
            search_type='standard'
        )
        
        comparison = self.service.compare_search_strategies(
            [str(self.session.id), str(session2.id)]
        )
        
        self.assertIsInstance(comparison, dict)
        self.assertIn('sessions', comparison)
        self.assertIn('similarities', comparison)
        self.assertIn('differences', comparison)
        self.assertIn('complexity_comparison', comparison)
        
        self.assertEqual(len(comparison['sessions']), 2)
    
    def test_generate_search_rationale_documentation(self):
        """Test generation of search rationale documentation."""
        rationale = self.service.generate_search_rationale_documentation(str(self.session.id))
        
        self.assertIsInstance(rationale, dict)
        self.assertIn('objective_alignment', rationale)
        self.assertIn('term_justification', rationale)
        self.assertIn('scope_decisions', rationale)
        self.assertIn('exclusion_rationale', rationale)
        
        # Check term justification
        term_just = rationale['term_justification']
        self.assertIsInstance(term_just, list)
        
        for term in term_just:
            self.assertIn('term', term)
            self.assertIn('reason', term)
            self.assertIn('alternatives', term)
    
    def test_validate_search_strategy_completeness(self):
        """Test validation of search strategy completeness."""
        validation = self.service.validate_search_strategy_completeness(str(self.session.id))
        
        self.assertIsInstance(validation, dict)
        self.assertIn('is_complete', validation)
        self.assertIn('completeness_score', validation)
        self.assertIn('missing_elements', validation)
        self.assertIn('recommendations', validation)
        
        # Check completeness score
        self.assertGreaterEqual(validation['completeness_score'], 0)
        self.assertLessEqual(validation['completeness_score'], 100)
        
        # Check recommendations
        recommendations = validation['recommendations']
        self.assertIsInstance(recommendations, list)
    
    def test_logging_in_report_generation(self):
        """Test that report generation is properly logged."""
        with self.assertLogs('apps.reporting.services.search_strategy_reporting_service', level='INFO') as cm:
            self.service.generate_search_strategy_report(str(self.session.id))
        
        self.assertTrue(any('Generating search strategy report' in msg for msg in cm.output))
        self.assertTrue(any('Search strategy report generated' in msg for msg in cm.output))