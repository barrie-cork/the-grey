from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class SignUpViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('accounts:signup')
        
    def test_signup_view_get(self):
        """Test GET request to signup view"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/signup.html')
        
    def test_signup_view_post_valid(self):
        """Test POST request with valid data"""
        response = self.client.post(self.url, {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'testpass123!',
            'password2': 'testpass123!',
            'first_name': 'John',
            'last_name': 'Doe'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after success
        self.assertTrue(User.objects.filter(username='newuser').exists())
        
    def test_signup_auto_login(self):
        """Test user is automatically logged in after signup"""
        response = self.client.post(self.url, {
            'username': 'newuser',
            'password1': 'testpass123!',
            'password2': 'testpass123!',
        }, follow=True)
        self.assertTrue(response.context['user'].is_authenticated)
        
    def test_signup_redirect_to_profile(self):
        """Test redirect to profile after signup"""
        response = self.client.post(self.url, {
            'username': 'newuser',
            'password1': 'testpass123!',
            'password2': 'testpass123!',
        })
        self.assertRedirects(response, reverse('accounts:profile'))


class ProfileViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.url = reverse('accounts:profile')
        
    def test_profile_view_requires_login(self):
        """Test profile view requires authentication"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
    def test_profile_view_get(self):
        """Test GET request to profile view"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/profile.html')
        
    def test_profile_view_post_valid(self):
        """Test POST request with valid data"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(self.url, {
            'email': 'newemail@example.com',
            'first_name': 'Updated',
            'last_name': 'Name'
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'newemail@example.com')
        
    def test_profile_view_success_message(self):
        """Test success message after profile update"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(self.url, {
            'email': 'newemail@example.com',
            'first_name': 'Updated',
            'last_name': 'Name'
        }, follow=True)
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), 'Profile updated successfully!')


class AuthenticationViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def test_login_view_get(self):
        """Test GET request to login view"""
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/login.html')
        
    def test_login_with_username(self):
        """Test login with username"""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)
        
    def test_login_with_email(self):
        """Test login with email"""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'test@example.com',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)
        
    def test_logout(self):
        """Test logout functionality"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('accounts:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:login'))