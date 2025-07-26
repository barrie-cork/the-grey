"""
Tests for SERP execution views.

Tests for all view classes and AJAX endpoints including ExecuteSearchView,
SearchExecutionStatusView, ErrorRecoveryView, and API endpoints.
"""

import json
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, Mock, MagicMock

from django.test import TestCase, Client, TransactionTestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.messages import get_messages

from apps.review_manager.models import SearchSession
from apps.search_strategy.models import SearchQuery
from apps.serp_execution.models import SearchExecution, RawSearchResult, ExecutionMetrics
from apps.serp_execution.forms import ExecutionConfirmationForm, ErrorRecoveryForm

User = get_user_model()


class TestExecuteSearchView(TestCase):
    """Test the execute search view."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create test session
        self.session = SearchSession.objects.create(
            title='Test Search Session',
            owner=self.user,
            status='ready_to_execute'
        )
        
        # Create test queries
        self.query1 = SearchQuery.objects.create(
            session=self.session,
            population='software developers',
            interest='code review practices',
            context='open source',
            query_string='software developers code review open source',
            search_engines=['google'],
            is_active=True
        )
        
        self.query2 = SearchQuery.objects.create(
            session=self.session,
            population='students',
            interest='online learning',
            context='pandemic',
            query_string='students online learning pandemic',
            search_engines=['google', 'bing'],
            is_active=True
        )
    
    def test_execute_search_view_requires_login(self):
        """Test that view requires authentication."""
        self.client.logout()
        url = reverse('serp_execution:execute_search', kwargs={'session_id': self.session.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_execute_search_view_validates_ownership(self):
        """Test that view validates session ownership."""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        self.client.login(username='otheruser', password='otherpass123')
        
        url = reverse('serp_execution:execute_search', kwargs={'session_id': self.session.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
    
    def test_execute_search_view_validates_status(self):
        """Test that view validates session status."""
        self.session.status = 'draft'
        self.session.save()
        
        url = reverse('serp_execution:execute_search', kwargs={'session_id': self.session.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(str(self.session.id), response.url)
    
    @patch('apps.serp_execution.views.UsageTracker')
    def test_execute_search_view_get(self, mock_usage_tracker):
        """Test GET request to execute search view."""
        # Mock usage tracker
        mock_tracker = Mock()
        mock_tracker.get_current_usage.return_value = {
            'remaining_credits': 10000
        }
        mock_usage_tracker.return_value = mock_tracker
        
        url = reverse('serp_execution:execute_search', kwargs={'session_id': self.session.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Execute Search')
        self.assertContains(response, self.session.title)
        self.assertContains(response, '2')  # Total queries
        self.assertContains(response, '300')  # Estimated credits (2 queries * 100 + 1 query with 2 engines * 100)
    
    @patch('apps.serp_execution.views.calculate_api_cost')
    @patch('apps.serp_execution.views.estimate_execution_time')
    @patch('apps.serp_execution.views.UsageTracker')
    def test_execute_search_view_context_calculations(self, mock_usage_tracker, mock_estimate_time, mock_calc_cost):
        """Test context data calculations."""
        # Setup mocks
        mock_tracker = Mock()
        mock_tracker.get_current_usage.return_value = {'remaining_credits': 5000}
        mock_usage_tracker.return_value = mock_tracker
        
        mock_estimate_time.return_value = 120  # 2 minutes per query
        mock_calc_cost.return_value = Decimal('0.30')
        
        url = reverse('serp_execution:execute_search', kwargs={'session_id': self.session.id})
        response = self.client.get(url)
        
        context = response.context
        self.assertEqual(context['total_queries'], 2)
        self.assertEqual(context['estimated_cost'], Decimal('0.30'))
        self.assertEqual(context['remaining_credits'], 5000)
        self.assertTrue(context['has_sufficient_credits'])
        self.assertEqual(context['estimated_time_minutes'], 4.0)  # 2 queries * 2 minutes
    
    @patch('apps.serp_execution.views.UsageTracker')
    def test_execute_search_insufficient_credits(self, mock_usage_tracker):
        """Test handling insufficient credits."""
        # Mock low credits
        mock_tracker = Mock()
        mock_tracker.get_current_usage.return_value = {'remaining_credits': 50}
        mock_usage_tracker.return_value = mock_tracker
        
        url = reverse('serp_execution:execute_search', kwargs={'session_id': self.session.id})
        response = self.client.get(url)
        
        context = response.context
        self.assertFalse(context['has_sufficient_credits'])
        self.assertContains(response, 'Insufficient credits', status_code=200)
    
    @patch('apps.serp_execution.tasks.initiate_search_session_execution_task')
    def test_execute_search_view_post(self, mock_task):
        """Test POST request to execute search."""
        mock_task.delay.return_value = Mock(id='test-task-id')
        
        url = reverse('serp_execution:execute_search', kwargs={'session_id': self.session.id})
        data = {
            'confirm_execution': True,
            'acknowledge_cost': True
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('execution/session/', response.url)
        mock_task.delay.assert_called_once_with(str(self.session.id))
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertIn('initiated', str(messages[0]))
    
    @patch('apps.serp_execution.tasks.initiate_search_session_execution_task')
    def test_execute_search_view_post_task_failure(self, mock_task):
        """Test handling task initiation failure."""
        mock_task.delay.side_effect = Exception('Celery connection failed')
        
        url = reverse('serp_execution:execute_search', kwargs={'session_id': self.session.id})
        data = {
            'confirm_execution': True,
            'acknowledge_cost': True
        }
        
        response = self.client.post(url, data)
        
        # Should show form again with error
        self.assertEqual(response.status_code, 200)
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('Failed to start', str(messages[0]))
    
    def test_execute_search_no_active_queries(self):
        """Test execution with no active queries."""
        # Deactivate all queries
        SearchQuery.objects.filter(session=self.session).update(is_active=False)
        
        url = reverse('serp_execution:execute_search', kwargs={'session_id': self.session.id})
        response = self.client.get(url)
        
        context = response.context
        self.assertEqual(context['total_queries'], 0)
        self.assertContains(response, 'No active queries')


class TestSearchExecutionStatusView(TestCase):
    """Test the search execution status view."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create test session
        self.session = SearchSession.objects.create(
            title='Test Search Session',
            owner=self.user,
            status='executing'
        )
        
        # Create test query
        self.query = SearchQuery.objects.create(
            session=self.session,
            population='developers',
            interest='testing',
            context='agile',
            query_string='developers testing agile',
            search_engines=['google'],
            is_active=True
        )
        
        # Create test execution
        self.execution = SearchExecution.objects.create(
            query=self.query,
            initiated_by=self.user,
            status='completed',
            results_count=50,
            api_credits_used=100,
            estimated_cost=Decimal('0.10')
        )
    
    def test_status_view_get(self):
        """Test GET request to status view."""
        url = reverse('serp_execution:execution_status', kwargs={'session_id': self.session.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Execution Status')
        self.assertContains(response, self.session.title)
        self.assertContains(response, '1')  # Total executions
        self.assertContains(response, 'Completed')
    
    @patch('apps.serp_execution.views.get_execution_statistics')
    @patch('apps.serp_execution.views.get_failed_executions_with_analysis')
    @patch('apps.serp_execution.views.calculate_search_coverage')
    def test_status_view_with_statistics(self, mock_coverage, mock_failed, mock_stats):
        """Test status view with detailed statistics."""
        # Setup mocks
        mock_stats.return_value = {
            'total_executions': 3,
            'successful_executions': 2,
            'failed_executions': 1,
            'total_results': 150,
            'total_credits': 300,
            'average_duration': 2.5
        }
        
        mock_failed.return_value = [
            {
                'execution_id': str(uuid.uuid4()),
                'query': 'test query',
                'error': 'Rate limit exceeded',
                'retry_eligible': True
            }
        ]
        
        mock_coverage.return_value = {
            'total_coverage': 0.85,
            'unique_domains': 45,
            'academic_percentage': 0.30
        }
        
        # Update session status to show coverage
        self.session.status = 'ready_for_review'
        self.session.save()
        
        url = reverse('serp_execution:execution_status', kwargs={'session_id': self.session.id})
        response = self.client.get(url)
        
        context = response.context
        self.assertEqual(context['stats']['total_executions'], 3)
        self.assertEqual(len(context['failed_executions']), 1)
        self.assertEqual(context['coverage_metrics']['total_coverage'], 0.85)
        self.assertFalse(context['has_running'])  # No running executions
        self.assertEqual(context['refresh_interval'], 0)  # No auto-refresh
    
    def test_status_view_with_running_executions(self):
        """Test status view with running executions."""
        # Create running execution
        SearchExecution.objects.create(
            query=self.query,
            initiated_by=self.user,
            status='running'
        )
        
        url = reverse('serp_execution:execution_status', kwargs={'session_id': self.session.id})
        response = self.client.get(url)
        
        context = response.context
        self.assertTrue(context['has_running'])
        self.assertEqual(context['refresh_interval'], 5000)  # Auto-refresh enabled
    
    def test_status_view_ordering(self):
        """Test execution ordering in status view."""
        # Create multiple executions with different timestamps
        for i in range(3):
            SearchExecution.objects.create(
                query=self.query,
                initiated_by=self.user,
                status='completed',
                created_at=timezone.now() - timedelta(hours=i)
            )
        
        url = reverse('serp_execution:execution_status', kwargs={'session_id': self.session.id})
        response = self.client.get(url)
        
        executions = response.context['executions']
        # Should be ordered by created_at descending (newest first)
        for i in range(len(executions) - 1):
            self.assertGreater(
                executions[i].created_at,
                executions[i + 1].created_at
            )


class TestErrorRecoveryView(TestCase):
    """Test the error recovery view."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create test session
        self.session = SearchSession.objects.create(
            title='Test Search Session',
            owner=self.user,
            status='executing'
        )
        
        # Create test query
        self.query = SearchQuery.objects.create(
            session=self.session,
            population='developers',
            interest='testing',
            context='agile',
            query_string='developers testing agile',
            search_engines=['google'],
            is_active=True
        )
        
        # Create failed execution
        self.execution = SearchExecution.objects.create(
            query=self.query,
            initiated_by=self.user,
            status='failed',
            error_message='Rate limit exceeded',
            retry_count=0
        )
    
    def test_error_recovery_view_get(self):
        """Test GET request to error recovery view."""
        url = reverse('serp_execution:error_recovery', kwargs={'execution_id': self.execution.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Error Recovery')
        self.assertContains(response, 'Rate limit exceeded')
        self.assertContains(response, 'Retry Execution')
    
    def test_error_recovery_view_validates_retry_eligibility(self):
        """Test that view validates retry eligibility."""
        self.execution.retry_count = 3  # Max retries reached
        self.execution.save()
        
        url = reverse('serp_execution:error_recovery', kwargs={'execution_id': self.execution.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 302)
        self.assertIn(str(self.session.id), response.url)
    
    @patch('apps.serp_execution.views.optimize_retry_strategy')
    def test_error_recovery_view_with_retry_strategy(self, mock_optimize):
        """Test error recovery with optimized retry strategy."""
        mock_optimize.return_value = {
            'should_retry': True,
            'delay_seconds': 120,
            'modifications': ['Reduce query complexity', 'Add delay'],
            'success_probability': 0.85
        }
        
        url = reverse('serp_execution:error_recovery', kwargs={'execution_id': self.execution.id})
        response = self.client.get(url)
        
        context = response.context
        self.assertEqual(context['retry_strategy']['delay_seconds'], 120)
        self.assertIn('Reduce query complexity', context['retry_strategy']['modifications'])
    
    @patch('apps.serp_execution.tasks.retry_failed_execution_task')
    def test_error_recovery_view_post_retry(self, mock_task):
        """Test POST request to retry execution."""
        mock_task.delay.return_value = Mock(id='test-task-id')
        
        url = reverse('serp_execution:error_recovery', kwargs={'execution_id': self.execution.id})
        data = {
            'recovery_action': 'retry',
            'retry_delay': 60,
            'notes': 'Retrying after rate limit'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 302)
        self.assertIn(str(self.session.id), response.url)
        mock_task.delay.assert_called_once()
        
        # Check success message
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('Retry scheduled', str(messages[0]))
    
    def test_error_recovery_view_post_skip(self):
        """Test POST request to skip execution."""
        url = reverse('serp_execution:error_recovery', kwargs={'execution_id': self.execution.id})
        data = {
            'recovery_action': 'skip',
            'notes': 'Skipping problematic query'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 302)
        
        # Verify execution marked as cancelled
        self.execution.refresh_from_db()
        self.assertEqual(self.execution.status, 'cancelled')
    
    def test_error_recovery_view_post_manual(self):
        """Test POST request for manual intervention."""
        url = reverse('serp_execution:error_recovery', kwargs={'execution_id': self.execution.id})
        data = {
            'recovery_action': 'manual',
            'notes': 'Need to check API credentials'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 302)
        messages = list(get_messages(response.wsgi_request))
        self.assertIn('manual', str(messages[0]))


class TestAjaxAPIViews(TestCase):
    """Test AJAX API views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create test session
        self.session = SearchSession.objects.create(
            title='Test Search Session',
            owner=self.user,
            status='executing'
        )
        
        # Create test query
        self.query = SearchQuery.objects.create(
            session=self.session,
            population='developers',
            interest='testing',
            context='agile',
            query_string='developers testing agile',
            search_engines=['google'],
            is_active=True
        )
        
        # Create test execution
        self.execution = SearchExecution.objects.create(
            query=self.query,
            initiated_by=self.user,
            status='running',
            results_count=25
        )
    
    def test_execution_status_api(self):
        """Test execution status API endpoint."""
        url = reverse('serp_execution:execution_status_api', kwargs={'execution_id': self.execution.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(data['id'], str(self.execution.id))
        self.assertEqual(data['status'], 'running')
        self.assertEqual(data['results_count'], 25)
        self.assertIn('progress', data)
    
    def test_session_progress_api(self):
        """Test session progress API endpoint."""
        url = reverse('serp_execution:session_progress_api', kwargs={'session_id': self.session.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(data['session_id'], str(self.session.id))
        self.assertEqual(data['session_status'], 'executing')
        self.assertTrue(data['has_running'])
        self.assertIn('statistics', data)
    
    @patch('apps.serp_execution.views.optimize_retry_strategy')
    @patch('apps.serp_execution.tasks.retry_failed_execution_task')
    def test_retry_execution_api(self, mock_task, mock_optimize):
        """Test retry execution API endpoint."""
        # Update execution to failed status
        self.execution.status = 'failed'
        self.execution.error_message = 'Test error'
        self.execution.save()
        
        # Mock retry strategy
        mock_optimize.return_value = {
            'should_retry': True,
            'delay_seconds': 30,
            'modifications': []
        }
        
        mock_task.apply_async.return_value = Mock(id='test-task-id')
        
        url = reverse('serp_execution:retry_execution_api', kwargs={'execution_id': self.execution.id})
        response = self.client.post(url, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['execution_id'], str(self.execution.id))
        self.assertIn('task_id', data)
        self.assertEqual(data['delay_seconds'], 30)
        
        # Verify execution updated
        self.execution.refresh_from_db()
        self.assertEqual(self.execution.status, 'pending')
        self.assertEqual(self.execution.retry_count, 1)
    
    @patch('apps.serp_execution.views.optimize_retry_strategy')
    def test_retry_execution_api_not_recommended(self, mock_optimize):
        """Test retry API when retry is not recommended."""
        self.execution.status = 'failed'
        self.execution.save()
        
        # Mock strategy recommending against retry
        mock_optimize.return_value = {
            'should_retry': False,
            'modifications': ['Manual intervention required']
        }
        
        url = reverse('serp_execution:retry_execution_api', kwargs={'execution_id': self.execution.id})
        response = self.client.post(url, content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        
        self.assertFalse(data['success'])
        self.assertIn('not recommended', data['error'])
        self.assertIn('Manual intervention', data['reason'])
    
    def test_api_authentication_required(self):
        """Test that API endpoints require authentication."""
        self.client.logout()
        
        endpoints = [
            ('serp_execution:execution_status_api', {'execution_id': self.execution.id}),
            ('serp_execution:session_progress_api', {'session_id': self.session.id}),
            ('serp_execution:retry_execution_api', {'execution_id': self.execution.id})
        ]
        
        for url_name, kwargs in endpoints:
            url = reverse(url_name, kwargs=kwargs)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_api_ownership_validation(self):
        """Test that API endpoints validate ownership."""
        # Create another user and their execution
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        other_session = SearchSession.objects.create(
            title='Other Session',
            owner=other_user
        )
        other_query = SearchQuery.objects.create(
            session=other_session,
            population='test',
            interest='test',
            context='test'
        )
        other_execution = SearchExecution.objects.create(
            query=other_query,
            initiated_by=other_user
        )
        
        # Try to access other user's data
        url = reverse('serp_execution:execution_status_api', kwargs={'execution_id': other_execution.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.content)
        self.assertIn('Permission denied', data['error'])
    
    def test_api_error_handling(self):
        """Test API error handling."""
        # Test with non-existent execution
        url = reverse('serp_execution:execution_status_api', kwargs={'execution_id': str(uuid.uuid4())})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn('not found', data['error'])
    
    def test_session_progress_api_calculations(self):
        """Test session progress calculations."""
        # Create multiple executions
        for i in range(3):
            SearchExecution.objects.create(
                query=self.query,
                initiated_by=self.user,
                status='completed' if i < 2 else 'failed',
                results_count=25 * (i + 1),
                api_credits_used=50
            )
        
        url = reverse('serp_execution:session_progress_api', kwargs={'session_id': self.session.id})
        response = self.client.get(url)
        
        data = json.loads(response.content)
        self.assertEqual(data['progress'], 100.0)  # All executions done
        self.assertFalse(data['has_running'])
        self.assertEqual(data['statistics']['total_executions'], 4)  # Including setUp execution
        self.assertEqual(data['statistics']['successful_executions'], 3)
        self.assertEqual(data['statistics']['failed_executions'], 1)