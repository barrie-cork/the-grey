# Quick Refactoring Plan - Python Code Quality

## Overview
This plan focuses on actionable refactoring items that can be completed in <1 hour each, prioritizing vertical slice boundaries, function complexity, and type safety with Pydantic v2.

## High Priority Issues

### 1. Long Functions (>20 lines) - Critical

#### 1.1 `process_session_results_task` - 101 lines
**Location**: `apps/results_manager/tasks.py:18-119`
**Problem**: Function handles too many responsibilities - fetching, processing, deduplication, and error handling
**Fix**: Decompose into smaller functions:
```python
# apps/results_manager/tasks.py
def process_session_results_task(session_id: str):
    """Process results - orchestrator function."""
    session = _get_session_or_fail(session_id)
    raw_results = _fetch_raw_results(session)
    processed_results = _process_results_batch(raw_results, session)
    _handle_deduplication(processed_results, session)
    _update_session_status(session)

def _get_session_or_fail(session_id: str) -> SearchSession:
    """Get session with proper error handling."""
    # Implementation here (5-10 lines)

def _fetch_raw_results(session: SearchSession) -> QuerySet:
    """Fetch raw results with optimization."""
    # Implementation here (10-15 lines)
```
**Priority**: HIGH - Core functionality, impacts performance

#### 1.2 `generate_query_optimization_report` - 97 lines
**Location**: `apps/reporting/services/performance_analytics_service.py:142-239`
**Problem**: Complex report generation with nested loops and conditions
**Fix**: Extract report sections into separate methods:
```python
class PerformanceAnalyticsService:
    def generate_query_optimization_report(self, session_id: str) -> dict:
        """Generate optimization report - orchestrator."""
        session = self._get_session(session_id)
        return {
            'summary': self._generate_summary(session),
            'query_performance': self._analyze_query_performance(session),
            'bottlenecks': self._identify_bottlenecks(session),
            'recommendations': self._generate_recommendations(session)
        }
```
**Priority**: HIGH - Performance critical

### 2. Cross-Feature Import Violations

#### 2.1 Core Signals Importing from Multiple Apps
**Location**: `apps/core/signals.py`
**Problem**: Core module imports from 4 different apps, creating circular dependency risk
**Fix**: Use Django's app registry for dynamic imports:
```python
# apps/core/signals.py
from django.apps import apps

def get_model_dynamically(app_label: str, model_name: str):
    """Dynamically import models to avoid circular imports."""
    return apps.get_model(app_label, model_name)

# Usage
SearchSession = get_model_dynamically('review_manager', 'SearchSession')
```
**Priority**: HIGH - Architecture integrity

#### 2.2 Reporting App Tight Coupling
**Location**: `apps/reporting/services/*.py`
**Problem**: Direct imports from all other apps
**Fix**: Create interfaces/contracts:
```python
# apps/reporting/interfaces.py
from typing import Protocol

class SessionDataProvider(Protocol):
    def get_session_data(self, session_id: str) -> dict: ...

class ResultsDataProvider(Protocol):
    def get_results_data(self, session_id: str) -> list: ...

# Use dependency injection in services
```
**Priority**: HIGH - Maintainability

### 3. Missing Pydantic Models for I/O

#### 3.1 Raw JSON Parsing in Search Strategy
**Location**: `apps/search_strategy/views.py:367`
**Problem**: Direct JSON parsing without validation
**Fix**: Add Pydantic model:
```python
# apps/search_strategy/schemas.py
from pydantic import BaseModel, validator

class QueryGenerationRequest(BaseModel):
    strategy_id: str
    template_ids: list[str]
    options: dict = {}
    
    @validator('template_ids')
    def validate_template_ids(cls, v):
        if not v:
            raise ValueError("At least one template required")
        return v

# apps/search_strategy/views.py:367
def generate_queries(self, request):
    data = QueryGenerationRequest(**request.data)
    # Use validated data
```
**Priority**: HIGH - Security/Data integrity

#### 3.2 Serper API Response Validation
**Location**: `apps/serp_execution/services/serper_client.py`
**Problem**: No validation of external API responses
**Fix**: Add response model:
```python
# apps/serp_execution/schemas.py
class SerperSearchResult(BaseModel):
    title: str
    link: str
    snippet: str = ""
    position: int
    
class SerperResponse(BaseModel):
    searchParameters: dict
    organic: list[SerperSearchResult]
    answerBox: dict = None
    
    class Config:
        extra = "ignore"  # Ignore unknown fields
```
**Priority**: HIGH - External API reliability

### 4. Classes with Multiple Responsibilities

#### 4.1 SerperClient Class
**Location**: `apps/serp_execution/services/serper_client.py`
**Problem**: Handles HTTP, rate limiting, caching, and error handling
**Fix**: Split into focused classes:
```python
# apps/serp_execution/services/http_client.py
class SerperHTTPClient:
    """Handle HTTP communication only."""
    def post(self, endpoint: str, data: dict) -> dict:
        # HTTP logic only

# apps/serp_execution/services/rate_limiter.py  
class RateLimiter:
    """Handle rate limiting logic."""
    def check_rate_limit(self) -> bool:
        # Rate limit logic

# apps/serp_execution/services/serper_client.py
class SerperClient:
    """Orchestrate search operations."""
    def __init__(self, http_client: SerperHTTPClient, rate_limiter: RateLimiter):
        self.http = http_client
        self.limiter = rate_limiter
```
**Priority**: MEDIUM - Clean architecture

### 5. Long Files Needing Decomposition

#### 5.1 `test_user_criteria.py` - 730 lines
**Location**: `apps/review_manager/test_user_criteria.py`
**Problem**: All UC tests in one file
**Fix**: Split by UC category:
```
tests/
├── test_uc1_authentication.py
├── test_uc2_session_management.py
├── test_uc3_search_strategy.py
└── test_uc4_execution.py
```
**Priority**: MEDIUM - Test maintainability

### 6. Missing Type Hints

#### 6.1 Template Tags
**Location**: All `templatetags/*.py` files
**Problem**: No type hints on template tag functions
**Fix**: Add type annotations:
```python
# apps/review_manager/templatetags/session_tags.py
from django import template
from typing import Any, Optional

register = template.Library()

@register.filter
def format_status(status: str) -> str:
    """Format session status for display."""
    return status.replace('_', ' ').title()

@register.simple_tag
def session_progress(session: Any) -> int:
    """Calculate session progress percentage."""
    # Implementation
```
**Priority**: LOW - Developer experience

### 7. Hardcoded Configuration Values - Critical

#### 7.1 Hardcoded Search Parameters
**Location**: `apps/serp_execution/tasks.py:177-183`
**Problem**: Hardcoded search parameters (location="United States", language="en", num=100) prevent flexibility and future configuration panel
**Fix**: Create centralized configuration system:
```python
# apps/core/config.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import json
from django.conf import settings

class SearchConfig(BaseModel):
    """Centralized search configuration."""
    default_num_results: int = Field(default=100, ge=1, le=100)
    default_location: Optional[str] = Field(default=None)
    default_language: str = Field(default="en")
    default_file_types: list[str] = Field(default_factory=lambda: ["pdf"])
    
class APIConfig(BaseModel):
    """API-specific configurations."""
    serper_timeout: int = Field(default=30)
    serper_max_retries: int = Field(default=3)
    rate_limit_per_minute: int = Field(default=100)
    
class SystemConfig(BaseModel):
    """System-wide configuration."""
    search: SearchConfig = Field(default_factory=SearchConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    batch_size: int = Field(default=50)
    cache_ttl: int = Field(default=3600)
    
    @classmethod
    def load_from_settings(cls) -> "SystemConfig":
        """Load configuration from Django settings or defaults."""
        config_dict = getattr(settings, 'THESIS_GREY_CONFIG', {})
        return cls(**config_dict)
    
    def save_to_db(self):
        """Save configuration to database for UI editing."""
        from apps.core.models import Configuration
        Configuration.objects.update_or_create(
            key="system_config",
            defaults={"value": self.dict()}
        )

# Singleton instance
config = SystemConfig.load_from_settings()

# apps/serp_execution/tasks.py - Updated usage
from apps.core.config import config

# In perform_serp_query_task
strategy = query.strategy
search_config = strategy.search_config or {}

api_params = {
    "q": search_query,
    "num": search_config.get("num_results", config.search.default_num_results),
    "location": search_config.get("location", config.search.default_location),
    "language": search_config.get("language", config.search.default_language),
    "file_types": search_config.get("file_types", config.search.default_file_types),
}
```
**Priority**: HIGH - Enables future configuration UI

#### 7.2 Hardcoded Batch Sizes
**Location**: Multiple locations (`results_manager/tasks.py`, `serp_execution/services/result_processor.py`)
**Problem**: Hardcoded batch_size=50 in multiple places
**Fix**: Use centralized config:
```python
# apps/results_manager/tasks.py
from apps.core.config import config

# Replace hardcoded 50 with
batch_size = config.batch_size
```
**Priority**: MEDIUM - Performance tuning

#### 7.3 Hardcoded Cache TTL
**Location**: `apps/serp_execution/services/cache_manager.py`
**Problem**: Hardcoded cache expiration times
**Fix**: Use centralized config:
```python
# apps/serp_execution/services/cache_manager.py
from apps.core.config import config

def cache_result(self, key: str, value: Any):
    cache.set(key, value, timeout=config.cache_ttl)
```
**Priority**: MEDIUM - Performance optimization

#### 7.4 Database Model for Configuration
**Location**: New file needed
**Problem**: No way to store/edit configuration in database
**Fix**: Add Configuration model:
```python
# apps/core/models.py
from django.db import models
from django.core.serializers.json import DjangoJSONEncoder

class Configuration(models.Model):
    """Store system configuration for runtime editing."""
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField(encoder=DjangoJSONEncoder)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        'accounts.User', 
        on_delete=models.SET_NULL, 
        null=True
    )
    
    class Meta:
        db_table = 'core_configuration'
        
    @classmethod
    def get_config(cls, key: str, default=None):
        """Get configuration value by key."""
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default
```
**Priority**: HIGH - Required for configuration UI

## Quick Wins (<30 minutes each)

1. **Add Pydantic model for search strategy JSON** (HIGH)
   - Location: `apps/search_strategy/views.py:367`
   - Time: 20 minutes

2. **Create centralized config for search parameters** (HIGH)
   - Location: `apps/core/config.py` (new file)
   - Time: 30 minutes

3. **Extract rate limiter from SerperClient** (MEDIUM)
   - Location: `apps/serp_execution/services/serper_client.py`
   - Time: 30 minutes

4. **Fix circular import in core signals** (HIGH)
   - Location: `apps/core/signals.py`
   - Time: 25 minutes

5. **Replace hardcoded batch sizes with config** (MEDIUM)
   - Location: Multiple files
   - Time: 15 minutes

## Implementation Order

1. **Week 1**: Fix critical security/data integrity issues
   - Create centralized configuration system
   - Pydantic models for all external inputs
   - Fix cross-feature imports
   - Replace hardcoded values with config

2. **Week 2**: Decompose long functions
   - Focus on task processing functions
   - Split report generation methods

3. **Week 3**: Architecture improvements
   - Split classes with multiple responsibilities
   - Create proper interfaces
   - Add Configuration model for UI editing

4. **Week 4**: Code quality cleanup
   - Add missing type hints
   - Split long test files
   - Consolidate all remaining hardcoded values

## Success Metrics

- No functions >40 lines (target: <20 lines)
- All external inputs validated with Pydantic
- Zero cross-app imports in core module
- 100% type hints in new code
- All classes follow single responsibility principle
- Zero hardcoded configuration values
- Centralized config system ready for UI panel