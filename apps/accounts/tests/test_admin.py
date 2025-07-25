from django.test import TestCase, Client
from django.contrib.admin.sites import site
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class AdminTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def test_user_registered_in_admin(self):
        """Test User model is registered in admin"""
        self.assertIn(User, site._registry)
        
    def test_admin_list_display(self):
        """Test admin list display fields"""
        self.client.login(username='admin', password='adminpass123')
        url = reverse('admin:accounts_user_changelist')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check for custom fields in response
        self.assertContains(response, 'Username')
        self.assertContains(response, 'Email')
        
    def test_admin_search_fields(self):
        """Test admin search functionality"""
        self.client.login(username='admin', password='adminpass123')
        url = reverse('admin:accounts_user_changelist')
        response = self.client.get(url, {'q': 'testuser'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')
        
    def test_admin_readonly_fields(self):
        """Test readonly fields in admin"""
        self.client.login(username='admin', password='adminpass123')
        url = reverse('admin:accounts_user_change', args=[self.user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check that id, created_at, updated_at are present but readonly
        self.assertContains(response, str(self.user.id))
        
    def test_admin_fieldsets(self):
        """Test custom fieldsets are displayed"""
        self.client.login(username='admin', password='adminpass123')
        url = reverse('admin:accounts_user_change', args=[self.user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Check for timestamps fieldset
        self.assertContains(response, 'Timestamps')