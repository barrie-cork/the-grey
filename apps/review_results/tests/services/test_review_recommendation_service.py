"""
Tests for ReviewRecommendationService.

Tests ML-based review recommendations and priority suggestions.
"""

from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.review_manager.models import SearchSession
from apps.results_manager.models import ProcessedResult
from apps.review_results.models import ReviewTag, ReviewTagAssignment
from apps.review_results.services.review_recommendation_service import ReviewRecommendationService


User = get_user_model()


class TestReviewRecommendationService(TestCase):
    """Test cases for ReviewRecommendationService."""
    
    def setUp(self):
        """Set up test data."""
        self.service = ReviewRecommendationService()
        
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
        
        # Create test sessions
        self.session = SearchSession.objects.create(
            title='Current Review Session',
            description='Testing recommendations',
            owner=self.user1,
            status='under_review'
        )
        
        # Create historical session for training data
        self.historical_session = SearchSession.objects.create(
            title='Historical Review Session',
            description='Completed review for training',
            owner=self.user1,
            status='completed',
            created_at=timezone.now() - timezone.timedelta(days=30)
        )
        
        # Create tags
        self.tag_include = ReviewTag.objects.create(name='Include')
        self.tag_exclude = ReviewTag.objects.create(name='Exclude')
        self.tag_maybe = ReviewTag.objects.create(name='Maybe')
        
        # Create historical results with patterns
        self._create_historical_data()
        
        # Create current results for recommendation
        self._create_current_results()
    
    def _create_historical_data(self):
        """Create historical review data with patterns."""
        # Pattern: High relevance + journal articles -> Include
        # Pattern: Low relevance + blog posts -> Exclude
        
        for i in range(50):
            relevance = 0.3 + (i * 0.014)  # 0.3 to 1.0
            doc_type = 'journal_article' if i % 3 == 0 else 'blog_post'
            
            result = ProcessedResult.objects.create(
                session=self.historical_session,
                title=f'Historical Result {i}: AI in Healthcare',
                url=f'https://example.com/historical/{i}',
                snippet=f'Study examining AI applications in healthcare settings',
                document_type=doc_type,
                publication_year=2020 + (i % 4),
                is_pdf=relevance > 0.7
            )
            
            # Create review pattern
            if relevance > 0.7 and doc_type == 'journal_article':
                tag = self.tag_include
            elif relevance < 0.5:
                tag = self.tag_exclude
            else:
                tag = self.tag_maybe
            
            ReviewTagAssignment.objects.create(
                result=result,
                tag=tag,
                assigned_by=self.user1
            )
    
    def _create_current_results(self):
        """Create current results needing recommendations."""
        self.current_results = []
        
        # Mix of reviewed and unreviewed results
        for i in range(20):
            relevance = 0.4 + (i * 0.03)
            doc_type = 'journal_article' if i % 2 == 0 else 'report'
            
            result = ProcessedResult.objects.create(
                session=self.session,
                title=f'Current Result {i}: Machine Learning Study',
                url=f'https://journal.com/current/{i}',
                snippet=f'Research on machine learning applications',
                document_type=doc_type,
                publication_year=2023 + (i % 2),
                is_pdf=i % 3 == 0
            )
            self.current_results.append(result)
            
            # Review first 10
            if i < 10:
                tag = self.tag_include if relevance > 0.65 else self.tag_exclude
                ReviewTagAssignment.objects.create(
                    result=result,
                    tag=tag,
                    assigned_by=self.user1
                )
    
    def test_generate_recommendations(self):
        """Test generation of review recommendations."""
        recommendations = self.service.generate_recommendations(
            str(self.session.id),
            user_id=self.user1.id
        )
        
        self.assertIsInstance(recommendations, list)
        self.assertEqual(len(recommendations), 10)  # Only unreviewed results
        
        # Check recommendation structure
        for rec in recommendations:
            self.assertIn('result_id', rec)
            self.assertIn('recommended_tag', rec)
            self.assertIn('confidence_score', rec)
            self.assertIn('reasoning', rec)
            self.assertIn('priority_score', rec)
            
            # Confidence should be between 0 and 1
            self.assertGreaterEqual(rec['confidence_score'], 0)
            self.assertLessEqual(rec['confidence_score'], 1)
            
            # Should recommend valid tags
            self.assertIn(rec['recommended_tag'], ['Include', 'Exclude', 'Maybe'])
    
    def test_calculate_recommendation_confidence(self):
        """Test confidence calculation for recommendations."""
        result = self.current_results[15]  # Unreviewed, high relevance
        
        confidence = self.service.calculate_recommendation_confidence(
            result,
            predicted_tag='Include'
        )
        
        self.assertIsInstance(confidence, float)
        self.assertGreaterEqual(confidence, 0)
        self.assertLessEqual(confidence, 1)
        
        # High relevance journal article should have high confidence for Include
        self.assertGreater(confidence, 0.7)
    
    def test_prioritize_review_queue(self):
        """Test prioritization of review queue."""
        unreviewed_results = ProcessedResult.objects.filter(
            session=self.session,
            reviewtagassignment__isnull=True
        )
        
        prioritized = self.service.prioritize_review_queue(
            list(unreviewed_results),
            str(self.session.id)
        )
        
        self.assertIsInstance(prioritized, list)
        self.assertEqual(len(prioritized), 10)
        
        # Check prioritization structure
        for item in prioritized:
            self.assertIn('result', item)
            self.assertIn('priority_score', item)
            self.assertIn('priority_factors', item)
            
            factors = item['priority_factors']
            self.assertIn('relevance_weight', factors)
            self.assertIn('uncertainty_weight', factors)
            self.assertIn('quality_weight', factors)
        
        # Should be ordered by priority score (descending)
        scores = [item['priority_score'] for item in prioritized]
        self.assertEqual(scores, sorted(scores, reverse=True))
    
    def test_analyze_reviewer_patterns(self):
        """Test analysis of individual reviewer patterns."""
        patterns = self.service.analyze_reviewer_patterns(
            self.user1.id,
            str(self.historical_session.id)
        )
        
        self.assertIsInstance(patterns, dict)
        self.assertIn('inclusion_threshold', patterns)
        self.assertIn('preferred_document_types', patterns)
        self.assertIn('decision_factors', patterns)
        self.assertIn('consistency_score', patterns)
        
        # Check decision factors
        factors = patterns['decision_factors']
        self.assertIn('relevance_importance', factors)
        self.assertIn('document_type_importance', factors)
        self.assertIn('has_full_text_importance', factors)
    
    def test_predict_review_decision(self):
        """Test prediction of review decision."""
        result = self.current_results[15]  # Unreviewed
        
        prediction = self.service.predict_review_decision(
            result,
            self.user1.id
        )
        
        self.assertIsInstance(prediction, dict)
        self.assertIn('predicted_tag', prediction)
        self.assertIn('probabilities', prediction)
        self.assertIn('features_used', prediction)
        
        # Check probabilities
        probs = prediction['probabilities']
        self.assertIn('Include', probs)
        self.assertIn('Exclude', probs)
        self.assertIn('Maybe', probs)
        
        # Probabilities should sum to 1
        total_prob = sum(probs.values())
        self.assertAlmostEqual(total_prob, 1.0, places=2)
    
    def test_generate_batch_recommendations(self):
        """Test batch recommendation generation."""
        result_ids = [str(r.id) for r in self.current_results[10:15]]
        
        batch_recs = self.service.generate_batch_recommendations(
            result_ids,
            self.user1.id
        )
        
        self.assertIsInstance(batch_recs, dict)
        self.assertEqual(len(batch_recs), 5)
        
        for result_id, rec in batch_recs.items():
            self.assertIn(result_id, result_ids)
            self.assertIn('recommended_tag', rec)
            self.assertIn('confidence', rec)
            self.assertIn('alternative_tags', rec)
    
    def test_explain_recommendation(self):
        """Test explanation generation for recommendations."""
        result = self.current_results[12]
        
        explanation = self.service.explain_recommendation(
            result,
            'Include',
            self.user1.id
        )
        
        self.assertIsInstance(explanation, dict)
        self.assertIn('main_factors', explanation)
        self.assertIn('supporting_evidence', explanation)
        self.assertIn('similar_reviewed_results', explanation)
        self.assertIn('confidence_breakdown', explanation)
        
        # Check main factors
        factors = explanation['main_factors']
        self.assertIsInstance(factors, list)
        self.assertTrue(len(factors) > 0)
        
        for factor in factors:
            self.assertIn('factor_name', factor)
            self.assertIn('impact', factor)
            self.assertIn('value', factor)
    
    def test_detect_review_inconsistencies(self):
        """Test detection of review inconsistencies."""
        # Create inconsistent reviews
        similar_result1 = ProcessedResult.objects.create(
            session=self.session,
            title='Identical Study A',
            url='https://example.com/studyA',
            snippet='Same content about AI',
            is_pdf=True,
            document_type='journal_article'
        )
        
        similar_result2 = ProcessedResult.objects.create(
            session=self.session,
            title='Identical Study A (duplicate)',
            url='https://other.com/studyA',
            snippet='Same content about AI',
            is_pdf=True,
            document_type='journal_article'
        )
        
        # Tag them differently
        ReviewTagAssignment.objects.create(
            result=similar_result1,
            tag=self.tag_include,
            assigned_by=self.user1
        )
        
        ReviewTagAssignment.objects.create(
            result=similar_result2,
            tag=self.tag_exclude,
            assigned_by=self.user1
        )
        
        inconsistencies = self.service.detect_review_inconsistencies(
            str(self.session.id)
        )
        
        self.assertIsInstance(inconsistencies, list)
        self.assertTrue(len(inconsistencies) > 0)
        
        # Check inconsistency structure
        for inconsistency in inconsistencies:
            self.assertIn('result_pair', inconsistency)
            self.assertIn('similarity_score', inconsistency)
            self.assertIn('tag_difference', inconsistency)
            self.assertIn('recommendation', inconsistency)
    
    def test_collaborative_filtering_recommendations(self):
        """Test collaborative filtering based on multiple reviewers."""
        # Add reviews from second user
        for i in range(5, 10):
            result = self.current_results[i]
            tag = self.tag_include if result.is_pdf else self.tag_maybe
            
            ReviewTagAssignment.objects.create(
                result=result,
                tag=tag,
                assigned_by=self.user2
            )
        
        collab_recs = self.service.generate_collaborative_recommendations(
            str(self.session.id),
            self.user1.id
        )
        
        self.assertIsInstance(collab_recs, list)
        
        for rec in collab_recs:
            self.assertIn('result_id', rec)
            self.assertIn('recommended_tag', rec)
            self.assertIn('agreement_score', rec)
            self.assertIn('similar_reviewers', rec)
    
    def test_adaptive_learning(self):
        """Test that recommendations adapt based on feedback."""
        # Get initial recommendation
        result = self.current_results[15]
        initial_rec = self.service.predict_review_decision(result, self.user1.id)
        
        # Provide feedback (actual review different from recommendation)
        actual_tag = self.tag_exclude if initial_rec['predicted_tag'] == 'Include' else self.tag_include
        
        ReviewTagAssignment.objects.create(
            result=result,
            tag=actual_tag,
            assigned_by=self.user1
        )
        
        # Update model with feedback
        self.service.update_recommendation_model(
            str(self.session.id),
            self.user1.id
        )
        
        # Get recommendation for similar result
        similar_result = self.current_results[16]
        new_rec = self.service.predict_review_decision(similar_result, self.user1.id)
        
        # Model should have learned from feedback
        self.assertIsNotNone(new_rec)
    
    def test_recommendation_performance_metrics(self):
        """Test calculation of recommendation performance metrics."""
        metrics = self.service.calculate_recommendation_performance(
            str(self.session.id)
        )
        
        self.assertIsInstance(metrics, dict)
        self.assertIn('accuracy', metrics)
        self.assertIn('precision_by_tag', metrics)
        self.assertIn('recall_by_tag', metrics)
        self.assertIn('user_adoption_rate', metrics)
        self.assertIn('confidence_calibration', metrics)
    
    def test_handle_cold_start(self):
        """Test recommendations with no historical data."""
        new_session = SearchSession.objects.create(
            title='New Session',
            description='No historical data',
            owner=self.user1,
            status='under_review'
        )
        
        new_result = ProcessedResult.objects.create(
            session=new_session,
            title='New Result',
            url='https://example.com/new',
            snippet='New content',
            is_pdf=False
        )
        
        # Should still provide recommendations using global patterns
        recommendations = self.service.generate_recommendations(
            str(new_session.id),
            self.user1.id
        )
        
        self.assertIsInstance(recommendations, list)
        # Should use rule-based approach for cold start
        self.assertTrue(any('rule-based' in r.get('reasoning', '') for r in recommendations))
    
    def test_logging_in_recommendations(self):
        """Test that recommendation operations are properly logged."""
        with self.assertLogs('apps.review_results.services.review_recommendation_service', level='INFO') as cm:
            self.service.generate_recommendations(str(self.session.id), self.user1.id)
        
        self.assertTrue(any('Generating recommendations' in msg for msg in cm.output))
        self.assertTrue(any('Recommendations generated' in msg for msg in cm.output))