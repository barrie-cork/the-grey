"""
Tests for ProcessingAnalyticsService.

Tests processing analytics and performance monitoring.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.review_manager.models import SearchSession
from apps.serp_execution.models import SearchExecution, RawSearchResult
from apps.results_manager.models import ProcessedResult, ProcessingSession, DuplicateGroup
from apps.results_manager.services.processing_analytics_service import ProcessingAnalyticsService


User = get_user_model()


class TestProcessingAnalyticsService(TestCase):
    """Test cases for ProcessingAnalyticsService."""
    
    def setUp(self):
        """Set up test data."""
        self.service = ProcessingAnalyticsService()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test session
        self.session = SearchSession.objects.create(
            title='Test Processing Analytics',
            description='Testing processing analytics',
            owner=self.user,
            status='processing_results'
        )
        
        # Create processing session
        self.processing_session = ProcessingSession.objects.create(
            session=self.session,
            status='completed',
            started_at=timezone.now() - timedelta(hours=2),
            completed_at=timezone.now() - timedelta(hours=1),
            total_raw_results=100,
            processed_results=85,
            duplicate_groups=15,
            errors_count=0
        )
        
        # Create raw results
        for i in range(100):
            RawSearchResult.objects.create(
                execution_id=f'exec-{i//10}',
                title=f'Result {i}',
                link=f'https://example.com/result/{i}',
                snippet=f'Snippet for result {i}',
                position=i + 1
            )
        
        # Create processed results
        for i in range(85):
            ProcessedResult.objects.create(
                session=self.session,
                title=f'Processed Result {i}',
                url=f'https://example.com/result/{i}',
                snippet=f'Processed snippet {i}',
                relevance_score=0.5 + (i * 0.005),
                processing_session=self.processing_session
            )
        
        # Create duplicate groups
        for i in range(15):
            DuplicateGroup.objects.create(
                session=self.session,
                group_key=f'group_{i}',
                member_count=2 + (i % 3),
                representative_result_id=f'result_{i}'
            )
    
    def test_calculate_processing_metrics(self):
        """Test calculation of processing metrics."""
        metrics = self.service.calculate_processing_metrics(str(self.session.id))
        
        self.assertIsInstance(metrics, dict)
        self.assertIn('total_processing_sessions', metrics)
        self.assertIn('average_processing_time', metrics)
        self.assertIn('processing_success_rate', metrics)
        self.assertIn('deduplication_effectiveness', metrics)
        self.assertIn('quality_metrics', metrics)
        
        # Check calculated values
        self.assertEqual(metrics['total_processing_sessions'], 1)
        self.assertEqual(metrics['processing_success_rate'], 100.0)
        self.assertEqual(metrics['deduplication_effectiveness'], 15.0)  # 15% duplicates
    
    def test_generate_processing_report(self):
        """Test generation of comprehensive processing report."""
        report = self.service.generate_processing_report(str(self.session.id))
        
        self.assertIsInstance(report, dict)
        self.assertIn('summary', report)
        self.assertIn('session_details', report)
        self.assertIn('performance_analysis', report)
        self.assertIn('quality_assessment', report)
        self.assertIn('recommendations', report)
        
        # Check summary
        summary = report['summary']
        self.assertIn('total_raw_results', summary)
        self.assertIn('unique_results', summary)
        self.assertIn('processing_duration', summary)
        
        self.assertEqual(summary['total_raw_results'], 100)
        self.assertEqual(summary['unique_results'], 85)
    
    def test_analyze_processing_performance(self):
        """Test analysis of processing performance."""
        performance = self.service.analyze_processing_performance(str(self.session.id))
        
        self.assertIsInstance(performance, dict)
        self.assertIn('throughput_per_minute', performance)
        self.assertIn('average_result_processing_time', performance)
        self.assertIn('bottlenecks', performance)
        self.assertIn('optimization_opportunities', performance)
        
        # Check throughput calculation
        self.assertGreater(performance['throughput_per_minute'], 0)
    
    def test_track_processing_errors(self):
        """Test tracking and analysis of processing errors."""
        # Create processing session with errors
        error_session = ProcessingSession.objects.create(
            session=self.session,
            status='completed_with_errors',
            started_at=timezone.now() - timedelta(hours=1),
            completed_at=timezone.now() - timedelta(minutes=30),
            total_raw_results=50,
            processed_results=45,
            duplicate_groups=3,
            errors_count=5,
            error_details={
                'network_errors': 2,
                'parsing_errors': 3,
                'error_messages': [
                    'Failed to parse URL',
                    'Network timeout',
                    'Invalid metadata format'
                ]
            }
        )
        
        error_analysis = self.service.track_processing_errors(str(self.session.id))
        
        self.assertIsInstance(error_analysis, dict)
        self.assertIn('total_errors', error_analysis)
        self.assertIn('error_rate', error_analysis)
        self.assertIn('error_types', error_analysis)
        self.assertIn('affected_sessions', error_analysis)
        
        self.assertEqual(error_analysis['total_errors'], 5)
        self.assertGreater(error_analysis['error_rate'], 0)
    
    def test_calculate_quality_scores(self):
        """Test calculation of processing quality scores."""
        quality = self.service.calculate_quality_scores(str(self.session.id))
        
        self.assertIsInstance(quality, dict)
        self.assertIn('completeness_score', quality)
        self.assertIn('accuracy_score', quality)
        self.assertIn('enrichment_score', quality)
        self.assertIn('overall_quality_score', quality)
        
        # Scores should be between 0 and 100
        for score in quality.values():
            self.assertGreaterEqual(score, 0)
            self.assertLessEqual(score, 100)
    
    def test_compare_processing_sessions(self):
        """Test comparison of multiple processing sessions."""
        # Create another processing session
        session2 = ProcessingSession.objects.create(
            session=self.session,
            status='completed',
            started_at=timezone.now() - timedelta(hours=4),
            completed_at=timezone.now() - timedelta(hours=3),
            total_raw_results=150,
            processed_results=140,
            duplicate_groups=10,
            errors_count=0
        )
        
        comparison = self.service.compare_processing_sessions(str(self.session.id))
        
        self.assertIsInstance(comparison, list)
        self.assertEqual(len(comparison), 2)
        
        # Check session comparison structure
        for session_data in comparison:
            self.assertIn('session_id', session_data)
            self.assertIn('processing_time', session_data)
            self.assertIn('success_rate', session_data)
            self.assertIn('throughput', session_data)
            self.assertIn('quality_score', session_data)
    
    def test_identify_processing_patterns(self):
        """Test identification of processing patterns."""
        patterns = self.service.identify_processing_patterns(str(self.session.id))
        
        self.assertIsInstance(patterns, dict)
        self.assertIn('common_duplicate_patterns', patterns)
        self.assertIn('quality_trends', patterns)
        self.assertIn('performance_patterns', patterns)
        self.assertIn('error_patterns', patterns)
        
        # Check duplicate patterns
        dup_patterns = patterns['common_duplicate_patterns']
        self.assertIsInstance(dup_patterns, list)
    
    def test_generate_processing_timeline(self):
        """Test generation of processing timeline."""
        timeline = self.service.generate_processing_timeline(str(self.session.id))
        
        self.assertIsInstance(timeline, list)
        self.assertTrue(len(timeline) > 0)
        
        for event in timeline:
            self.assertIn('timestamp', event)
            self.assertIn('event_type', event)
            self.assertIn('details', event)
            self.assertIn('metrics', event)
    
    def test_calculate_resource_utilization(self):
        """Test calculation of resource utilization metrics."""
        utilization = self.service.calculate_resource_utilization(str(self.session.id))
        
        self.assertIsInstance(utilization, dict)
        self.assertIn('cpu_usage_estimate', utilization)
        self.assertIn('memory_usage_estimate', utilization)
        self.assertIn('api_calls_made', utilization)
        self.assertIn('database_operations', utilization)
        self.assertIn('efficiency_rating', utilization)
    
    def test_batch_processing_analysis(self):
        """Test analysis of batch processing performance."""
        # Create batch processing data
        batch_data = {
            'batch_1': {'size': 50, 'duration': 120, 'errors': 0},
            'batch_2': {'size': 50, 'duration': 150, 'errors': 2}
        }
        
        self.processing_session.metadata = {'batch_data': batch_data}
        self.processing_session.save()
        
        batch_analysis = self.service.analyze_batch_processing(str(self.session.id))
        
        self.assertIsInstance(batch_analysis, dict)
        self.assertIn('total_batches', batch_analysis)
        self.assertIn('average_batch_size', batch_analysis)
        self.assertIn('average_batch_duration', batch_analysis)
        self.assertIn('batch_error_rate', batch_analysis)
        self.assertIn('optimal_batch_size', batch_analysis)
    
    def test_generate_optimization_recommendations(self):
        """Test generation of optimization recommendations."""
        recommendations = self.service.generate_optimization_recommendations(
            str(self.session.id)
        )
        
        self.assertIsInstance(recommendations, list)
        
        for rec in recommendations:
            self.assertIn('category', rec)
            self.assertIn('priority', rec)
            self.assertIn('recommendation', rec)
            self.assertIn('expected_impact', rec)
            self.assertIn('implementation_complexity', rec)
    
    def test_processing_with_no_results(self):
        """Test analytics for session with no processing."""
        empty_session = SearchSession.objects.create(
            title='Empty Processing Session',
            description='No results processed',
            owner=self.user,
            status='ready_for_review'
        )
        
        metrics = self.service.calculate_processing_metrics(str(empty_session.id))
        
        self.assertEqual(metrics['total_processing_sessions'], 0)
        self.assertEqual(metrics['processing_success_rate'], 0.0)
    
    def test_calculate_deduplication_impact(self):
        """Test calculation of deduplication impact."""
        impact = self.service.calculate_deduplication_impact(str(self.session.id))
        
        self.assertIsInstance(impact, dict)
        self.assertIn('duplicates_removed', impact)
        self.assertIn('storage_saved_percentage', impact)
        self.assertIn('processing_time_saved', impact)
        self.assertIn('quality_improvement', impact)
        
        self.assertEqual(impact['duplicates_removed'], 15)
        self.assertGreater(impact['storage_saved_percentage'], 0)
    
    def test_logging_in_analytics(self):
        """Test that analytics operations are properly logged."""
        with self.assertLogs('apps.results_manager.services.processing_analytics_service', level='INFO') as cm:
            self.service.calculate_processing_metrics(str(self.session.id))
        
        self.assertTrue(any('Calculating processing metrics' in msg for msg in cm.output))
        self.assertTrue(any('Processing metrics calculated' in msg for msg in cm.output))