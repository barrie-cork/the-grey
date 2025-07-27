# Code Quality Issues Report

## Summary
This report identifies specific code quality issues in the Django codebase, focusing on actionable items that can be fixed quickly.

## 1. Functions Longer Than 20 Lines (Need Decomposition)

### High Priority (>50 lines)
1. **apps/core/logging.py:108** - `__call__()` - 72 lines
   - Action: Extract logging level handling into separate methods
   
2. **apps/reporting/services/export_service.py:81** - `export_to_csv()` - 57 lines
   - Action: Extract CSV row building into separate method
   
3. **apps/reporting/services/export_service.py:199** - `generate_export_summary()` - 63 lines
   - Action: Split into metadata collection and summary generation methods

4. **apps/reporting/services/search_strategy_reporting_service.py:19** - `generate_search_strategy_report()` - 94 lines
   - Action: Extract query processing and statistics calculation
   
5. **apps/reporting/services/search_strategy_reporting_service.py:114** - `generate_query_optimization_report()` - 97 lines
   - Action: Split optimization analysis into separate methods

6. **apps/results_manager/tasks.py:30** - `process_session_results_task()` - 101 lines
   - Action: Extract batch creation and monitoring logic

### Medium Priority (20-50 lines)
1. **apps/accounts/forms.py:108** - `clean()` - 30 lines
   - Action: Extract validation logic into separate methods
   
2. **apps/reporting/services/performance_analytics_service.py:17** - `calculate_search_performance_metrics()` - 53 lines
   - Action: Split metric calculations by type

3. **apps/results_manager/tasks.py:276** - `process_single_result()` - 47 lines
   - Action: Extract content extraction and quality scoring

## 2. Long Files (>500 lines)

1. **apps/review_manager/test_user_criteria.py** - 730 lines
   - Action: Split into multiple test modules by UC category
   
2. **apps/serp_execution/tasks.py** - 614 lines
   - Action: Split into execution_tasks.py and monitoring_tasks.py
   
3. **apps/serp_execution/views.py** - 542 lines
   - Action: Extract API views into separate api.py module

## 3. Missing Pydantic Models for Data Validation

### Critical Areas Needing Validation
1. **apps/search_strategy/views.py:367** - Raw JSON parsing without validation
   ```python
   data = json.loads(request.body)  # No validation!
   ```
   Action: Create SearchQueryCreateSchema for validation

2. **apps/review_manager/api/views.py:45** - Direct request.data access
   ```python
   new_status = request.data.get("status")  # No validation!
   ```
   Action: Create StatusUpdateSchema with allowed transitions

3. **apps/serp_execution/services/result_processor.py** - Processing raw API responses
   - Action: Create SerperResponseSchema for API response validation

## 4. Cross-Feature Imports (Vertical Slice Violations)

### Most Problematic Cross-Imports
1. **apps/core/signals.py** - Imports from 4 different apps
   - Violates: Core should not depend on feature modules
   - Action: Move signals to respective apps or use interfaces

2. **apps/reporting/** - Heavy coupling to all other apps
   - Files: prisma_reporting_service.py, performance_analytics_service.py
   - Action: Use API contracts/interfaces instead of direct imports

3. **apps/core/bootstrap.py** - Direct provider imports
   ```python
   from apps.review_manager.providers import SessionProviderImpl
   from apps.search_strategy.providers import QueryProviderImpl
   ```
   - Action: Use dependency injection pattern

## 5. Classes with Multiple Responsibilities

1. **SerperClient** (apps/serp_execution/services/serper_client.py)
   - Current: HTTP client + rate limiting + caching + error handling
   - Action: Extract RateLimiter and CacheManager classes

2. **SearchSession** model (likely in apps/review_manager/models.py)
   - Current: State management + workflow + activity tracking
   - Action: Extract WorkflowStateMachine class

3. **ResultProcessor** (apps/serp_execution/services/result_processor.py)
   - Current: Parsing + quality scoring + deduplication
   - Action: Split into Parser, QualityScorer, and Deduplicator

## 6. Missing Type Hints

### Files with No Type Hints
1. Most templatetag files lack type hints:
   - apps/reporting/templatetags/report_tags.py
   - apps/search_strategy/templatetags/query_tags.py
   - apps/serp_execution/templatetags/execution_tags.py

2. API views missing return type hints:
   - apps/review_manager/api/views.py
   - apps/results_manager/api.py

## Quick Wins (Can be fixed in <30 minutes each)

1. **Add Pydantic validation to search_strategy/views.py:367**
2. **Add type hints to all API view methods**
3. **Extract long template tag functions into smaller helpers**
4. **Create interfaces for cross-app dependencies in core/**
5. **Split test_user_criteria.py by UC category**

## Recommended Action Plan

### Phase 1: Critical Issues (1-2 days)
1. Add Pydantic validation to all API endpoints
2. Fix cross-app imports in core/signals.py
3. Decompose functions >70 lines

### Phase 2: Architecture (3-5 days)
1. Implement proper dependency injection
2. Split classes with multiple responsibilities
3. Create API contracts between apps

### Phase 3: Maintenance (1 week)
1. Add type hints throughout codebase
2. Break down long files
3. Decompose remaining long functions