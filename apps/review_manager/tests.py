from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import SearchSession, SessionActivity
from .forms import SessionCreateForm, SessionEditForm

User = get_user_model()


class SearchSessionModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def test_create_session(self):
        """Test creating a new search session."""
        session = SearchSession.objects.create(
            title='Test Literature Review',
            description='Testing the review process',
            owner=self.user
        )
        self.assertEqual(session.status, 'draft')
        self.assertEqual(session.owner, self.user)
        self.assertEqual(str(session), 'Test Literature Review (Draft)')
        
    def test_status_transitions(self):
        """Test allowed status transitions."""
        session = SearchSession.objects.create(
            title='Test Session',
            owner=self.user
        )
        
        # Test valid transition
        self.assertTrue(session.can_transition_to('defining_search'))
        session.status = 'defining_search'
        session.save()
        
        # Test invalid transition
        self.assertFalse(session.can_transition_to('completed'))
        
    def test_progress_percentage(self):
        """Test progress percentage calculation."""
        session = SearchSession.objects.create(
            title='Test Session',
            owner=self.user,
            total_results=100,
            reviewed_results=25
        )
        self.assertEqual(session.progress_percentage, 25.0)
        
    def test_inclusion_rate(self):
        """Test inclusion rate calculation."""
        session = SearchSession.objects.create(
            title='Test Session',
            owner=self.user,
            reviewed_results=50,
            included_results=10
        )
        self.assertEqual(session.inclusion_rate, 20.0)


class SessionActivityModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.session = SearchSession.objects.create(
            title='Test Session',
            owner=self.user
        )
        
    def test_log_activity(self):
        """Test activity logging."""
        activity = SessionActivity.log_activity(
            session=self.session,
            activity_type='created',
            description='Session created for testing',
            user=self.user,
            metadata={'test': 'data'}
        )
        
        self.assertEqual(activity.session, self.session)
        self.assertEqual(activity.activity_type, 'created')
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.metadata['test'], 'data')


class FormsTests(TestCase):
    def test_session_create_form_valid(self):
        """Test valid session creation form."""
        form = SessionCreateForm(data={
            'title': 'Test Literature Review',
            'description': 'A test description'
        })
        self.assertTrue(form.is_valid())
        
    def test_session_create_form_required_title(self):
        """Test that title is required."""
        form = SessionCreateForm(data={
            'description': 'A test description'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        
    def test_session_edit_form(self):
        """Test session edit form."""
        form = SessionEditForm(data={
            'title': 'Updated Title',
            'description': 'Updated description'
        })
        self.assertTrue(form.is_valid())


class ViewsTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.session = SearchSession.objects.create(
            title='Test Session',
            description='Test description',
            owner=self.user
        )
        
    def test_dashboard_view_requires_login(self):
        """Test that dashboard requires authentication."""
        response = self.client.get(reverse('review_manager:dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
    def test_dashboard_view_authenticated(self):
        """Test dashboard view for authenticated user."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('review_manager:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your Literature Reviews')
        
    def test_create_session_view(self):
        """Test session creation view."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('review_manager:create_session'))
        self.assertEqual(response.status_code, 200)
        
        # Test POST
        response = self.client.post(reverse('review_manager:create_session'), {
            'title': 'New Test Session',
            'description': 'New test description'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            SearchSession.objects.filter(title='New Test Session').exists()
        )
        
    def test_session_detail_view(self):
        """Test session detail view."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('review_manager:session_detail', 
                    kwargs={'session_id': self.session.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.session.title)
        
    def test_session_update_view(self):
        """Test session update view."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('review_manager:edit_session', 
                    kwargs={'session_id': self.session.id})
        )
        self.assertEqual(response.status_code, 200)
        
        # Test POST
        response = self.client.post(
            reverse('review_manager:edit_session', 
                    kwargs={'session_id': self.session.id}),
            {
                'title': 'Updated Title',
                'description': 'Updated description'
            }
        )
        self.assertEqual(response.status_code, 302)
        self.session.refresh_from_db()
        self.assertEqual(self.session.title, 'Updated Title')
        
    def test_user_owner_mixin(self):
        """Test that users can only access their own sessions."""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='otherpass123'
        )
        self.client.login(username='otheruser', password='otherpass123')
        
        response = self.client.get(
            reverse('review_manager:session_detail', 
                    kwargs={'session_id': self.session.id})
        )
        self.assertEqual(response.status_code, 302)  # Redirect
        
    def test_duplicate_session_view(self):
        """Test session duplication."""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('review_manager:duplicate_session', 
                    kwargs={'session_id': self.session.id})
        )
        self.assertEqual(response.status_code, 302)
        
        # Check that duplicate was created
        duplicates = SearchSession.objects.filter(
            title__contains='(Copy)'
        )
        self.assertEqual(duplicates.count(), 1)
        
    def test_delete_session_only_draft(self):
        """Test that only draft sessions can be deleted."""
        self.client.login(username='testuser', password='testpass123')
        
        # Should work for draft
        response = self.client.get(
            reverse('review_manager:delete_session', 
                    kwargs={'session_id': self.session.id})
        )
        self.assertEqual(response.status_code, 200)
        
        # Change status and test again
        self.session.status = 'executing'
        self.session.save()
        
        response = self.client.get(
            reverse('review_manager:delete_session', 
                    kwargs={'session_id': self.session.id})
        )
        self.assertEqual(response.status_code, 302)  # Redirect (permission denied)