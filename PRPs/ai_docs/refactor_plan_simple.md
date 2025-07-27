# Quick Refactoring Plan - Code Quality Issues

**Generated on:** 2025-01-26  
**Scope:** Python code quality improvements focusing on vertical slice boundaries, function complexity, and type safety  
**Architecture:** Simplified after recent refactoring - focus on remaining issues  

## Executive Summary

After analyzing the codebase, I found several refactoring opportunities that can be addressed quickly (<1 hour each). The code already shows good Pydantic v2 adoption in schemas and vertical slice architecture, but there are specific areas for improvement.

## 1. Vertical Slice Boundary Violations (High Priority)

### Issue 1.1: Cross-Feature Imports in Views
**Location:** `apps/serp_execution/views.py:8-10`  
**Problem:** Direct imports from other slices violating VSA boundaries
```python
from apps.review_manager.models import SearchSession
from apps.review_manager.signals import get_session_data
from apps.search_strategy.signals import get_session_queries_data
```

**Fix:** Create dependency injection service
```python
# apps/serp_execution/dependencies.py
from typing import Protocol
from apps.core.interfaces import SessionProvider, QueryProvider

class SessionDependencies:
    def __init__(self, session_provider: SessionProvider, query_provider: QueryProvider):
        self.session_provider = session_provider
        self.query_provider = query_provider

# Update views.py to use dependency injection
```
**Implementation:** `apps/serp_execution/views.py`  
**Priority:** High (30 minutes)

### Issue 1.2: Test Cross-Slice Dependencies
**Location:** Multiple test files importing across slices  
**Problem:** Tests importing models from other slices directly
```python
# Found in 15+ test files
from apps.review_manager.models import SearchSession
from apps.results_manager.models import ProcessedResult
```

**Fix:** Use factory patterns and interface abstractions
```python
# apps/core/test_factories.py
class SessionFactory:
    @staticmethod
    def create_session(**kwargs):
        # Abstract session creation
        pass

# Update test imports to use factories
```
**Implementation:** Create `apps/core/test_factories.py`  
**Priority:** Medium (45 minutes)

## 2. Function Complexity Issues (Medium Priority)

### Issue 2.1: SerperClient._build_request_params() Too Complex
**Location:** `apps/serp_execution/services/serper_client.py:123-165`  
**Problem:** 43-line function with multiple responsibilities
```python
def _build_request_params(self, query: str, num_results: int = 10, ...):
    # 43 lines of parameter building logic
```

**Fix:** Extract parameter builders
```python
def _build_request_params(self, query: str, num_results: int = 10, **kwargs) -> Dict[str, Any]:
    params = self._build_base_params(query, num_results)
    params.update(self._build_date_params(kwargs))
    params.update(self._build_file_type_params(query, kwargs))
    return params

def _build_base_params(self, query: str, num_results: int) -> Dict[str, Any]:
    # 10 lines of base parameter logic
    
def _build_date_params(self, kwargs: Dict) -> Dict[str, Any]:
    # 5 lines of date parameter logic
    
def _build_file_type_params(self, query: str, kwargs: Dict) -> Dict[str, Any]:
    # 8 lines of file type logic
```
**Implementation:** `apps/serp_execution/services/serper_client.py:123-165`  
**Priority:** Medium (30 minutes)

### Issue 2.2: DeduplicationService.detect_duplicates() Complex Logic
**Location:** `apps/results_manager/services/deduplication_service.py:111-158`  
**Problem:** 47-line function with nested loops and complex logic

**Fix:** Extract duplicate detection strategies
```python
def detect_duplicates(self, results: QuerySet, similarity_threshold: float = 0.8) -> List[Dict[str, Any]]:
    detector = DuplicateDetector(similarity_threshold)
    return detector.process_results(results)

class DuplicateDetector:
    def __init__(self, threshold: float):
        self.threshold = threshold
        
    def process_results(self, results: QuerySet) -> List[Dict[str, Any]]:
        # Simplified main logic
        
    def _compare_results(self, result1, result2) -> Optional[Dict[str, Any]]:
        # Extracted comparison logic
```
**Implementation:** `apps/results_manager/services/deduplication_service.py:111-158`  
**Priority:** Medium (35 minutes)

## 3. Missing Type Hints (Medium Priority)

### Issue 3.1: View Methods Missing Return Types
**Location:** Multiple view files  
**Problem:** Class-based view methods missing type annotations
```python
# Current
def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    # ...

# Fixed
def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
    context = super().get_context_data(**kwargs)
    # ...
```

**Fix:** Add comprehensive type hints to view methods
**Implementation:** 
- `apps/results_manager/views.py` (3 methods)
- `apps/serp_execution/views.py` (4 methods)  
**Priority:** Medium (20 minutes total)

### Issue 3.2: Service Methods Missing Type Annotations
**Location:** Service classes in multiple apps  
**Problem:** Service methods missing proper type hints

**Fix:** Add type annotations following Pydantic v2 patterns
```python
# Before
def process_results(self, results):
    # ...

# After  
def process_results(self, results: QuerySet[ProcessedResult]) -> ProcessingResult:
    # ...
```
**Implementation:** Service files in `apps/*/services/`  
**Priority:** Medium (25 minutes)

## 4. Pydantic v2 Schema Gaps (Low Priority)

### Issue 4.1: Missing Input/Output Schemas for Services
**Location:** Service classes throughout codebase  
**Problem:** Services not using Pydantic schemas for validation

**Fix:** Add Pydantic schemas for service I/O
```python
# apps/results_manager/schemas.py (add)
class ProcessingRequest(BaseModel):
    session_id: UUID
    batch_size: int = Field(default=50, ge=1, le=100)
    force_reprocess: bool = False

class ProcessingResult(BaseModel):
    processed_count: int
    duplicate_count: int
    error_count: int
    processing_time: float
```
**Implementation:** Add schemas to existing apps  
**Priority:** Low (40 minutes total)

## 5. Single Responsibility Violations (Low Priority)

### Issue 5.1: Mixed Concerns in SessionActivity.log_activity()
**Location:** `apps/review_manager/models.py:261-282`  
**Problem:** Model method handling logging logic

**Fix:** Extract to service
```python
# apps/review_manager/services/activity_logger.py
class ActivityLogger:
    @classmethod
    def log_session_activity(cls, session: SearchSession, activity_type: str, ...):
        return SessionActivity.objects.create(...)
```
**Implementation:** New service file + update model  
**Priority:** Low (25 minutes)

## Implementation Priority Order

### High Priority (1 hour total)
1. **Fix cross-slice imports in serp_execution views** (30 min)
2. **Create dependency injection interfaces** (30 min)

### Medium Priority (2 hours total)  
3. **Refactor SerperClient._build_request_params()** (30 min)
4. **Refactor DeduplicationService.detect_duplicates()** (35 min)
5. **Add type hints to view methods** (20 min)
6. **Add type hints to service methods** (25 min)
7. **Create test factories for cross-slice dependencies** (45 min)

### Low Priority (1.5 hours total)
8. **Add Pydantic schemas for service I/O** (40 min)
9. **Extract ActivityLogger service** (25 min)
10. **Add remaining type annotations** (25 min)

## Benefits After Refactoring

### Code Quality Improvements
- **Reduced coupling** between vertical slices
- **Better testability** with dependency injection
- **Improved maintainability** with single-responsibility functions
- **Enhanced type safety** with comprehensive annotations

### Performance Benefits
- **Reduced import complexity** improving startup time
- **Better IDE support** with complete type annotations
- **Cleaner test execution** with proper factory patterns

### Developer Experience
- **Clearer code organization** following VSA principles
- **Better error messages** with Pydantic validation
- **Improved debugging** with type safety
- **Easier onboarding** with clear boundaries

## Success Metrics

- **Vertical Slice Compliance:** Zero direct cross-slice imports in business logic
- **Function Complexity:** All functions under 20 lines
- **Type Coverage:** 95%+ type annotation coverage
- **Test Isolation:** Tests run independently without cross-slice dependencies

## Notes

- All fixes are backwards compatible
- No breaking changes to existing APIs
- Can be implemented incrementally
- Each fix is independently testable

This refactoring plan focuses on quick wins that improve code quality without major architectural changes, building on the recent simplification work.