# VSA-Aligned Code Quality Refactor Plan

Generated: 2025-07-25
Focus: Vertical Slice Architecture alignment, function complexity, type safety with Pydantic v2

## Executive Summary

The Django project follows Vertical Slice Architecture (VSA) principles as documented in the PRD. This refactor plan focuses on improving code quality while maintaining VSA's core tenets: feature-complete slices, minimal cross-slice dependencies, and business capability organization. Key areas for improvement include reducing large functions within slices, adding type safety with Pydantic, and replacing direct cross-app imports with event-driven communication.

## 🔴 High Priority Issues (Fix in <1 hour each)

### 1. Cross-Slice Communication Anti-Patterns

**Location**: Direct imports between Django apps/slices
**Files**: 
- `apps/reporting/utils.py` (lines 27-31)
- `apps/review_results/utils.py` (lines 26, 108, 205, 242, 302-303)
- `apps/serp_execution/views.py` (lines 24-25)
- `apps/search_strategy/signals.py` (lines 10-12)

**Why it's a problem**: Direct cross-slice imports violate VSA principles of self-contained slices and create tight coupling.

**VSA-Compliant fix**:
```python
# Instead of direct imports:
from apps.review_manager.models import SearchSession

# Use Django signals for cross-slice communication:
from django.dispatch import Signal, receiver

# Define signals in each slice
session_status_changed = Signal(['session_id', 'old_status', 'new_status'])

# Listen to events from other slices
@receiver(session_status_changed)
def handle_session_status_change(sender, session_id, old_status, new_status, **kwargs):
    # Handle in this slice without direct model access
    pass

# Or use internal APIs for data access:
class SessionDataAPI:
    @staticmethod
    def get_session_status(session_id: str) -> str:
        # Returns data without exposing internal models
        pass
```

**Implementation location**: Add signals.py to each app, create internal APIs within each slice.

**Priority**: High

### 2. Missing Pydantic Models for API I/O

**Location**: All apps lack Pydantic validation
**Files**: No `schemas.py` files exist in any app

**Why it's a problem**: Using raw dictionaries for API responses and validation creates type safety issues and runtime errors.

**Specific fix**:
```python
# Create schemas.py in each app
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class SearchSessionResponse(BaseModel):
    id: str
    title: str
    status: str
    created_at: datetime
    progress_percentage: float
    
class SearchExecutionRequest(BaseModel):
    query_string: str = Field(..., min_length=1, max_length=500)
    search_engines: List[str] = Field(default=["google"])
    max_results: int = Field(default=100, ge=1, le=1000)
```

**Implementation location**: Create `schemas.py` in each app directory.

**Priority**: High

### 3. Large Files Within Slices Need Business-Focused Organization

**Location**: Large utility files that could be better organized by business capability
**Files**:
- `apps/serp_execution/utils.py` (730 lines)
- `apps/results_manager/utils.py` (540 lines)
- `apps/reporting/utils.py` (541 lines)
- `apps/review_results/utils.py` (425 lines)

**Why it's a problem**: Large files make code harder to navigate and maintain, even within a well-defined slice.

**VSA-Compliant fix**:
```python
# Organize serp_execution by business capabilities within the slice:
apps/serp_execution/
├── execution/
│   ├── services.py       # Core execution logic
│   ├── views.py         # Execution endpoints
│   └── schemas.py       # Execution-specific Pydantic models
├── monitoring/
│   ├── services.py       # Cost tracking, performance analysis
│   ├── views.py         # Monitoring endpoints
│   └── schemas.py       # Monitoring-specific models
└── recovery/
    ├── services.py       # Retry logic, failure handling
    ├── views.py         # Recovery endpoints
    └── schemas.py       # Recovery-specific models

# Each service remains complete within its business context:
class ExecutionService:
    def calculate_cost(self, credits: int) -> Decimal:
        # Cost logic stays with execution
        return Decimal(credits) * Decimal('0.001')
    
    def estimate_time(self, complexity: int, engines: List[str]) -> int:
        # Time estimation stays with execution
        return 5 * len(engines) * (1 + complexity / 20)
```

**Implementation location**: Reorganize each slice by business capability, keeping related functionality together.

**Priority**: High

## 🟡 Medium Priority Issues

### 4. Functions Exceeding 20 Lines

**Location**: Several complex functions found
**Files**:
- `apps/review_results/utils.py:calculate_review_progress()` (~50 lines)
- `apps/results_manager/utils.py:detect_duplicates()` (~50 lines)
- `apps/serp_execution/services/result_processor.py:process_results()` (~80 lines)

**Why it's a problem**: Large functions are harder to test, understand, and maintain.

**Specific fix**:
```python
# Break down calculate_review_progress():
def calculate_review_progress(session_id: str) -> Dict[str, Any]:
    results_summary = _get_results_summary(session_id)
    tag_distribution = _calculate_tag_distribution(session_id)
    velocity = _calculate_review_velocity(session_id)
    
    return {
        **results_summary,
        'tag_distribution': tag_distribution,
        'review_velocity': velocity
    }

def _get_results_summary(session_id: str) -> Dict[str, Any]:
    # 10-15 lines max
    pass

def _calculate_tag_distribution(session_id: str) -> Dict[str, int]:
    # 10-15 lines max
    pass
```

**Implementation location**: Within existing utility files, create private helper functions.

**Priority**: Medium

### 5. Large Classes Within Business Context

**Location**: Service classes that are large but within appropriate business scope
**Files**:
- `apps/serp_execution/services/result_processor.py:ResultProcessor` (600+ lines)

**Why it's a problem**: Large classes are harder to test and maintain, even when appropriately scoped.

**VSA-Compliant fix**:
```python
# Keep ResultProcessor within serp_execution slice but break into focused methods:
class ResultProcessor:
    """Handles all result processing within serp_execution slice."""
    
    def process_search_results(self, raw_results: List[Dict]) -> List[ProcessedResult]:
        processed = []
        for raw_result in raw_results:
            metadata = self._extract_metadata(raw_result)
            content_type = self._detect_content_type(raw_result)
            pub_date = self._extract_publication_date(raw_result)
            
            processed.append(ProcessedResult(
                metadata=metadata,
                content_type=content_type,
                publication_date=pub_date
            ))
        return processed
    
    def _extract_metadata(self, result: Dict) -> Dict[str, Any]:
        # 10-15 lines max - focused extraction logic
        pass
    
    def _detect_content_type(self, result: Dict) -> str:
        # 10-15 lines max - focused detection logic
        pass
    
    def _extract_publication_date(self, result: Dict) -> Optional[datetime]:
        # 10-15 lines max - focused date extraction
        pass
```

**Implementation location**: Break large methods into smaller, focused private methods within the same service class.

**Priority**: Medium

### 6. Missing Type Hints in Key Areas

**Location**: Some functions lack complete type annotations
**Files**: Various utility functions in all apps

**Why it's a problem**: Reduces IDE support and makes runtime errors more likely.

**Specific fix**:
```python
# Add complete type hints:
from typing import Dict, List, Optional, Union, Any
from decimal import Decimal

def calculate_api_cost(credits_used: int, 
                      rate_per_credit: Decimal = Decimal('0.001')) -> Decimal:
    return Decimal(credits_used) * rate_per_credit

def get_failed_executions_with_analysis(session_id: str) -> List[Dict[str, Any]]:
    # Implementation with proper return type
    pass
```

**Implementation location**: Update existing function signatures throughout codebase.

**Priority**: Medium

## 🟢 Low Priority Issues

### 7. Improve Error Handling Consistency

**Location**: Inconsistent error handling patterns
**Files**: Various service classes

**Why it's a problem**: Makes debugging and error tracking difficult.

**Specific fix**: Implement consistent exception hierarchy and error response patterns.

**Priority**: Low

## VSA-Aligned Implementation Roadmap

### Phase 1 (Week 1): Strengthen Slice Boundaries
1. Replace direct cross-slice imports with Django signals/events
2. Add Pydantic schemas within each slice for type safety
3. Create internal APIs for controlled cross-slice data access

### Phase 2 (Week 2): Optimize Within Slices
1. Reorganize large files by business capability within each slice
2. Break down large functions into focused methods
3. Improve large classes while keeping them in appropriate business context

### Phase 3 (Week 3): Type Safety & Polish
1. Complete type hint coverage across all slices
2. Implement consistent error handling patterns
3. Add comprehensive validation within each slice

## VSA-Aligned Success Metrics

- [ ] Zero direct cross-slice imports (use events/signals instead)
- [ ] Each slice has complete Pydantic schemas for its data contracts
- [ ] All utility files under 200 lines, organized by business capability
- [ ] No functions over 20 lines within any slice
- [ ] 100% type hint coverage on public interfaces within each slice
- [ ] Each slice is feature-complete and self-contained
- [ ] Cross-slice communication follows event-driven patterns
- [ ] Service classes handle complete business capabilities within their slice

## VSA-Compatible Tools Recommended

- `mypy` for type checking within each slice
- `flake8` for complexity analysis  
- `pydantic[email]` for validation within slices
- Django's built-in signals for cross-slice communication
- `pytest` with slice-focused test organization

## Estimated Total Effort

- High priority: 8-12 hours
- Medium priority: 6-8 hours  
- Low priority: 4-6 hours
- **Total: 18-26 hours**

Each individual fix is designed to take less than 1 hour to maintain quick iteration cycles.