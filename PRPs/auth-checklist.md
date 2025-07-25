# Authentication System Implementation Checklist

**Based on:** `/docs/auth/PRD-auth.md`  
**Created:** 2025-01-25  
**Status:** In Progress

## Task List

```yaml
Task 1: Complete User Model Implementation
STATUS [ ]
MODIFY apps/accounts/models.py:
  - FIND pattern: "class User(AbstractUser):"
  - INJECT after field "id = models.UUIDField":
    - email override with unique=True, null=True, blank=True
    - created_at with auto_now_add=True, db_column='createdAt'
    - updated_at with auto_now=True, db_column='updatedAt'
  - ADD Meta class with db_table='User'
  - PRESERVE AbstractUser functionality

STATUS [ ]
CREATE apps/accounts/tests/test_models.py:
  - TEST User creation with UUID generation
  - TEST email uniqueness constraint
  - TEST timestamp auto-population
  - TEST username required validation
  - VERIFY db_table naming matches 'User'

Task 2: Register User Model in Admin
STATUS [ ]
MODIFY apps/accounts/admin.py:
  - IMPORT UserAdmin from django.contrib.auth.admin
  - IMPORT User from .models
  - CREATE CustomUserAdmin extending UserAdmin
  - ADD list_display with id, username, email, is_active
  - ADD search_fields for username and email
  - ADD ordering by created_at descending
  - REGISTER User with CustomUserAdmin

STATUS [ ]
CREATE apps/accounts/tests/test_admin.py:
  - TEST admin registration exists
  - TEST list_display fields
  - TEST search functionality
  - VERIFY admin access permissions

Task 3: Create Authentication Forms
STATUS [ ]
CREATE apps/accounts/forms.py:
  - IMPORT UserCreationForm, UserChangeForm from django.contrib.auth.forms
  - CREATE SignUpForm extending UserCreationForm:
    - ADD email field (optional with validation)
    - ADD first_name, last_name fields
    - IMPLEMENT clean_email for uniqueness check
    - CONFIGURE Meta with User model and fields
  - CREATE ProfileForm extending UserChangeForm:
    - REMOVE password field
    - KEEP only email, first_name, last_name
    - IMPLEMENT clean_email excluding current user

STATUS [ ]
CREATE apps/accounts/tests/test_forms.py:
  - TEST SignUpForm validation (all fields)
  - TEST email uniqueness validation
  - TEST password matching validation
  - TEST ProfileForm update validation
  - TEST email change uniqueness check
  - VERIFY form field rendering

Task 4: Implement Authentication Views
STATUS [ ]
CREATE apps/accounts/views.py:
  - IMPORT CreateView, UpdateView, LoginRequiredMixin
  - IMPORT reverse_lazy, authenticate, login
  - CREATE SignUpView(CreateView):
    - SET form_class = SignUpForm
    - SET template_name = 'accounts/signup.html'
    - IMPLEMENT form_valid to auto-login after signup
    - SET success_url to 'accounts:profile'
  - CREATE ProfileView(LoginRequiredMixin, UpdateView):
    - SET model = User
    - SET form_class = ProfileForm
    - SET template_name = 'accounts/profile.html'
    - OVERRIDE get_object to return request.user
    - ADD success message on update

STATUS [ ]
CREATE apps/accounts/tests/test_views.py:
  - TEST signup view GET request
  - TEST signup view POST with valid data
  - TEST auto-login after signup
  - TEST profile view requires login
  - TEST profile update functionality
  - VERIFY CSRF protection

Task 5: Configure URL Patterns
STATUS [ ]
CREATE apps/accounts/urls.py:
  - IMPORT path, include from django.urls
  - IMPORT auth_views from django.contrib.auth
  - IMPORT SignUpView, ProfileView from .views
  - SET app_name = 'accounts'
  - ADD urlpatterns:
    - path('login/', LoginView) with template
    - path('logout/', LogoutView) with next_page
    - path('signup/', SignUpView)
    - path('profile/', ProfileView)
    - ADD password reset paths with templates

STATUS [ ]
MODIFY grey_lit_project/urls.py:
  - FIND pattern: "urlpatterns = ["
  - INJECT after "path(\"admin/\","
  - ADD path('accounts/', include('apps.accounts.urls'))
  - PRESERVE existing patterns

Task 6: Create Template Structure
STATUS [ ]
CREATE apps/accounts/templates/accounts/ directory structure:
  - EXECUTE mkdir -p apps/accounts/templates/accounts
  - VERIFY directory creation

STATUS [ ]
CREATE apps/accounts/templates/accounts/base_auth.html:
  - EXTEND templates/base.html
  - ADD authentication-specific CSS block
  - CREATE centered container for forms
  - ADD card layout structure
  - PRESERVE Bootstrap 5 styling

Task 7: Implement Login Template
STATUS [ ]
CREATE apps/accounts/templates/accounts/login.html:
  - EXTEND accounts/base_auth.html
  - ADD form with csrf_token
  - CREATE username/email field with Bootstrap classes
  - CREATE password field with form-control
  - ADD "Forgot password?" link
  - ADD "Sign up" link for new users
  - INCLUDE non-field error display

STATUS [ ]
CREATE apps/accounts/tests/test_login_template.py:
  - TEST template rendering
  - TEST form fields present
  - TEST CSRF token included
  - TEST links to signup and password reset

Task 8: Implement Signup Template
STATUS [ ]
CREATE apps/accounts/templates/accounts/signup.html:
  - EXTEND accounts/base_auth.html
  - ADD form with all fields
  - CREATE field loop with Bootstrap styling
  - ADD help text display
  - ADD error message display per field
  - ADD "Already have account?" link
  - INCLUDE password strength indicator placeholder

STATUS [ ]
CREATE apps/accounts/tests/test_signup_template.py:
  - TEST template rendering
  - TEST all form fields present
  - TEST error display functionality
  - VERIFY Bootstrap classes applied

Task 9: Implement Profile Template
STATUS [ ]
CREATE apps/accounts/templates/accounts/profile.html:
  - EXTEND templates/base.html
  - CREATE two-column layout
  - ADD read-only section (username, date joined)
  - ADD editable form section
  - CREATE save/cancel buttons
  - INCLUDE success message display area

STATUS [ ]
CREATE apps/accounts/tests/test_profile_template.py:
  - TEST authenticated access only
  - TEST user data display
  - TEST form rendering
  - VERIFY read-only fields

Task 10: Implement Password Reset Templates
STATUS [ ]
CREATE apps/accounts/templates/accounts/password_reset.html:
  - EXTEND accounts/base_auth.html
  - ADD email input form
  - CREATE clear instructions
  - ADD submit button
  - INCLUDE link back to login

STATUS [ ]
CREATE apps/accounts/templates/accounts/password_reset_done.html:
  - EXTEND accounts/base_auth.html
  - ADD confirmation message
  - CREATE instructions to check email
  - ADD link to login page

STATUS [ ]
CREATE apps/accounts/templates/accounts/password_reset_confirm.html:
  - EXTEND accounts/base_auth.html
  - ADD new password form
  - CREATE password confirmation field
  - ADD password requirements display
  - HANDLE invalid token case

STATUS [ ]
CREATE apps/accounts/templates/accounts/password_reset_complete.html:
  - EXTEND accounts/base_auth.html
  - ADD success message
  - CREATE prominent login link

Task 11: Update Base Template Navigation
STATUS [ ]
MODIFY templates/base.html:
  - FIND pattern: "{% if user.is_authenticated %}"
  - MODIFY Dashboard link to use review_manager URL when available
  - MODIFY profile link to use {% url 'accounts:profile' %}
  - MODIFY logout link to use {% url 'accounts:logout' %}
  - MODIFY login link to use {% url 'accounts:login' %}
  - ADD signup link in else block

Task 12: Configure Authentication Settings
STATUS [ ]
MODIFY grey_lit_project/settings/base.py:
  - FIND pattern: "# Password validation"
  - ADD LOGIN_URL = 'accounts:login'
  - ADD LOGIN_REDIRECT_URL = 'accounts:profile'
  - ADD LOGOUT_REDIRECT_URL = 'accounts:login'
  - VERIFY password validators configured
  - ADD SESSION_COOKIE_AGE for timeout

STATUS [ ]
MODIFY grey_lit_project/settings/local.py:
  - ADD EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
  - ADD DEFAULT_FROM_EMAIL = 'Thesis Grey <noreply@localhost>'

Task 13: Create Custom Authentication Form
STATUS [ ]
MODIFY apps/accounts/forms.py:
  - CREATE CustomAuthenticationForm:
    - EXTEND AuthenticationForm
    - MODIFY username field to accept email
    - OVERRIDE clean to support email login
    - ADD proper error messages

STATUS [ ]
MODIFY apps/accounts/urls.py:
  - FIND LoginView configuration
  - ADD authentication_form=CustomAuthenticationForm

Task 14: Add Form Styling and Widgets
STATUS [ ]
MODIFY apps/accounts/forms.py:
  - FIND each form class
  - ADD widget attributes with Bootstrap classes
  - SET placeholders for all fields
  - ADD help_text where appropriate
  - CONFIGURE autofocus on first fields

Task 15: Create Integration Tests
STATUS [ ]
CREATE apps/accounts/tests/test_integration.py:
  - TEST complete signup → login flow
  - TEST profile update after login
  - TEST logout functionality
  - TEST password reset email flow
  - TEST session expiry behavior
  - VERIFY redirect chains

Task 16: Add Security Tests
STATUS [ ]
CREATE apps/accounts/tests/test_security.py:
  - TEST CSRF token verification
  - TEST SQL injection attempts on forms
  - TEST XSS prevention in templates
  - TEST password hashing verification
  - TEST session security settings
  - VERIFY secure redirects

Task 17: Create Migration for User Model Updates
STATUS [ ]
EXECUTE python manage.py makemigrations accounts:
  - VERIFY migration created for model changes
  - CHECK migration file for correctness

STATUS [ ]
EXECUTE python manage.py migrate accounts:
  - APPLY migration to database
  - VERIFY schema changes applied

Task 18: Create Static Files Structure
STATUS [ ]
CREATE static/css/auth.css:
  - ADD authentication-specific styles
  - CREATE form container styles
  - ADD responsive breakpoints
  - STYLE error messages
  - ADD loading states

STATUS [ ]
CREATE static/js/auth.js:
  - ADD password visibility toggle
  - CREATE form validation helpers
  - ADD loading state handlers
  - IMPLEMENT autofocus behavior

Task 19: Documentation and README
STATUS [ ]
CREATE apps/accounts/README.md:
  - DOCUMENT app purpose and features
  - LIST all URLs and views
  - ADD setup instructions
  - INCLUDE testing commands
  - PROVIDE usage examples

Task 20: Final Integration Testing
STATUS [ ]
EXECUTE python manage.py test apps.accounts:
  - RUN all unit tests
  - VERIFY 90%+ coverage
  - FIX any failing tests

STATUS [ ]
MANUAL testing checklist:
  - TEST signup with all field combinations
  - TEST login with username and email
  - TEST profile update
  - TEST password reset flow
  - VERIFY mobile responsiveness
  - CHECK accessibility compliance
```

## Summary

**Total Tasks:** 20 main tasks with ~120 subtasks  
**Priority:** CRITICAL - Authentication blocks all other features  
**Estimated Time:** 40-60 hours  

## Next Steps

1. Start with Task 1 (Complete User Model)
2. Run tests after each task
3. Commit after each major task completion
4. Update task status as work progresses

## Dependencies

- Django 4.2.x (already installed)
- PostgreSQL (already configured)
- Bootstrap 5 (already in base.html)
- Email backend (console for development)