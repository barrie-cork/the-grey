# Review Manager App - Comprehensive Developer Guide

**Version:** 1.0.0  
**Status:** Production Ready ✅  
**Coverage:** 381+ Tests (95.8% Coverage)  
**Security:** Enterprise-grade with comprehensive audit trail  
**Last Updated:** 2025-05-31

## 📋 Overview

This document consolidates all critical information for developers working with the Review Manager app, including migration details, security patterns, testing approaches, and architectural decisions established during Sprint 9-11 completion.

## 🏗️ Architecture & Core Models

### Model Hierarchy
```
SearchSession (Core Entity - UUID Primary Key)
├── SessionActivity (Audit Trail - Field Migrated ✅)
├── SessionStatusHistory (Status Tracking)
├── SessionArchive (Archive Management)
└── UserSessionStats (Analytics & Metrics)
```

### SessionActivity Field Migration (COMPLETED ✅)

**Critical Migration Details:**
| Old Field Name | New Field Name | Purpose | Migration Status |
|----------------|----------------|---------|------------------|
| `activity_type` | `action` | Activity classification | ✅ Complete |
| `performed_by` | `user` | User who performed action | ✅ Complete |
| `performed_at` | `timestamp` | When action occurred | ✅ Complete |
| `metadata` | `details` | JSON metadata storage | ✅ Complete |

**Files Updated During Migration:**
- ✅ `models.py` - Core model definition with new field names
- ✅ `admin.py` - Admin interface field references
- ✅ `views_sprint6.py` - Analytics views using activity data
- ✅ `views_sprint7.py` - Real-time monitoring views
- ✅ `signals.py` - Automatic activity logging system
- ✅ `recovery.py` - Error recovery utilities
- ✅ `tests/test_core.py` - Updated test references after directory reorganization

## 🔐 Security Implementation (Sprint 8)

### Critical Security Patterns

**1. Custom User Model (MANDATORY)**
```python
# ALWAYS use this pattern - NEVER import User directly
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

# In models - use settings reference
class MyModel(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
```

**2. Security Decorators**
```python
from apps.review_manager.decorators import owns_session, session_status_required, rate_limit

@login_required
@owns_session  # Validates session ownership
@session_status_required('draft', 'strategy_ready')  # Status validation
@rate_limit('session_edit', requests=10, window=3600)  # Rate limiting
def my_view(request, session_id):
    # request.session_obj is available from @owns_session
    pass
```

**3. Permission Validation**
```python
from apps.review_manager.permissions import SessionPermission

# Check ownership
if not SessionPermission.can_view(request.user, session):
    raise PermissionDenied()

# Check status-based permissions
if not session.can_transition_to('strategy_ready'):
    raise PermissionDenied("Cannot advance session in current status")
```

### Security Test Coverage
- **319 Security Tests** across all attack vectors
- **CSRF Protection** on all forms and AJAX endpoints
- **Rate Limiting** on sensitive operations
- **Input Validation** with comprehensive sanitization
- **Audit Logging** for all security-relevant actions

## 📁 Directory Structure (Post-Cleanup)

### Organized Structure
```
apps/review_manager/
├── models.py                    # Core data models
├── views.py                     # Main CRUD operations
├── views_sprint6.py            # Analytics & advanced features
├── views_sprint7.py            # Real-time monitoring
├── views_sprint8.py            # Security-enhanced views
├── forms.py                    # Form definitions
├── urls.py                     # URL routing
├── decorators.py               # Security decorators
├── permissions.py              # Permission classes
├── middleware.py               # Custom middleware
├── signals.py                  # Activity logging signals
├── docs/                       # Documentation files
│   ├── api.md                 # API documentation
│   ├── architecture.md        # Technical architecture
│   ├── deployment.md          # Deployment guide
│   └── user-guide.md          # User documentation
├── tests/                      # Organized test suite
│   ├── __init__.py
│   ├── test_core.py           # Core functionality tests
│   ├── test_security.py       # Security test suite
│   ├── test_performance.py    # Performance benchmarks
│   ├── test_accessibility.py  # Accessibility validation
│   ├── test_coverage.py       # Coverage improvement tests
│   └── test_sprints.py        # Sprint-specific tests
├── management/commands/        # Management commands
│   ├── create_sample_sessions.py
│   ├── run_security_tests.py
│   ├── security_audit.py
│   └── test_sprint8.py
└── static/review_manager/      # Static assets
    ├── css/
    ├── js/
    └── images/
```

## 🧪 Testing Approach

### Test Organization
- **Core Tests**: Basic functionality, CRUD operations, permissions
- **Security Tests**: Comprehensive security validation (319 tests)
- **Performance Tests**: Load testing and optimization validation
- **Accessibility Tests**: WCAG 2.1 AA compliance
- **Sprint Tests**: Feature-specific test suites

### Running Tests
```bash
# All tests
python manage.py test apps.review_manager

# Specific test categories
python manage.py test apps.review_manager.tests.test_core
python manage.py test apps.review_manager.tests.test_security
python manage.py test apps.review_manager.tests.test_performance

# Management command tests
python manage.py run_security_tests
python manage.py security_audit

# Quick verification
python quick_test.py  # Runs 5 basic tests for rapid validation
```

### Test Data Generation
```bash
# Create sample sessions for testing
python manage.py create_sample_sessions --count 10 --username testuser

# Clean test data
python manage.py create_sample_sessions --clean
```

## 🔄 Status Workflow

### 9-State Workflow
1. **draft** → Session created, can edit/delete
2. **strategy_ready** → Search strategy defined
3. **executing** → Background search in progress
4. **processing** → Results being processed
5. **ready_for_review** → Results ready for manual review
6. **in_review** → Active review in progress
7. **completed** → Review finished, can archive
8. **failed** → Error state, can reset
9. **archived** → Long-term storage

### Transition Validation
```python
# Check valid transitions
session.can_transition_to('strategy_ready')  # Returns True/False

# Status manager for complex logic
from apps.review_manager.models import SessionStatusManager
manager = SessionStatusManager()
manager.can_transition('draft', 'completed')  # Returns False
```

## 📊 Activity Logging System

### Automatic Logging (Signal-Based)
```python
# Automatic logging for all model changes
session.title = "Updated Title"
session.save()  # Automatically creates SessionActivity record

# Add context for better logging
from apps.review_manager.signals import SignalUtils

SignalUtils.set_change_context(
    session,
    user=request.user,
    reason='Manual update via dashboard'
)
session.status = 'completed'
session.save()
```

### Manual Activity Logging
```python
from apps.review_manager.models import SessionActivity

SessionActivity.log_activity(
    session=session,
    action=SessionActivity.ActivityType.COMMENT,
    description='Strategy review completed',
    user=user,
    details={'review_duration': 30, 'outcome': 'approved'}
)
```

## 🛠️ Development Patterns

### Model Development
```python
import uuid
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

class MyModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'review_manager_mymodel'
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
```

### View Development
```python
from django.contrib.auth.decorators import login_required
from apps.review_manager.decorators import owns_session, session_status_required

@login_required
@owns_session
@session_status_required('draft', 'strategy_ready')
def edit_session(request, session_id):
    session = request.session_obj  # Available from @owns_session
    
    if request.method == 'POST':
        # Process form
        pass
    
    return render(request, 'template.html', {'session': session})
```

### Test Development
```python
from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()

class MyTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
```

## ⚠️ Common Issues & Solutions

### Custom User Model Errors
**Error:** "Manager isn't available; 'auth.User' has been swapped"
**Solution:** Always use `get_user_model()` instead of importing User directly

### Import Errors After Directory Reorganization
**Error:** Import errors in test files
**Solution:** Update relative imports from `.models` to `..models` when moving tests to subdirectories

### Permission Errors
**Error:** 403 Forbidden on session access
**Solution:** Verify session ownership and user authentication:
```python
# Check ownership
if session.created_by != request.user:
    raise PermissionDenied()

# Check session exists
session = get_object_or_404(SearchSession, id=session_id, created_by=request.user)
```

### Activity Timeline Access
**Error:** 403 on activity timeline
**Solution:** Ensure proper authentication and ownership validation in view's `test_func()`

## 🚀 Performance Considerations

### Database Optimization
```python
# Optimize queries with select_related and prefetch_related
sessions = SearchSession.objects.filter(created_by=user)\
    .select_related('created_by')\
    .prefetch_related('activities')

# Use pagination for large datasets
from django.core.paginator import Paginator
paginator = Paginator(sessions, 25)
```

### Caching Strategy
```python
from django.core.cache import cache

# Cache user statistics
cache_key = f"user_stats_{user.id}"
stats = cache.get(cache_key)
if not stats:
    stats = UserSessionStats.calculate_stats(user)
    cache.set(cache_key, stats, 300)  # 5 minutes
```

## 🔮 Integration Points

### Future App Integration
- **Search Strategy App**: Transitions from `draft` to `strategy_ready`
- **SERP Execution App**: Background tasks for `executing` status
- **Results Manager App**: Data processing for `processing` status
- **Review Results App**: Manual review for `in_review` status
- **Reporting App**: Export capabilities for `completed` sessions

### API Compatibility
All endpoints designed for future REST API implementation with consistent JSON response format.

## 📚 Development Commands

### Essential Commands
```bash
# Development setup
python manage.py migrate
python manage.py createsuperuser
python manage.py create_sample_sessions --count 10

# Testing
python manage.py test apps.review_manager
python manage.py run_security_tests
python quick_test.py

# Production checks
python manage.py security_audit
python manage.py collectstatic
```

## 🎯 Production Readiness

### Deployment Checklist
- ✅ **381+ Tests** with 95.8% coverage
- ✅ **Security Implementation** with comprehensive audit
- ✅ **Performance Optimization** with database indexes
- ✅ **Documentation** complete and up-to-date
- ✅ **Error Handling** with graceful degradation
- ✅ **Logging & Monitoring** for production troubleshooting

### Version Information
- **Git Tag:** v1.0.0-review-manager
- **Branch:** Merged to main
- **Status:** Production Ready
- **Next Phase:** Search Strategy Builder implementation

---

**Important:** This app serves as the reference implementation for all architectural patterns, security practices, and development standards in the thesis project. New apps should follow these established patterns.