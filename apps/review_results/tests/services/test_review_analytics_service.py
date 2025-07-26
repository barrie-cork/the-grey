"""
Tests for ReviewAnalyticsService.

Tests review data export, validation, and analytics functionality.
"""

from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from urllib.parse import urlparse

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.review_manager.models import SearchSession
from apps.results_manager.models import ProcessedResult
from apps.review_results.models import ReviewTag, ReviewTagAssignment
from apps.review_results.services.review_analytics_service import ReviewAnalyticsService


User = get_user_model()


class TestReviewAnalyticsService(TestCase):
    """Test cases for ReviewAnalyticsService."""
    
    def setUp(self):
        """Set up test data."""
        self.service = ReviewAnalyticsService()
        
        # Create test users
        self.user1 = User.objects.create_user(
            username='reviewer1',
            email='reviewer1@example.com',
            password='testpass123'
        )
        
        self.user2 = User.objects.create_user(
            username='reviewer2',
            email='reviewer2@example.com',
            password='testpass123'
        )
        
        # Create test session
        self.session = SearchSession.objects.create(
            title='Test Review Analytics',
            description='Testing review analytics',
            owner=self.user1,
            status='under_review'
        )
        
        # Create test results
        self.results = []
        for i in range(20):
            result = ProcessedResult.objects.create(
                session=self.session,
                title=f'Result {i}: Study on Topic X',
                url=f'https://journal{i % 3}.com/article/{i}',
                snippet=f'This study examines topic X with methodology Y',
                publication_year=2020 + (i % 5),
                document_type='journal_article' if i % 2 == 0 else 'report',
                is_pdf=i % 2 == 0,
                has_full_text=i % 3 == 0
            )
            self.results.append(result)
        
        # Create tags
        self.tag_include = ReviewTag.objects.create(
            name='Include',
            description='Include in final review'
        )
        self.tag_exclude = ReviewTag.objects.create(
            name='Exclude', 
            description='Exclude from final review'
        )
        self.tag_maybe = ReviewTag.objects.create(
            name='Maybe',
            description='Requires further review'
        )
        
        # Create tag assignments (15 reviewed, 5 unreviewed)
        for i in range(15):
            tag = self.tag_include if i < 8 else self.tag_exclude
            notes = f'Review notes for result {i}' if i % 2 == 0 else ''
            
            ReviewTagAssignment.objects.create(
                result=self.results[i],
                tag=tag,
                assigned_by=self.user1 if i % 3 != 0 else self.user2,
                notes=notes
            )
    
    def test_export_review_data(self):
        """Test export of review data."""
        export_data = self.service.export_review_data(
            str(self.session.id),
            format_type='csv'
        )
        
        self.assertIsInstance(export_data, dict)
        self.assertIn('session_id', export_data)
        self.assertIn('export_format', export_data)
        self.assertIn('export_timestamp', export_data)
        self.assertIn('results', export_data)
        self.assertIn('summary', export_data)
        
        # Check results data
        results = export_data['results']
        self.assertEqual(len(results), 20)
        
        # Check first reviewed result
        reviewed_result = results[0]
        self.assertIn('id', reviewed_result)
        self.assertIn('title', reviewed_result)
        self.assertIn('url', reviewed_result)
        self.assertIn('is_reviewed', reviewed_result)
        self.assertIn('tags', reviewed_result)
        self.assertIn('domain', reviewed_result)
        
        self.assertTrue(reviewed_result['is_reviewed'])
        self.assertEqual(len(reviewed_result['tags']), 1)
    
    def test_safe_get_display_url(self):
        """Test safe extraction of display URL."""
        # Create mock result with get_display_url method
        mock_result = Mock()
        mock_result.get_display_url.return_value = 'example.com'
        mock_result.url = 'https://example.com/page'
        
        display_url = self.service._safe_get_display_url(mock_result)
        self.assertEqual(display_url, 'example.com')
        
        # Test result without get_display_url method
        result_without_method = self.results[0]
        display_url = self.service._safe_get_display_url(result_without_method)
        self.assertEqual(display_url, 'journal0.com')
        
        # Test result with exception in get_display_url
        mock_result.get_display_url.side_effect = Exception('Test error')
        display_url = self.service._safe_get_display_url(mock_result)
        self.assertEqual(display_url, 'https://example.com/page')
        
        # Test result with no URL
        empty_result = Mock()
        empty_result.url = None
        display_url = self.service._safe_get_display_url(empty_result)
        self.assertEqual(display_url, '')
    
    def test_validate_review_completeness(self):
        """Test validation of review completeness."""
        validation = self.service.validate_review_completeness(str(self.session.id))
        
        self.assertIsInstance(validation, dict)
        self.assertIn('is_complete', validation)
        self.assertIn('total_results', validation)
        self.assertIn('reviewed_results', validation)
        self.assertIn('missing_reviews', validation)
        self.assertIn('issues', validation)
        self.assertIn('recommendations', validation)
        
        # Check validation results
        self.assertFalse(validation['is_complete'])  # Not all reviewed
        self.assertEqual(validation['total_results'], 20)
        self.assertEqual(validation['reviewed_results'], 15)
        self.assertEqual(validation['missing_reviews'], 5)
        
        # Check issues
        self.assertTrue(len(validation['issues']) > 0)
        self.assertTrue(any('not been reviewed' in issue for issue in validation['issues']))
    
    def test_generate_review_quality_metrics(self):
        """Test generation of review quality metrics."""
        metrics = self.service.generate_review_quality_metrics(str(self.session.id))
        
        self.assertIsInstance(metrics, dict)
        self.assertIn('session_id', metrics)
        self.assertIn('overall_quality_score', metrics)
        self.assertIn('metrics', metrics)
        self.assertIn('statistics', metrics)
        self.assertIn('recommendations', metrics)
        
        # Check individual metrics
        individual_metrics = metrics['metrics']
        self.assertIn('coverage_score', individual_metrics)
        self.assertIn('balance_score', individual_metrics)
        self.assertIn('consistency_score', individual_metrics)
        self.assertIn('notes_quality_score', individual_metrics)
        
        # Check statistics
        stats = metrics['statistics']
        self.assertIn('total_results', stats)
        self.assertIn('reviewed_results', stats)
        self.assertIn('inclusion_rate', stats)
        
        self.assertEqual(stats['total_results'], 20)
        self.assertEqual(stats['reviewed_results'], 15)
    
    def test_generate_reviewer_performance_report(self):
        """Test generation of reviewer performance report."""
        report = self.service.generate_reviewer_performance_report(str(self.session.id))
        
        self.assertIsInstance(report, dict)
        self.assertIn('session_id', report)
        self.assertIn('total_reviewers', report)
        self.assertIn('reviewer_performance', report)
        self.assertIn('summary', report)
        
        # Check reviewer count
        self.assertEqual(report['total_reviewers'], 2)
        
        # Check performance data
        performance = report['reviewer_performance']
        self.assertEqual(len(performance), 2)
        
        for reviewer_data in performance:
            self.assertIn('username', reviewer_data)
            self.assertIn('total_assignments', reviewer_data)
            self.assertIn('unique_results_reviewed', reviewer_data)
            self.assertIn('inclusion_rate', reviewer_data)
            self.assertIn('notes_rate', reviewer_data)
        
        # Check summary
        summary = report['summary']
        self.assertIn('most_active_reviewer', summary)
        self.assertIn('avg_inclusion_rate', summary)
        self.assertIn('avg_notes_rate', summary)
    
    def test_export_with_multiple_tags(self):
        """Test export when results have multiple tags."""
        # Add multiple tags to a result
        ReviewTagAssignment.objects.create(
            result=self.results[0],
            tag=self.tag_maybe,
            assigned_by=self.user2,
            notes='Needs second opinion'
        )
        
        export_data = self.service.export_review_data(str(self.session.id))
        
        # Find the result with multiple tags
        multi_tag_result = next(
            r for r in export_data['results'] 
            if str(r['id']) == str(self.results[0].id)
        )
        
        self.assertEqual(len(multi_tag_result['tags']), 2)
        self.assertIn('Include', multi_tag_result['tags'])
        self.assertIn('Maybe', multi_tag_result['tags'])
    
    def test_calculate_exclusion_distribution(self):
        """Test calculation of exclusion reason distribution."""
        # Add exclusion reasons to notes
        for i in range(8, 15):
            assignment = ReviewTagAssignment.objects.get(
                result=self.results[i],
                tag=self.tag_exclude
            )
            reasons = [
                'Out of scope',
                'Poor quality',
                'Duplicate content',
                'Not peer reviewed',
                'Out of scope',
                'Poor quality',
                'Out of scope'
            ]
            assignment.notes = f'Excluded: {reasons[i-8]}'
            assignment.save()
        
        # Run validation which includes exclusion analysis
        validation = self.service.validate_review_completeness(str(self.session.id))
        
        # Export data should show exclusion patterns
        export_data = self.service.export_review_data(str(self.session.id))
        
        excluded_results = [
            r for r in export_data['results'] 
            if 'Exclude' in r['tags']
        ]
        
        self.assertEqual(len(excluded_results), 7)
    
    def test_quality_metrics_edge_cases(self):
        """Test quality metrics with edge cases."""
        # Create session with no reviews
        empty_session = SearchSession.objects.create(
            title='Empty Review Session',
            description='No reviews yet',
            owner=self.user1,
            status='ready_for_review'
        )
        
        ProcessedResult.objects.create(
            session=empty_session,
            title='Unreviewed Result',
            url='https://example.com',
            snippet='Test',
            is_pdf=False
        )
        
        metrics = self.service.generate_review_quality_metrics(str(empty_session.id))
        
        self.assertEqual(metrics['overall_quality_score'], 0)
        self.assertEqual(metrics['statistics']['reviewed_results'], 0)
    
    def test_reviewer_agreement_analysis(self):
        """Test analysis of inter-reviewer agreement."""
        # Create overlapping reviews
        result = self.results[16]
        
        # Both reviewers tag the same result
        ReviewTagAssignment.objects.create(
            result=result,
            tag=self.tag_include,
            assigned_by=self.user1
        )
        
        ReviewTagAssignment.objects.create(
            result=result,
            tag=self.tag_include,
            assigned_by=self.user2
        )
        
        metrics = self.service.generate_review_quality_metrics(str(self.session.id))
        
        # Agreement should be reflected in consistency score
        self.assertGreater(metrics['metrics']['consistency_score'], 0)
    
    def test_export_format_variations(self):
        """Test different export format types."""
        formats = ['csv', 'json', 'excel']
        
        for format_type in formats:
            export_data = self.service.export_review_data(
                str(self.session.id),
                format_type=format_type
            )
            
            self.assertEqual(export_data['export_format'], format_type)
            self.assertIsInstance(export_data['results'], list)
    
    def test_notes_aggregation(self):
        """Test aggregation of review notes."""
        # Add multiple notes to same result
        result = self.results[17]
        
        ReviewTagAssignment.objects.create(
            result=result,
            tag=self.tag_include,
            assigned_by=self.user1,
            notes='First reviewer notes'
        )
        
        ReviewTagAssignment.objects.create(
            result=result,
            tag=self.tag_maybe,
            assigned_by=self.user2,
            notes='Second reviewer notes'
        )
        
        export_data = self.service.export_review_data(str(self.session.id))
        
        # Find the result
        noted_result = next(
            r for r in export_data['results']
            if str(r['id']) == str(result.id)
        )
        
        # Notes should be concatenated
        self.assertIn('First reviewer notes', noted_result['review_notes'])
        self.assertIn('Second reviewer notes', noted_result['review_notes'])
    
    def test_completeness_with_all_reviewed(self):
        """Test completeness validation when all results are reviewed."""
        # Review remaining results
        for i in range(15, 20):
            ReviewTagAssignment.objects.create(
                result=self.results[i],
                tag=self.tag_include if i < 18 else self.tag_exclude,
                assigned_by=self.user1
            )
        
        validation = self.service.validate_review_completeness(str(self.session.id))
        
        self.assertTrue(validation['is_complete'])
        self.assertEqual(validation['missing_reviews'], 0)
        self.assertEqual(len(validation['issues']), 0)
    
    def test_logging_in_analytics(self):
        """Test that analytics operations are properly logged."""
        with self.assertLogs('apps.review_results.services.review_analytics_service', level='INFO') as cm:
            self.service.export_review_data(str(self.session.id))
        
        self.assertTrue(any('Exporting review data' in msg for msg in cm.output))
        self.assertTrue(any('Export completed' in msg for msg in cm.output))