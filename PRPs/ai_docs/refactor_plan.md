# Thesis Grey Refactoring Plan

**Generated**: 2025-01-25
**Scope**: Django application code quality improvements
**Time Estimate**: Each item designed to be completed in <1 hour

## 1. Functions >20 Lines That Need Decomposition

### HIGH PRIORITY: DuplicateGroup.merge_results() [44 lines]
**Location**: `/apps/results_manager/models.py:230-274`

**Why it's a problem**: 
- Violates single responsibility principle
- Hard to test individual parts
- Complex nested logic makes it error-prone

**Specific fix**:
```python
# In apps/results_manager/models.py

class DuplicateGroup(models.Model):
    # ... existing code ...
    
    def merge_results(self) -> None:
        """Merge duplicate results, keeping the best version."""
        results = self.results.all()
        if results.count() <= 1:
            return
        
        best_result = self._find_best_result(results)
        if best_result:
            self._merge_metadata_into_best(best_result, results)
            best_result.save()
            self.save()
    
    def _find_best_result(self, results: models.QuerySet) -> Optional['ProcessedResult']:
        """Find the result with the most complete metadata."""
        best_result = None
        best_score = 0
        
        for result in results:
            score = self._calculate_result_score(result)
            if score > best_score:
                best_score = score
                best_result = result
        
        return best_result
    
    def _calculate_result_score(self, result: 'ProcessedResult') -> float:
        """Calculate quality score for a result based on metadata completeness."""
        score = 0
        if result.snippet:
            score += 1
        if result.authors:
            score += 2
        if result.publication_date:
            score += 2
        if result.has_full_text:
            score += 3
        if result.relevance_score:
            score += result.relevance_score
        return score
    
    def _merge_metadata_into_best(self, best_result: 'ProcessedResult', 
                                  all_results: models.QuerySet) -> None:
        """Merge missing metadata from other results into the best result."""
        for result in all_results:
            if result != best_result:
                if not best_result.snippet and result.snippet:
                    best_result.snippet = result.snippet
                if not best_result.authors and result.authors:
                    best_result.authors = result.authors
                # Update sources list
                if result.raw_result and result.raw_result.execution.search_engine not in self.sources:
                    self.sources.append(result.raw_result.execution.search_engine)
```

**Priority**: HIGH (complex business logic that's hard to test)

### MEDIUM PRIORITY: ExecutionMetrics.update_metrics() [34 lines]
**Location**: `/apps/serp_execution/models.py:357-391`

**Why it's a problem**:
- Mixes data aggregation with database updates
- Multiple responsibilities in one method

**Specific fix**:
```python
# In apps/serp_execution/models.py

class ExecutionMetrics(models.Model):
    # ... existing code ...
    
    def update_metrics(self) -> None:
        """Update metrics based on current executions."""
        executions = SearchExecution.objects.filter(query__session=self.session)
        
        self._update_execution_counts(executions)
        self._update_aggregate_metrics(executions)
        self._update_last_execution_time(executions)
        
        self.save()
    
    def _update_execution_counts(self, executions: models.QuerySet) -> None:
        """Update execution count metrics."""
        self.total_executions = executions.count()
        self.successful_executions = executions.filter(status='completed').count()
        self.failed_executions = executions.filter(status='failed').count()
    
    def _update_aggregate_metrics(self, executions: models.QuerySet) -> None:
        """Update aggregated metrics from executions."""
        from django.db.models import Avg, Sum
        
        aggs = executions.aggregate(
            total_results=Sum('results_count'),
            total_credits=Sum('api_credits_used'),
            total_cost=Sum('estimated_cost'),
            avg_time=Avg('duration_seconds')
        )
        
        self.total_results_retrieved = aggs['total_results'] or 0
        self.total_api_credits = aggs['total_credits'] or 0
        self.total_estimated_cost = aggs['total_cost'] or Decimal('0.00')
        self.average_execution_time = aggs['avg_time']
    
    def _update_last_execution_time(self, executions: models.QuerySet) -> None:
        """Update the last execution timestamp."""
        latest = executions.order_by('-completed_at').first()
        if latest:
            self.last_execution = latest.completed_at
```

**Priority**: MEDIUM

## 2. Long Files That Need Decomposition

### HIGH PRIORITY: Split review_results models
**Location**: `/apps/review_results/models.py` (392 lines)

**Why it's a problem**:
- Hard to navigate
- Violates single file, single concept principle
- Makes imports unnecessarily heavy

**Specific fix**:
```python
# Create directory: apps/review_results/models/

# apps/review_results/models/__init__.py
from .tags import ReviewTag
from .decisions import ReviewDecision
from .assignments import ReviewTagAssignment
from .comments import ReviewComment

__all__ = ['ReviewTag', 'ReviewDecision', 'ReviewTagAssignment', 'ReviewComment']

# apps/review_results/models/base.py
import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()

# apps/review_results/models/tags.py
from .base import *

class ReviewTag(models.Model):
    """Tags for categorizing and filtering reviewed results."""
    # ... move existing ReviewTag code here ...

# apps/review_results/models/decisions.py
from .base import *

class ReviewDecision(models.Model):
    """Review decision for a processed result."""
    # ... move existing ReviewDecision code here ...

# Similar pattern for assignments.py and comments.py
```

**Priority**: HIGH (improves code organization significantly)

## 3. Missing Pydantic Models for I/O

### HIGH PRIORITY: Create API schemas for Search Session
**Location**: Create new file `/apps/review_manager/schemas.py`

**Why it's a problem**:
- No input validation for API endpoints
- No consistent response format
- Type safety issues

**Specific fix**:
```python
# apps/review_manager/schemas.py
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, validator
from enum import Enum

class SessionStatus(str, Enum):
    DRAFT = 'draft'
    DEFINING_SEARCH = 'defining_search'
    READY_TO_EXECUTE = 'ready_to_execute'
    EXECUTING = 'executing'
    PROCESSING_RESULTS = 'processing_results'
    READY_FOR_REVIEW = 'ready_for_review'
    UNDER_REVIEW = 'under_review'
    COMPLETED = 'completed'
    ARCHIVED = 'archived'

class CreateSessionSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    
    @validator('title')
    def title_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Title cannot be empty or whitespace')
        return v.strip()

class UpdateSessionSchema(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    status: Optional[SessionStatus] = None
    notes: Optional[str] = None
    tags: Optional[List[str]] = None

class SessionResponseSchema(BaseModel):
    id: UUID
    title: str
    description: str
    status: SessionStatus
    owner_id: UUID
    owner_username: str
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    total_queries: int
    total_results: int
    reviewed_results: int
    included_results: int
    progress_percentage: float
    inclusion_rate: float
    allowed_transitions: List[SessionStatus]
    tags: List[str]
    
    class Config:
        from_attributes = True

class SessionListResponseSchema(BaseModel):
    count: int
    next: Optional[str]
    previous: Optional[str]
    results: List[SessionResponseSchema]
```

**Priority**: HIGH (critical for API safety and documentation)

### MEDIUM PRIORITY: Create schemas for Search Query
**Location**: Create new file `/apps/search_strategy/schemas.py`

**Specific fix**:
```python
# apps/search_strategy/schemas.py
from datetime import date
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, validator

class PICFrameworkSchema(BaseModel):
    """Population, Interest, Context framework validation"""
    population: str = Field(..., min_length=1, max_length=1000)
    interest: str = Field(..., min_length=1, max_length=1000)
    context: str = Field(..., min_length=1, max_length=1000)
    
    @validator('population', 'interest', 'context')
    def not_empty(cls, v):
        if not v.strip():
            raise ValueError('Field cannot be empty or whitespace')
        return v.strip()

class CreateQuerySchema(PICFrameworkSchema):
    session_id: UUID
    include_keywords: List[str] = Field(default_factory=list)
    exclude_keywords: List[str] = Field(default_factory=list)
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    languages: List[str] = Field(default_factory=list)
    document_types: List[str] = Field(default_factory=list)
    search_engines: List[str] = Field(default=['google'])
    max_results: int = Field(100, ge=1, le=1000)
    is_primary: bool = True
    
    @validator('date_to')
    def date_range_valid(cls, v, values):
        if v and 'date_from' in values and values['date_from']:
            if v < values['date_from']:
                raise ValueError('date_to must be after date_from')
        return v
```

**Priority**: MEDIUM

## 4. Cross-Feature Imports Violating Vertical Slices

### MEDIUM PRIORITY: Use Django signals for cross-app communication
**Location**: Multiple apps

**Why it's a problem**:
- Direct foreign key references create tight coupling
- Hard to test apps in isolation
- Violates vertical slice architecture

**Specific fix**:
```python
# apps/review_manager/signals.py
from django.dispatch import Signal

# Define signals
session_status_changed = Signal()  # args: session, old_status, new_status
session_completed = Signal()       # args: session

# apps/review_manager/models.py
from .signals import session_status_changed, session_completed

class SearchSession(models.Model):
    # ... existing code ...
    
    def save(self, *args, **kwargs):
        old_status = None
        if self.pk:
            old_instance = SearchSession.objects.get(pk=self.pk)
            old_status = old_instance.status
        
        super().save(*args, **kwargs)
        
        if old_status and old_status != self.status:
            session_status_changed.send(
                sender=self.__class__,
                session=self,
                old_status=old_status,
                new_status=self.status
            )
            
            if self.status == 'completed':
                session_completed.send(sender=self.__class__, session=self)

# apps/serp_execution/apps.py
from django.apps import AppConfig

class SerpExecutionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.serp_execution'
    
    def ready(self):
        from . import receivers  # noqa

# apps/serp_execution/receivers.py
from django.dispatch import receiver
from apps.review_manager.signals import session_status_changed

@receiver(session_status_changed)
def handle_session_status_change(sender, session, old_status, new_status, **kwargs):
    if new_status == 'executing':
        # Trigger search execution
        from .tasks import execute_search_queries
        execute_search_queries.delay(session.id)
```

**Priority**: MEDIUM (improves architecture but not critical)

## 5. Classes with Multiple Responsibilities

### LOW PRIORITY: Extract SearchSession state machine
**Location**: `/apps/review_manager/models.py`

**Why it's a problem**:
- Model handles both data and complex state logic
- Hard to test state transitions in isolation

**Specific fix**:
```python
# apps/review_manager/state_machine.py
from typing import List, Optional

class SessionStateMachine:
    """Handles SearchSession state transitions and validation."""
    
    ALLOWED_TRANSITIONS = {
        'draft': ['defining_search', 'archived'],
        'defining_search': ['ready_to_execute', 'draft', 'archived'],
        'ready_to_execute': ['executing', 'defining_search', 'archived'],
        'executing': ['processing_results', 'ready_to_execute', 'archived'],
        'processing_results': ['ready_for_review', 'executing', 'archived'],
        'ready_for_review': ['under_review', 'processing_results', 'archived'],
        'under_review': ['completed', 'ready_for_review', 'archived'],
        'completed': ['archived', 'under_review'],
        'archived': ['draft'],
    }
    
    def __init__(self, current_status: str):
        self.current_status = current_status
    
    def can_transition_to(self, new_status: str) -> bool:
        """Check if transition to new status is allowed."""
        if self.current_status == new_status:
            return True
        return new_status in self.ALLOWED_TRANSITIONS.get(self.current_status, [])
    
    def get_allowed_transitions(self) -> List[str]:
        """Get list of allowed status transitions."""
        return self.ALLOWED_TRANSITIONS.get(self.current_status, [])
    
    def validate_transition(self, new_status: str) -> None:
        """Validate and raise exception if transition not allowed."""
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Cannot transition from '{self.current_status}' to '{new_status}'"
            )

# Update SearchSession to use the state machine
class SearchSession(models.Model):
    # ... existing fields ...
    
    def clean(self):
        """Validate status transitions."""
        if self.pk:
            try:
                old_instance = SearchSession.objects.get(pk=self.pk)
                state_machine = SessionStateMachine(old_instance.status)
                state_machine.validate_transition(self.status)
            except SearchSession.DoesNotExist:
                pass
    
    def can_transition_to(self, new_status: str) -> bool:
        """Check if transition to new status is allowed."""
        state_machine = SessionStateMachine(self.status)
        return state_machine.can_transition_to(new_status)
```

**Priority**: LOW (nice to have but not critical)

## 6. Missing Type Hints

### HIGH PRIORITY: Add type hints to all model methods
**Location**: All model files

**Why it's a problem**:
- No IDE autocomplete support
- Runtime type errors not caught early
- Poor documentation for method contracts

**Specific fix example**:
```python
# apps/review_manager/models.py
from typing import List, Optional, Dict, Any
from django.db import models
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()

class SearchSession(models.Model):
    # ... existing fields ...
    
    def __str__(self) -> str:
        return f"{self.title} ({self.get_status_display()})"
    
    def clean(self) -> None:
        """Validate status transitions."""
        # ... existing code ...
    
    def save(self, *args: Any, **kwargs: Any) -> None:
        """Override save to handle status change timestamps."""
        # ... existing code ...
    
    def can_transition_to(self, new_status: str) -> bool:
        """Check if transition to new status is allowed."""
        # ... existing code ...
    
    def get_allowed_transitions(self) -> List[str]:
        """Get list of allowed status transitions from current status."""
        # ... existing code ...
    
    @property
    def progress_percentage(self) -> float:
        """Calculate review progress as a percentage."""
        # ... existing code ...
    
    @property
    def inclusion_rate(self) -> float:
        """Calculate the rate of included results."""
        # ... existing code ...

class SessionActivity(models.Model):
    # ... existing fields ...
    
    @classmethod
    def log_activity(
        cls, 
        session: SearchSession, 
        activity_type: str, 
        description: str, 
        user: Optional[User] = None, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> 'SessionActivity':
        """Convenience method to log an activity."""
        # ... existing code ...
```

**Priority**: HIGH (improves code quality and prevents bugs)

## Summary Action Plan

### Immediate Actions (Complete First):
1. **Add Pydantic schemas** for SearchSession API (1 hour)
2. **Add type hints** to SearchSession and SessionActivity models (30 mins)
3. **Decompose DuplicateGroup.merge_results()** method (45 mins)

### Next Sprint:
1. **Split review_results models** into separate files (1 hour)
2. **Add Pydantic schemas** for remaining apps (1 hour each)
3. **Add type hints** to remaining models (1 hour total)

### Future Improvements:
1. Implement signal-based cross-app communication
2. Extract state machine logic from models
3. Create service layers for complex business logic
4. Add comprehensive logging and monitoring

## Validation Checklist

After each refactoring:
- [ ] Run all tests: `python manage.py test`
- [ ] Check type hints: `mypy apps/`
- [ ] Verify imports: `python -m py_compile apps/**/*.py`
- [ ] Run linter: `flake8 apps/ --max-line-length=120`
- [ ] Test in Docker: `docker-compose run --rm web python manage.py test`