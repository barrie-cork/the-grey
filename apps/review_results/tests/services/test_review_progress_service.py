"""
Tests for ReviewProgressService.

Tests review progress tracking and visualization functionality.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.review_manager.models import SearchSession, SessionActivity
from apps.results_manager.models import ProcessedResult
from apps.review_results.models import ReviewTag, ReviewTagAssignment
from apps.review_results.services.review_progress_service import ReviewProgressService


User = get_user_model()


class TestReviewProgressService(TestCase):
    """Test cases for ReviewProgressService."""
    
    def setUp(self):
        """Set up test data."""
        self.service = ReviewProgressService()
        
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
            title='Test Review Progress',
            description='Testing review progress tracking',
            owner=self.user1,
            status='under_review'
        )
        
        # Create test results
        self.results = []
        for i in range(30):
            result = ProcessedResult.objects.create(
                session=self.session,
                title=f'Result {i}',
                url=f'https://example.com/result/{i}',
                snippet=f'Snippet for result {i}',
                relevance_score=0.5 + (i * 0.015)
            )
            self.results.append(result)
        
        # Create tags
        self.tag_include = ReviewTag.objects.create(name='Include')
        self.tag_exclude = ReviewTag.objects.create(name='Exclude')
        self.tag_maybe = ReviewTag.objects.create(name='Maybe')
        
        # Create tag assignments over time (20 reviewed, 10 pending)
        base_time = timezone.now() - timedelta(hours=5)
        for i in range(20):
            tag = self.tag_include if i < 12 else self.tag_exclude
            user = self.user1 if i % 3 != 0 else self.user2
            
            assignment = ReviewTagAssignment.objects.create(
                result=self.results[i],
                tag=tag,
                assigned_by=user,
                created_at=base_time + timedelta(minutes=i*15)
            )
            # Manually set created_at since auto_now_add=True
            assignment.created_at = base_time + timedelta(minutes=i*15)
            assignment.save()
    
    def test_calculate_review_progress(self):
        """Test calculation of review progress."""
        progress = self.service.calculate_review_progress(str(self.session.id))
        
        self.assertIsInstance(progress, dict)
        self.assertIn('total_results', progress)
        self.assertIn('reviewed_count', progress)
        self.assertIn('pending_count', progress)
        self.assertIn('progress_percentage', progress)
        self.assertIn('review_rate', progress)
        self.assertIn('estimated_completion_time', progress)
        
        # Check values
        self.assertEqual(progress['total_results'], 30)
        self.assertEqual(progress['reviewed_count'], 20)
        self.assertEqual(progress['pending_count'], 10)
        self.assertAlmostEqual(progress['progress_percentage'], 66.67, places=1)
    
    def test_get_review_timeline(self):
        """Test generation of review timeline."""
        timeline = self.service.get_review_timeline(str(self.session.id))
        
        self.assertIsInstance(timeline, list)
        self.assertEqual(len(timeline), 20)  # One entry per review
        
        # Check timeline structure
        for entry in timeline:
            self.assertIn('timestamp', entry)
            self.assertIn('action', entry)
            self.assertIn('user', entry)
            self.assertIn('result_title', entry)
            self.assertIn('tag', entry)
            self.assertIn('cumulative_progress', entry)
        
        # Timeline should be chronologically ordered
        timestamps = [entry['timestamp'] for entry in timeline]
        self.assertEqual(timestamps, sorted(timestamps))
        
        # Check cumulative progress
        self.assertAlmostEqual(timeline[-1]['cumulative_progress'], 66.67, places=1)
    
    def test_get_reviewer_statistics(self):
        """Test calculation of reviewer statistics."""
        stats = self.service.get_reviewer_statistics(str(self.session.id))
        
        self.assertIsInstance(stats, list)
        self.assertEqual(len(stats), 2)  # Two reviewers
        
        # Check reviewer stats structure
        for reviewer_stat in stats:
            self.assertIn('username', reviewer_stat)
            self.assertIn('reviews_completed', reviewer_stat)
            self.assertIn('review_percentage', reviewer_stat)
            self.assertIn('tag_distribution', reviewer_stat)
            self.assertIn('average_review_time', reviewer_stat)
            self.assertIn('last_review_date', reviewer_stat)
        
        # Check tag distribution
        reviewer1_stats = next(s for s in stats if s['username'] == 'reviewer1')
        tag_dist = reviewer1_stats['tag_distribution']
        self.assertIn('Include', tag_dist)
        self.assertIn('Exclude', tag_dist)
    
    def test_generate_progress_visualization_data(self):
        """Test generation of progress visualization data."""
        viz_data = self.service.generate_progress_visualization_data(str(self.session.id))
        
        self.assertIsInstance(viz_data, dict)
        self.assertIn('progress_chart', viz_data)
        self.assertIn('tag_distribution_chart', viz_data)
        self.assertIn('reviewer_contribution_chart', viz_data)
        self.assertIn('time_series_chart', viz_data)
        
        # Check progress chart data
        progress_chart = viz_data['progress_chart']
        self.assertIn('labels', progress_chart)
        self.assertIn('values', progress_chart)
        self.assertEqual(len(progress_chart['labels']), 2)  # Reviewed, Pending
        
        # Check tag distribution
        tag_chart = viz_data['tag_distribution_chart']
        self.assertIn('Include', tag_chart['labels'])
        self.assertIn('Exclude', tag_chart['labels'])
    
    def test_calculate_review_velocity(self):
        """Test calculation of review velocity."""
        velocity = self.service.calculate_review_velocity(str(self.session.id))
        
        self.assertIsInstance(velocity, dict)
        self.assertIn('current_velocity', velocity)
        self.assertIn('average_velocity', velocity)
        self.assertIn('velocity_trend', velocity)
        self.assertIn('peak_velocity', velocity)
        self.assertIn('velocity_by_hour', velocity)
        
        # Check velocity values
        self.assertGreaterEqual(velocity['current_velocity'], 0)
        self.assertGreaterEqual(velocity['average_velocity'], 0)
        self.assertIn(velocity['velocity_trend'], ['increasing', 'stable', 'decreasing'])
    
    def test_predict_completion_time(self):
        """Test prediction of review completion time."""
        prediction = self.service.predict_completion_time(str(self.session.id))
        
        self.assertIsInstance(prediction, dict)
        self.assertIn('estimated_completion_date', prediction)
        self.assertIn('confidence_level', prediction)
        self.assertIn('hours_remaining', prediction)
        self.assertIn('reviews_per_day_needed', prediction)
        self.assertIn('based_on_velocity', prediction)
        
        # Check that prediction makes sense
        self.assertGreater(prediction['hours_remaining'], 0)
        self.assertIn(prediction['confidence_level'], ['high', 'medium', 'low'])
    
    def test_get_progress_milestones(self):
        """Test identification of progress milestones."""
        milestones = self.service.get_progress_milestones(str(self.session.id))
        
        self.assertIsInstance(milestones, list)
        
        # Should have milestones for 25%, 50%, etc.
        milestone_percentages = [m['percentage'] for m in milestones]
        self.assertIn(25, milestone_percentages)
        self.assertIn(50, milestone_percentages)
        
        # Check milestone structure
        for milestone in milestones:
            self.assertIn('percentage', milestone)
            self.assertIn('achieved', milestone)
            self.assertIn('achieved_date', milestone)
            self.assertIn('reviews_needed', milestone)
    
    def test_analyze_review_patterns(self):
        """Test analysis of review patterns."""
        patterns = self.service.analyze_review_patterns(str(self.session.id))
        
        self.assertIsInstance(patterns, dict)
        self.assertIn('peak_review_times', patterns)
        self.assertIn('average_session_duration', patterns)
        self.assertIn('review_clustering', patterns)
        self.assertIn('tag_patterns', patterns)
        self.assertIn('reviewer_agreement', patterns)
        
        # Check tag patterns
        tag_patterns = patterns['tag_patterns']
        self.assertIn('inclusion_rate', tag_patterns)
        self.assertIn('exclusion_rate', tag_patterns)
        self.assertIn('uncertainty_rate', tag_patterns)
    
    def test_generate_progress_report(self):
        """Test generation of comprehensive progress report."""
        report = self.service.generate_progress_report(str(self.session.id))
        
        self.assertIsInstance(report, dict)
        self.assertIn('summary', report)
        self.assertIn('detailed_progress', report)
        self.assertIn('reviewer_performance', report)
        self.assertIn('quality_indicators', report)
        self.assertIn('recommendations', report)
        
        # Check summary
        summary = report['summary']
        self.assertIn('current_status', summary)
        self.assertIn('key_metrics', summary)
        self.assertIn('projected_completion', summary)
        
        # Check recommendations
        recommendations = report['recommendations']
        self.assertIsInstance(recommendations, list)
        self.assertTrue(len(recommendations) > 0)
    
    def test_track_review_quality_over_time(self):
        """Test tracking of review quality metrics over time."""
        quality_tracking = self.service.track_review_quality_over_time(str(self.session.id))
        
        self.assertIsInstance(quality_tracking, dict)
        self.assertIn('consistency_trend', quality_tracking)
        self.assertIn('thoroughness_trend', quality_tracking)
        self.assertIn('speed_vs_quality', quality_tracking)
        self.assertIn('reviewer_fatigue_indicators', quality_tracking)
    
    def test_progress_with_no_reviews(self):
        """Test progress calculation with no reviews."""
        empty_session = SearchSession.objects.create(
            title='Empty Review Session',
            description='No reviews yet',
            owner=self.user1,
            status='ready_for_review'
        )
        
        # Add results but no reviews
        for i in range(10):
            ProcessedResult.objects.create(
                session=empty_session,
                title=f'Unreviewed Result {i}',
                url=f'https://example.com/unreviewed/{i}',
                snippet='Unreviewed snippet',
                relevance_score=0.5
            )
        
        progress = self.service.calculate_review_progress(str(empty_session.id))
        
        self.assertEqual(progress['progress_percentage'], 0.0)
        self.assertEqual(progress['reviewed_count'], 0)
        self.assertEqual(progress['pending_count'], 10)
        self.assertIsNone(progress['estimated_completion_time'])
    
    def test_review_session_boundaries(self):
        """Test identification of review session boundaries."""
        # Add reviews with gaps to simulate sessions
        base_time = timezone.now()
        
        # Morning session
        for i in range(5):
            ReviewTagAssignment.objects.create(
                result=self.results[20+i],
                tag=self.tag_include,
                assigned_by=self.user1,
                created_at=base_time - timedelta(hours=8, minutes=i*5)
            )
        
        # Afternoon session  
        for i in range(5):
            ReviewTagAssignment.objects.create(
                result=self.results[25+i],
                tag=self.tag_exclude,
                assigned_by=self.user1,
                created_at=base_time - timedelta(hours=2, minutes=i*5)
            )
        
        patterns = self.service.analyze_review_patterns(str(self.session.id))
        
        # Should detect multiple review sessions
        self.assertGreater(len(patterns['review_clustering']), 1)
    
    def test_progress_alerts(self):
        """Test generation of progress-based alerts."""
        alerts = self.service.generate_progress_alerts(str(self.session.id))
        
        self.assertIsInstance(alerts, list)
        
        for alert in alerts:
            self.assertIn('type', alert)
            self.assertIn('severity', alert)
            self.assertIn('message', alert)
            self.assertIn('recommendation', alert)
            self.assertIn(['info', 'warning', 'critical'], alert['severity'])
    
    def test_logging_in_progress_tracking(self):
        """Test that progress tracking operations are properly logged."""
        with self.assertLogs('apps.review_results.services.review_progress_service', level='INFO') as cm:
            self.service.calculate_review_progress(str(self.session.id))
        
        self.assertTrue(any('Calculating review progress' in msg for msg in cm.output))
        self.assertTrue(any('Progress calculation completed' in msg for msg in cm.output))