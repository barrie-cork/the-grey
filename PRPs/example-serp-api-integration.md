# PRP: SERP API Integration for Thesis Grey

## Goal
Complete the Serper API integration for the serp_execution app to enable automated search query execution.

## Why
- Currently, the serp_execution app has models and managers but lacks API integration
- Users need automated search execution to collect grey literature efficiently
- This is blocking the complete workflow from search strategy to results processing

## What
Implement Celery tasks that:
1. Execute search queries against Serper API
2. Store raw results in the database
3. Update execution status and progress
4. Handle errors and implement retry logic

### Success Criteria
- [ ] Serper API client configured and tested
- [ ] Celery task executes searches successfully
- [ ] Results stored in RawSearchResult model
- [ ] Progress tracking works in real-time
- [ ] Error handling and retry logic implemented
- [ ] All tests pass with >90% coverage

## All Needed Context

### Current Implementation Status
- file: docs/PRD.md:296-339
  why: Shows serp_execution is in progress with models complete

### Model Structure
- file: docs/PRD.md:326-336
  why: SearchExecution model structure with status workflow

### API Configuration
- doc: https://serper.dev/docs
  why: Serper API documentation for implementation

### Django Project Structure
- SERP app location: apps/serp_execution/
- Celery configured with Redis broker
- Custom managers already implemented
- UUID primary keys throughout

### Known Gotchas
# CRITICAL: Store Serper API key in environment variables, never in code
# CRITICAL: Implement rate limiting to respect API quotas
# CRITICAL: All API calls must be async via Celery
# CRITICAL: Use idempotent task design for safe retries

## Implementation Blueprint

1. Create Serper API client class
   - Configure with API key from settings
   - Implement search method with error handling
   - Add rate limiting decorator

2. Implement Celery task
   ```python
   @shared_task(bind=True, max_retries=3)
   def perform_serp_query_task(self, execution_id):
       # Get execution instance
       # Call Serper API
       # Store results in RawSearchResult
       # Update execution status and progress
   ```

3. Add progress tracking
   - Update progress_percentage during execution
   - Send real-time updates via channels/websockets

4. Implement retry logic
   - Exponential backoff for rate limits
   - Different retry strategies for different error types

## Validation Loop

### Level 1: Syntax & Linting
```bash
flake8 apps/serp_execution/ --max-line-length=120
mypy apps/serp_execution/
```

### Level 2: Unit Tests
```bash
python manage.py test apps.serp_execution.tests.test_tasks -v
python manage.py test apps.serp_execution.tests.test_api_client -v
```

### Level 3: Integration Test
```bash
# Start Celery worker
celery -A grey_lit_project worker -l info

# Run integration test
python manage.py test apps.serp_execution.tests.test_integration -v
```

### Level 4: Coverage Check
```bash
coverage run --source='apps/serp_execution' manage.py test apps.serp_execution
coverage report --fail-under=90
```