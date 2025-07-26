"""
Tests for review_results models.

Tests for ReviewTag and ReviewTagAssignment models including
tagging functionality and review management.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.review_manager.models import SearchSession
from apps.results_manager.models import ProcessedResult
from ..models import ReviewTag, ReviewTagAssignment

User = get_user_model()


class ReviewTagModelTests(TestCase):
    """Test cases for ReviewTag model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
    
    def test_tag_creation(self):
        """Test creating a review tag."""
        tag = ReviewTag.objects.create(
            name='Include',
            slug='include',
            description='Studies to include in final review',
            tag_type='relevance'
        )
        
        self.assertEqual(tag.name, 'Include')
        self.assertEqual(tag.slug, 'include')
        self.assertEqual(tag.tag_type, 'relevance')


class ReviewTagAssignmentModelTests(TestCase):
    """Test cases for ReviewTagAssignment model."""
    
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
        self.result = ProcessedResult.objects.create(
            session=self.session,
            title='Test Result',
            url='https://example.com/test'
        )
        self.tag = ReviewTag.objects.create(
            name='Include',
            slug='include',
            tag_type='relevance'
        )
    
    def test_tag_assignment_creation(self):
        """Test creating a tag assignment."""
        assignment = ReviewTagAssignment.objects.create(
            result=self.result,
            tag=self.tag,
            assigned_by=self.user,
            notes='This study is relevant'
        )
        
        self.assertEqual(assignment.result, self.result)
        self.assertEqual(assignment.tag, self.tag)
        self.assertEqual(assignment.assigned_by, self.user)
        self.assertEqual(assignment.notes, 'This study is relevant')