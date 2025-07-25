# Authentication Feature - Product Requirements Document

**Project:** Thesis Grey  
**Feature:** Authentication System  
**Version:** 1.0  
**Date:** 2025-01-03  
**Status:** Implementation Ready

## 1. Executive Summary

The Authentication feature provides the foundational user management system for Thesis Grey, enabling researchers to securely create accounts, log in, and manage their profiles. This system ensures that each user's review sessions and data remain private and secure while providing a seamless user experience.

### Schema Alignment Note

This PRD has been updated to align with the Prisma schema definition. The User model follows a minimal approach with:
- UUID primary keys (`id`)
- Required unique `username`
- Optional unique `email`
- Timestamps using `createdAt`/`updatedAt` naming convention
- Additional profile fields (institution, research area) deferred to future phases

This ensures compatibility between Django ORM and Prisma implementations.

## 2. Feature Overview

### 2.1 Purpose
The authentication system allows researchers to:
- Register for new accounts
- Securely log in to access their review sessions
- Manage their profile information
- Reset forgotten passwords
- Maintain secure sessions across the application

### 2.2 Integration Points
- **Review Manager Dashboard:** Requires authenticated users to display personalized sessions
- **All other features:** Depend on authentication for user identification and data isolation
- **Django Admin:** Leverages the same authentication system for administrative access

## 3. Technical Requirements

### 3.1 Technology Stack
- **Framework:** Django 4.2 built-in authentication system (`django.contrib.auth`)
- **Database:** PostgreSQL (user data storage)
- **Security:** Django's password hashing (PBKDF2 by default)
- **Sessions:** Django session framework with database backend

### 3.2 Database Schema

#### User Model
Based on the Prisma schema, extend Django's `AbstractUser` to match the simplified structure:

```python
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # Override the id field to use UUID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Username and email are already in AbstractUser, but we need to ensure email is unique
    email = models.EmailField(unique=True, null=True, blank=True)
    
    # AbstractUser already includes:
    # - username (we'll keep this as required and unique)
    # - password (hashed)
    # - first_name (optional)
    # - last_name (optional)
    # - is_active
    # - is_staff
    # - is_superuser
    # - date_joined (maps to createdAt)
    # - last_login
    
    # Override the default timestamps to match Prisma schema
    created_at = models.DateTimeField(auto_now_add=True, db_column='createdAt')
    updated_at = models.DateTimeField(auto_now=True, db_column='updatedAt')
    
    # Hide the default date_joined field from forms/serializers
    date_joined = None
    
    class Meta:
        db_table = 'User'  # Match Prisma's table naming
        db_table_comment = 'User accounts for Thesis Grey researchers'
```

**Note:** The Prisma schema shows a minimal User model. Additional fields like `institution` and `research_area` can be added in a separate UserProfile model if needed in the future, maintaining schema compatibility.

#### Migration Considerations
Since the Prisma schema uses:
- UUID for primary keys
- `createdAt`/`updatedAt` naming convention
- Simplified user fields

The Django implementation will need custom migrations to ensure database compatibility if switching between Prisma and Django ORMs.

### 3.3 App Structure

```
apps/accounts/
├── __init__.py
├── admin.py         # User admin configuration
├── apps.py          # App configuration
├── forms.py         # Custom forms (SignUpForm, ProfileForm)
├── migrations/      # Database migrations
├── models.py        # Custom User model
├── templates/       
│   └── accounts/
│       ├── login.html
│       ├── signup.html
│       ├── profile.html
│       ├── password_reset.html
│       ├── password_reset_done.html
│       ├── password_reset_confirm.html
│       └── password_reset_complete.html
├── tests.py         # Unit tests
├── urls.py          # URL routing
├── views.py         # View functions/classes
└── README.md        # App documentation
```

## 4. Functional Requirements

### 4.1 User Registration

**Endpoint:** `/accounts/signup/`

**Requirements:**
- Custom registration form with fields:
  - Username (required, unique)
  - Email (optional, unique if provided)
  - Password (required, min 8 characters)
  - Password confirmation (required, must match)
  - First name (optional)
  - Last name (optional)
- Form validation:
  - Username uniqueness check
  - Email format validation (if provided)
  - Email uniqueness check (if provided)
  - Password strength requirements
  - Password confirmation matching
- Success flow:
  - Create user account with UUID primary key
  - Automatically log in user
  - Redirect to Review Manager Dashboard
- Error handling:
  - Display field-specific validation errors
  - Preserve form data on error (except passwords)

### 4.2 User Login

**Endpoint:** `/accounts/login/`

**Requirements:**
- Login form with fields:
  - Username or email
  - Password
  - "Remember me" checkbox (optional)
- Authentication flow:
  - Support login via username OR email
  - Create secure session on success
  - Redirect to `next` parameter or dashboard
- Security features:
  - CSRF protection
  - Rate limiting (future enhancement)
  - Session timeout configuration
- Error handling:
  - Generic "Invalid credentials" message
  - Account lockout after X failed attempts (future)

### 4.3 User Logout

**Endpoint:** `/accounts/logout/`

**Requirements:**
- Clear user session
- Redirect to login page
- Display success message
- POST request only (CSRF protected)

### 4.4 User Profile

**Endpoint:** `/accounts/profile/`

**Requirements:**
- Display current user information
- Editable fields:
  - First name
  - Last name
  - Email
- Non-editable fields (display only):
  - Username
  - Date joined (created_at)
  - Last login
- Update functionality:
  - Validate email uniqueness (if changed)
  - Success message on save
  - Preserve data on validation error

### 4.5 Password Reset

**Endpoints:**
- `/accounts/password-reset/` - Request reset
- `/accounts/password-reset/done/` - Confirmation page
- `/accounts/reset/<uidb64>/<token>/` - Reset form
- `/accounts/password-reset/complete/` - Success page

**Requirements:**
- Email-based password reset flow
- Token generation and validation
- Email template with reset link
- New password form with confirmation
- Success message and redirect to login

## 5. UI/UX Requirements

### 5.1 Design Principles
- Clean, professional interface suitable for researchers
- Consistent with overall Thesis Grey branding
- Mobile-responsive design
- Accessibility compliant (WCAG 2.1 AA)

### 5.2 Page Layouts

#### Login Page
- Centered form container
- Logo/branding at top
- Form fields with labels
- "Forgot password?" link
- "Don't have an account? Sign up" link
- Submit button

#### Registration Page
- Similar layout to login
- Progress indicator (optional)
- Clear field requirements
- Terms of service checkbox (if applicable)
- "Already have an account? Log in" link

#### Profile Page
- Navigation header with logout option
- Form sections:
  - Account Information (read-only)
  - Personal Information (editable)
- Save and Cancel buttons
- Success/error messages area

### 5.3 Error Handling
- Field-level error messages
- Form-level error summary
- Clear, actionable error text
- Preserve user input on errors

## 6. Security Requirements

### 6.1 Password Security
- Minimum 8 characters
- Django's default password validators:
  - UserAttributeSimilarityValidator
  - MinimumLengthValidator
  - CommonPasswordValidator
  - NumericPasswordValidator
- Secure password hashing (PBKDF2)

### 6.2 Session Security
- Secure session cookies (HTTPS in production)
- Session expiry configuration
- CSRF token protection on all forms
- XSS prevention via template escaping

### 6.3 Access Control
- Login required for all authenticated views
- User isolation (users see only their data)
- Superuser access to Django admin

## 7. Implementation Details

### 7.1 Views Implementation

```python
# views.py structure
class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = 'accounts/signup.html'
    success_url = reverse_lazy('review_manager:dashboard')

class ProfileView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = ProfileForm
    template_name = 'accounts/profile.html'
    
    def get_object(self):
        return self.request.user
```

### 7.2 Forms Implementation

```python
# forms.py structure
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User

class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=False, help_text='Optional. Enter a valid email address.')
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 
                 'first_name', 'last_name')
    
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
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email
```

**Note:** Institution and research area fields have been removed to match the Prisma schema. These can be added to a separate UserProfile model in a future phase if needed.

### 7.3 URL Configuration

```python
# urls.py
app_name = 'accounts'
urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('signup/', SignUpView.as_view(), name='signup'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html'), name='password_reset'),
    # ... other password reset URLs
]
```

## 8. Testing Requirements

### 8.1 Unit Tests
- User model creation and validation
- Form validation (signup, profile)
- View access control
- Password reset token generation

### 8.2 Integration Tests
- Complete registration flow
- Login/logout functionality
- Profile update process
- Password reset email flow

### 8.3 Security Tests
- CSRF protection verification
- Session security
- Password validation rules
- SQL injection prevention

## 9. Deployment Considerations

### 9.1 Environment Variables
```python
# Required in production
EMAIL_HOST = 'smtp.example.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'noreply@thesisgrey.com'
EMAIL_HOST_PASSWORD = '<secure-password>'
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = 'Thesis Grey <noreply@thesisgrey.com>'
```

### 9.2 Production Settings
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`
- `SECURE_SSL_REDIRECT = True`
- Email backend configuration

## 10. Success Metrics

- User registration completion rate > 80%
- Login success rate > 95%
- Password reset completion rate > 70%
- Zero security vulnerabilities in auth system
- Page load time < 2 seconds for all auth pages

## 11. Future Enhancements (Phase 2)

- Social authentication (Google, ORCID)
- Two-factor authentication (2FA)
- Advanced password policies
- Account activity logging
- Email verification on registration
- Remember device functionality
- API authentication tokens

## 12. Dependencies

- Django 4.2.x
- PostgreSQL with psycopg 3
- Django's built-in auth system
- Email service for password reset
- Frontend: Django templates, CSS framework (TailwindCSS candidate)

## 13. Acceptance Criteria

The authentication feature is considered complete when:

1. ✅ Users can successfully register with all required fields
2. ✅ Users can log in with username or email
3. ✅ Users can update their profile information
4. ✅ Users can reset forgotten passwords via email
5. ✅ All forms have proper validation and error handling
6. ✅ Security requirements are met (CSRF, secure passwords)
7. ✅ All pages are mobile-responsive
8. ✅ Unit and integration tests pass with >90% coverage
9. ✅ Documentation is complete (code comments, README)
10. ✅ Feature integrates seamlessly with Review Manager Dashboard 