# Migration Cleanup and App Restoration Handover Document

## Overview
This document provides a comprehensive guide for continuing the migration cleanup and app restoration work on the Thesis Grey project. The project recently underwent major refactoring to remove complexity around cost tracking, usage monitoring, and quality metrics. This guide is written for junior developers who will continue this work.

## Current Situation

### What Was Done
1. **Service Simplification in `serp_execution` app**:
   - Removed 4 complex service files:
     - `cost_service.py` - Cost tracking and budget management
     - `content_analysis_service.py` - Complex content quality analysis
     - `usage_tracker.py` - Usage analytics and budget enforcement
     - `monitoring_service.py` - Detailed monitoring (moved basic functions to execution_service)
   
   - Simplified remaining services:
     - `query_builder.py`: Reduced from 500+ lines to 70 lines
     - `cache_manager.py`: Reduced from 300+ lines to 57 lines
     - `execution_service.py`: Reduced from 200+ lines to 47 lines
     - `result_processor.py`: Reduced from 600+ lines to 77 lines

2. **Migration Issues Discovered**:
   - The app won't start due to migration conflicts
   - Error: `django.db.utils.ProgrammingError: column "session_id" does not exist`
   - The migrations reference fields and indexes that don't match the current simplified models

3. **Decision Made**: Start fresh with all migrations across all apps to ensure consistency

### Current State
- All migration files have been deleted from all apps (except `__init__.py` files)
- Migration cache directories have been cleared
- Models have been cleaned of cost/usage/quality tracking fields
- The app cannot start until fresh migrations are created

## Understanding the Migration System

### What are Django Migrations?
Migrations are Django's way of propagating changes you make to your models (adding a field, deleting a model, etc.) into your database schema. They're essentially Python files that describe database changes.

### Why Start Fresh?
After major refactoring:
- Old migrations reference removed fields (like `api_credits_used`, `estimated_cost`)
- Dependencies between apps may reference non-existent migrations
- It's cleaner to create new initial migrations that match the simplified models

## Next Steps - Complete Guide

### Step 1: Create Fresh Migrations for All Apps

**Important**: The order matters due to dependencies between apps!

1. **First, create migrations for apps with no dependencies**:
   ```bash
   python manage.py makemigrations accounts
   python manage.py makemigrations core
   ```

2. **Then create migrations for foundation apps**:
   ```bash
   python manage.py makemigrations review_manager
   python manage.py makemigrations search_strategy
   ```

3. **Then apps that depend on the above**:
   ```bash
   python manage.py makemigrations serp_execution
   python manage.py makemigrations results_manager
   python manage.py makemigrations review_results
   ```

4. **Finally, the reporting app**:
   ```bash
   python manage.py makemigrations reporting
   ```

### Step 2: Handle Potential Issues

#### Issue 1: Circular Dependencies
If you get an error about circular dependencies:
1. Look at which models reference each other
2. You may need to create migrations without foreign keys first, then add them in a second migration

Example:
```bash
# If serp_execution and results_manager have circular dependencies:
python manage.py makemigrations serp_execution --empty
# Then manually edit to add only the models without foreign keys
```

#### Issue 2: Missing Dependencies
If you get `NodeNotFoundError`:
1. Check which app is missing
2. Create its migration first
3. Then retry the failing app

### Step 3: Reset the Database (Development Only!)

**WARNING**: This will delete all data! Only do this in development.

```bash
# Stop all services
docker-compose down

# Remove the database volume
docker volume rm agent-grey_postgres_data

# Start the database service
docker-compose up -d db

# Wait for it to be healthy
docker-compose exec db pg_isready -U thesis_grey_user
```

### Step 4: Apply Migrations

```bash
# Apply all migrations
docker-compose run --rm web python manage.py migrate

# Create a superuser
docker-compose run --rm web python manage.py createsuperuser
```

### Step 5: Verify Everything Works

1. **Start all services**:
   ```bash
   docker-compose up -d
   ```

2. **Check logs for errors**:
   ```bash
   docker-compose logs -f web
   ```

3. **Test basic functionality**:
   - Visit http://localhost:8000/admin/
   - Log in with superuser credentials
   - Check that all models appear correctly

## Understanding the Simplified Architecture

### What Was Removed
- **Cost Tracking**: No more tracking of API credits, costs, or budgets
- **Usage Analytics**: No more detailed usage statistics per user
- **Quality Scoring**: No more complex content quality analysis
- **Complex Monitoring**: Only basic success/failure tracking remains

### What Remains (Core Functionality)
1. **Search Execution**: Basic API calls to Serper
2. **Result Storage**: Raw results from API stored simply
3. **Basic Caching**: Simple key-value caching for performance
4. **Simple Processing**: Basic metadata extraction (title, URL, snippet)

## Common Commands Reference

### Docker Commands
```bash
# View running containers
docker-compose ps

# View logs
docker-compose logs -f [service_name]

# Restart a service
docker-compose restart [service_name]

# Run Django commands
docker-compose run --rm web python manage.py [command]
```

### Django Commands
```bash
# Create migrations
python manage.py makemigrations [app_name]

# Apply migrations
python manage.py migrate

# Check for issues
python manage.py check

# Django shell
python manage.py shell
```

## Troubleshooting Guide

### Problem: "No such table" errors
**Solution**: Migrations haven't been applied. Run `python manage.py migrate`

### Problem: "Field does not exist" errors
**Solution**: Models and migrations are out of sync. Check that migrations match current models.

### Problem: Container keeps restarting
**Solution**: Check logs with `docker-compose logs web`. Usually a migration error.

### Problem: "NodeNotFoundError" during migration
**Solution**: Dependencies are wrong. Check the order of migration creation.

## File Locations

### Key Directories
- `/apps/*/models.py` - Django models (database structure)
- `/apps/*/migrations/` - Migration files (database changes)
- `/apps/*/services/` - Business logic services
- `/docker-compose.yml` - Docker service configuration
- `/.env` - Environment variables (don't commit!)

### Recently Modified Files
- `/apps/serp_execution/services/` - All services simplified
- `/apps/serp_execution/models.py` - Cleaned of cost/quality fields
- `/apps/serp_execution/views.py` - Updated imports
- `/apps/serp_execution/utils.py` - Simplified utility functions

## Testing After Completion

1. **Create a test session**:
   - Log into admin
   - Create a SearchSession
   - Set status to "draft"

2. **Test search strategy**:
   - Create a SearchStrategy
   - Add some PIC terms
   - Generate queries

3. **Test execution** (if Serper API key is configured):
   - Change session status to "ready_to_execute"
   - Try executing a search
   - Check for results

## Important Notes

1. **Don't Restore Complexity**: The removed services were intentionally deleted to simplify the codebase
2. **Keep It Simple**: When fixing issues, use the simplest solution
3. **Test Incrementally**: Test after each major step
4. **Ask for Help**: If stuck, the error messages usually point to the exact problem

## Contact Information

If you encounter issues:
1. Check Docker logs first: `docker-compose logs -f`
2. Check Django logs: Look in `/logs/` directory
3. Try running `python manage.py check` for configuration issues

Good luck with the migration cleanup! Remember, you're essentially creating a fresh database schema that matches the new simplified models. Take it step by step, and the app will be running smoothly again.