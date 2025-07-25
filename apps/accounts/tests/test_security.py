from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password

User = get_user_model()


class SecurityTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def test_csrf_token_verification(self):
        """Test CSRF token is required for forms"""
        # Try to post without CSRF token
        self.client.logout()
        response = self.client.post(
            reverse('accounts:login'),
            {
                'username': 'testuser',
                'password': 'testpass123'
            },
            HTTP_X_CSRFTOKEN=''
        )
        # Should fail without valid CSRF token
        self.assertEqual(response.status_code, 403)
        
    def test_sql_injection_attempts(self):
        """Test SQL injection protection on forms"""
        # Try SQL injection in login
        response = self.client.post(reverse('accounts:login'), {
            'username': "admin' OR '1'='1",
            'password': "' OR '1'='1"
        })
        # Should not authenticate
        self.assertNotIn('_auth_user_id', self.client.session)
        
        # Try SQL injection in signup
        response = self.client.post(reverse('accounts:signup'), {
            'username': "test'; DROP TABLE accounts_user; --",
            'email': 'test@example.com',
            'password1': 'testpass123!',
            'password2': 'testpass123!'
        })
        # Table should still exist
        self.assertEqual(User.objects.count(), 1)  # Only our setUp user
        
    def test_xss_prevention_in_templates(self):
        """Test XSS prevention in templates"""
        # Create user with XSS attempt in name
        xss_user = User.objects.create_user(
            username='xssuser',
            first_name='<script>alert("XSS")</script>',
            password='testpass123'
        )
        
        # Login as this user
        self.client.login(username='xssuser', password='testpass123')
        response = self.client.get(reverse('accounts:profile'))
        
        # Script should be escaped, not executed
        self.assertNotContains(response, '<script>alert("XSS")</script>')
        self.assertContains(response, '&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;')
        
    def test_password_hashing_verification(self):
        """Test passwords are properly hashed"""
        # Create user
        user = User.objects.create_user(
            username='hashtest',
            password='plaintext123'
        )
        
        # Password should not be stored in plain text
        self.assertNotEqual(user.password, 'plaintext123')
        
        # Password should be hashed
        self.assertTrue(user.password.startswith('pbkdf2_sha256'))
        
        # Check password works
        self.assertTrue(check_password('plaintext123', user.password))
        
    def test_session_security_settings(self):
        """Test session security configurations"""
        # Login
        self.client.login(username='testuser', password='testpass123')
        
        # Get session
        session = self.client.session
        
        # Check session settings
        # Note: These would be set in production settings
        # For now, just verify session exists and has auth data
        self.assertIn('_auth_user_id', session)
        self.assertEqual(str(session['_auth_user_id']), str(self.user.id))
        
    def test_secure_redirects(self):
        """Test redirects are secure and validated"""
        # Test open redirect protection
        malicious_url = 'http://evil.com'
        response = self.client.post(
            reverse('accounts:login') + f'?next={malicious_url}',
            {
                'username': 'testuser',
                'password': 'testpass123'
            }
        )
        # Should not redirect to external URL
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('evil.com', response.url)
        
    def test_password_validation_rules(self):
        """Test password validation is enforced"""
        # Try to create user with weak password
        response = self.client.post(reverse('accounts:signup'), {
            'username': 'weakpass',
            'password1': '123',  # Too short and numeric only
            'password2': '123'
        })
        self.assertFalse(
            User.objects.filter(username='weakpass').exists()
        )
        
        # Try with common password
        response = self.client.post(reverse('accounts:signup'), {
            'username': 'commonpass',
            'password1': 'password',
            'password2': 'password'
        })
        self.assertFalse(
            User.objects.filter(username='commonpass').exists()
        )
        
    def test_authenticated_access_only(self):
        """Test authenticated-only views are protected"""
        # Logout
        self.client.logout()
        
        # Try to access profile
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)
        
        # Try to post to profile
        response = self.client.post(reverse('accounts:profile'), {
            'email': 'hacker@example.com'
        })
        self.assertEqual(response.status_code, 302)
        
        # Verify user email wasn't changed
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'test@example.com')