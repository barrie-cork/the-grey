from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.accounts.forms import SignUpForm, ProfileForm, CustomAuthenticationForm

User = get_user_model()


class SignUpFormTest(TestCase):
    def test_signup_form_valid_data(self):
        """Test signup form with valid data"""
        form = SignUpForm(data={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'testpass123!',
            'password2': 'testpass123!',
            'first_name': 'John',
            'last_name': 'Doe'
        })
        self.assertTrue(form.is_valid())
        
    def test_signup_form_no_email(self):
        """Test signup form without email (should be valid)"""
        form = SignUpForm(data={
            'username': 'newuser',
            'password1': 'testpass123!',
            'password2': 'testpass123!',
        })
        self.assertTrue(form.is_valid())
        
    def test_signup_form_duplicate_email(self):
        """Test signup form with duplicate email"""
        User.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='pass123'
        )
        form = SignUpForm(data={
            'username': 'newuser',
            'email': 'existing@example.com',
            'password1': 'testpass123!',
            'password2': 'testpass123!',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        
    def test_signup_form_password_mismatch(self):
        """Test signup form with mismatched passwords"""
        form = SignUpForm(data={
            'username': 'newuser',
            'password1': 'testpass123!',
            'password2': 'different123!',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
        
    def test_signup_form_widgets(self):
        """Test form widgets have correct CSS classes"""
        form = SignUpForm()
        self.assertIn('form-control', form.fields['username'].widget.attrs['class'])
        self.assertIn('form-control', form.fields['email'].widget.attrs['class'])


class ProfileFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def test_profile_form_valid_data(self):
        """Test profile form with valid data"""
        form = ProfileForm(instance=self.user, data={
            'email': 'newemail@example.com',
            'first_name': 'Updated',
            'last_name': 'Name'
        })
        self.assertTrue(form.is_valid())
        
    def test_profile_form_no_password_field(self):
        """Test profile form doesn't have password field"""
        form = ProfileForm(instance=self.user)
        self.assertNotIn('password', form.fields)
        
    def test_profile_form_duplicate_email(self):
        """Test profile form with duplicate email from another user"""
        User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='pass123'
        )
        form = ProfileForm(instance=self.user, data={
            'email': 'other@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        
    def test_profile_form_same_email(self):
        """Test profile form with user's own email (should be valid)"""
        form = ProfileForm(instance=self.user, data={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User'
        })
        self.assertTrue(form.is_valid())


class CustomAuthenticationFormTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def test_login_with_username(self):
        """Test login with username"""
        form = CustomAuthenticationForm(data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertTrue(form.is_valid())
        
    def test_login_with_email(self):
        """Test login with email"""
        form = CustomAuthenticationForm(data={
            'username': 'test@example.com',
            'password': 'testpass123'
        })
        self.assertTrue(form.is_valid())
        
    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        form = CustomAuthenticationForm(data={
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)