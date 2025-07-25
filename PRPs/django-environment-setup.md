# PRP: Django Environment Setup for Thesis Grey

## Goal
Set up the complete Django 4.2 development environment for Thesis Grey according to the PRD specifications, including project structure, database configuration, and core dependencies.

## Why
- No Django project structure currently exists in the repository
- Need to establish the foundation for all subsequent development
- PRD specifies exact technology stack and project organization
- Essential for implementing the 7 Django apps (accounts, review_manager, etc.)

## What
Create a fully configured Django 4.2 project with:
1. Modular app structure as specified in PRD
2. PostgreSQL database with Psycopg 3
3. Celery + Redis for background tasks
4. Docker configuration for development
5. Base settings structure (base, local, production)

### Success Criteria
- [ ] Django 4.2.x project initialized with correct structure
- [ ] PostgreSQL connected and migrations run
- [ ] Celery configured with Redis broker
- [ ] Docker Compose setup for all services
- [ ] Custom User model with UUID primary key
- [ ] Base templates and static files structure
- [ ] Development server runs successfully
- [ ] All tests pass

## All Needed Context

### Project Structure from PRD
- file: docs/PRD.md:46-101
  why: Exact project structure specification

### Technology Stack
- file: docs/PRD.md:29-38
  why: Core technology requirements

### Database Architecture
- file: docs/PRD.md:130-204
  why: Database schema and model requirements

### Custom User Model Requirement
- file: docs/PRD.md:187
  why: UUID-based custom User model specification

### Tech Stack Details
- file: docs/tech-stack.md:1-120
  why: Detailed rationale for technology choices

### Known Gotchas
# CRITICAL: Create custom User model BEFORE first migration
# CRITICAL: Use UUID primary keys for all models
# CRITICAL: PostgreSQL must use Psycopg 3, not Psycopg 2
# CRITICAL: Settings must be split into base/local/production
# CRITICAL: Never commit sensitive data (use .env files)

## Implementation Blueprint

### 1. Project Initialization
```bash
# Create project root
mkdir -p thesis_grey_project
cd thesis_grey_project

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Django 4.2
pip install Django==4.2.* psycopg[binary]==3.* python-decouple
```

### 2. Django Project Creation
```bash
# Create Django project
django-admin startproject grey_lit_project .

# Create apps directory
mkdir apps
touch apps/__init__.py
```

### 3. Settings Structure
```python
# grey_lit_project/settings/__init__.py
# grey_lit_project/settings/base.py - common settings
# grey_lit_project/settings/local.py - development settings
# grey_lit_project/settings/production.py - production settings
```

### 4. Create Core Apps
```bash
# Create accounts app with custom User
python manage.py startapp accounts apps/accounts

# Update INSTALLED_APPS and AUTH_USER_MODEL
```

### 5. Database Configuration
```python
# PostgreSQL with Psycopg 3
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'thesis_grey_db',
        'USER': 'thesis_grey_user',
        'PASSWORD': 'secure_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### 6. Docker Compose Setup
```yaml
version: '3.8'
services:
  db:
    image: postgres:15
  redis:
    image: redis:7
  web:
    build: .
  celery:
    build: .
```

### 7. Requirements Files
```
requirements/
├── base.txt      # Core dependencies
├── local.txt     # Development dependencies
└── production.txt # Production dependencies
```

## Validation Loop

### Level 1: Environment Check
```bash
python --version  # Should be 3.8+
pip list | grep Django  # Should show 4.2.x
```

### Level 2: Django Check
```bash
python manage.py check
python manage.py check --deploy
```

### Level 3: Database Connection
```bash
python manage.py dbshell
# Should connect to PostgreSQL
```

### Level 4: Migration Test
```bash
python manage.py makemigrations
python manage.py migrate
```

### Level 5: Server Test
```bash
python manage.py runserver
# Should start on http://127.0.0.1:8000/
```

### Level 6: Celery Test
```bash
celery -A grey_lit_project worker -l info
# Should connect to Redis
```

### Level 7: Docker Test
```bash
docker-compose up
# All services should start successfully
```