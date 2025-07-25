# PRP: Authentication System Implementation

**Status:** Ready for Execution  
**Priority:** CRITICAL  
**Estimated Time:** 40-60 hours  
**Created:** 2025-01-25  

## Goal

Implement a complete authentication system for the Agent Grey (Thesis Grey) Django application, enabling secure user registration, login, profile management, and password reset functionality.

## Why

Authentication is the foundational feature blocking all other functionality. Without it:
- Users cannot create accounts or access the system
- Session management is impossible
- All user-specific features (search sessions, results review) cannot function
- Security and data isolation cannot be enforced

## Context

### Current State
- **User Model**: Partially implemented with UUID primary key
- **Views/Forms/Templates**: None exist
- **URLs**: Not configured
- **Admin**: Not configured for User model
- **Tests**: No tests written

### Technical Stack
- Django 4.2.11 with PostgreSQL
- Custom User model extending AbstractUser
- Bootstrap 5 for UI (already in base.html)
- Session-based authentication
- Email backend for password reset

### Key Requirements
- UUID primary keys matching Prisma schema
- Support login via username OR email
- Auto-login after registration
- PRISMA schema compatibility (createdAt/updatedAt)
- 90%+ test coverage
- Mobile-responsive design

## Implementation

### Phase 1: Core Model & Admin (Tasks 1-2)

#### Task 1: Complete User Model
```python
# apps/accounts/models.py
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_column='createdAt')
    updated_at = models.DateTimeField(auto_now=True, db_column='updatedAt')
    
    # Hide default date_joined to avoid confusion
    date_joined = None
    
    class Meta:
        db_table = 'User'
        db_table_comment = 'User accounts for Thesis Grey researchers'
```

#### Task 2: Admin Configuration
```python
# apps/accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('id', 'username', 'email', 'is_active', 'created_at')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'created_at')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    ordering = ('-created_at',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    readonly_fields = ('id', 'created_at', 'updated_at')
```

### Phase 2: Forms Implementation (Task 3)

```python
# apps/accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.contrib.auth import authenticate
from django.db.models import Q
from .models import User


class SignUpForm(UserCreationForm):
    email = forms.EmailField(
        required=False,
        help_text='Optional. Enter a valid email address.',
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email (optional)'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'first_name', 'last_name')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username',
                'autofocus': True
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name (optional)'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name (optional)'
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
            'placeholder': 'Confirm Password'
        })
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email


class ProfileForm(UserChangeForm):
    password = None  # Remove password field from profile form
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last Name'
            }),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email


class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label='Username or Email',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if username and password:
            # Try to authenticate with username first
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password
            )
            
            # If that fails, try with email
            if self.user_cache is None:
                try:
                    user = User.objects.get(email=username)
                    self.user_cache = authenticate(
                        self.request,
                        username=user.username,
                        password=password
                    )
                except User.DoesNotExist:
                    pass
            
            if self.user_cache is None:
                raise forms.ValidationError(
                    'Invalid login credentials. Please try again.',
                    code='invalid_login',
                    params={'username': self.username_field.verbose_name},
                )
            else:
                self.confirm_login_allowed(self.user_cache)
        
        return self.cleaned_data
```

### Phase 3: Views Implementation (Task 4)

```python
# apps/accounts/views.py
from django.contrib.auth import login
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from .forms import SignUpForm, ProfileForm
from .models import User


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('accounts:profile')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # Auto-login after successful signup
        login(self.request, self.object)
        return response


class ProfileView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = ProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('accounts:profile')
    success_message = 'Profile updated successfully!'
    
    def get_object(self, queryset=None):
        return self.request.user
```

### Phase 4: URL Configuration (Task 5)

```python
# apps/accounts/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from .views import SignUpView, ProfileView
from .forms import CustomAuthenticationForm

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', auth_views.LoginView.as_view(
        template_name='accounts/login.html',
        authentication_form=CustomAuthenticationForm
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(
        next_page='accounts:login'
    ), name='logout'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('profile/', ProfileView.as_view(), name='profile'),
    
    # Password Reset
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

### Phase 5: Templates (Tasks 6-10)

#### Base Authentication Template
```html
<!-- apps/accounts/templates/accounts/base_auth.html -->
{% extends 'base.html' %}

{% block content %}
<div class="container">
    <div class="row justify-content-center">
        <div class="col-md-6 col-lg-5">
            <div class="card shadow mt-5">
                <div class="card-body p-5">
                    {% block auth_content %}{% endblock %}
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_css %}
<style>
    .auth-container {
        min-height: 80vh;
        display: flex;
        align-items: center;
    }
</style>
{% endblock %}
```

### Phase 6: Settings Configuration (Task 12)

```python
# grey_lit_project/settings/base.py additions
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'accounts:profile'
LOGOUT_REDIRECT_URL = 'accounts:login'

# Session configuration
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# grey_lit_project/settings/local.py additions
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'Thesis Grey <noreply@localhost>'
```

### Testing Strategy

#### Unit Tests Structure
```
apps/accounts/tests/
├── __init__.py
├── test_models.py
├── test_forms.py
├── test_views.py
├── test_admin.py
├── test_integration.py
└── test_security.py
```

#### Sample Test
```python
# apps/accounts/tests/test_models.py
from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class UserModelTest(TestCase):
    def test_create_user_with_uuid(self):
        user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.assertIsNotNone(user.id)
        self.assertEqual(len(str(user.id)), 36)  # UUID length
    
    def test_email_unique_constraint(self):
        User.objects.create_user(
            username='user1',
            email='test@example.com',
            password='pass123'
        )
        with self.assertRaises(Exception):
            User.objects.create_user(
                username='user2',
                email='test@example.com',
                password='pass123'
            )
    
    def test_timestamps_auto_populated(self):
        user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)
```

## Validation

### Automated Validation Loop
```bash
#!/bin/bash
# validate_auth.sh

echo "=== Authentication System Validation ==="

# 1. Run migrations
echo "1. Running migrations..."
python manage.py makemigrations accounts
python manage.py migrate

# 2. Run tests
echo "2. Running tests..."
python manage.py test apps.accounts -v 2

# 3. Check coverage
echo "3. Checking test coverage..."
coverage run --source='apps.accounts' manage.py test apps.accounts
coverage report

# 4. Lint checks
echo "4. Running linters..."
flake8 apps/accounts/ --max-line-length=120
mypy apps/accounts/

# 5. Security checks
echo "5. Running security checks..."
python manage.py check --deploy

# 6. Template validation
echo "6. Validating templates..."
python manage.py validate_templates

echo "=== Validation Complete ==="
```

### Manual Testing Checklist
1. **Registration Flow**
   - [ ] Register with username only
   - [ ] Register with username and email
   - [ ] Verify auto-login after registration
   - [ ] Check duplicate username/email validation

2. **Login Flow**
   - [ ] Login with username
   - [ ] Login with email
   - [ ] Verify invalid credentials handling
   - [ ] Check "Remember me" functionality

3. **Profile Management**
   - [ ] Update email
   - [ ] Update name fields
   - [ ] Verify email uniqueness on update
   - [ ] Check success messages

4. **Password Reset**
   - [ ] Request reset with valid email
   - [ ] Check email received in console
   - [ ] Complete reset with new password
   - [ ] Login with new password

5. **Security**
   - [ ] CSRF tokens present in forms
   - [ ] Session timeout working
   - [ ] Unauthorized access redirects

### Success Criteria
- [ ] All 20 tasks completed
- [ ] 90%+ test coverage achieved
- [ ] All manual tests passing
- [ ] No security warnings
- [ ] Mobile responsive design verified
- [ ] Documentation complete

## Common Gotchas

1. **Migration Issues**
   - Always create User model BEFORE first migration
   - Use `--fake-initial` if needed for UUID migration

2. **Email Configuration**
   - Console backend only works in DEBUG mode
   - Production needs real SMTP configuration

3. **Template Inheritance**
   - Ensure `base.html` exists before testing
   - Check static files are configured

4. **Form Widgets**
   - Bootstrap classes must match version (5.x)
   - Autofocus only on first field

5. **URL Namespacing**
   - Always use `accounts:` prefix in templates
   - Update base.html navigation URLs

## File Creation Order

1. Models → Admin → Migrations
2. Forms → Views → URLs
3. Template directories → Base template → Individual templates
4. Tests directory → Test files
5. Static files → Documentation

## Execution Commands

```bash
# Start implementation
cd /mnt/d/Python/Projects/django/HTA-projects/agent-grey

# Create test directory structure
mkdir -p apps/accounts/tests
touch apps/accounts/tests/__init__.py

# Create template directory structure  
mkdir -p apps/accounts/templates/accounts

# Run migrations after model changes
python manage.py makemigrations accounts
python manage.py migrate

# Run tests continuously during development
python manage.py test apps.accounts --keepdb

# Final validation
./validate_auth.sh
```

## Dependencies Verification

```python
# Verify in Django shell
python manage.py shell
>>> from django.conf import settings
>>> assert settings.AUTH_USER_MODEL == 'accounts.User'
>>> assert 'apps.accounts' in settings.INSTALLED_APPS
>>> assert 'django.contrib.auth' in settings.INSTALLED_APPS
>>> assert 'django.contrib.messages' in settings.INSTALLED_APPS
```

## Next Steps After Completion

1. Create basic dashboard view in review_manager
2. Update all foreign keys to use AUTH_USER_MODEL
3. Add user filtering to all querysets
4. Implement API authentication (if needed)
5. Add social authentication (Phase 2)