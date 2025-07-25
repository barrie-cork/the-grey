# Django Setup Resume Checklist

## Pre-Flight Checks Before Resuming

### 1. Environment Verification
- [ ] Confirm working directory: `/mnt/d/Python/Projects/django/HTA-projects/agent-grey/`
- [ ] Verify Docker Desktop is running (Windows/Mac)
- [ ] Ensure WSL2 is active (Windows)
- [ ] Check Docker service: `docker --version`
- [ ] Verify docker-compose: `docker-compose --version`

### 2. File System Check
- [ ] Verify `.env` file exists (copy from `.env.example` if missing)
- [ ] Check Docker files exist:
  - [ ] `docker-compose.yml`
  - [ ] `.docker/django/Dockerfile`
  - [ ] `.docker/nginx/default.conf`
- [ ] Confirm requirements files:
  - [ ] `requirements/base.txt`
  - [ ] `requirements/local.txt`
  - [ ] `requirements/production.txt`

### 3. Current State Verification
- [ ] Check if `manage.py` exists (NO = good, need to create project)
- [ ] Check if `grey_lit_project/` directory exists (NO = good)
- [ ] Check if `apps/` directory exists (NO = good)
- [ ] Verify no migrations exist yet

## Critical Warnings Reminder

### ⚠️ MUST DO BEFORE FIRST MIGRATION
1. Create custom User model with UUID primary key
2. Set AUTH_USER_MODEL in settings
3. Only then run first migration

### ⚠️ DJANGO COMMANDS IN DOCKER
Always use docker-compose:
```bash
# WRONG: python manage.py ...
# RIGHT: docker-compose run --rm web python manage.py ...
```

### ⚠️ FILE LOCATIONS IN WSL2
Work in WSL2 filesystem, not Windows:
```bash
# GOOD: /mnt/d/Python/Projects/...
# BAD: /mnt/c/Users/...
```

## Quick Command Reference

### 1. Build Docker Environment (First Time)
```bash
cd /mnt/d/Python/Projects/django/HTA-projects/agent-grey/
docker-compose build
```

### 2. Initialize Django Project
```bash
# Create project structure
docker-compose run --rm web django-admin startproject grey_lit_project .

# Create apps directory
docker-compose run --rm web mkdir -p apps
docker-compose run --rm web touch apps/__init__.py
```

### 3. Create Accounts App (CRITICAL - Do First!)
```bash
# Create the accounts app
docker-compose run --rm web python manage.py startapp accounts apps/accounts

# STOP HERE - Add User model before migrations!
```

### 4. After User Model Created
```bash
# First migration
docker-compose run --rm web python manage.py makemigrations
docker-compose run --rm web python manage.py migrate

# Create superuser
docker-compose run --rm web python manage.py createsuperuser
```

### 5. Start Development Environment
```bash
# Start all services
docker-compose up

# Or run in background
docker-compose up -d

# View logs
docker-compose logs -f web
```

### 6. Create Remaining Apps
```bash
docker-compose run --rm web python manage.py startapp review_manager apps/review_manager
docker-compose run --rm web python manage.py startapp search_strategy apps/search_strategy
docker-compose run --rm web python manage.py startapp serp_execution apps/serp_execution
docker-compose run --rm web python manage.py startapp results_manager apps/results_manager
docker-compose run --rm web python manage.py startapp review_results apps/review_results
docker-compose run --rm web python manage.py startapp reporting apps/reporting
```

## Status Check Commands

### Docker Status
```bash
# Check running containers
docker-compose ps

# Check service logs
docker-compose logs db
docker-compose logs redis
docker-compose logs web
```

### Django Status
```bash
# Check Django installation
docker-compose run --rm web python -m django --version

# Run Django checks
docker-compose run --rm web python manage.py check

# Check database connection
docker-compose run --rm web python manage.py dbshell
```

## Troubleshooting Quick Fixes

### If Docker build fails:
```bash
# Clean rebuild
docker-compose down -v
docker-compose build --no-cache
```

### If database connection fails:
```bash
# Check PostgreSQL is running
docker-compose logs db

# Verify .env has correct credentials
cat .env | grep POSTGRES
```

### If ports are in use:
```bash
# Find process using port
sudo lsof -i :8000
sudo lsof -i :5432

# Or change ports in docker-compose.yml
```

## Next Steps After Resume

1. **If Docker not built**: Start with `docker-compose build`
2. **If project not initialized**: Run Django project creation
3. **If User model not created**: THIS IS CRITICAL - do immediately
4. **If apps not created**: Create all 7 apps
5. **If ready to develop**: Start implementing models

## PRP Commands for Next Features

After setup complete, use:
- `/create-base-prp implement review manager dashboard`
- `/create-base-prp implement search strategy with PIC framework`
- `/create-base-prp implement SERP execution with Celery`

## Validation Before Starting Work

Run through PRP validation loop:
1. Environment check
2. Django check
3. Database connection
4. Migration test
5. Server test
6. Celery test
7. Full Docker test

## Session Handoff Location

For detailed context, see:
- `PRPs/handoffs/2025-01-25-django-setup-session.md`
- `PRPs/completed/django-environment-setup-COMPLETED.md`
- `PRPs/research/django-4.2-docker-wsl-research.md`

This checklist ensures a smooth resume of the Django setup process with all critical warnings and commands readily available.