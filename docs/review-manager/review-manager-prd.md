# Review Manager App - Implementation PRD

**Version:** 2.0  
**Date:** 2025-05-29  
**App:** `apps/review_manager/`  
**Master PRD:** `docs/PRD.md` (refer for overall project context)  
**Dependencies:** `accounts` (User model)  
**Development Phase:** Post-Accounts App Implementation

---

## 🎯 **Executive Summary**

This app-specific PRD provides detailed implementation specifications for the Review Manager app, which serves as the central hub for researchers conducting grey literature systematic reviews. This document combines technical implementation details with user-centered acceptance criteria and should be used alongside the master PRD (`docs/PRD.md`) for overall project context.

**For overall project vision, architecture decisions, and cross-app standards, refer to the Master PRD: `docs/PRD.md`**

This document focuses specifically on the Review Manager app implementation details that development teams need for focused feature development.

---

## 📋 **Pre-Implementation Checklist**

- [ ] Accounts app fully implemented and tested
- [ ] User authentication working correctly
- [ ] Django 4.2 environment configured on Windows
- [ ] Development database set up
- [ ] Testing framework configured

---

## 1. **Session Status Workflow with User Criteria**

### **Complete Status Definitions:**

```python
STATUS_CHOICES = [
    ('draft', 'Draft'),                    # Just created, no strategy defined
    ('strategy_ready', 'Strategy Ready'),  # PIC terms defined, ready to execute
    ('executing', 'Executing Searches'),   # Background tasks running
    ('processing', 'Processing Results'),  # Raw results being processed
    ('ready_for_review', 'Ready for Review'), # Results available for screening
    ('in_review', 'Under Review'),         # User actively reviewing results
    ('completed', 'Completed'),            # Review finished, ready for export
    ('failed', 'Failed'),                  # Error occurred during execution
    ('archived', 'Archived'),              # User archived completed session
]
```

### **User Acceptance Criteria - Status Management:**

- [ ] **UC-4.1.1**: Status badges clearly visible on dashboard cards
- [ ] **UC-4.1.2**: Status labels use plain English (no technical jargon)
- [ ] **UC-4.1.3**: Visual grouping by status type (active, completed, failed)
- [ ] **UC-4.1.4**: Progress indicators show "X results ready for review" where applicable
- [ ] **UC-4.1.5**: User can identify session stage within 2 seconds
- [ ] **UC-4.2.1**: Failed sessions show clear, non-technical error explanations
- [ ] **UC-4.2.2**: Failed sessions offer actionable recovery options
- [ ] **UC-4.2.3**: Partial results preserved and accessible after failures

### **Status Transition Rules:**
```python
# Implement with state machine pattern for reliability
class SessionStatusManager:
    """Manages status transitions with validation and logging"""
    
    ALLOWED_TRANSITIONS = {
        'draft': ['strategy_ready'],
        'strategy_ready': ['executing', 'draft'],
        'executing': ['processing', 'failed'],
        'processing': ['ready_for_review', 'failed'],
        'ready_for_review': ['in_review'],
        'in_review': ['completed', 'ready_for_review'],
        'completed': ['archived', 'in_review'],
        'failed': ['draft', 'strategy_ready'],
        'archived': ['completed']
    }
    
    def can_transition(self, from_status, to_status):
        return to_status in self.ALLOWED_TRANSITIONS.get(from_status, [])
```

---

## 2. **Session Creation Workflow with User Criteria**

### **Two-Step Creation Process:**

**Step 1: Minimal Session Creation**

### **User Acceptance Criteria - Session Creation:**

- [ ] **UC-2.1.1**: "New Review Session" button prominent on dashboard
- [ ] **UC-2.1.2**: Form shows only title (required) and description (optional)
- [ ] **UC-2.1.3**: Meaningful title can be provided without defining search terms
- [ ] **UC-2.1.4**: Session creation completes in under 30 seconds
- [ ] **UC-2.1.5**: Success message confirms session was created
- [ ] **UC-2.1.6**: Automatic redirect to search strategy setup
- [ ] **UC-2.2.1**: Clear explanation of what needs defining in strategy setup
- [ ] **UC-2.2.2**: Session title visible at top for context
- [ ] **UC-2.2.3**: Can save strategy and choose immediate execution or return to dashboard

### **Enhanced Form Design:**
```python
class SessionCreateForm(forms.ModelForm):
    class Meta:
        model = SearchSession
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'e.g., Diabetes Management Guidelines Review',
                'class': 'form-control',
                'required': True,
                'autofocus': True,
                'maxlength': 200
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Brief description of your systematic review objectives (optional)',
                'class': 'form-control',
                'rows': 3,
                'maxlength': 1000
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['title'].label = "Review Title"
        self.fields['title'].help_text = "Give your review a clear, descriptive title"
        self.fields['description'].label = "Description (Optional)"
        self.fields['description'].help_text = "Add any additional context or objectives"
    
    def save(self, commit=True, user=None):
        session = super().save(commit=False)
        if user:
            session.created_by = user
        session.status = 'draft'
        if commit:
            session.save()
            # Log creation for analytics
            SessionActivity.objects.create(
                session=session,
                action='created',
                user=user
            )
        return session
```

---

## 3. **Dashboard Implementation with User Criteria**

### **User Acceptance Criteria - Dashboard:**

- [ ] **UC-1.1.1**: All review sessions visible in one place
- [ ] **UC-1.1.2**: Cards show title, description, and current status
- [ ] **UC-1.1.3**: Creation and last update dates visible
- [ ] **UC-1.1.4**: Sessions organised by status (active first, then completed)
- [ ] **UC-1.1.5**: Count of total and active sessions displayed
- [ ] **UC-1.1.6**: Workload understood within 5 seconds of loading
- [ ] **UC-1.1.7**: Active vs completed reviews distinguishable at a glance
- [ ] **UC-1.3.1**: Real-time search filtering by title/description
- [ ] **UC-1.3.2**: Status filter dropdown functional
- [ ] **UC-1.3.3**: Search and filters can be combined
- [ ] **UC-1.3.4**: Clear filters option available
- [ ] **UC-1.3.5**: Any session findable within 10 seconds

### **Enhanced Dashboard View:**
```python
class DashboardView(LoginRequiredMixin, ListView):
    model = SearchSession
    template_name = 'review_manager/dashboard.html'
    context_object_name = 'sessions'
    paginate_by = 12  # 4x3 grid on desktop
    
    def get_queryset(self):
        queryset = SearchSession.objects.filter(
            created_by=self.request.user
        ).select_related('created_by').prefetch_related(
            'searchquery_set',
            'searchexecution_set',
            'processedresult_set'
        )
        
        # Apply filters
        status_filter = self.request.GET.get('status')
        search_query = self.request.GET.get('q')
        
        if status_filter and status_filter != 'all':
            if status_filter == 'active':
                queryset = queryset.exclude(
                    status__in=['completed', 'archived', 'failed']
                )
            else:
                queryset = queryset.filter(status=status_filter)
        
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
        
        # Order by status priority then date
        return queryset.extra(
            select={'status_order': """
                CASE status
                    WHEN 'in_review' THEN 1
                    WHEN 'ready_for_review' THEN 2
                    WHEN 'processing' THEN 3
                    WHEN 'executing' THEN 4
                    WHEN 'strategy_ready' THEN 5
                    WHEN 'draft' THEN 6
                    WHEN 'failed' THEN 7
                    WHEN 'completed' THEN 8
                    WHEN 'archived' THEN 9
                END
            """}
        ).order_by('status_order', '-updated_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_sessions = SearchSession.objects.filter(created_by=self.request.user)
        
        context.update({
            'total_sessions': all_sessions.count(),
            'active_sessions': all_sessions.exclude(
                status__in=['completed', 'archived', 'failed']
            ).count(),
            'completed_sessions': all_sessions.filter(status='completed').count(),
            'current_filter': self.request.GET.get('status', 'all'),
            'search_query': self.request.GET.get('q', ''),
        })
        return context
```

### **Dashboard Template Structure:**
```html
<!-- review_manager/templates/review_manager/dashboard.html -->
<div class="dashboard-container">
    <!-- Header Section -->
    <div class="dashboard-header">
        <div class="welcome-section">
            <h1>Your Literature Reviews</h1>
            <div class="quick-stats">
                <span class="stat">
                    <i class="icon-total"></i>
                    <strong>{{ total_sessions }}</strong> Total
                </span>
                <span class="stat">
                    <i class="icon-active"></i>
                    <strong>{{ active_sessions }}</strong> Active
                </span>
                <span class="stat">
                    <i class="icon-completed"></i>
                    <strong>{{ completed_sessions }}</strong> Completed
                </span>
            </div>
        </div>
        <a href="{% url 'review_manager:create_session' %}" 
           class="btn btn-primary btn-lg">
            <i class="icon-plus"></i> New Review Session
        </a>
    </div>
    
    <!-- Filters Section -->
    <div class="filters-section">
        <form method="get" class="filter-form">
            <div class="search-box">
                <input type="text" 
                       name="q" 
                       value="{{ search_query }}"
                       placeholder="Search sessions..."
                       class="form-control">
            </div>
            <div class="status-filter">
                <select name="status" class="form-control" onchange="this.form.submit()">
                    <option value="all">All Sessions</option>
                    <option value="active" {% if current_filter == 'active' %}selected{% endif %}>
                        Active Only
                    </option>
                    <option value="completed" {% if current_filter == 'completed' %}selected{% endif %}>
                        Completed
                    </option>
                    <option value="archived" {% if current_filter == 'archived' %}selected{% endif %}>
                        Archived
                    </option>
                </select>
            </div>
            {% if search_query or current_filter != 'all' %}
            <a href="{% url 'review_manager:dashboard' %}" class="btn btn-link">
                Clear Filters
            </a>
            {% endif %}
        </form>
    </div>
    
    <!-- Session Cards Grid -->
    <div class="sessions-grid">
        {% for session in sessions %}
        <div class="session-card" data-status="{{ session.status }}">
            <!-- Card implementation here -->
        </div>
        {% empty %}
        <div class="empty-state">
            <h3>No sessions found</h3>
            <p>Create your first literature review to get started!</p>
        </div>
        {% endfor %}
    </div>
</div>
```

---

## 4. **Smart Navigation with User Criteria**

### **User Acceptance Criteria - Navigation:**

- [ ] **UC-1.2.1**: Click on session card navigates to appropriate next step
- [ ] **UC-1.2.2**: Navigation based on session status is logical
- [ ] **UC-1.2.3**: Clear indication of why brought to specific page
- [ ] **UC-1.2.4**: Easy navigation back to dashboard
- [ ] **UC-1.2.5**: Never have to think "what do I do next?"
- [ ] **UC-5.2.1**: Prominent buttons for relevant next steps
- [ ] **UC-5.2.2**: All actions accessible through clear menu
- [ ] **UC-5.2.3**: Can reach any workflow part within 2 clicks

### **Enhanced Navigation System:**
```python
class SessionNavigationMixin:
    """Mixin for smart session navigation"""
    
    def get_session_next_url(self, session):
        """Determine where to send user when they click on a session"""
        navigation_map = {
            'draft': {
                'url': reverse('search_strategy:define', kwargs={'session_id': session.id}),
                'text': 'Complete Search Strategy',
                'icon': 'icon-strategy',
                'help': 'Define your Population, Interest, and Context terms'
            },
            'strategy_ready': {
                'url': reverse('serp_execution:execute', kwargs={'session_id': session.id}),
                'text': 'Execute Searches',
                'icon': 'icon-search',
                'help': 'Run searches across selected databases'
            },
            'executing': {
                'url': reverse('serp_execution:status', kwargs={'session_id': session.id}),
                'text': 'View Progress',
                'icon': 'icon-progress',
                'help': 'Monitor search execution progress'
            },
            'processing': {
                'url': reverse('serp_execution:status', kwargs={'session_id': session.id}),
                'text': 'Processing Results',
                'icon': 'icon-processing',
                'help': 'Results are being processed'
            },
            'ready_for_review': {
                'url': reverse('review_results:overview', kwargs={'session_id': session.id}),
                'text': 'Start Review',
                'icon': 'icon-review',
                'help': f'{session.stats["processed_results_count"]} results ready for review'
            },
            'in_review': {
                'url': reverse('review_results:overview', kwargs={'session_id': session.id}),
                'text': 'Continue Review',
                'icon': 'icon-continue',
                'help': f'{session.stats["reviewed_results_count"]} of {session.stats["processed_results_count"]} reviewed'
            },
            'completed': {
                'url': reverse('reporting:summary', kwargs={'session_id': session.id}),
                'text': 'View Report',
                'icon': 'icon-report',
                'help': 'Access final report and export options'
            },
            'failed': {
                'url': reverse('review_manager:session_detail', kwargs={'session_id': session.id}),
                'text': 'View Error Details',
                'icon': 'icon-error',
                'help': 'See what went wrong and recovery options'
            },
            'archived': {
                'url': reverse('reporting:summary', kwargs={'session_id': session.id}),
                'text': 'View Archived Report',
                'icon': 'icon-archive',
                'help': 'Access archived review report'
            },
        }
        
        return navigation_map.get(
            session.status, 
            {
                'url': reverse('review_manager:session_detail', kwargs={'session_id': session.id}),
                'text': 'View Details',
                'icon': 'icon-info',
                'help': 'View session information'
            }
        )
```

---

## 5. **Session Management Features with User Criteria**

### **User Acceptance Criteria - Session Management:**

- [ ] **UC-3.1.1**: Edit button/link visible on session details
- [ ] **UC-3.1.2**: Can modify title and description only
- [ ] **UC-3.1.3**: Cannot accidentally change search strategy
- [ ] **UC-3.1.4**: Confirmation shown when changes saved
- [ ] **UC-3.1.5**: Returns to session details with updated info
- [ ] **UC-3.2.1**: Delete option available for draft sessions
- [ ] **UC-3.2.2**: Confirmation dialog before deletion
- [ ] **UC-3.2.3**: Success message after deletion
- [ ] **UC-3.2.4**: Cannot delete sessions beyond draft status
- [ ] **UC-3.3.1**: Archive option for completed sessions
- [ ] **UC-3.3.2**: Archived sessions hidden from main dashboard
- [ ] **UC-3.3.3**: "View Archived" link provides access
- [ ] **UC-3.3.4**: Can unarchive sessions
- [ ] **UC-3.4.1**: Duplicate option creates copy with "(Copy)" suffix
- [ ] **UC-3.4.2**: Duplicated session starts as draft
- [ ] **UC-3.4.3**: Can immediately edit duplicated session
- [ ] **UC-3.4.4**: Original session unchanged

### **Enhanced CRUD Operations:**

```python
class SessionUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Edit session title and description only"""
    model = SearchSession
    form_class = SessionEditForm
    template_name = 'review_manager/session_edit.html'
    pk_url_kwarg = 'session_id'
    
    def test_func(self):
        session = self.get_object()
        return session.created_by == self.request.user
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'Session "{self.object.title}" has been updated successfully.'
        )
        return response
    
    def get_success_url(self):
        return reverse('review_manager:session_detail', 
                      kwargs={'session_id': self.object.id})


class SessionDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete draft sessions only"""
    model = SearchSession
    template_name = 'review_manager/session_confirm_delete.html'
    pk_url_kwarg = 'session_id'
    
    def test_func(self):
        session = self.get_object()
        return (session.created_by == self.request.user and 
                session.status == 'draft')
    
    def delete(self, request, *args, **kwargs):
        session_title = self.get_object().title
        response = super().delete(request, *args, **kwargs)
        messages.success(
            request, 
            f'Session "{session_title}" has been deleted.'
        )
        return response
    
    def get_success_url(self):
        return reverse('review_manager:dashboard')


class DuplicateSessionView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Create a copy of an existing session"""
    
    def test_func(self):
        session = get_object_or_404(SearchSession, pk=self.kwargs['session_id'])
        return session.created_by == self.request.user
    
    def post(self, request, session_id):
        original = get_object_or_404(SearchSession, pk=session_id)
        
        # Create duplicate
        duplicate = SearchSession.objects.create(
            title=f"{original.title} (Copy)",
            description=original.description,
            population_terms=original.population_terms.copy() if original.population_terms else [],
            interest_terms=original.interest_terms.copy() if original.interest_terms else [],
            context_terms=original.context_terms.copy() if original.context_terms else [],
            created_by=request.user,
            status='draft'
        )
        
        messages.success(
            request,
            f'Session duplicated successfully. You can now edit "{duplicate.title}".'
        )
        
        # Redirect to edit the duplicate
        return redirect('review_manager:edit_session', session_id=duplicate.id)
```

---

## 6. **Session Details View with User Criteria**

### **User Acceptance Criteria - Session Details:**

- [ ] **UC-5.1.1**: Complete session information visible
- [ ] **UC-5.1.2**: Current status with explanation shown
- [ ] **UC-5.1.3**: Search strategy details displayed (if defined)
- [ ] **UC-5.1.4**: Progress statistics visible
- [ ] **UC-5.1.5**: Next recommended action with CTA button
- [ ] **UC-5.1.6**: Recent activity or changes shown
- [ ] **UC-5.1.7**: Information in scannable layout
- [ ] **UC-5.1.8**: Can find specific info without reading everything

### **Enhanced Session Detail View:**
```python
class SessionDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = SearchSession
    template_name = 'review_manager/session_detail.html'
    context_object_name = 'session'
    pk_url_kwarg = 'session_id'
    
    def test_func(self):
        return self.get_object().created_by == self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.object
        
        # Get navigation info
        nav_info = self.get_session_next_url(session)
        
        # Get recent activity
        recent_activities = SessionActivity.objects.filter(
            session=session
        ).order_by('-created_at')[:5]
        
        # Get detailed statistics
        stats = session.stats
        
        # Status explanation
        status_explanations = {
            'draft': 'Your session is created but needs a search strategy.',
            'strategy_ready': 'Your search strategy is defined. Ready to execute searches.',
            'executing': 'Searches are currently running across selected databases.',
            'processing': 'Search results are being processed and deduplicated.',
            'ready_for_review': f'{stats["processed_results_count"]} results are ready for your review.',
            'in_review': f'You have reviewed {stats["reviewed_results_count"]} of {stats["processed_results_count"]} results.',
            'completed': 'Your review is complete and ready for reporting.',
            'failed': 'An error occurred. Check the error details for recovery options.',
            'archived': 'This session has been archived but remains accessible.',
        }
        
        context.update({
            'nav_info': nav_info,
            'recent_activities': recent_activities,
            'stats': stats,
            'status_explanation': status_explanations.get(session.status, ''),
            'can_delete': session.status == 'draft',
            'can_archive': session.status == 'completed',
            'can_duplicate': session.status != 'draft',
        })
        
        return context
```

---

## 7. **Responsive Design with User Criteria**

### **User Acceptance Criteria - Responsive Design:**

- [ ] **UC-6.1.1**: Layout adapts for desktop (3 cards/row)
- [ ] **UC-6.1.2**: Layout adapts for tablet (2 cards/row)
- [ ] **UC-6.1.3**: Layout adapts for mobile (1 card/row)
- [ ] **UC-6.1.4**: Text remains readable at all sizes
- [ ] **UC-6.1.5**: Buttons easily clickable on touch devices
- [ ] **UC-6.1.6**: All core actions work on any device
- [ ] **UC-6.1.7**: Touch targets minimum 44x44 pixels

### **Responsive CSS Framework:**
```css
/* review_manager/static/review_manager/css/dashboard.css */

/* Mobile First Approach */
.sessions-grid {
    display: grid;
    gap: 1.5rem;
    grid-template-columns: 1fr;
    padding: 1rem;
}

/* Tablet and up */
@media (min-width: 768px) {
    .sessions-grid {
        grid-template-columns: repeat(2, 1fr);
        padding: 1.5rem;
    }
}

/* Desktop */
@media (min-width: 1200px) {
    .sessions-grid {
        grid-template-columns: repeat(3, 1fr);
        gap: 2rem;
        padding: 2rem;
    }
}

/* Touch-friendly elements */
.btn, .card-clickable {
    min-height: 44px;
    min-width: 44px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.75rem 1.5rem;
}

/* Readable typography */
body {
    font-size: 16px; /* Prevent zoom on iOS */
    line-height: 1.6;
}

.session-card h3 {
    font-size: clamp(1.1rem, 2.5vw, 1.3rem);
    margin-bottom: 0.5rem;
}

.session-card p {
    font-size: clamp(0.9rem, 2vw, 1rem);
}

/* Status badges responsive */
.status-badge {
    font-size: clamp(0.75rem, 1.5vw, 0.875rem);
    padding: 0.25rem 0.75rem;
    white-space: nowrap;
}
```

---

## 8. **User Feedback System with User Criteria**

### **User Acceptance Criteria - Feedback:**

- [ ] **UC-6.2.1**: Clear success messages for all actions
- [ ] **UC-6.2.2**: Clear error messages with recovery suggestions
- [ ] **UC-6.2.3**: Messages appear prominently
- [ ] **UC-6.2.4**: Messages auto-dismiss after reasonable time
- [ ] **UC-6.2.5**: Plain English used (no technical jargon)
- [ ] **UC-6.2.6**: Messages don't interfere with ongoing work

### **Enhanced Messaging System:**
```python
# review_manager/mixins.py
class UserFeedbackMixin:
    """Mixin for consistent user feedback"""
    
    success_messages = {
        'create': 'Your review session "{title}" has been created successfully.',
        'update': 'Session "{title}" has been updated.',
        'delete': 'Session "{title}" has been deleted.',
        'duplicate': 'Session duplicated. You can now edit "{title}".',
        'archive': 'Session "{title}" has been archived.',
        'unarchive': 'Session "{title}" has been restored from archive.',
    }
    
    error_messages = {
        'permission': "You don't have permission to access this session.",
        'not_found': "The requested session could not be found.",
        'invalid_status': "This action cannot be performed on a session in {status} status.",
        'delete_non_draft': "Only draft sessions can be deleted. Try archiving completed sessions instead.",
    }
    
    def add_success_message(self, action, **kwargs):
        message = self.success_messages.get(action, "Action completed successfully.")
        messages.success(self.request, message.format(**kwargs))
    
    def add_error_message(self, error_type, **kwargs):
        message = self.error_messages.get(error_type, "An error occurred. Please try again.")
        messages.error(self.request, message.format(**kwargs))
```

### **Frontend Message Display:**
```javascript
// review_manager/static/review_manager/js/messages.js
class MessageHandler {
    constructor() {
        this.container = document.getElementById('message-container');
        this.displayTime = 5000; // 5 seconds
        this.init();
    }
    
    init() {
        // Auto-dismiss messages
        document.querySelectorAll('.alert-dismissible').forEach(alert => {
            setTimeout(() => {
                this.dismissMessage(alert);
            }, this.displayTime);
        });
    }
    
    dismissMessage(alert) {
        alert.classList.add('fade-out');
        setTimeout(() => {
            alert.remove();
        }, 300);
    }
    
    // For AJAX operations
    showMessage(type, text) {
        const alertClass = {
            'success': 'alert-success',
            'error': 'alert-danger',
            'warning': 'alert-warning',
            'info': 'alert-info'
        }[type] || 'alert-info';
        
        const messageHtml = `
            <div class="alert ${alertClass} alert-dismissible fade show" role="alert">
                ${text}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        this.container.insertAdjacentHTML('beforeend', messageHtml);
        const newAlert = this.container.lastElementChild;
        
        setTimeout(() => {
            this.dismissMessage(newAlert);
        }, this.displayTime);
    }
}
```

---

## 9. **Testing Strategy with User Criteria Coverage**

### **Test Coverage Requirements:**

```python
# review_manager/tests/test_user_criteria.py
class UserCriteriaTestCase(TestCase):
    """Test all user acceptance criteria"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='researcher',
            password='testpass123'
        )
        self.client.login(username='researcher', password='testpass123')
    
    # UC-2.1.4: Session creation under 30 seconds
    def test_session_creation_performance(self):
        start_time = time.time()
        response = self.client.post(reverse('review_manager:create_session'), {
            'title': 'Test Review',
            'description': 'Test description'
        })
        end_time = time.time()
        
        self.assertLess(end_time - start_time, 1.0)  # Should be well under 30s
        self.assertEqual(response.status_code, 302)
    
    # UC-1.3.5: Find session within 10 seconds
    def test_session_search_performance(self):
        # Create 100 sessions for realistic test
        for i in range(100):
            SearchSession.objects.create(
                title=f'Review {i}',
                description=f'Description {i}',
                created_by=self.user
            )
        
        start_time = time.time()
        response = self.client.get(
            reverse('review_manager:dashboard'), 
            {'q': 'Review 50'}
        )
        end_time = time.time()
        
        self.assertLess(end_time - start_time, 0.5)  # Should be well under 10s
        self.assertContains(response, 'Review 50')
    
    # UC-4.1.5: Identify session stage within 2 seconds
    def test_status_visibility(self):
        session = SearchSession.objects.create(
            title='Test Review',
            status='ready_for_review',
            created_by=self.user
        )
        
        response = self.client.get(reverse('review_manager:dashboard'))
        self.assertContains(response, 'Ready for Review')
        self.assertContains(response, 'status-ready_for_review')
    
    # UC-3.2.4: Cannot delete non-draft sessions
    def test_delete_restrictions(self):
        session = SearchSession.objects.create(
            title='Active Review',
            status='strategy_ready',
            created_by=self.user
        )
        
        response = self.client.post(
            reverse('review_manager:delete_session', args=[session.id])
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(SearchSession.objects.filter(id=session.id).exists())
    
    # UC-6.1: Responsive design
    def test_responsive_templates(self):
        response = self.client.get(reverse('review_manager:dashboard'))
        self.assertContains(response, 'sessions-grid')
        self.assertContains(response, 'viewport')
```

### **Integration Test Suite:**
```python
# review_manager/tests/test_integration.py
class WorkflowIntegrationTest(TestCase):
    """Test complete user workflows"""
    
    def test_complete_session_creation_workflow(self):
        """Test UC-2.1 and UC-2.2 workflow"""
        # Step 1: Create session
        response = self.client.post(reverse('review_manager:create_session'), {
            'title': 'Diabetes Guidelines Review',
            'description': 'Systematic review of diabetes management guidelines'
        })
        
        # Should redirect to strategy definition
        self.assertEqual(response.status_code, 302)
        session = SearchSession.objects.latest('created_at')
        self.assertRedirects(
            response, 
            reverse('search_strategy:define', args=[session.id])
        )
        
        # Verify session created correctly
        self.assertEqual(session.status, 'draft')
        self.assertEqual(session.created_by, self.user)
    
    def test_session_navigation_by_status(self):
        """Test UC-1.2 smart navigation"""
        statuses_and_urls = [
            ('draft', 'search_strategy:define'),
            ('strategy_ready', 'serp_execution:execute'),
            ('ready_for_review', 'review_results:overview'),
            ('completed', 'reporting:summary'),
        ]
        
        for status, expected_url_name in statuses_and_urls:
            session = SearchSession.objects.create(
                title=f'Test {status}',
                status=status,
                created_by=self.user
            )
            
            # Click on session card
            response = self.client.get(
                reverse('review_manager:session_click', args=[session.id])
            )
            
            expected_url = reverse(expected_url_name, args=[session.id])
            self.assertRedirects(response, expected_url)
```

---

## 10. **Performance Requirements**

### **Performance Criteria Checkboxes:**

- [ ] **PERF-1**: Dashboard loads in < 2 seconds with 100+ sessions
- [ ] **PERF-2**: Search returns results in < 500ms
- [ ] **PERF-3**: Session creation completes in < 1 second
- [ ] **PERF-4**: Status updates propagate immediately
- [ ] **PERF-5**: Pagination works smoothly with large datasets

### **Performance Optimisation:**
```python
# review_manager/managers.py
class SearchSessionQuerySet(models.QuerySet):
    def with_stats(self):
        """Optimised query with pre-calculated stats"""
        return self.annotate(
            query_count=Count('searchquery'),
            execution_count=Count('searchexecution'),
            result_count=Count('processedresult'),
            reviewed_count=Count(
                'processedresult',
                filter=Q(processedresult__reviewtagassignment__isnull=False)
            )
        )
    
    def for_dashboard(self, user):
        """Optimised query for dashboard display"""
        return self.filter(
            created_by=user
        ).select_related(
            'created_by'
        ).prefetch_related(
            Prefetch(
                'searchexecution_set',
                queryset=SearchExecution.objects.filter(
                    status='completed'
                ).only('id', 'status', 'completed_at')
            )
        ).with_stats()


class SearchSessionManager(models.Manager):
    def get_queryset(self):
        return SearchSessionQuerySet(self.model, using=self._db)
    
    def with_stats(self):
        return self.get_queryset().with_stats()
    
    def for_dashboard(self, user):
        return self.get_queryset().for_dashboard(user)
```

---

## 11. **Security & Data Protection**

### **Security Criteria Checkboxes:**

- [ ] **SEC-1**: Users can only access their own sessions
- [ ] **SEC-2**: CSRF protection on all forms
- [ ] **SEC-3**: SQL injection prevention through ORM
- [ ] **SEC-4**: XSS prevention in templates
- [ ] **SEC-5**: Proper authentication required for all views
- [ ] **SEC-6**: Session data validated before save

### **Security Implementation:**
```python
# review_manager/decorators.py
def owns_session(view_func):
    """Decorator to ensure user owns the session"""
    @wraps(view_func)
    def wrapped_view(request, session_id, *args, **kwargs):
        session = get_object_or_404(SearchSession, pk=session_id)
        if session.created_by != request.user:
            messages.error(request, "You don't have permission to access this session.")
            return redirect('review_manager:dashboard')
        return view_func(request, session_id, *args, **kwargs)
    return wrapped_view


# review_manager/middleware.py
class SessionSecurityMiddleware:
    """Additional security checks for session access"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Clear any session data if user changes
        if request.user.is_authenticated:
            stored_user = request.session.get('_auth_user_id')
            if stored_user and str(request.user.id) != stored_user:
                request.session.flush()
        
        return response
```

---

## 12. **Accessibility Requirements**

### **Accessibility Criteria Checkboxes:**

- [ ] **A11Y-1**: All interactive elements keyboard accessible
- [ ] **A11Y-2**: Proper ARIA labels on dynamic content
- [ ] **A11Y-3**: Colour contrast ratio ≥ 4.5:1
- [ ] **A11Y-4**: Focus indicators visible
- [ ] **A11Y-5**: Screen reader announcements for status changes
- [ ] **A11Y-6**: Skip navigation links available

### **Accessibility Implementation:**
```html
<!-- Accessible session card -->
<article class="session-card" 
         role="article"
         aria-label="Review session: {{ session.title }}">
    <header>
        <h3 id="session-{{ session.id }}-title">{{ session.title }}</h3>
        <span class="status-badge"
              role="status"
              aria-label="Status: {{ session.get_status_display }}">
            {{ session.get_status_display }}
        </span>
    </header>
    
    <div class="card-body">
        <p id="session-{{ session.id }}-desc">{{ session.description|truncatewords:20 }}</p>
        
        <dl class="card-stats">
            <dt class="visually-hidden">Created</dt>
            <dd>{{ session.created_at|date:"M d, Y" }}</dd>
            
            {% if session.stats.processed_results_count %}
            <dt class="visually-hidden">Results</dt>
            <dd>{{ session.stats.processed_results_count }} results ready</dd>
            {% endif %}
        </dl>
    </div>
    
    <footer>
        <a href="{{ session.get_next_url }}" 
           class="btn btn-primary"
           aria-describedby="session-{{ session.id }}-title session-{{ session.id }}-desc">
            {{ session.get_next_action_text }}
            <span class="visually-hidden">for {{ session.title }}</span>
        </a>
    </footer>
</article>
```

---

## 13. **Phase 2 Preparation**

### **Future-Proofing Checkboxes:**

- [ ] **FUTURE-1**: Database includes unused collaboration fields
- [ ] **FUTURE-2**: Models support multi-user ownership
- [ ] **FUTURE-3**: Status workflow accommodates collaborative review
- [ ] **FUTURE-4**: URL structure supports team namespacing
- [ ] **FUTURE-5**: Templates have placeholders for team features
- [ ] **FUTURE-6**: API structure supports future mobile apps

### **Phase 2 Ready Models:**
```python
# review_manager/models.py
class SearchSession(models.Model):
    """Session model ready for Phase 2 collaboration"""
    
    # Current Phase 1 fields
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Ownership - Phase 1: single user, Phase 2: team support
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_sessions')
    
    # Phase 2 collaboration fields (unused in Phase 1)
    team = models.ForeignKey('teams.Team', null=True, blank=True, on_delete=models.SET_NULL)
    collaborators = models.ManyToManyField(User, blank=True, related_name='collaborative_sessions')
    visibility = models.CharField(
        max_length=20,
        choices=[
            ('private', 'Private'),
            ('team', 'Team'),
            ('public', 'Public')
        ],
        default='private'
    )
    
    # Permissions placeholder
    permissions = models.JSONField(default=dict, blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User, 
        null=True, 
        blank=True,
        on_delete=models.SET_NULL,
        related_name='updated_sessions'
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['created_by', 'status']),
            models.Index(fields=['team', 'status']),  # Ready for Phase 2
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
        ]
```

---

## 14. **Deployment Checklist**

### **Pre-Deployment Requirements:**

- [ ] **DEPLOY-1**: All user criteria tests passing
- [ ] **DEPLOY-2**: Performance benchmarks met
- [ ] **DEPLOY-3**: Security audit completed
- [ ] **DEPLOY-4**: Accessibility audit passed
- [ ] **DEPLOY-5**: Cross-browser testing completed
- [ ] **DEPLOY-6**: Mobile testing on real devices
- [ ] **DEPLOY-7**: Database migrations tested
- [ ] **DEPLOY-8**: Backup and recovery procedures tested
- [ ] **DEPLOY-9**: Documentation complete
- [ ] **DEPLOY-10**: User acceptance testing signed off

---

## 15. **Success Metrics Dashboard**

### **Metrics to Track:**

```python
# review_manager/analytics.py
class ReviewManagerAnalytics:
    """Track success metrics for user criteria"""
    
    @staticmethod
    def get_metrics(user):
        sessions = SearchSession.objects.filter(created_by=user)
        
        return {
            # User Efficiency Metrics
            'avg_session_creation_time': calculate_avg_creation_time(),
            'avg_session_find_time': calculate_avg_search_time(),
            'task_completion_rate': calculate_completion_rate(),
            
            # System Reliability Metrics
            'avg_page_load_time': get_avg_page_load_time(),
            'error_rate': calculate_error_rate(),
            'data_loss_incidents': count_data_loss_incidents(),
            
            # User Satisfaction Indicators
            'sessions_without_help': count_unassisted_completions(),
            'navigation_confidence_score': calculate_nav_confidence(),
            'support_request_rate': calculate_support_rate(),
        }
```

---

## 📊 **Final Implementation Summary**

This enhanced PRD provides:

1. **Clear Development Path**: Each feature has specific implementation details with code examples
2. **User-Centric Focus**: Every technical decision ties back to user acceptance criteria
3. **Measurable Success**: Checkboxes for tracking progress against user requirements
4. **Future-Ready Architecture**: Phase 2 collaboration features considered but not implemented
5. **Quality Assurance**: Comprehensive testing strategy covering all user stories
6. **Windows Development Ready**: Django 4.2 compatible with Windows-specific considerations

### **Development Priority Order:**

1. **Core Models & Database** (1-2 days)
2. **Dashboard & Navigation** (2-3 days)
3. **Session CRUD Operations** (2 days)
4. **Status Management & Workflow** (1-2 days)
5. **Responsive UI & Accessibility** (2 days)
6. **Testing & Security** (2 days)
7. **Performance Optimisation** (1 day)
8. **Documentation & Deployment** (1 day)

**Total Estimated Development Time**: 12-15 days

---

## 🚀 **Next Steps**

1. Review and approve this PRD with the development team
2. Set up the Django app structure within the existing project
3. Create the database models with migrations
4. Implement views and templates following the user criteria
5. Write tests for each user acceptance criterion
6. Conduct user acceptance testing with the personas defined
7. Deploy and monitor success metrics

This PRD ensures that the Review Manager app will provide an intuitive, efficient experience for researchers conducting grey literature systematic reviews while maintaining technical excellence and preparing for future collaboration features.