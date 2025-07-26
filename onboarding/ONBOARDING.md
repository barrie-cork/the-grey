# Thesis Grey - Developer Onboarding Guide

Welcome to **Thesis Grey**, a Django-based web application for systematic grey literature review! This guide will help you get up and running as a new developer on the project.

## 1. Project Overview

### What is Thesis Grey?
Thesis Grey is a specialized web application designed to help researchers systematically find, manage, and review "grey literature" – research found outside traditional academic databases (reports, theses, conference proceedings). It follows PRISMA guidelines and automates search execution through Google Search API via Serper.

### Core Functionality
- **9-State Workflow Management**: Systematic progression from draft to completion
- **PIC Framework**: Population, Interest, Context-based search query builder  
- **Automated Search Execution**: Serper API integration with Celery task management
- **Result Deduplication**: Intelligent duplicate detection and grouping
- **PRISMA Compliance**: Export reports following systematic review standards
- **Collaborative Review**: Tagging system and review comments

### Tech Stack
- **Backend**: Django 4.2 LTS with PostgreSQL 15
- **Task Queue**: Celery with Redis broker
- **Cache**: Redis
- **Web Server**: Nginx (reverse proxy)
- **Container**: Docker with Docker Compose
- **Frontend**: Django Templates, HTML, CSS, JavaScript (AJAX)
- **Testing**: Django TestCase with 364+ tests and 95.8% coverage

### Architecture Pattern
The project follows **Vertical Slice Architecture** using Django's modular app structure. Each feature is implemented end-to-end within its own Django app, promoting separation of concerns and maintainability.

### Key Dependencies
- **Django 4.2.11**: Web framework with custom User model
- **PostgreSQL**: Database with UUID primary keys throughout
- **Redis**: Caching and Celery message broker
- **Celery 5.5.3**: Background task processing for API calls
- **djangorestframework**: API development
- **requests/httpx**: Serper API integration

## 2. Repository Structure

```
agent-grey/
├── manage.py                   # Django management script
├── grey_lit_project/          # Main Django project configuration
│   ├── settings/              # Three-tier settings (base, local, production)
│   ├── urls.py               # Project-level URL routing
│   ├── celery.py             # Celery configuration
│   └── wsgi.py/asgi.py       # WSGI/ASGI entry points
├── apps/                      # Modular Django applications
│   ├── accounts/             # ✅ Custom User model (UUID-based)
│   ├── core/                 # Shared utilities (logging, mixins)
│   ├── review_manager/       # ✅ Session workflow management
│   ├── search_strategy/      # ✅ PIC framework search builder
│   ├── serp_execution/       # 🚧 API integration & background tasks
│   ├── results_manager/      # ✅ Result processing pipeline (90%)
│   ├── review_results/       # 📋 Manual review interface
│   └── reporting/           # 📋 PRISMA-compliant exports
├── templates/                # Global Django templates
├── static/                   # Project-wide static files
├── staticfiles/              # Collected static files for production
├── docs/                     # Comprehensive documentation
│   ├── PRD.md               # Master project requirements
│   └── features/            # App-specific PRDs
├── PRPs/                     # Product Requirement Prompts (AI development)
├── requirements/             # Python dependencies (base, local, production)
├── docker-compose.yml        # Multi-container Docker setup
├── .env.example             # Environment variables template
└── logs/                    # Application logs
```

### Code Organization by Type
- **Models**: Each app's `models.py` file
- **Views**: Each app's `views.py` file (Class-Based Views primarily)
- **Business Logic**: Each app's `services/` directory
- **Tests**: Each app's `tests/` directory or `tests.py` file
- **Templates**: Each app's `templates/{app_name}/` directory
- **Static Files**: Each app's `static/{app_name}/` directory
- **URL Routing**: Each app's `urls.py` file

### Unique Organizational Patterns
- **Service Layer Pattern**: Business logic separated into `services/` directories using `ServiceLoggerMixin`
- **UUID Architecture**: All models use UUID primary keys instead of auto-incrementing integers
- **PRP System**: Product Requirement Prompts for AI-assisted development
- **Three-tier Settings**: Base, local, and production configurations

## 3. Getting Started

### Prerequisites
- **Docker & Docker Compose**: For containerized development
- **Git**: Version control
- **Python 3.12+**: For local development (optional if using Docker)
- **VS Code or PyCharm**: Recommended IDEs

### Quick Setup (Docker - Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/thesis-grey.git
   cd thesis-grey
   ```

2. **Create environment file**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start Docker services**:
   ```bash
   docker-compose up -d
   ```

4. **Run migrations**:
   ```bash
   docker-compose run --rm web python manage.py migrate
   ```

5. **Create superuser**:
   ```bash
   docker-compose run --rm web python manage.py createsuperuser
   ```

6. **Access the application**:
   - Application: http://localhost:8000/
   - Django Admin: http://localhost:8000/admin/
   - Flower (Celery): http://localhost:5555/

### Local Development Setup (Alternative)

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements/local.txt
   ```

3. **Set up database** (requires PostgreSQL running):
   ```bash
   python manage.py migrate
   ```

4. **Run development server**:
   ```bash
   python manage.py runserver
   ```

### Running Tests
```bash
# All tests
python manage.py test

# Specific app
python manage.py test apps.accounts

# With coverage
coverage run --source='.' manage.py test
coverage report
```

### Code Quality Checks
```bash
# PEP 8 compliance
flake8 apps/ --max-line-length=120

# Type checking
mypy apps/

# Security checks
python manage.py check --deploy
```

## 4. Key Components

### Entry Points
- **`manage.py`**: Django's command-line utility
- **`grey_lit_project/urls.py`**: Main URL configuration
- **`grey_lit_project/wsgi.py`**: Production WSGI entry point
- **`grey_lit_project/celery.py`**: Celery task configuration

### Core Business Logic Locations
- **Session Management**: `apps/review_manager/models.py` (SearchSession model)
- **Search Strategy**: `apps/search_strategy/models.py` (PIC framework)
- **Result Processing**: `apps/results_manager/services/` (deduplication, metadata extraction)
- **API Integration**: `apps/serp_execution/services/serper_client.py`

### Database Models (Key)
- **`apps/accounts/models.py`**: Custom User model with UUID primary key
- **`apps/review_manager/models.py`**: SearchSession (core entity) with 9-state workflow
- **`apps/results_manager/models.py`**: ProcessedResult, DuplicateGroup, ProcessingSession
- **`apps/review_results/models.py`**: ReviewDecision, ReviewTagAssignment, ReviewTag

### API Endpoints/Routes
- **Session Management**: `apps/review_manager/urls.py`
- **AJAX APIs**: Each app's `api.py` or `views.py` with AJAX decorators
- **REST Framework**: `apps/review_manager/api/` (where implemented)

### Configuration Management
- **Settings**: `grey_lit_project/settings/` (base.py, local.py, production.py)
- **Environment**: `.env` file with `python-decouple`
- **Celery**: `grey_lit_project/celery.py`
- **Docker**: `docker-compose.yml` and `.docker/` directory

### Authentication/Authorization
- **Custom User Model**: `apps/accounts/models.py`
- **Views**: `apps/accounts/views.py` (login, signup, profile)
- **Mixins**: `apps/review_manager/mixins.py` (UserOwnerMixin, SessionNavigationMixin)
- **Security Decorators**: `@login_required`, `@require_http_methods` patterns

## 5. Development Workflow

### Git Branch Naming Conventions
- **Feature branches**: `feature/description-of-feature`
- **Bug fixes**: `bugfix/description-of-fix`
- **Hot fixes**: `hotfix/description-of-fix`
- **Current main branch**: `feature/major-refactor-api-tests`

### Creating a New Feature
1. Create feature branch from main
2. Implement following Django best practices
3. Add comprehensive tests (aim for 90%+ coverage)
4. Update relevant documentation
5. Run code quality checks
6. Create pull request

### Testing Requirements
- **Minimum 90% test coverage** for new features
- **Unit tests** for models, views, forms
- **Integration tests** for complete workflows
- **Security tests** for authentication/authorization
- Use Django's TestCase and factory patterns

### Code Style/Linting Rules
- **PEP 8 compliance** with 120 character line limit
- **Type hints** where beneficial
- **Comprehensive docstrings** for classes and methods
- **Meaningful variable names**
- **No commented-out code** in commits

### PR Process and Review Guidelines
- All PRs require review
- Must pass all tests and quality checks
- Update documentation if needed
- Follow established patterns from existing code

### CI/CD Pipeline
- Currently configured for Docker-based deployment
- GitHub Actions ready for implementation
- Automated testing on PR creation

## 6. Architecture Decisions

### Design Patterns Used
- **Service Layer Pattern**: Business logic in `services/` with `ServiceLoggerMixin`
- **Repository Pattern**: Custom model managers for complex queries
- **Decorator Pattern**: AJAX views with `@login_required`, `@require_http_methods`
- **Strategy Pattern**: Different processing strategies for result deduplication

### State Management Approach
- **9-State Workflow**: SearchSession progresses through defined states
- **Transition Validation**: Only allowed transitions between states
- **Audit Logging**: SessionActivity tracks all state changes

### Error Handling Strategy
- **Comprehensive logging** with request ID tracking
- **Graceful degradation** for external API failures
- **Retry mechanisms** for background tasks
- **User-friendly error messages** in templates

### Logging and Monitoring
- **Structured logging** with JSON format
- **Request ID tracking** across all components
- **Rotating log files** (app.log, errors.log)
- **Celery monitoring** via Flower

### Security Measures
- **UUID primary keys** prevent enumeration attacks
- **CSRF protection** on all forms
- **XSS prevention** in templates
- **SQL injection prevention** through Django ORM
- **Rate limiting** implemented
- **Security headers** configured

### Performance Optimizations
- **Database indexes** on frequently queried fields
- **select_related/prefetch_related** for query optimization
- **Redis caching** for expensive operations
- **Pagination** for large result sets (25 items default)
- **Batch processing** for bulk operations (50 items per batch)

## 7. Common Tasks

### How to Add a New API Endpoint

1. **Create the view** (example in `apps/review_results/views.py`):
   ```python
   from django.contrib.auth.decorators import login_required
   from django.views.decorators.http import require_http_methods
   from django.http import JsonResponse

   @login_required
   @require_http_methods(["POST"])
   def your_api_endpoint(request, result_id: str) -> JsonResponse:
       try:
           # Your logic here
           return JsonResponse({'success': True})
       except Exception as e:
           logger.error(f"Error in endpoint: {str(e)}")
           return JsonResponse({'error': 'Internal server error'}, status=500)
   ```

2. **Add URL pattern** in the app's `urls.py`:
   ```python
   path('api/your-endpoint/<uuid:result_id>/', views.your_api_endpoint, name='your_api_endpoint'),
   ```

3. **Add tests** in `tests/test_views.py`:
   ```python
   def test_your_api_endpoint(self):
       response = self.client.post(f'/api/your-endpoint/{self.result.id}/')
       self.assertEqual(response.status_code, 200)
   ```

### How to Create a New Database Model

1. **Define the model** in the app's `models.py`:
   ```python
   import uuid
   from django.db import models

   class YourModel(models.Model):
       id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
       name = models.CharField(max_length=255)
       created_at = models.DateTimeField(auto_now_add=True)
       updated_at = models.DateTimeField(auto_now=True)

       class Meta:
           db_table = 'your_table_name'
           ordering = ['-created_at']
   ```

2. **Create and apply migration**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. **Add to admin** (optional) in `admin.py`:
   ```python
   from django.contrib import admin
   from .models import YourModel

   @admin.register(YourModel)
   class YourModelAdmin(admin.ModelAdmin):
       list_display = ['name', 'created_at']
   ```

### How to Add a New Test

1. **Unit test** in the app's `tests/test_models.py`:
   ```python
   from django.test import TestCase
   from .models import YourModel

   class YourModelTest(TestCase):
       def test_model_creation(self):
           obj = YourModel.objects.create(name="Test")
           self.assertEqual(obj.name, "Test")
   ```

2. **View test** in `tests/test_views.py`:
   ```python
   from django.test import TestCase, Client
   from django.contrib.auth import get_user_model

   User = get_user_model()

   class YourViewTest(TestCase):
       def setUp(self):
           self.client = Client()
           self.user = User.objects.create_user(
               username='testuser',
               password='testpass'
           )

       def test_view_requires_login(self):
           response = self.client.get('/your-url/')
           self.assertEqual(response.status_code, 302)  # Redirect to login
   ```

### How to Debug Common Issues

1. **Check Docker logs**:
   ```bash
   docker-compose logs -f web
   docker-compose logs -f celery_worker
   ```

2. **Access Django shell**:
   ```bash
   docker-compose run --rm web python manage.py shell
   ```

3. **Check database**:
   ```bash
   docker-compose run --rm web python manage.py dbshell
   ```

4. **Review application logs**:
   ```bash
   tail -f logs/app.log
   tail -f logs/errors.log
   ```

### How to Update Dependencies

1. **Update requirements file** (`requirements/base.txt`, `local.txt`, or `production.txt`)

2. **Rebuild Docker containers**:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

3. **For local development**:
   ```bash
   pip install -r requirements/local.txt
   ```

## 8. Potential Gotchas

### Non-obvious Configurations
- **Custom User Model**: Uses UUID primary keys, not auto-incrementing integers
- **Three-tier Settings**: Different settings for base/local/production
- **Celery Tasks**: Must be defined in each app's `tasks.py` file
- **Static Files**: Use `python manage.py collectstatic` for production

### Required Environment Variables
Create `.env` file with these critical variables:
```bash
SECRET_KEY=your-secret-key
POSTGRES_DB=thesis_grey_db
POSTGRES_USER=thesis_grey_user
POSTGRES_PASSWORD=secure_password
SERPER_API_KEY=your-serper-api-key
```

### External Service Dependencies
- **Serper API**: Required for search execution functionality
- **PostgreSQL**: Cannot use SQLite due to advanced features used
- **Redis**: Required for Celery and caching

### Known Issues or Workarounds
- **UUID Fields**: Always use `str(obj.id)` when passing UUIDs to templates or APIs
- **Migration Dependencies**: Custom User model must be created before other app migrations
- **Docker Volumes**: May need to reset volumes if database schema changes significantly

### Performance Bottlenecks
- **Large Result Sets**: Use pagination and batch processing
- **Complex Queries**: Always use `select_related()` and `prefetch_related()`
- **API Rate Limits**: Serper API has usage limits that must be respected

### Areas of Technical Debt
- **SERP Execution**: API integration still in progress
- **Review Results**: Manual review interface not yet implemented
- **Reporting**: PRISMA export functionality planned
- **Test Coverage**: Some areas below 90% coverage target

## 9. Documentation and Resources

### Existing Documentation
- **`README.md`**: Project overview and quick start guide
- **`CLAUDE.md`**: Development guidance and project architecture
- **`docs/PRD.md`**: Master project requirements document (697 lines)
- **`docs/features/`**: App-specific Product Requirement Documents
- **`PRPs/`**: Product Requirement Prompts for AI-assisted development

### API Documentation
- **Django Admin**: http://localhost:8000/admin/ (browse models and data)
- **API Endpoints**: Documented in each app's `views.py` and `api.py`
- **REST Framework**: http://localhost:8000/api/ (when DRF views are available)

### Database Schemas
- **Model Definitions**: Each app's `models.py` file
- **Relationships**: Documented in `docs/features/` PRDs
- **Migrations**: Each app's `migrations/` directory

### Deployment Guides
- **Docker Setup**: `docker-compose.yml` and `.docker/` directory
- **Production Settings**: `grey_lit_project/settings/production.py`
- **Environment Configuration**: `.env.example`

### Team Conventions
- **Code Style**: PEP 8 with 120 character line limit
- **Testing**: Django TestCase with 90%+ coverage requirement
- **Documentation**: Comprehensive docstrings and comments
- **Git**: Feature branch workflow with descriptive commit messages

## 10. Next Steps - Onboarding Checklist

### Initial Setup ✅
- [ ] Clone the repository
- [ ] Set up Docker environment
- [ ] Create `.env` file from template
- [ ] Start Docker services (`docker-compose up -d`)
- [ ] Run migrations
- [ ] Create superuser account
- [ ] Access application at http://localhost:8000/

### Verification ✅
- [ ] Log into Django admin
- [ ] Create a test SearchSession
- [ ] Run the test suite (`python manage.py test`)
- [ ] Check Celery is running (visit http://localhost:5555/)
- [ ] Review logs for any errors

### Code Exploration 🔍
- [ ] Read through `docs/PRD.md` for project understanding
- [ ] Explore the `apps/` directory structure
- [ ] Examine `apps/accounts/models.py` for User model
- [ ] Review `apps/review_manager/` for workflow implementation
- [ ] Look at `apps/results_manager/services/` for business logic patterns

### Make Your First Change 🛠️
- [ ] Create a new feature branch
- [ ] Add a simple test to an existing test suite
- [ ] Run tests to ensure they pass
- [ ] Make a small UI change (e.g., update a template)
- [ ] Commit and push your changes

### Understand the Main User Flow 📋
- [ ] Create a SearchSession through the UI
- [ ] Define a search strategy using PIC framework
- [ ] Understand the 9-state workflow progression
- [ ] Explore the dashboard and session management
- [ ] Review the intended flow from search → results → review

### Choose Your First Contribution Area 🎯
Based on current implementation status:
- **Frontend/UI**: Improve existing templates and JavaScript
- **API Integration**: Help complete SERP execution functionality  
- **Review Interface**: Implement the review_results app
- **Testing**: Add tests to increase coverage
- **Documentation**: Improve existing docs or add new ones
- **Performance**: Optimize database queries or caching

### Get Help 🤝
- Review existing code patterns before implementing new features
- Check the `PRPs/` directory for implementation guidance
- Use the Django admin to understand data relationships
- Ask questions about architectural decisions in the team chat
- Pair program with existing team members on complex features

---

## Welcome to the Team! 🎉

You're now ready to contribute to Thesis Grey. The project follows Django best practices with a focus on systematic literature review workflows. Start with small changes to get familiar with the codebase, then gradually take on larger features.

Remember: When in doubt, follow the established patterns you see in the existing code, and don't hesitate to ask questions!