# Thesis Grey Django Project Task List

## Project Context
Thesis Grey is a Django 4.2 web application for systematically managing grey literature research, following PRISMA guidelines with automated search execution via Serper API.

## Current State Analysis

### ✅ Already Completed:
1. **Django Project Initialized** - `grey_lit_project/` exists with proper structure
2. **Custom User Model Created** - UUID-based User model in `apps/accounts/models.py` 
3. **Initial Migration Done** - `0001_initial.py` exists for accounts app
4. **Settings Structure** - Three-tier settings (base/local/production) implemented
5. **All 7 Apps Created** - accounts, review_manager, search_strategy, serp_execution, results_manager, review_results, reporting
6. **Docker Configuration** - Dockerfile and docker-compose.yml configured
7. **Requirements Files** - base.txt, local.txt with all dependencies
8. **Celery Configuration** - celery.py configured with Redis broker
9. **.env File** - Environment variables configured

### ❌ Not Yet Done:
1. **Docker Entrypoint Scripts** - Missing entrypoint.sh and start.sh
2. **Templates Directory** - Empty, needs base.html
3. **URL Configuration** - Apps not added to INSTALLED_APPS (except accounts)
4. **Static/Media Directories** - Need to be created
5. **Docker Build & Test** - Not yet built and tested
6. **Superuser Creation** - No superuser created yet

## Comprehensive Task List

### Task 1: Create Docker Entrypoint Scripts
STATUS [DONE]
CREATE .docker/django/entrypoint.sh:
  - MIRROR pattern from: Standard Django Docker setups
  - ADD PostgreSQL health check: `until pg_isready -h $DB_HOST -p $DB_PORT`
  - PRESERVE executable permissions: chmod +x
  - INJECT wait-for-postgres logic before exec "$@"

CREATE .docker/django/start.sh:
  - ADD migration command: `python manage.py migrate --noinput`
  - ADD static collection: `python manage.py collectstatic --noinput`
  - ADD server startup: `python manage.py runserver 0.0.0.0:8000`
  - PRESERVE executable permissions: chmod +x

### Task 2: Complete Django Settings Configuration
STATUS [DONE]
MODIFY grey_lit_project/settings/base.py:
  - FIND pattern: "# Local apps"
  - INJECT after "apps.accounts":
    - "apps.review_manager"
    - "apps.search_strategy"
    - "apps.serp_execution"
    - "apps.results_manager"
    - "apps.review_results"
    - "apps.reporting"
  - PRESERVE existing app order
  - VERIFY django_extensions in INSTALLED_APPS

### Task 3: Create Base Templates
STATUS [DONE]
CREATE templates/ directory:
  - EXECUTE: mkdir -p templates

CREATE templates/base.html:
  - ADD HTML5 doctype and structure
  - ADD Django template language: {% load static %}
  - INJECT blocks: title, extra_css, content, extra_js
  - MIRROR pattern from: Standard Django base templates
  - ADD Bootstrap 5 CDN for styling

### Task 4: Create Static and Media Directories
STATUS [DONE]
CREATE directories:
  - EXECUTE: mkdir -p static
  - EXECUTE: mkdir -p media
  - VERIFY paths match settings: STATIC_ROOT and MEDIA_ROOT

MODIFY .gitignore (if exists):
  - ADD /static/ to ignore collected static files
  - ADD /media/ to ignore uploaded files
  - PRESERVE existing ignore patterns

### Task 5: Update App Configurations
STATUS [DONE]
MODIFY apps/review_manager/apps.py:
  - FIND pattern: "name = 'review_manager'"
  - REPLACE with: "name = 'apps.review_manager'"

MODIFY apps/search_strategy/apps.py:
  - FIND pattern: "name = 'search_strategy'"
  - REPLACE with: "name = 'apps.search_strategy'"

MODIFY apps/serp_execution/apps.py:
  - FIND pattern: "name = 'serp_execution'"
  - REPLACE with: "name = 'apps.serp_execution'"

MODIFY apps/results_manager/apps.py:
  - FIND pattern: "name = 'results_manager'"
  - REPLACE with: "name = 'apps.results_manager'"

MODIFY apps/review_results/apps.py:
  - FIND pattern: "name = 'review_results'"
  - REPLACE with: "name = 'apps.review_results'"

MODIFY apps/reporting/apps.py:
  - FIND pattern: "name = 'reporting'"
  - REPLACE with: "name = 'apps.reporting'"

### Task 6: Configure URLs
STATUS [DONE]
MODIFY grey_lit_project/urls.py:
  - FIND pattern: "urlpatterns = ["
  - INJECT admin import: from django.contrib import admin
  - INJECT static imports: from django.conf import settings
  - INJECT static imports: from django.conf.urls.static import static
  - ADD admin path: path('admin/', admin.site.urls)
  - ADD static file serving for development

### Task 7: Build and Test Docker Environment
STATUS [DONE]
EXECUTE docker-compose build:
  - VERIFY all images build successfully
  - CHECK for any missing dependencies
  - MONITOR build output for errors

EXECUTE docker-compose up -d:
  - VERIFY all 7 services start
  - CHECK health status: docker-compose ps
  - MONITOR logs: docker-compose logs

### Task 8: Run Database Migrations
STATUS [DONE]
EXECUTE migrations:
  - RUN: docker-compose exec web python manage.py showmigrations
  - RUN: docker-compose exec web python manage.py migrate
  - VERIFY all migrations applied
  - CHECK database tables created

### Task 9: Create Superuser
STATUS [DONE]
EXECUTE superuser creation:
  - RUN: docker-compose exec web python manage.py createsuperuser
  - SET username: admin
  - SET email: admin@thesisgrey.local
  - SET password: (secure password)
  - TEST login at http://localhost:8000/admin/

### Task 10: Validate Complete Setup
STATUS [DONE]
RUN validation checks:
  - EXECUTE: docker-compose exec web python manage.py check --deploy
  - TEST Celery: docker-compose exec web python manage.py shell
    - from celery import current_app
    - current_app.send_task('grey_lit_project.celery.debug_task')
  - VERIFY Flower at http://localhost:5555/
  - CHECK static files served correctly
  - TEST Redis connection
  - VERIFY all apps loaded in Django admin

## Unit Test Coverage Requirements

Each task should include tests:
- Task 1: Test entrypoint scripts handle PostgreSQL connection
- Task 2: Test all apps are importable
- Task 3: Test template renders without errors
- Task 7: Test all Docker services are accessible
- Task 8: Test database connections and migrations
- Task 10: Test all validation checks pass

## Success Criteria

- [X] All Docker services running and healthy
- [X] Django admin accessible with custom User model
- [X] All 7 apps registered and visible in admin
- [X] Celery processes tasks successfully
- [X] Static files served correctly
- [X] No Django check warnings or errors
- [ ] All unit tests pass (to be implemented)