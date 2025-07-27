# Authentication: App-Specific Product Requirements Document

**Project Title:** Thesis Grey - Authentication App  
**Version:** 2.0  
**Date:** 2025-01-25  
**App Path:** `apps/accounts/`  
**Master PRD:** [docs/PRD.md](../PRD.md)  
**Dependencies:** None (Foundation app)  
**Status:** Implemented

## 1. Executive Summary

The Authentication app provides the foundational user management system for Thesis Grey, enabling researchers to securely create accounts, authenticate, and manage their profiles. As the foundation of the application's security model, this app ensures proper user identification, session management, and data isolation while providing a seamless authentication experience.

### Key Responsibilities

- **User Registration**: Account creation with email validation
- **Authentication**: Secure login via username or email
- **Session Management**: Secure session handling and persistence
- **Profile Management**: User profile viewing and editing
- **Password Security**: Reset flow and strong password enforcement
- **Access Control**: Foundation for all app-level permissions

### Integration Points

- **Used by**: All other apps for user identification
- **Provides**: User model, authentication decorators, session management
- **Critical for**: Data isolation, audit trails, permission checks

## 2. Technical Architecture

### 2.1 Technology Stack

- **Framework**: Django 4.2 with built-in auth system
- **Database**: PostgreSQL with UUID primary keys
- **Security**: PBKDF2 password hashing, CSRF protection
- **Sessions**: Database-backed sessions for scalability
- **Frontend**: Django Templates with Bootstrap 5
- **Testing**: Django TestCase with 95%+ coverage

### 2.2 App Structure

```
apps/accounts/
├── __init__.py
├── admin.py                 # CustomUserAdmin configuration
├── apps.py                  # App configuration
├── forms.py                 # Authentication forms
├── models.py                # Custom User model
├── views.py                 # Auth views (signup, profile)
├── urls.py                  # URL patterns
├── managers.py              # Custom user manager
├── backends.py              # Email authentication backend
├── validators.py            # Custom password validators
├── templates/
│   └── accounts/
│       ├── base_auth.html   # Auth pages base template
│       ├── login.html       # Login page
│       ├── signup.html      # Registration page
│       ├── profile.html     # User profile page
│       ├── password_reset.html
│       ├── password_reset_done.html
│       ├── password_reset_confirm.html
│       ├── password_reset_complete.html
│       └── password_reset_email.html
├── static/
│   └── accounts/
│       ├── css/
│       │   └── auth.css     # Auth-specific styles
│       └── js/
│           └── password.js   # Password visibility toggle
├── tests/
│   ├── test_models.py       # User model tests
│   ├── test_forms.py        # Form validation tests
│   ├── test_views.py        # View tests
│   ├── test_backends.py     # Auth backend tests
│   ├── test_integration.py  # Full flow tests
│   └── test_security.py     # Security tests
└── migrations/
    └── 0001_initial.py      # Custom User model

### 2.3 Database Models

#### User Model

```python
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Custom User model with UUID primary key.
    Extends Django's AbstractUser for compatibility.
    """
    
    # UUID primary key for better distributed system compatibility
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False
    )
    
    # Email as optional but unique if provided
    email = models.EmailField(
        unique=True, 
        null=True, 
        blank=True,
        help_text="Optional email address for account recovery"
    )
    
    # Timestamps for audit trail
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # AbstractUser provides:
    # - username (required, unique)
    # - password (hashed)
    # - first_name, last_name
    # - is_active, is_staff, is_superuser
    # - last_login, date_joined
    
    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.username
    
    @property
    def full_name(self):
        """Get user's full name or username"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def get_sessions_count(self):
        """Get count of user's search sessions"""
        return self.created_sessions.count()
    
    def get_active_sessions_count(self):
        """Get count of active search sessions"""
        return self.created_sessions.exclude(
            status__in=['completed', 'archived', 'failed']
        ).count()
```

### 2.4 Custom Authentication Backend

```python
# apps/accounts/backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class EmailOrUsernameBackend(ModelBackend):
    """
    Custom authentication backend that allows login with email or username.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        
        try:
            # Try to fetch the user by searching the username or email field
            user = User.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username)
            )
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a non-existing user
            User().set_password(password)
        except User.MultipleObjectsReturned:
            # Edge case: multiple users with same email (shouldn't happen)
            return None
        
        return None
```

## 3. API Endpoints

### 3.1 Authentication API (Phase 2)

While Phase 1 uses Django's session-based authentication, the app is structured to support API authentication in Phase 2:

```python
# Future: apps/accounts/api/views.py
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

@api_view(['POST'])
def api_login(request):
    """API endpoint for token-based authentication"""
    # Implementation for Phase 2
    pass

@api_view(['POST'])
def api_register(request):
    """API endpoint for user registration"""
    # Implementation for Phase 2
    pass
```

## 4. User Interface

### 4.1 Views Implementation

```python
# apps/accounts/views.py
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from .forms import SignUpForm, ProfileForm
from .models import User

class SignUpView(CreateView):
    """User registration view"""
    form_class = SignUpForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('accounts:profile')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # Auto-login after successful signup
        login(self.request, self.object, backend='accounts.backends.EmailOrUsernameBackend')
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Account'
        return context


class ProfileView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """User profile management view"""
    model = User
    form_class = ProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')
    success_message = 'Profile updated successfully!'
    
    def get_object(self, queryset=None):
        return self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'My Profile'
        context['sessions_count'] = self.object.get_sessions_count()
        context['active_sessions_count'] = self.object.get_active_sessions_count()
        return context
```

### 4.2 Forms

```python
# apps/accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate
from .models import User

class SignUpForm(UserCreationForm):
    """Enhanced registration form with email"""
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address (optional)'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username',
                'autofocus': True
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email


class ProfileForm(forms.ModelForm):
    """Profile edit form"""
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email


class CustomAuthenticationForm(AuthenticationForm):
    """Custom login form supporting email or username"""
    username = forms.CharField(
        label='Username or Email',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    
    error_messages = {
        'invalid_login': 'Invalid username/email or password.',
        'inactive': 'This account is inactive.',
    }
```

### 4.3 URL Configuration

```python
# apps/accounts/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import CustomAuthenticationForm

app_name = 'accounts'
urlpatterns = [
    # Authentication
    path('login/', auth_views.LoginView.as_view(
        template_name='accounts/login.html',
        authentication_form=CustomAuthenticationForm,
        redirect_authenticated_user=True
    ), name='login'),
    
    path('logout/', auth_views.LogoutView.as_view(
        next_page='accounts:login'
    ), name='logout'),
    
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    
    # Password reset flow
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/password_reset_email.html',
        success_url=reverse_lazy('accounts:password_reset_done')
    ), name='password_reset'),
    
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url=reverse_lazy('accounts:password_reset_complete')
    ), name='password_reset_confirm'),
    
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
]
```

## 5. Business Logic

### 5.1 User Manager

```python
# apps/accounts/managers.py
from django.contrib.auth.base_user import BaseUserManager

class UserManager(BaseUserManager):
    """Custom user manager supporting email-less users"""
    
    def create_user(self, username, email=None, password=None, **extra_fields):
        """Create and save a regular User with the given username and password"""
        if not username:
            raise ValueError('The Username field must be set')
        
        username = self.model.normalize_username(username)
        email = self.normalize_email(email) if email else None
        
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        """Create and save a SuperUser with the given username and password"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(username, email, password, **extra_fields)
```

### 5.2 Password Validators

```python
# apps/accounts/validators.py
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class MinimumLengthValidator:
    """Enhanced minimum length validator with better messages"""
    
    def __init__(self, min_length=8):
        self.min_length = min_length
    
    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                _(f"Password must be at least {self.min_length} characters long."),
                code='password_too_short',
                params={'min_length': self.min_length},
            )
    
    def get_help_text(self):
        return _(f"Your password must contain at least {self.min_length} characters.")
```

## 6. Testing Requirements

### 6.1 Model Tests

```python
# apps/accounts/tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class UserModelTest(TestCase):
    def test_create_user(self):
        """Test creating a user with username only"""
        user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.assertEqual(user.username, 'testuser')
        self.assertTrue(user.check_password('testpass123'))
        self.assertIsInstance(user.id, uuid.UUID)
        self.assertIsNone(user.email)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
    
    def test_create_user_with_email(self):
        """Test creating a user with email"""
        user = User.objects.create_user(
            username='emailuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.assertEqual(user.email, 'test@example.com')
    
    def test_email_uniqueness(self):
        """Test that email must be unique"""
        User.objects.create_user(
            username='user1',
            email='same@example.com',
            password='pass123'
        )
        
        with self.assertRaises(Exception):
            User.objects.create_user(
                username='user2',
                email='same@example.com',
                password='pass123'
            )
    
    def test_full_name_property(self):
        """Test full_name property"""
        user = User.objects.create_user(
            username='testuser',
            first_name='John',
            last_name='Doe',
            password='pass123'
        )
        
        self.assertEqual(user.full_name, 'John Doe')
        
        user.first_name = ''
        self.assertEqual(user.full_name, 'testuser')
```

### 6.2 View Tests

```python
# apps/accounts/tests/test_views.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class AuthViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_signup_view(self):
        """Test user registration"""
        response = self.client.post(reverse('accounts:signup'), {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'newpass123',
            'password2': 'newpass123'
        })
        
        # Should redirect to profile after signup
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('accounts:profile'))
        
        # User should be created and logged in
        self.assertTrue(User.objects.filter(username='newuser').exists())
        self.assertTrue('_auth_user_id' in self.client.session)
    
    def test_login_with_username(self):
        """Test login with username"""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue('_auth_user_id' in self.client.session)
    
    def test_login_with_email(self):
        """Test login with email"""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'test@example.com',
            'password': 'testpass123'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue('_auth_user_id' in self.client.session)
    
    def test_profile_view_requires_login(self):
        """Test profile view requires authentication"""
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 302)
        
        # Login and try again
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('accounts:profile'))
        self.assertEqual(response.status_code, 200)
    
    def test_profile_update(self):
        """Test profile update"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(reverse('accounts:profile'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john@example.com'
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Verify update
        user = User.objects.get(username='testuser')
        self.assertEqual(user.first_name, 'John')
        self.assertEqual(user.last_name, 'Doe')
        self.assertEqual(user.email, 'john@example.com')
```

### 6.3 Security Tests

```python
# apps/accounts/tests/test_security.py
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class SecurityTest(TestCase):
    def setUp(self):
        self.client = Client()
    
    def test_password_validation(self):
        """Test password validation rules"""
        response = self.client.post(reverse('accounts:signup'), {
            'username': 'weakpass',
            'password1': 'short',
            'password2': 'short'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'password2', 
                           'This password is too short. It must contain at least 8 characters.')
    
    def test_csrf_protection(self):
        """Test CSRF protection on forms"""
        # Try to post without CSRF token
        self.client.cookies.clear()
        response = self.client.post(reverse('accounts:login'), {
            'username': 'test',
            'password': 'test'
        }, HTTP_X_CSRFTOKEN='invalid')
        
        self.assertEqual(response.status_code, 403)
    
    def test_session_security(self):
        """Test session security settings"""
        user = User.objects.create_user(
            username='sessiontest',
            password='testpass123'
        )
        
        self.client.login(username='sessiontest', password='testpass123')
        
        # Verify session exists
        self.assertTrue('_auth_user_id' in self.client.session)
        
        # Logout should clear session
        self.client.logout()
        self.assertFalse('_auth_user_id' in self.client.session)
```

## 7. Performance Optimization

### 7.1 Query Optimization

```python
# apps/accounts/models.py additions
class User(AbstractUser):
    # ... existing fields ...
    
    objects = UserManager()
    
    class Meta:
        # ... existing meta ...
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]
```

### 7.2 Caching Strategy

```python
# apps/accounts/utils.py
from django.core.cache import cache
from django.conf import settings

def get_user_session_stats(user_id):
    """Get cached user session statistics"""
    cache_key = f"user_stats_{user_id}"
    stats = cache.get(cache_key)
    
    if stats is None:
        from apps.review_manager.models import SearchSession
        sessions = SearchSession.objects.filter(created_by_id=user_id)
        
        stats = {
            'total_sessions': sessions.count(),
            'active_sessions': sessions.exclude(
                status__in=['completed', 'archived', 'failed']
            ).count(),
            'completed_sessions': sessions.filter(status='completed').count(),
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, stats, 300)
    
    return stats
```

## 8. Security Considerations

### 8.1 Password Security

- Minimum 8 characters enforced
- PBKDF2 hashing with 260,000 iterations
- Common password validation
- User attribute similarity check
- Numeric-only password prevention

### 8.2 Session Security

- Database-backed sessions for scalability
- Session expiry after 2 weeks (configurable)
- Secure cookies in production (HTTPS only)
- CSRF protection on all forms
- Session rotation on login

### 8.3 Access Control

- LoginRequiredMixin for protected views
- User isolation enforced at view level
- Superuser access restricted to admin
- Email authentication backend security

## 9. Phase Implementation

### Phase 1 (Current)

- ✅ Custom User model with UUID
- ✅ Registration with optional email
- ✅ Login via username or email
- ✅ Profile management
- ✅ Password reset via email
- ✅ Django admin integration
- ✅ Comprehensive test coverage

### Phase 2 (Future)

- OAuth2 integration (Google, ORCID)
- Two-factor authentication (2FA)
- API token authentication
- Advanced audit logging
- Email verification on signup
- Account deactivation workflow
- Password strength meter
- Remember device feature

## 10. Development Checklist

### Pre-Implementation
- [x] User model designed with UUID
- [x] Authentication flow planned
- [x] Security requirements defined
- [x] Template structure planned

### Implementation
- [x] Custom User model created
- [x] Forms implemented
- [x] Views created
- [x] Templates designed
- [x] Email backend configured
- [x] Tests written (95%+ coverage)

### Post-Implementation
- [x] Security audit passed
- [x] Performance testing completed
- [x] Documentation updated
- [x] Integration with other apps verified

## 11. Success Metrics

- Registration completion rate > 80%
- Login success rate > 95%
- Password reset completion > 70%
- Zero authentication vulnerabilities
- Page load time < 1 second
- Session creation time < 100ms

## 12. References

- [Master PRD](../PRD.md) - Overall project requirements
- [Django Authentication](https://docs.djangoproject.com/en/4.2/topics/auth/)
- [OWASP Authentication Guidelines](https://owasp.org/www-project-cheat-sheets/cheatsheets/Authentication_Cheat_Sheet)
- [UUID Best Practices](https://www.postgresql.org/docs/current/datatype-uuid.html)