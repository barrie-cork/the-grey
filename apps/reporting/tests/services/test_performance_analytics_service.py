"""
Tests for PerformanceAnalyticsService.

Tests performance analytics and metric calculations.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.review_manager.models import SearchSession, SessionActivity
from apps.search_strategy.models import SearchQuery
from apps.serp_execution.models import SearchExecution
from apps.results_manager.models import ProcessedResult
from apps.reporting.services.performance_analytics_service import PerformanceAnalyticsService


User = get_user_model()


class TestPerformanceAnalyticsService(TestCase):
    """Test cases for PerformanceAnalyticsService."""
    
    def setUp(self):
        """Set up test data."""
        self.service = PerformanceAnalyticsService()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test session
        self.session = SearchSession.objects.create(
            title='Test Session',
            description='Test description',
            owner=self.user,
            status='completed'
        )
        
        # Create search queries
        self.query1 = SearchQuery.objects.create(
            session=self.session,
            query_string='test query 1',
            search_type='standard'
        )
        
        self.query2 = SearchQuery.objects.create(
            session=self.session,
            query_string='test query 2',
            search_type='academic'
        )
        
        # Create search executions
        self.execution1 = SearchExecution.objects.create(
            query=self.query1,
            search_engine='google',
            status='completed',
            results_count=10,
            estimated_cost=Decimal('0.50'),
            duration_seconds=2.5,
            started_at=timezone.now() - timedelta(hours=2),
            completed_at=timezone.now() - timedelta(hours=2) + timedelta(seconds=3)
        )
        
        self.execution2 = SearchExecution.objects.create(
            query=self.query2,
            search_engine='google',
            status='failed',
            error_message='Rate limit exceeded',
            estimated_cost=Decimal('0.00'),
            duration_seconds=1.0
        )
    
    def test_calculate_session_performance_metrics(self):
        """Test calculation of session performance metrics."""
        metrics = self.service.calculate_session_performance_metrics(str(self.session.id))
        
        self.assertIsInstance(metrics, dict)
        self.assertIn('session_id', metrics)
        self.assertIn('execution_metrics', metrics)
        self.assertIn('timing_metrics', metrics)
        self.assertIn('cost_metrics', metrics)
        self.assertIn('quality_metrics', metrics)
        
        # Check execution metrics
        exec_metrics = metrics['execution_metrics']
        self.assertEqual(exec_metrics['total_executions'], 2)
        self.assertEqual(exec_metrics['successful_executions'], 1)
        self.assertEqual(exec_metrics['failed_executions'], 1)
        self.assertEqual(exec_metrics['success_rate'], 50.0)
        
        # Check cost metrics
        cost_metrics = metrics['cost_metrics']
        self.assertEqual(cost_metrics['total_cost'], Decimal('0.50'))
        self.assertEqual(cost_metrics['average_cost_per_execution'], Decimal('0.25'))
    
    def test_generate_performance_report(self):
        """Test generation of comprehensive performance report."""
        report = self.service.generate_performance_report(str(self.session.id))
        
        self.assertIn('summary', report)
        self.assertIn('detailed_metrics', report)
        self.assertIn('recommendations', report)
        self.assertIn('timeline', report)
        
        # Check summary
        summary = report['summary']
        self.assertIn('overall_performance_score', summary)
        self.assertIn('key_findings', summary)
        
        # Check recommendations
        recommendations = report['recommendations']
        self.assertIsInstance(recommendations, list)
        self.assertTrue(len(recommendations) > 0)
    
    def test_calculate_time_series_metrics(self):
        """Test calculation of time series metrics."""
        # Create more executions over time
        for i in range(5):
            SearchExecution.objects.create(
                query=self.query1,
                search_engine='google',
                status='completed',
                results_count=10 + i,
                estimated_cost=Decimal('0.50'),
                duration_seconds=2.0 + (i * 0.5),
                started_at=timezone.now() - timedelta(days=i),
                completed_at=timezone.now() - timedelta(days=i) + timedelta(seconds=3)
            )
        
        time_series = self.service.calculate_time_series_metrics(
            str(self.session.id), 
            interval='daily'
        )
        
        self.assertIsInstance(time_series, list)
        self.assertTrue(len(time_series) > 0)
        
        # Check time series structure
        for point in time_series:
            self.assertIn('timestamp', point)
            self.assertIn('executions', point)
            self.assertIn('success_rate', point)
            self.assertIn('average_duration', point)
            self.assertIn('total_cost', point)
    
    def test_compare_search_engines_performance(self):
        """Test comparison of different search engines."""
        # Add execution with different engine
        SearchExecution.objects.create(
            query=self.query1,
            search_engine='bing',
            status='completed',
            results_count=8,
            estimated_cost=Decimal('0.40'),
            duration_seconds=3.0
        )
        
        comparison = self.service.compare_search_engines_performance(str(self.session.id))
        
        self.assertIn('google', comparison)
        self.assertIn('bing', comparison)
        
        google_stats = comparison['google']
        self.assertEqual(google_stats['total_executions'], 2)
        self.assertEqual(google_stats['success_rate'], 50.0)
        
        bing_stats = comparison['bing']
        self.assertEqual(bing_stats['total_executions'], 1)
        self.assertEqual(bing_stats['success_rate'], 100.0)
    
    def test_identify_performance_bottlenecks(self):
        """Test identification of performance bottlenecks."""
        bottlenecks = self.service.identify_performance_bottlenecks(str(self.session.id))
        
        self.assertIsInstance(bottlenecks, list)
        
        for bottleneck in bottlenecks:
            self.assertIn('type', bottleneck)
            self.assertIn('severity', bottleneck)
            self.assertIn('description', bottleneck)
            self.assertIn('recommendation', bottleneck)
            self.assertIn(['high', 'medium', 'low'], bottleneck['severity'])
    
    def test_calculate_cost_efficiency_metrics(self):
        """Test calculation of cost efficiency metrics."""
        # Add more results
        for i in range(5):
            ProcessedResult.objects.create(
                session=self.session,
                title=f'Result {i}',
                url=f'https://example.com/{i}',
                snippet=f'Snippet {i}',
                is_pdf=i % 2 == 0,
                publication_year=2020 + (i % 5)
            )
        
        efficiency = self.service.calculate_cost_efficiency_metrics(str(self.session.id))
        
        self.assertIn('cost_per_result', efficiency)
        self.assertIn('cost_per_relevant_result', efficiency)
        self.assertIn('efficiency_score', efficiency)
        self.assertIn('cost_breakdown', efficiency)
        
        # Check cost breakdown
        breakdown = efficiency['cost_breakdown']
        self.assertIn('by_engine', breakdown)
        self.assertIn('by_query_type', breakdown)
    
    def test_metrics_with_no_executions(self):
        """Test metrics calculation for session with no executions."""
        empty_session = SearchSession.objects.create(
            title='Empty Session',
            description='No executions',
            owner=self.user,
            status='draft'
        )
        
        metrics = self.service.calculate_session_performance_metrics(str(empty_session.id))
        
        self.assertEqual(metrics['execution_metrics']['total_executions'], 0)
        self.assertEqual(metrics['execution_metrics']['success_rate'], 0.0)
        self.assertEqual(metrics['cost_metrics']['total_cost'], Decimal('0.00'))
    
    def test_performance_trend_analysis(self):
        """Test performance trend analysis over time."""
        trends = self.service.analyze_performance_trends(str(self.session.id))
        
        self.assertIn('duration_trend', trends)
        self.assertIn('success_rate_trend', trends)
        self.assertIn('cost_trend', trends)
        self.assertIn('overall_trend', trends)
        
        # Trend should be one of: improving, stable, declining
        self.assertIn(trends['overall_trend'], ['improving', 'stable', 'declining'])
    
    def test_generate_optimization_suggestions(self):
        """Test generation of optimization suggestions."""
        suggestions = self.service.generate_optimization_suggestions(str(self.session.id))
        
        self.assertIsInstance(suggestions, list)
        
        for suggestion in suggestions:
            self.assertIn('category', suggestion)
            self.assertIn('priority', suggestion)
            self.assertIn('description', suggestion)
            self.assertIn('expected_impact', suggestion)
            self.assertIn('implementation_difficulty', suggestion)
    
    def test_calculate_api_usage_statistics(self):
        """Test calculation of API usage statistics."""
        stats = self.service.calculate_api_usage_statistics(str(self.session.id))
        
        self.assertIn('total_api_calls', stats)
        self.assertIn('successful_calls', stats)
        self.assertIn('failed_calls', stats)
        self.assertIn('rate_limit_hits', stats)
        self.assertIn('average_response_time', stats)
        self.assertIn('api_availability', stats)
        
        self.assertEqual(stats['total_api_calls'], 2)
        self.assertEqual(stats['rate_limit_hits'], 1)
    
    def test_session_duration_analysis(self):
        """Test session duration analysis."""
        # Add session activities
        SessionActivity.objects.create(
            session=self.session,
            user=self.user,
            action='session_started',
            timestamp=timezone.now() - timedelta(hours=3)
        )
        
        SessionActivity.objects.create(
            session=self.session,
            user=self.user,
            action='session_completed',
            timestamp=timezone.now() - timedelta(minutes=30)
        )
        
        duration = self.service.analyze_session_duration(str(self.session.id))
        
        self.assertIn('total_duration_hours', duration)
        self.assertIn('active_duration_hours', duration)
        self.assertIn('idle_time_percentage', duration)
        self.assertIn('phase_durations', duration)
    
    def test_logging_in_performance_calculations(self):
        """Test that performance calculations are properly logged."""
        with self.assertLogs('apps.reporting.services.performance_analytics_service', level='INFO') as cm:
            self.service.calculate_session_performance_metrics(str(self.session.id))
        
        self.assertTrue(any('Calculating performance metrics' in msg for msg in cm.output))
        self.assertTrue(any('Performance metrics calculated' in msg for msg in cm.output))