name: "Django 4.2 Project Initialization with Custom User Model"
description: |

## Purpose

Initialize the Thesis Grey Django 4.2 project with a production-ready structure, custom User model with UUID primary keys, Docker environment, and all foundational components required before any feature development can begin.

## Core Principles

1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance

---

## Goal

Initialize a Django 4.2 project named "grey_lit_project" with:
- Custom User model with UUID primary keys (CRITICAL: before first migration)
- Three-tier settings structure (base/local/production)
- Docker environment with 7 services
- PostgreSQL 15 with Psycopg 3
- Redis 7 for caching and Celery broker
- Celery 5.3 for background tasks
- Modular app structure following vertical slice architecture
- All security best practices enabled

## Why

- **Foundation First**: Cannot create any Django apps without the project initialized
- **Custom User Critical**: Changing User model after migrations is extremely complex
- **Docker Consistency**: Ensures all developers work in identical environments
- **Production Ready**: Starting with proper structure prevents technical debt
- **WSL Performance**: Proper setup ensures 20x better performance on Windows

## What

Initialize a complete Django project environment that:
- Creates the base Django project structure
- Implements custom User model with UUID before any migrations
- Configures Docker services for development
- Sets up three-tier settings (base/local/production)
- Establishes the app directory structure
- Configures static/media file handling
- Implements security best practices

### Success Criteria

- [ ] Django project created with proper structure
- [ ] Custom User model with UUID implemented
- [ ] All Docker services start successfully
- [ ] Database migrations run without errors
- [ ] Admin interface accessible
- [ ] Celery worker processes tasks
- [ ] All security checks pass

## All Needed Context

### Documentation & References

```yaml
# MUST READ - Include these in your context window
- url: https://docs.djangoproject.com/en/4.2/topics/auth/customizing/#substituting-a-custom-user-model
  why: Critical instructions for custom User model implementation

- url: https://docs.djangoproject.com/en/4.2/ref/settings/#auth-user-model
  why: AUTH_USER_MODEL setting configuration

- url: https://docs.docker.com/desktop/features/wsl/best-practices/
  why: WSL2 performance optimization for Docker volumes

- file: /mnt/d/Python/Projects/django/HTA-projects/agent-grey/docs/PRD.md
  why: Project requirements and User model specifications

- file: /mnt/d/Python/Projects/django/HTA-projects/agent-grey/docs/auth/PRD-auth.md
  why: Detailed User model requirements with UUID

- file: /mnt/d/Python/Projects/django/HTA-projects/agent-grey/docker-compose.yml
  why: Existing Docker configuration to integrate with

- file: /mnt/d/Python/Projects/django/HTA-projects/agent-grey/.env.example
  why: Environment variables template

- docfile: /mnt/d/Python/Projects/django/HTA-projects/agent-grey/PRPs/research/django-4.2-docker-wsl-research.md
  why: WSL2 and Docker best practices research
```

### Current Codebase State

```bash
# Project has Docker configuration but no Django project yet
/agent-grey/
├── docker-compose.yml      # 7 services configured
├── .env.example           # Environment template
├── requirements/          # Empty requirements structure
│   ├── base.txt
│   ├── local.txt
│   └── production.txt
├── docs/                  # Comprehensive documentation
└── PRPs/                  # Project requirement prompts
```

### Desired Codebase Structure

```bash
/agent-grey/
├── manage.py                    # Django management script
├── grey_lit_project/           # Main project package
│   ├── __init__.py
│   ├── settings/               # Three-tier settings
│   │   ├── __init__.py
│   │   ├── base.py            # Common settings
│   │   ├── local.py           # Development settings
│   │   └── production.py      # Production settings
│   ├── urls.py                # Root URL configuration
│   ├── wsgi.py               # WSGI entry point
│   ├── asgi.py               # ASGI entry point
│   └── celery.py             # Celery configuration
├── apps/                      # All Django apps directory
│   ├── __init__.py
│   └── accounts/             # Custom User app (FIRST APP)
│       ├── __init__.py
│       ├── models.py         # Custom User model
│       ├── admin.py          # User admin config
│       ├── apps.py           # App configuration
│       └── migrations/       # Will contain 0001_initial.py
├── static/                   # Static files root
├── media/                    # Media files root
├── templates/                # Project-wide templates
│   └── base.html            # Base template
├── .docker/                  # Docker configuration
│   ├── django/
│   │   ├── Dockerfile       # Django container
│   │   ├── entrypoint.sh    # Container entrypoint
│   │   └── start.sh         # Development server start
│   └── nginx/
│       └── default.conf     # Nginx configuration
└── requirements/            # Updated with dependencies
    ├── base.txt            # Core dependencies
    ├── local.txt           # Dev dependencies
    └── production.txt      # Prod dependencies
```

### Known Gotchas & Critical Requirements

```python
# CRITICAL: Custom User model MUST be created before ANY migrations
# Once you run migrations with default User, changing is extremely difficult

# CRITICAL: In WSL2, project MUST be in Linux filesystem for performance
# BAD:  /mnt/c/Users/... (Windows filesystem - 20x slower)
# GOOD: ~/projects/... (Linux filesystem - full speed)

# CRITICAL: AUTH_USER_MODEL must be set before first migration
# This cannot be changed after database tables are created

# Docker health checks prevent race conditions
# PostgreSQL must be healthy before Django starts

# Django 4.2 requires Python 3.8+ (we use 3.11)
# Psycopg 3 is the new adapter (not psycopg2)
```

## Implementation Blueprint

### Data Models and Structure

```python
# apps/accounts/models.py - Custom User Model
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Custom User model with UUID primary key.
    Extends Django's AbstractUser to maintain all built-in functionality.
    """
    id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        db_comment="UUID primary key for distributed system compatibility"
    )
    
    # Email as unique field (AbstractUser has it non-unique by default)
    email = models.EmailField(
        unique=True, 
        null=True, 
        blank=True,
        db_comment="Unique email address for user identification"
    )
    
    # Timestamps following project naming convention
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_comment="Timestamp when user account was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        db_comment="Timestamp when user account was last modified"
    )
    
    class Meta:
        db_table = 'accounts_user'
        db_table_comment = "User accounts for Thesis Grey researchers"
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return self.username
```

### List of Tasks to Complete

```yaml
Task 1: Create Requirements Files
CREATE requirements/base.txt:
  - Django==4.2.11
  - psycopg[binary]==3.1.18
  - redis==5.0.1
  - celery==5.3.6
  - django-environ==0.11.2
  - Pillow==10.2.0  # For ImageField support
  - django-extensions==3.2.3

CREATE requirements/local.txt:
  - -r base.txt
  - django-debug-toolbar==4.2.0
  - ipython==8.20.0
  - Werkzeug==3.0.1  # Better error pages

CREATE requirements/production.txt:
  - -r base.txt
  - gunicorn==21.2.0
  - sentry-sdk==1.40.0  # Error tracking
  - django-storages[boto3]==1.14.2  # AWS S3 support

Task 2: Create Docker Configuration
CREATE .docker/django/Dockerfile:
  - FROM python:3.11-slim
  - Install system dependencies
  - Copy requirements and install
  - Set working directory to /app
  - Copy entrypoint and start scripts

CREATE .docker/django/entrypoint.sh:
  - Wait for PostgreSQL to be healthy
  - Execute passed command

CREATE .docker/django/start.sh:
  - Run database migrations
  - Collect static files
  - Start Django development server

CREATE .docker/nginx/default.conf:
  - Proxy pass to Django app
  - Serve static and media files
  - Gzip compression enabled

Task 3: Initialize Django Project
RUN: django-admin startproject grey_lit_project .
  - Creates manage.py at root level
  - Creates grey_lit_project package
  - IMPORTANT: Use . to create at current directory

Task 4: Create Settings Structure
MOVE grey_lit_project/settings.py TO grey_lit_project/settings/base.py
CREATE grey_lit_project/settings/__init__.py:
  - Import appropriate settings based on environment

MODIFY grey_lit_project/settings/base.py:
  - Add custom User model setting
  - Configure apps directory
  - Set up static/media paths
  - Configure allowed hosts
  - Add security settings

CREATE grey_lit_project/settings/local.py:
  - Import from .base
  - DEBUG = True
  - Development database settings
  - Django Debug Toolbar configuration

CREATE grey_lit_project/settings/production.py:
  - Import from .base
  - DEBUG = False
  - Production security settings
  - Production database from environment

Task 5: Create Custom User App
CREATE apps/__init__.py:
  - Empty file to make it a package

RUN: python manage.py startapp accounts apps/accounts
  - Creates accounts app in apps directory
  - CRITICAL: Must be done before any migrations

MODIFY apps/accounts/models.py:
  - Implement custom User model with UUID
  - Add Meta class with db_table

MODIFY apps/accounts/apps.py:
  - Update name to 'apps.accounts'

MODIFY apps/accounts/admin.py:
  - Register User model with UserAdmin

Task 6: Configure Celery
CREATE grey_lit_project/celery.py:
  - Celery app configuration
  - Autodiscover tasks
  - Configure Redis broker

MODIFY grey_lit_project/__init__.py:
  - Import celery app
  - Set default Django settings module

Task 7: Create Initial Templates
CREATE templates/base.html:
  - Basic HTML5 structure
  - Django template blocks
  - Static files loading

Task 8: Update Project Configuration
MODIFY grey_lit_project/urls.py:
  - Add admin URLs
  - Add static/media file serving for development
  - Include apps.accounts URLs when created

MODIFY grey_lit_project/settings/base.py:
  - Add 'apps.accounts' to INSTALLED_APPS
  - Set AUTH_USER_MODEL = 'accounts.User'
  - Configure TEMPLATES to find project templates
  - Set up STATICFILES_DIRS and STATIC_ROOT

Task 9: Run Initial Migrations
RUN: python manage.py makemigrations
  - Creates initial migration for custom User

RUN: python manage.py migrate
  - Creates all database tables
  - CRITICAL: User model is now locked in

Task 10: Create Superuser and Verify
RUN: python manage.py createsuperuser
  - Test custom User model works
  - Verify UUID primary key
```

### Integration Points

```yaml
DATABASE:
  - PostgreSQL connection via DATABASE_URL
  - Custom User model with UUID primary keys
  - db_table names follow pattern: {app_name}_{model_name}

DOCKER:
  - Dockerfile references in docker-compose.yml
  - Volume mounts for code hot-reloading
  - Health checks for service dependencies

SETTINGS:
  - DJANGO_SETTINGS_MODULE environment variable
  - Split settings for different environments
  - Environment variables via django-environ

CELERY:
  - Import in __init__.py
  - Redis connection configuration
  - Task autodiscovery in apps
```

## Validation Loop

### Level 1: Syntax & Style

```bash
# Check Python syntax
python -m py_compile grey_lit_project/settings/base.py
python -m py_compile apps/accounts/models.py

# Django checks
python manage.py check --deploy --settings=grey_lit_project.settings.local

# Expected: System check identified no issues (0 silenced)
```

### Level 2: Docker Services

```bash
# Build and start all services
docker-compose build
docker-compose up -d

# Verify all services are running
docker-compose ps

# Expected: All services show "Up" status
# Check health status
docker-compose ps | grep -E "(healthy|starting)"

# Expected: db and redis show (healthy)
```

### Level 3: Django Functionality

```bash
# Run migrations
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate

# Expected: 
# - Creates migration for accounts.User
# - Applies all migrations successfully

# Create test superuser
docker-compose exec web python manage.py createsuperuser --username admin --email admin@example.com

# Access admin interface
curl -I http://localhost:8000/admin/

# Expected: HTTP 302 redirect to login page
```

### Level 4: Celery Verification

```bash
# Send test task
docker-compose exec web python manage.py shell
>>> from celery import current_app
>>> current_app.send_task('debug_task')
>>> exit()

# Check Celery logs
docker-compose logs celery_worker | grep "debug_task"

# Expected: Task received and executed

# Check Flower monitoring
curl http://localhost:5555/

# Expected: Flower dashboard accessible
```

### Level 5: Database Verification

```bash
# Verify custom User model
docker-compose exec web python manage.py shell
>>> from apps.accounts.models import User
>>> user = User.objects.first()
>>> print(f"User ID type: {type(user.id)}")
>>> print(f"User ID: {user.id}")
>>> import uuid
>>> assert isinstance(user.id, uuid.UUID)
>>> exit()

# Expected: User ID is UUID type
```

### Level 6: Security Validation

```bash
# Run Django security checks
docker-compose exec web python manage.py check --deploy --settings=grey_lit_project.settings.production

# Expected: Some warnings for local development, but no critical issues

# Verify CSRF protection
curl -X POST http://localhost:8000/admin/login/ -d "username=test&password=test"

# Expected: 403 Forbidden (CSRF token required)
```

## Final Validation Checklist

- [ ] All requirements installed: `pip freeze | grep Django`
- [ ] Docker services running: `docker-compose ps`
- [ ] Custom User model created: Check accounts_user table exists
- [ ] Migrations successful: No pending migrations
- [ ] Admin interface accessible: http://localhost:8000/admin/
- [ ] Static files served: CSS loads on admin interface  
- [ ] Celery processes tasks: Check worker logs
- [ ] PostgreSQL stores data: Users persist after container restart
- [ ] Redis caches data: Check with redis-cli
- [ ] Settings structure correct: local.py imports from base.py
- [ ] Security checks pass: No critical issues in production settings
- [ ] Project structure follows plan: Apps in apps/ directory

---

## Anti-Patterns to Avoid

- ❌ Don't run migrate before creating custom User model
- ❌ Don't skip PostgreSQL health checks in Docker
- ❌ Don't store code in Windows filesystem (/mnt/c/)
- ❌ Don't use psycopg2 - use psycopg (v3)
- ❌ Don't hardcode sensitive values in settings
- ❌ Don't forget to set AUTH_USER_MODEL before migrations
- ❌ Don't create apps outside the apps/ directory
- ❌ Don't skip setting DJANGO_SETTINGS_MODULE

## Troubleshooting Guide

### Common Issues and Solutions

1. **"auth.User has been swapped for 'accounts.User'"**
   - Ensure AUTH_USER_MODEL is set before first migration
   - If migrations exist, must reset database

2. **"ModuleNotFoundError: No module named 'apps'"**
   - Add apps directory to Python path in settings
   - Ensure __init__.py exists in apps/

3. **"psycopg2.OperationalError: FATAL: password authentication failed"**
   - Check .env file has correct database credentials
   - Ensure docker-compose.yml uses same env vars

4. **Slow file system performance on Windows**
   - Move project to WSL2 filesystem
   - Use: \\wsl$\Ubuntu\home\{user}\projects\

5. **"Connection refused" to Redis/PostgreSQL**
   - Check service health: `docker-compose ps`
   - Ensure services are on same network
   - Verify connection strings use service names

## Success Indicators

When implementation is complete, you should see:
1. Django admin interface with custom User model at http://localhost:8000/admin/
2. UUID values in the User ID field (not integers)
3. All Docker services showing "Up" and "healthy" status
4. Successful Celery task execution in worker logs
5. Static files (CSS/JS) loading correctly in admin interface
6. No errors when running `python manage.py check --deploy`

## Next Steps After Completion

Once this PRP is successfully implemented:
1. Commit the initial project structure
2. Document any deviations from the plan
3. Proceed with implementing the first feature app (review_manager)
4. Ensure all developers clone into WSL2 filesystem
5. Share .env file securely with team members