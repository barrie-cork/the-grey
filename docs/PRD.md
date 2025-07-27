# Thesis Grey: Master Project Plan (Django Edition)

**Project Title:** Thesis Grey  
**Version:** 2.2  
**Date:** 2025-05-31    

## 1. Executive Summary

Thesis Grey is a specialized web application designed to help researchers, particularly those developing clinical guidelines, systematically find, manage, and review "grey literature" – research found outside traditional academic databases (like reports, theses, conference proceedings). It streamlines the process of creating search strategies, running them against search engines like Google, and organizing the results for review, following best practices like PRISMA.

The application, built using the **Django 4.2 framework**, addresses the challenge of finding relevant grey literature for systematic reviews and clinical guidelines, which is currently a manual, time-consuming, and often unsystematic process. Researchers struggle to document their search strategies, efficiently execute searches across multiple sources, manage large volumes of results, and track the review process in a way that meets reporting standards like PRISMA.

### Key Benefits

- **Saves significant researcher time** by automating search execution and results organization.
- **Improves the rigor and comprehensiveness** of literature reviews by making grey literature searching more systematic.
- **Organizes information** effectively, managing search strategies, results, and review decisions in one place.
- **Supports compliance** with reporting standards like PRISMA through structured workflows and data export.

## 2. Project Goals (Phase 1)

1. Provide researchers with tools to create and execute systematic search strategies.
2. Enable efficient processing and review of search results.
3. Support PRISMA-compliant workflows for literature reviews.
4. Establish a foundation that can be extended in Phase 2 without significant refactoring.

## 3. Technical Architecture

### 3.1 Technology Stack

- **Framework:** Django `4.2.x` (Python)
- **Frontend:** Django Templates, HTML, CSS (with TailwindCSS), JavaScript (for AJAX interactivity)
- **Backend:** Django, Django ORM
- **Database:** PostgreSQL (using Psycopg 3)
- **APIs:** Google Search API via Serper (using a Python client like `requests`)
- **Background Tasks:** Celery with Redis as the message broker
- **DevOps:** Docker, GitHub Actions (basic CI/CD)
- **API Development (Phase 1):** Django built-in JSON responses for AJAX functionality, Django REST Framework for Phase 2 if needed

### 3.2 Architectural Approach

The project will adopt a **modular design using Django Apps**. Each core feature or domain will be encapsulated within its own app, promoting separation of concerns and maintainability. While Django's app structure provides a natural way to organize by feature, the principles of **Vertical Slice Architecture** will still guide development, focusing on implementing features end-to-end. This allows implementation to focus on one feature at a time, ensuring the feature in focus passes all tests before moving to the next. This should guide the roadmap.

**Each Django app should have its own detailed PRD** located in `docs/features/{app_name}/{app_name}-prd.md` that provides implementation-specific details while referencing this master PRD for overall context and architectural decisions.

### 3.3 Project Structure (Illustrative)

```
agent-grey/
├── manage.py                 # Django's command-line utility
├── grey_lit_project/      # Main project Python package
│   ├── __init__.py
│   ├── settings/             # Settings directory
│   │   ├── __init__.py
│   │   ├── base.py           # Base settings
│   │   ├── local.py          # Local development settings
│   │   └── production.py     # Production settings
│   ├── urls.py               # Project-level URL configuration
│   ├── wsgi.py               # WSGI entry-point
│   └── asgi.py               # ASGI entry-point (for Celery/Channels if needed)
├── apps/                     # Directory for all Django apps
│   ├── accounts/             # User authentication and profiles
│   │   ├── migrations/
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── forms.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   └── templates/
│   │       └── accounts/
│   ├── review_manager/       # Review Manager Dashboard and session creation
│   │   └── ... (similar structure to accounts)
│   ├── search_strategy/      # Search Strategy definition
│   │   └── ...
│   ├── serp_execution/       # Search Execution and background tasks (Celery tasks)
│   │   ├── tasks.py          # Celery tasks
│   │   └── ...
│   ├── results_manager/      # Results processing and management
│   │   └── ...
│   ├── review_results/       # Results review, tagging, notes
│   │   └── ...
│   ├── reporting/            # Reporting and data export
│   │   └── ...
├── docs/                     # Documentation
│   ├── PRD.md                # This master PRD
│   └── features/             # App-specific PRDs organized by feature
│       ├── accounts/         # Authentication app PRD
│       │   └── PRD-auth.md
│       ├── review_manager/   # Review Manager app PRD
│       │   └── review-manager-prd.md
│       ├── search_strategy/  # Search Strategy app PRD
│       │   └── search-strategy-prd.md
│       ├── serp_execution/   # SERP Execution app PRD
│       │   └── serp-execution-prd.md
│       ├── results_manager/  # Results Manager app PRD
│       │   └── results-manager-prd.md
│       ├── review_results/   # Review Results app PRD
│       │   └── review-results-prd.md
│       └── reporting/        # Reporting app PRD
│           └── reporting-prd.md
├── static/                   # Project-wide static files (CSS, JS, images)
│   └── css/
│   └── js/
├── templates/                # Project-wide base templates
│   └── base.html
└── requirements/
    ├── base.txt
    ├── local.txt
    └── production.txt
```

### Directory Structure (within each app)

Each Django app (e.g., `apps/search_strategy/`) will generally follow this structure:

```
apps/{feature_app_name}/
├── __init__.py
├── admin.py         # Django admin configurations
├── apps.py          # App configuration
├── forms.py         # Django forms
├── migrations/      # Database migrations
├── models.py        # Django ORM models
├── templates/       # HTML templates specific to this app
│   └── {feature_app_name}/
│       ├── some_page.html
├── templatetags/    # Custom template tags and filters
├── tests.py         # Unit and integration tests
├── urls.py          # URL routing for this app
├── views.py         # View functions or class-based views
└── utils.py         # Utility functions specific to this app (if any)
```

### File types
- All Python code will be `.py`.
- HTML templates will be `.html`.
- Static assets will be `.css`, `.js`, etc.

### 3.4 Database Architecture

Phase 1 implements the full database schema designed for both phases, using the **Django ORM** with PostgreSQL. The core entities include:

#### Core Models

**SearchSession Model (Primary Entity)**
```python
class SearchSession(models.Model):
    # Core Phase 1 fields
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Search strategy fields (PIC framework)
    population_terms = models.JSONField(default=list, blank=True)
    interest_terms = models.JSONField(default=list, blank=True)
    context_terms = models.JSONField(default=list, blank=True)
    
    # Ownership and permissions
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_sessions')
    
    # Phase 2 collaboration fields (prepared but unused in Phase 1)
    team = models.ForeignKey('teams.Team', null=True, blank=True, on_delete=models.SET_NULL)
    collaborators = models.ManyToManyField(User, blank=True, related_name='collaborative_sessions')
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='private')
    permissions = models.JSONField(default=dict, blank=True)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='updated_sessions')
```

**Status Workflow**
```python
STATUS_CHOICES = [
    ('draft', 'Draft'),                                         # Just created, no strategy defined
    ('strategy_ready', 'Strategy Ready'),                       # PIC terms defined, ready to execute
    ('executing', 'Executing Searches'),                        # Background tasks running
    ('processing', 'Processing Results'),                       # Raw results being processed
    ('ready_for_review', 'Ready for Review'),                   # Results available for screening
    ('in_review', 'Under Review'),                              # User actively reviewing results
    ('completed_fully_reviewed', 'Completed - Fully Reviewed'), # All items tagged by user(s)
    ('review_concluded_incomplete', 'Review Concluded (Incomplete)'), # User finished review early, not all items tagged
    ('failed', 'Failed'),                                       # Error occurred during execution or processing
    ('archived', 'Archived'),                                   # User archived a session (typically after a form of completion)
]

VISIBILITY_CHOICES = [
    ('private', 'Private'),
    ('team', 'Team'),
    ('public', 'Public')
]
```

**Additional Core Models:**
- `User`: Stores user authentication and profile information (likely extending Django's built-in `AbstractUser`). `db_comment` will be used for clarity.
- `SearchQuery`: Defines specific queries within a session.
- `SearchExecution`: Tracks the execution of search queries.
- `RawSearchResult`: Stores raw data from search engines.
- `ProcessedResult`: Contains normalized and processed search results.
- `DuplicateRelationship`: Tracks duplicate results.
- `ReviewTag`: Defines tags for categorizing results (Include, Exclude, Maybe).
- `ReviewTagAssignment`: Links tags to results.
- `Note`: Stores notes added to results.
- `SessionActivity`: Audit trail for session changes and activities.

**Database Integrity Rules:**
- `created_by` uses `CASCADE` - when user is deleted, their sessions are deleted
- Audit fields (`performed_by`, `updated_by`) use `PROTECT` - preserves audit trail integrity
- Foreign keys to optional Phase 2 models use `SET_NULL` - allows graceful degradation

Django's migration system will manage schema changes.

## 4. Core Features

### 4.1 Authentication

**Description:** Basic user authentication system allowing researchers to register, log in, and manage their profiles.

**Key Components (Django context):**
- Django's built-in `AuthenticationForm`, `UserCreationForm`.
- Custom templates for login, signup, profile pages.
- Views: `LoginView`, `LogoutView`, custom views for signup and profile.

**Technical Implementation:**
- Utilizes Django's built-in authentication system (`django.contrib.auth`).
- Password hashing handled by Django.
- Session management handled by Django.
- Basic role-based permissions using Django's permission system or custom groups.
- Potentially a custom User model inheriting from `AbstractUser` if additional fields are needed.

### 4.2 Review Manager Dashboard ✅ **IMPLEMENTED**

**Description:** Central landing page displaying the user's review sessions with smart navigation and comprehensive session management.

**Key Components (Django context):**
- `DashboardView` (Class-Based View) with session filtering and statistics ✅
- `SessionCreateView` implementing two-step creation workflow ✅
- `SessionDetailView`, `SessionUpdateView`, `SessionDeleteView` for full CRUD operations ✅
- Django templates with responsive card-based layout ✅
- Session duplication and archiving functionality ✅

**Technical Implementation:**
- **Two-Step Session Creation:** Minimal creation (title + description) → immediate redirect to search strategy definition ✅
- **Smart Navigation:** Session clicks route to next logical step based on status (draft → strategy, ready_for_review → results, etc.) ✅
- **Status-Based Grouping:** Sessions organised by Active, Completed, Failed with visual status indicators ✅
- **9-State Status Workflow:** Robust status management with transition validation ✅
- **Session Management:** Delete (draft only), duplicate (any status), archive (completed only) ✅
- **Enterprise Security:** Rate limiting, CSRF protection, comprehensive audit logging ✅
- **Performance Optimised:** Database indexes and query optimisation for dashboard performance ✅

**Status Workflow Management:**
```python
class SessionStatusManager:
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
```

**✅ COMPLETED - Production Ready with 364 tests and 95.8% coverage**  
**Detailed implementation specifications available in:** [docs/features/review_manager/review-manager-prd.md](features/review_manager/review-manager-prd.md)

### 4.3 Search Strategy ✅ **IMPLEMENTED**

**Description:** Interface for defining search strategies using the PIC framework (Population, Interest, Context) and configuring search parameters.

**Key Components (Django context):**
- `SearchStrategyCreateView`, `SearchStrategyDetailView`, `SearchStrategyUpdateView` (CBVs) ✅
- Django `SearchStrategyForm` with comprehensive validation ✅
- Dynamic Django templates with tag-based input interface ✅
- JavaScript for real-time query preview and dynamic form management ✅
- Complete integration with SearchSession workflow ✅
- Multi-domain search configuration with Boolean query generation ✅

**Technical Implementation:**
- **PIC Framework:** Population, Interest, Context terms with ArrayField storage ✅
- **Dynamic Interface:** Tag-based input system replacing comma-separated fields ✅
- **Query Generation:** Advanced Boolean logic with file type expansion ✅
- **Multi-Domain Support:** N domains + general search = N+1 queries ✅
- **Real-time Preview:** Live query generation and validation ✅
- **File Type Filtering:** PDF and Word document support with .doc/.docx expansion ✅

**Search Strategy Model:**
```python
class SearchStrategy(models.Model):
    session = models.OneToOneField(SearchSession, related_name='search_strategy')
    population_terms = ArrayField(CharField, default=list, blank=True)
    interest_terms = ArrayField(CharField, default=list, blank=True) 
    context_terms = ArrayField(CharField, default=list, blank=True)
    search_config = JSONField(default=dict)  # domains, file_types, search_types
    # Advanced query generation methods implemented
```

**✅ COMPLETED - Production Ready with dynamic UI and comprehensive testing**  
**Detailed implementation specifications available in:** [docs/features/search_strategy/search-strategy-prd.md](features/search_strategy/search-strategy-prd.md)

### 4.4 SERP Execution 🚧 **IN PROGRESS**

**Description:** System for executing search queries against external APIs and tracking progress.

**✅ Implemented Components:**
- Complete Django ORM models: `SearchQuery`, `SearchExecution`, `RawSearchResult` ✅
- Custom managers with query patterns and filtering methods ✅
- Status workflow with retry logic and progress tracking ✅
- API usage tracking and cost monitoring fields ✅
- Comprehensive model relationships and constraints ✅

**🚧 In Progress:**
- Celery task (`perform_serp_query_task`) for making API calls to Serper
- `SearchExecutionStatusView` for progress monitoring
- Serper API client implementation
- JavaScript for real-time status updates

**📋 Planned:**
- Background job queue integration
- User interface for execution monitoring
- Error handling and retry mechanisms
- Integration with search strategy workflow

**Technical Architecture:**
- **Models Foundation:** Complete with UUID primary keys and proper relationships ✅
- **Status Workflow:** pending → running → completed/failed → retrying ✅
- **Progress Tracking:** Percentage-based with detailed metadata ✅
- **API Integration:** Serper.dev for Google Search (implementation pending)
- **Background Processing:** Celery with Redis message broker (configuration pending)

**Model Structure:**
```python
class SearchExecution(models.Model):
    query = ForeignKey(SearchQuery, related_name='executions')
    status = CharField(choices=STATUS_CHOICES, default='pending')
    progress_percentage = IntegerField(default=0, validators=[0-100])
    retry_count = IntegerField(default=0)
    api_calls_made = IntegerField(default=0)
    api_credits_used = DecimalField(max_digits=10, decimal_places=4)
    # + timing, error handling, results tracking
```

**🎯 Current Status:** Foundation models complete, API integration in progress  
**Detailed implementation specifications available in:** [docs/features/serp_execution/serp-execution-prd.md](features/serp_execution/serp-execution-prd.md)

### 4.5 Results Manager ✅ **COMPLETED (90% COMPLETE)**

**Description:** Backend system for processing raw search results and preparing them for review.

**✅ Implemented Components:**
- Complete Django ORM models: `ProcessedResult`, `DuplicateRelationship`, `ProcessingSession` ✅
- Custom model managers with common query patterns ✅
- Core processing services: URL normalization, metadata extraction, deduplication engines ✅
- Processing pipeline orchestration with batch processing (50 results per batch) ✅
- Comprehensive test suite with 43+ test cases and 95%+ coverage ✅
- Database migrations and proper model relationships ✅
- Complete Celery background tasks for asynchronous processing ✅
- `ResultsOverviewView` with comprehensive filtering and sorting ✅
- `ProcessingStatusView` for real-time status monitoring ✅
- User interface for processing status monitoring ✅
- Error handling and recovery mechanisms with retry functionality ✅
- Real-time progress updates and AJAX endpoints ✅

**🔄 Final Integration:**
- Integration with SERP execution completion workflow (pending SERP completion)
- End-to-end workflow testing (pending full pipeline completion)

**Technical Implementation:**
- **URL Normalization:** Comprehensive URL cleaning with tracking parameter removal ✅
- **Metadata Extraction:** File type detection, quality scoring (0.0-1.0), and domain analysis ✅
- **Deduplication Engine:** URL exact/similar matching + title similarity for same domain ✅
- **Processing Pipeline:** Batch processing with progress tracking and error handling ✅
- **Performance:** Memory-efficient design targeting 1000+ results within 2 minutes ✅

**Model Architecture:**
```python
class ProcessedResult(models.Model):
    # Core relationships and normalized data
    session = ForeignKey(SearchSession, related_name='processed_results')
    raw_result = ForeignKey(RawSearchResult, related_name='processed_result')
    normalized_url = URLField(max_length=2048)
    
    # Extracted metadata
    file_type = CharField(max_length=50)  # pdf, doc, html, etc.
    processing_quality_score = FloatField(default=0.0)  # 0.0-1.0
    is_duplicate = BooleanField(default=False)
    enhanced_metadata = JSONField(default=dict)  # Phase 2 extensibility
```

**🎯 Current Status:** Production-ready with comprehensive UI and background processing. Only final workflow integration pending.  
**Detailed implementation specifications available in:** [docs/features/results_manager/results-manager-prd.md](features/results_manager/results-manager-prd.md)

### 4.6 Review Results

**Description:** Interface for reviewing search results, applying tags, and adding notes, all within a single paginated view.

**Key Components (Django context):**
- `ResultsOverviewView` (CBV or function view) with pagination.
- Django templates for displaying results.
- Django Forms for tagging and adding notes.
- Django ORM queries for fetching `ProcessedResult` with pagination, `ReviewTag`, `Note`.
- Views/logic to handle `ReviewTagAssignment` and `Note` creation/updates.

**Technical Implementation:**
- Scroll-paginated results display (e.g., 25 results at a time, loading more on scroll).
- Interactive tagging for each result item using dedicated buttons for "Include", "Exclude", "Maybe". Tag selection updates button appearance (e.g., color). Only one tag active per result.
- Clicking "Exclude" prompts for a reason via a modal window (simple text input for Phase 1). No reason required for "Include" or "Maybe".
- Tag assignments are handled via AJAX for a dynamic UX.
- Users must tag every result to achieve a 'completed_fully_reviewed' session status. However, users can opt to 'Conclude Review Early', resulting in a 'review_concluded_incomplete' status if not all items are tagged. This distinction will be important for reporting.
- Simple notes system integrated with each result item, likely via AJAX.
- Visual indication if a result is a duplicate (e.g., an icon). Clicking this provides a modal listing the titles of related duplicates.
- The workflow aims to support PRISMA guidelines by capturing necessary data for the flow diagram (e.g., counts of included/excluded items).

**Detailed implementation specifications available in:** [docs/features/review_results/review-results-prd.md](features/review_results/review-results-prd.md)

### 4.7 Reporting

**Description:** System for generating reports and exporting data from review sessions.

**Key Components (Django context):**
- `ReportingView` (CBV or function view).
- Django templates for displaying statistics.
- Django ORM queries to aggregate report data.
- Python libraries for CSV (e.g., `csv` module), JSON (e.g., `json` module), and PDF (e.g., `ReportLab` or `WeasyPrint`) export.

**Technical Implementation:**
- Basic PRISMA flow statistics calculated via ORM queries.
- Search strategy summary display.
- CSV, JSON, and PDF export of included/excluded results.
- Summary statistics dashboard with tag distribution and domain distribution.

**Detailed implementation specifications available in:** [docs/features/reporting/reporting-prd.md](features/reporting/reporting-prd.md)

## 5. Project-Wide Standards

### 5.1 User Experience Standards

**Performance Requirements:**
- Dashboard loads in < 2 seconds with 100+ sessions
- Session search returns results in < 500ms
- Session creation completes in < 30 seconds
- All user actions receive immediate feedback

**Accessibility Standards:**
- WCAG 2.1 AA compliance
- Keyboard navigation support
- Screen reader compatibility
- Minimum colour contrast 4.5:1
- Touch-friendly interface (44px minimum touch targets)

**Responsive Design:**
- Mobile-first approach
- Adaptive layout: 1 column (mobile), 2 columns (tablet), 3 columns (desktop)
- Cross-browser compatibility (Chrome, Firefox, Safari, Edge)

**User Feedback System:**
- Clear success/error messages for all actions
- Plain English used (no technical jargon)
- Status explanations with next steps
- Contextual help and tooltips

### 5.2 Security Standards

**Authentication & Authorisation:**
- Users can only access their own sessions (Phase 1) ✅ Implemented
- CSRF protection on all forms ✅ Implemented
- XSS prevention in templates ✅ Implemented
- Proper authentication required for all views ✅ Implemented

**Data Protection:**
- SQL injection prevention through ORM ✅ Implemented
- Input validation on all forms ✅ Implemented
- Session data validated before save ✅ Implemented
- Audit logging for sensitive operations ✅ Implemented

**Enterprise Security Features (Implemented in Sprint 8):**
- Rate limiting and DoS protection ✅ Implemented
- Security headers (CSP, HSTS, XSS Protection) ✅ Implemented
- Session ownership validation with decorators ✅ Implemented
- Comprehensive security monitoring and alerting ✅ Implemented
- OWASP Top 10 compliance and protection ✅ Implemented

### 5.3 Testing Standards

**Required Test Coverage:**
- Unit tests for all models, views, and forms ✅ Implemented
- Integration tests for complete workflows ✅ Implemented
- Performance tests for dashboard and search functionality ✅ Implemented
- Accessibility testing with automated tools (Sprint 9)
- Cross-browser testing ✅ Implemented
- Security testing comprehensive suite ✅ Implemented (319 tests)

**Testing Framework:**
- Django's built-in test framework ✅ Configured
- Factory Boy for test data generation (Sprint 9)
- Coverage.py for test coverage measurement ✅ Configured
- Selenium for end-to-end testing ✅ Configured
- pytest for advanced testing scenarios ✅ Configured

**Current Testing Status (Latest):**
- **364+ total tests implemented** (319 security + 45+ core functionality)
- **95.8%+ test coverage achieved** 
- **100% security feature coverage**
- **Production-ready testing infrastructure**
- **Search Strategy:** 100% test coverage with comprehensive validation
- **SERP Execution:** Model tests complete, integration tests pending

### 5.4 Code Quality Standards

**Code Style:**
- PEP 8 compliance
- Type hints where appropriate
- Comprehensive docstrings
- Meaningful variable and function names

**Architecture:**
- Django best practices
- DRY (Don't Repeat Yourself) principle
- SOLID principles where applicable
- Clear separation of concerns between apps

## 6. Implementation Plan

### 6.1 Phase 1 Implementation Status

1.  **Project Setup** ✅ **COMPLETED**
    *   Initialize Django project with modular app structure ✅
    *   Configure PostgreSQL database with custom User model ✅
    *   Set up Django apps with proper organization ✅
    *   Define core models with UUID primary keys ✅
    *   Configure Django's authentication with custom User ✅
    *   Celery configuration ready for background tasks ✅

2.  **Core Feature Implementation Status**
    *   **Authentication System (`accounts` app):** ✅ **COMPLETE**
        *   Custom User model with UUID primary key ✅
        *   Complete template system (login, signup, profile) ✅
        *   Comprehensive views and forms ✅
        *   Full test coverage ✅
    *   **Review Manager Dashboard (`review_manager` app):** ✅ **COMPLETE**
        *   Advanced models with 9-state workflow ✅
        *   Complete dashboard with smart navigation ✅
        *   Full CRUD operations with security ✅
        *   Enterprise-grade security and testing ✅
        *   Activity logging and audit trail ✅
    *   **Search Strategy (`search_strategy` app):** ✅ **COMPLETE**
        *   PIC framework models and forms ✅
        *   Dynamic tag-based interface ✅
        *   Real-time query generation ✅
        *   Multi-domain and Boolean query support ✅
        *   Comprehensive testing and validation ✅
    *   **SERP Execution (`serp_execution` app):** 🚧 **IN PROGRESS**
        *   Foundation models complete ✅
        *   Custom managers and relationships ✅
        *   Status workflow and progress tracking ✅
        *   API client implementation (in progress) 🚧
        *   Celery tasks for execution (planned) 📋
        *   User interface for monitoring (planned) 📋
    *   **Results Manager (`results_manager` app):** ✅ **COMPLETE - 90% IMPLEMENTED**
        *   Foundation models and migrations complete ✅
        *   Core processing services (URL normalization, metadata extraction, deduplication) ✅
        *   Comprehensive test suite (43+ test cases) ✅
        *   Background task implementation complete ✅
        *   User interface for results overview and processing status ✅
        *   AJAX endpoints for real-time updates ✅
        *   Error handling and retry mechanisms ✅
        *   Integration with SERP execution output (pending SERP completion) 🔄
    *   **Review Results (`review_results` app):** 📋 **PLANNED**
        *   Manual review interface with tagging
        *   PRISMA workflow implementation
    *   **Reporting (`reporting` app):** 📋 **PLANNED**
        *   Statistics generation and data export

3.  **Integration & Testing** 🔄 **ONGOING**
    *   App integration via Django URL routing ✅
    *   Comprehensive unit and integration tests ✅
    *   Security testing suite (364 tests) ✅
    *   Performance optimization implemented ✅
    *   End-to-end testing (pending full workflow completion) 📋

4.  **Deployment** 📋 **PREPARED**
    *   Docker configuration ready ✅
    *   Production settings structure complete ✅
    *   Deployment workflow (pending Phase 1 completion) 📋

### 6.2 App Development Status

1. **accounts** ✅ **COMPLETE** - Foundation for all user-related functionality
2. **review_manager** ✅ **COMPLETE** - Core session management and dashboard
3. **search_strategy** ✅ **COMPLETE** - Search strategy definition with PIC framework
4. **serp_execution** 🚧 **IN PROGRESS** - API integration and background tasks
5. **results_manager** ✅ **COMPLETE (90%)** - Production-ready with comprehensive UI and processing
6. **review_results** 📋 **PLANNED** - Results review interface with tagging
7. **reporting** 📋 **PLANNED** - Reports and data export

### 6.3 Key Dependencies and Considerations

- **Schema Updates**: The `ReviewTagAssignment` model includes a `reason` field (`reason = models.TextField(blank=True, null=True)`) to store the justification when a result is tagged as "Exclude". This field is required for Exclude tags and optional for others.
- **API Integration**: Proper configuration of the Serper API (API keys in environment variables/Django settings). Python `requests` library for making calls.
- **Background Jobs**: Celery for handling long-running tasks (API calls, results processing). Requires a message broker like Redis or RabbitMQ.
- **Data Flow**: Ensuring proper data flow from search strategy definition through execution, processing, review, and reporting, managed by Django views, models, and Celery tasks.
- **Static Files & Media**: Configure Django for serving static files (CSS, JS) and potentially user-uploaded media if that becomes a feature.
- **Security**: Implement Django's security best practices (CSRF protection, XSS prevention, HTTPS in production).

## 7. Future Expansion (Phase 2)

While Phase 1 focuses on core functionality, the architecture is designed to support future expansion in Phase 2:

**Collaboration Features:**
- Multi-user teams and organisations
- Role-based permissions (Admin, Reviewer, Observer)
- Real-time collaborative review
- Session sharing and visibility controls

**Advanced Features:**
- **Session Hub**: Enhanced central landing page with team views
- **Search Strategy Enhancements**: Advanced operators, strategy templates, saved searches
- **Results Manager Enhancements**: Advanced deduplication algorithms, bulk operations, AI-assisted categorisation
- **Review Results Enhancements**: Custom tagging systems, collaborative review workflows, conflict resolution
- **Reporting Enhancements**: Custom report templates, advanced visualisations, automated report generation

**Technical Enhancements:**
- **REST API Development**: Full API using Django REST Framework for mobile apps and integrations
- **Real-time Updates**: WebSocket support for live collaboration
- **Advanced Search**: Elasticsearch integration for full-text search
- **Cloud Storage**: Integration with cloud storage providers
- **Mobile Apps**: Native mobile applications

## 8. Documentation Structure ✅ **COMPREHENSIVE**

### 8.1 Master Documentation

- **PRD.md** (This Document): Overall project vision and goals ✅
- **ARCHITECTURE.MD**: Technical architecture and system design ✅
- **DEVELOPER_ONBOARDING.md**: Complete setup and development guide ✅
- **DEVELOPMENT_GUIDE.md**: Coding standards and best practices ✅
- **CUSTOM_USER_ALERT.md**: Critical custom User model information ✅

### 8.2 Architecture Reference ✅ **COMPLETE**

- **entities.json**: Complete entity definitions with current implementation ✅
- **relations.json**: Model relationships mapping ✅
- **Model_Architecture_Reference.md**: Detailed model documentation ✅

### 8.3 App-Specific Documentation

**Complete PRDs Available:**
- **accounts**: [docs/features/accounts/PRD-auth.md](features/accounts/PRD-auth.md) - Authentication and user management ✅
- **review_manager**: [docs/features/review_manager/review-manager-prd.md](features/review_manager/review-manager-prd.md) - Session management and dashboard ✅  
- **search_strategy**: [docs/features/search_strategy/search-strategy-prd.md](features/search_strategy/search-strategy-prd.md) - PIC framework implementation ✅
- **serp_execution**: [docs/features/serp_execution/serp-execution-prd.md](features/serp_execution/serp-execution-prd.md) - API integration and background tasks 🚧
- **results_manager**: [docs/features/results_manager/results-manager-prd.md](features/results_manager/results-manager-prd.md) - Results processing pipeline ✅
- **review_results**: [docs/features/review_results/review-results-prd.md](features/review_results/review-results-prd.md) - Review interface and tagging 📋
- **reporting**: [docs/features/reporting/reporting-prd.md](features/reporting/reporting-prd.md) - PRISMA reports and data export 📋

### 8.4 Implementation Tracking ✅ **ACTIVE**

Detailed task tracking with sprint methodology:
- Sprint completion reports for review_manager ✅
- Task implementation tracking for search_strategy ✅
- Progress tracking for SERP execution 🚧
- QA documentation and entity relationships ✅

## 9. Conclusion

The Thesis Grey project, leveraging the robust **Django 4.2 framework**, is successfully delivering on its mission to improve the process of finding, managing, and reviewing grey literature for systematic reviews and clinical guidelines. With three core apps now production-ready and SERP execution in progress, Phase 1 has established a solid foundation with comprehensive functionality.

**✅ Major Achievements:**
- **Custom User Model:** UUID-based authentication system production-ready
- **Review Manager:** Enterprise-grade session management with 9-state workflow
- **Search Strategy:** Dynamic PIC framework with advanced query generation
- **Security:** Comprehensive security testing with 364+ tests and 95.8% coverage
- **Testing:** Production-ready test infrastructure and quality assurance
- **Documentation:** Complete architecture reference and implementation tracking

**🚧 Current Progress:**
- **SERP Execution:** Foundation models complete, API integration in progress
- **Workflow Integration:** Seamless app integration with intelligent navigation
- **Performance:** Optimized database queries and responsive user interface

**Key Success Factors Achieved:**
- ✅ Modular app architecture with clear separation of concerns
- ✅ Comprehensive documentation at both project and app levels  
- ✅ User-centered design with measurable acceptance criteria
- ✅ Performance and accessibility standards implementation
- ✅ Future-proof design for Phase 2 collaboration features
- ✅ Robust testing and quality assurance processes (364+ tests)
- ✅ Enterprise-grade security with comprehensive protection

**Next Phase:** Complete SERP execution implementation, followed by results processing and review workflow to deliver end-to-end grey literature management functionality.

This master PRD continues to serve as the single source of truth for overall project direction, with proven success in guiding the implementation of production-ready Django applications that meet the specialized needs of systematic literature review researchers.
