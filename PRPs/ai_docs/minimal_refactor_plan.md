# Minimal Refactoring Plan: Type Hints & Pydantic Schemas

**Generated**: 2025-01-25  
**Scope**: Type safety improvements only  
**Approach**: Incremental, as-you-go implementation

## Philosophy

"Add type safety as you build, not as a separate refactoring project"

## 1. Type Hints Strategy

### When to Add Type Hints

- **DO**: Add type hints when you:
  - Write new methods
  - Modify existing methods
  - Create new classes
  - Debug type-related issues

- **DON'T**: 
  - Refactor working code just for type hints
  - Spend time on rarely-used private methods
  - Add complex generic types early

### Basic Type Hint Template

```python
# At the top of each model file, add as needed:
from typing import List, Optional, Dict, Any, Union, Tuple
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

# For Django models:
from django.db import models
from django.db.models import QuerySet

# Example method with type hints:
def can_transition_to(self, new_status: str) -> bool:
    """Check if transition to new status is allowed."""
    return new_status in self.ALLOWED_TRANSITIONS.get(self.status, [])

@property
def progress_percentage(self) -> float:
    """Calculate review progress as a percentage."""
    if self.total_results == 0:
        return 0.0
    return round((self.reviewed_results / self.total_results) * 100, 1)

@classmethod
def log_activity(
    cls, 
    session: 'SearchSession', 
    activity_type: str, 
    description: str, 
    user: Optional['User'] = None, 
    metadata: Optional[Dict[str, Any]] = None
) -> 'SessionActivity':
    """Convenience method to log an activity."""
    # implementation
```

## 2. Pydantic Schemas Strategy

### When to Create Schemas

**Create schemas ONLY when you're building the view/API that needs them.**

### Schema Naming Convention

- **Input**: `Create{Model}Schema`, `Update{Model}Schema`
- **Output**: `{Model}ResponseSchema`, `{Model}ListResponseSchema`
- **Shared**: `{Model}BaseSchema` (for common fields)

### Basic Schema Template

```python
# apps/{app_name}/schemas.py
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

# Base schema with common fields
class SessionBaseSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None

# Input schema for creation
class CreateSessionSchema(SessionBaseSchema):
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None

# Input schema for updates  
class UpdateSessionSchema(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None

# Output schema for responses
class SessionResponseSchema(SessionBaseSchema):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    status: str
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
    progress_percentage: float
    
# List response with pagination
class SessionListResponseSchema(BaseModel):
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: List[SessionResponseSchema]
```

## 3. Incremental Implementation Guide

### Week 1-2: Foundation
1. Add type hints to methods as you implement views
2. Create schemas for your first API endpoint
3. Add `from typing import ...` to files you're working on

### Week 3-4: Expansion
1. Type hints for any methods you're testing
2. Schemas for CRUD operations you're building
3. Basic validation rules in schemas

### Week 5+: Refinement
1. Type hints for utility methods and helpers
2. Advanced schema validators for business logic
3. Reusable schema mixins for common patterns

## 4. Practical Examples by App

### When implementing SearchSession views:

```python
# apps/review_manager/schemas.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class CreateSessionSchema(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    tags: List[str] = Field(default_factory=list)
    
    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()

# In your view:
def create_session(request):
    # Parse and validate input
    schema = CreateSessionSchema(**request.POST)
    
    # Create session with validated data
    session = SearchSession.objects.create(
        title=schema.title,
        description=schema.description,
        tags=schema.tags,
        owner=request.user
    )
    
    # Return response using output schema
    return SessionResponseSchema.model_validate(session)
```

### When implementing Search Query views:

```python
# apps/search_strategy/schemas.py
class PICFrameworkSchema(BaseModel):
    population: str = Field(..., min_length=1)
    interest: str = Field(..., min_length=1)
    context: str = Field(..., min_length=1)

class CreateQuerySchema(PICFrameworkSchema):
    session_id: UUID
    max_results: int = Field(100, ge=1, le=1000)
```

## 5. Testing Type Hints

### Using mypy (optional for now)

```bash
# Install mypy
pip install mypy django-stubs

# Check a single file
mypy apps/review_manager/models.py

# Check an app
mypy apps/review_manager/

# Ignore missing imports
mypy apps/ --ignore-missing-imports
```

## 6. Common Type Hint Patterns

```python
# Django QuerySet
from django.db.models import QuerySet

def get_active_sessions(self) -> QuerySet['SearchSession']:
    return self.search_sessions.filter(status='active')

# Optional returns
def get_latest_result(self) -> Optional['ProcessedResult']:
    return self.processed_results.order_by('-created_at').first()

# Multiple return types
def process_result(self) -> Union[ProcessedResult, None]:
    # returns ProcessedResult or None

# Method with no return
def update_metrics(self) -> None:
    # updates internal state

# Callable types
from typing import Callable

def apply_filter(
    self, 
    filter_func: Callable[['ProcessedResult'], bool]
) -> List['ProcessedResult']:
    return [r for r in self.results if filter_func(r)]
```

## 7. Quick Reference Card

### For Every New Method
```python
def method_name(self, param: str, optional: Optional[int] = None) -> bool:
    """Docstring here."""
    pass
```

### For Every New Schema
```python
class CreateModelSchema(BaseModel):
    field: type = Field(..., description="help")
    optional_field: Optional[type] = None
```

### Common Imports
```python
from typing import List, Dict, Optional, Any, Union, Tuple
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
```

## Remember

- Type hints are documentation that runs
- Pydantic schemas are validation that prevents bugs
- Add them as you go, not all at once
- Perfect is the enemy of good enough

Start with the methods you're writing today!