# Results Manager App Refactoring Plan

**Generated**: 2025-07-26  
**Scope**: apps/results_manager app quick refactoring opportunities  
**Focus**: Vertical slice boundaries, single responsibility, type safety with Pydantic v2  
**Time Estimate**: Each item designed to be completed in <1 hour  

## Executive Summary

The `results_manager` app is generally well-structured but has several refactoring opportunities to improve code quality, maintainability, and alignment with vertical slice architecture principles. This analysis identified 18 specific refactoring opportunities prioritized by impact and implementation effort.

## 1. Functions >20 Lines That Need Decomposition

### HIGH PRIORITY: DuplicateGroup.merge_results() [~50 lines]
**Location**: `/mnt/d/Python/Projects/django/HTA-projects/agent-grey/apps/results_manager/models.py:177-227`

**Why it's a problem**:
- Violates single responsibility (finds best result + merges data + updates sources)
- Complex nested logic makes testing difficult
- No error handling for edge cases
- Hard to extend for new merge strategies

**Specific fix**:
```python
# In apps/results_manager/models.py
class DuplicateGroup(models.Model):
    # ... existing code ...
    
    def merge_results(self) -> None:
        """Merge duplicate results, keeping the best version."""
        results = self.results.select_related("raw_result__execution").all()
        if results.count() <= 1:
            return
        
        best_result = self._find_best_result(results)
        if best_result:
            self._merge_metadata_into_best(best_result, results)
            self._update_sources(results)
            best_result.save()
            self.save()
    
    def _find_best_result(self, results: models.QuerySet) -> Optional['ProcessedResult']:
        """Find the result with the highest quality score."""
        best_result = None
        best_score = -1
        
        for result in results:
            score = self._calculate_quality_score(result)
            if score > best_score:
                best_score = score
                best_result = result
        
        return best_result
    
    def _calculate_quality_score(self, result: 'ProcessedResult') -> int:
        """Calculate quality score based on available metadata."""
        score = 0
        if result.snippet:
            score += 1
        if result.authors:
            score += 2
        if result.publication_date:
            score += 2
        if result.is_pdf:
            score += 2
        return score
    
    def _merge_metadata_into_best(self, best_result: 'ProcessedResult', all_results: models.QuerySet) -> None:
        """Merge missing metadata from other results into the best result."""
        for result in all_results:
            if result != best_result:
                if not best_result.snippet and result.snippet:
                    best_result.snippet = result.snippet
                if not best_result.authors and result.authors:
                    best_result.authors = result.authors
    
    def _update_sources(self, results: models.QuerySet) -> None:
        """Update the sources list with search engines from all results."""
        for result in results:
            if (result.raw_result 
                and result.raw_result.execution.search_engine 
                and result.raw_result.execution.search_engine not in self.sources):
                self.sources.append(result.raw_result.execution.search_engine)
```

**Priority**: HIGH (complex business logic that's hard to test)

### MEDIUM PRIORITY: ProcessingAnalyticsService.export_results_summary() [60 lines]
**Location**: `/mnt/d/Python/Projects/django/HTA-projects/agent-grey/apps/results_manager/services/processing_analytics_service.py:126-185`

**Why it's a problem**:
- Mixes data retrieval, processing, and formatting
- Complex nested data structure construction
- Multiple responsibilities in one method

**Specific fix**:
```python
# In apps/results_manager/services/processing_analytics_service.py
def export_results_summary(self, session_id: str) -> Dict[str, Any]:
    """Export a comprehensive summary of processed results."""
    stats = self.get_processing_statistics(session_id)
    sample_results = self._get_sample_results_by_type(session_id, stats)
    all_results = self._get_formatted_results_list(session_id)
    
    return self._build_export_summary(session_id, stats, sample_results, all_results)

def _get_sample_results_by_type(self, session_id: str, stats: Dict[str, Any]) -> Dict[str, List[Dict]]:
    """Get sample results for each document type."""
    from ..models import ProcessedResult
    
    results = ProcessedResult.objects.filter(session_id=session_id)
    sample_results = {}
    
    for doc_type in stats["document_types"].keys():
        samples = results.filter(document_type=doc_type).order_by(
            "-publication_year", "-is_pdf"
        )[:ProcessingConstants.SAMPLE_RESULTS_LIMIT]
        
        sample_results[doc_type] = [
            self._format_sample_result(result) for result in samples
        ]
    
    return sample_results

def _format_sample_result(self, result) -> Dict[str, Any]:
    """Format a single result for sample display."""
    return {
        "title": result.title,
        "url": result.url,
        "publication_year": result.publication_year,
        "is_pdf": result.is_pdf,
    }

def _get_formatted_results_list(self, session_id: str) -> List[Dict[str, Any]]:
    """Get all results formatted for export."""
    from ..models import ProcessedResult
    
    results = ProcessedResult.objects.filter(session_id=session_id).order_by(
        "-publication_year", "title"
    )
    
    return [self._format_full_result(result) for result in results]

def _format_full_result(self, result) -> Dict[str, Any]:
    """Format a single result for full export."""
    return {
        "title": result.title,
        "url": result.url,
        "snippet": (
            result.snippet[:200] + "..." if len(result.snippet) > 200 
            else result.snippet
        ),
        "publication_year": result.publication_year,
        "source_organization": result.source_organization,
        "is_pdf": result.is_pdf,
        "is_duplicate": bool(result.duplicate_group),
    }

def _build_export_summary(self, session_id: str, stats: Dict, samples: Dict, results: List) -> Dict[str, Any]:
    """Build the final export summary structure."""
    return {
        "session_id": session_id,
        "total_results": len(results),
        "basic_stats": {
            "total": stats["total_results"],
            "duplicates": stats["duplicate_groups"],
            "pdf_count": stats.get("pdf_count", 0),
        },
        "sample_results": samples,
        "results": results,
        "export_timestamp": timezone.now().isoformat(),
    }
```

**Priority**: MEDIUM

### MEDIUM PRIORITY: process_session_results_task() [100+ lines]
**Location**: `/mnt/d/Python/Projects/django/HTA-projects/agent-grey/apps/results_manager/tasks.py:29-131`

**Why it's a problem**:
- Orchestrates multiple concerns (validation, setup, workflow creation)
- Complex error handling mixed with business logic
- Hard to test individual components

**Specific fix**:
```python
# In apps/results_manager/tasks.py
@shared_task(bind=True, max_retries=MAX_RETRIES)
def process_session_results_task(self, session_id: str) -> Dict[str, Any]:
    """Main orchestration task for processing all results for a search session."""
    logger.info(f"Starting results processing for session {session_id}")
    
    try:
        session_processor = SessionProcessor(session_id, self)
        return session_processor.process()
    except Exception as exc:
        return session_processor.handle_error(exc)


class SessionProcessor:
    """Handles the orchestration of session result processing."""
    
    def __init__(self, session_id: str, task_instance):
        self.session_id = session_id
        self.task_instance = task_instance
        self.session = None
        self.processing_session = None
    
    def process(self) -> Dict[str, Any]:
        """Execute the processing workflow."""
        self._load_session()
        
        if self._is_already_completed():
            return self._completed_response()
        
        raw_results = self._get_raw_results()
        if not raw_results.exists():
            return self._no_results_response()
        
        self._setup_processing(raw_results.count())
        workflow = self._create_workflow()
        
        return self._started_response(raw_results.count(), workflow.id)
    
    def _load_session(self) -> None:
        """Load and validate the session."""
        self.session = SearchSession.objects.get(id=self.session_id)
        self.processing_session, created = ProcessingSession.objects.get_or_create(
            search_session=self.session, defaults={"status": "pending"}
        )
    
    def _is_already_completed(self) -> bool:
        """Check if processing is already completed."""
        return self.processing_session.status == "completed"
    
    def _get_raw_results(self) -> QuerySet:
        """Get raw results that need processing."""
        return RawSearchResult.objects.filter(
            execution__query__session=self.session, is_processed=False
        ).select_related("execution", "execution__query")
    
    def _setup_processing(self, total_results: int) -> None:
        """Setup processing session and update session status."""
        self.session.status = "processing_results"
        self.session.save(update_fields=["status"])
        
        self.processing_session.start_processing(
            total_raw_results=total_results, 
            celery_task_id=self.task_instance.request.id
        )
    
    def _create_workflow(self):
        """Create the processing workflow."""
        return create_processing_workflow.delay(
            session_id=self.session_id, 
            processing_session_id=str(self.processing_session.id)
        )
    
    def handle_error(self, exc: Exception) -> Dict[str, Any]:
        """Handle processing errors with retry logic."""
        logger.error(f"Error starting processing for session {self.session_id}: {str(exc)}")
        
        self._mark_processing_failed(exc)
        
        if self._should_retry():
            return self._retry_with_backoff(exc)
        
        return {"status": "failed", "error": str(exc)}
```

**Priority**: MEDIUM

## 2. Missing Constants Causing Import Errors

### HIGH PRIORITY: Complete DeduplicationConstants
**Location**: `/mnt/d/Python/Projects/django/HTA-projects/agent-grey/apps/results_manager/constants.py`

**Why it's a problem**:
- Missing constants referenced in deduplication_service.py cause import errors
- Hardcoded magic numbers reduce maintainability
- No centralized configuration

**Specific fix**:
```python
# In apps/results_manager/constants.py
class DeduplicationConstants:
    """Constants for deduplication service."""

    # Similarity thresholds
    DEFAULT_SIMILARITY_THRESHOLD: float = 0.85
    TITLE_SIMILARITY_THRESHOLD: float = 0.8
    FUZZY_MATCH_THRESHOLD: float = 0.7
    CONTENT_HASH_THRESHOLD: float = 0.9
    EXACT_URL_CONFIDENCE: float = 1.0
    
    # URL normalization
    TRACKING_PARAMS: Set[str] = {
        "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
        "gclid", "fbclid", "ref", "source", "medium", "campaign"
    }
    DEFAULT_PATH: str = "/"
    WWW_PREFIX: str = "www."
    
    # Text processing
    MIN_WORD_LENGTH: int = 3
    STOP_WORDS: Set[str] = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
        "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
        "to", "was", "will", "with", "the", "this", "these", "those"
    }


class ProcessingConstants:
    """Constants for processing services."""

    # Batch processing
    DEFAULT_BATCH_SIZE: int = 50
    SAMPLE_RESULTS_LIMIT: int = 5
    
    # Percentage calculations
    PERCENTAGE_MULTIPLIER: int = 100
    DECIMAL_PLACES: Dict[str, int] = {
        "percentage": 1,
        "score": 2,
        "ratio": 3
    }
    
    # Statistics defaults
    EMPTY_STATS_DEFAULTS: Dict[str, int] = {
        "total_results": 0,
        "processed_results": 0,
        "duplicate_groups": 0,
        "unique_results": 0,
        "document_types": {},
        "publication_years": {},
        "pdf_count": 0,
        "academic_results": 0,
        "pdf_percentage": 0,
        "academic_percentage": 0
    }


class QualityConstants:
    """Constants for quality assessment."""
    
    # Thresholds
    MAX_QUALITY_SCORE: float = 10.0
    MAX_SCORE: float = 1.0
    RECENT_PUBLICATION_THRESHOLD: int = 2020
    MODERATELY_RECENT_THRESHOLD: int = 2015
    MIN_TITLE_LENGTH: int = 10
    MIN_SNIPPET_LENGTH: int = 50
    
    # Quality scoring weights
    QUALITY_SCORES: Dict[str, float] = {
        "full_text_available": 3.0,
        "pdf_format": 2.0,
        "recent_publication": 2.0,
        "moderately_recent": 1.0,
        "good_title": 1.0,
        "good_snippet": 1.0
    }
```

**Priority**: HIGH (fixes import errors)

## 3. Cross-Feature Imports Violating Vertical Slices

### MEDIUM PRIORITY: Remove direct model imports in tasks.py
**Location**: `/mnt/d/Python/Projects/django/HTA-projects/agent-grey/apps/results_manager/tasks.py`

**Why it's a problem**:
- Direct imports from `apps.review_manager.models` and `apps.serp_execution.models`
- Violates vertical slice boundaries
- Creates tight coupling between apps

**Specific fix**:
```python
# In apps/results_manager/tasks.py - Replace direct model imports
# OLD:
from apps.review_manager.models import SearchSession
from apps.serp_execution.models import RawSearchResult

# NEW: Use dependency injection through services
from .services.session_interface import SessionServiceInterface
from .services.raw_result_interface import RawResultServiceInterface

# In apps/results_manager/services/session_interface.py (NEW FILE)
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class SessionServiceInterface(ABC):
    """Interface for session-related operations."""
    
    @abstractmethod
    def get_session(self, session_id: str) -> Any:
        """Get session by ID."""
        pass
    
    @abstractmethod
    def update_session_status(self, session_id: str, status: str) -> None:
        """Update session status."""
        pass

# In apps/results_manager/services/session_adapter.py (NEW FILE)
from apps.review_manager.models import SearchSession
from .session_interface import SessionServiceInterface

class DjangoSessionAdapter(SessionServiceInterface):
    """Django ORM adapter for session operations."""
    
    def get_session(self, session_id: str) -> SearchSession:
        return SearchSession.objects.get(id=session_id)
    
    def update_session_status(self, session_id: str, status: str) -> None:
        session = self.get_session(session_id)
        session.status = status
        session.save(update_fields=["status"])

# Usage in tasks.py:
session_service = DjangoSessionAdapter()
session = session_service.get_session(session_id)
```

**Priority**: MEDIUM (improves architecture)

## 4. Missing Type Hints

### HIGH PRIORITY: Add comprehensive type hints to models.py
**Location**: `/mnt/d/Python/Projects/django/HTA-projects/agent-grey/apps/results_manager/models.py`

**Why it's a problem**:
- Missing return types on many methods
- No type hints on method parameters
- Reduces IDE support and type safety

**Specific fix**:
```python
# In apps/results_manager/models.py
from typing import Any, Dict, List, Optional, Union
from django.db import models
from django.http import QueryDict

class ProcessingSession(models.Model):
    # ... existing fields ...
    
    def __str__(self) -> str:
        return f"Processing {self.search_session.title} - {self.get_status_display()}"
    
    @property
    def progress_percentage(self) -> int:
        """Calculate overall progress percentage."""
        if self.total_raw_results == 0:
            return 0
        return min(100, int((self.processed_count / self.total_raw_results) * 100))
    
    def update_heartbeat(self) -> None:
        """Update the last heartbeat timestamp."""
        self.last_heartbeat = timezone.now()
        self.save(update_fields=["last_heartbeat"])
    
    def start_processing(self, total_raw_results: int, celery_task_id: str) -> None:
        """Start the processing session."""
        self.status = "in_progress"
        self.total_raw_results = total_raw_results
        self.celery_task_id = celery_task_id
        self.started_at = timezone.now()
        self.save()
    
    def update_progress(
        self, 
        stage: str, 
        stage_progress: int, 
        processed_count: Optional[int] = None,
        error_count: Optional[int] = None,
        duplicate_count: Optional[int] = None
    ) -> None:
        """Update processing progress."""
        self.current_stage = stage
        self.stage_progress = max(0, min(100, stage_progress))
        
        if processed_count is not None:
            self.processed_count = processed_count
        if error_count is not None:
            self.error_count = error_count
        if duplicate_count is not None:
            self.duplicate_count = duplicate_count
            
        self.update_heartbeat()
    
    def complete_processing(self) -> None:
        """Mark processing as completed."""
        self.status = "completed"
        self.completed_at = timezone.now()
        self.current_stage = "finalization"
        self.stage_progress = 100
        self.save()
    
    def fail_processing(self, error_message: str, error_details: Optional[Dict[str, Any]] = None) -> None:
        """Mark processing as failed."""
        self.status = "failed"
        self.completed_at = timezone.now()
        
        error_entry = {
            "timestamp": timezone.now().isoformat(),
            "message": error_message,
            "details": error_details or {}
        }
        
        if not self.error_details:
            self.error_details = []
        self.error_details.append(error_entry)
        self.error_count += 1
        
        self.save()
    
    def add_error(self, error_message: str, error_details: Optional[Dict[str, Any]] = None) -> None:
        """Add an error without failing the entire processing."""
        error_entry = {
            "timestamp": timezone.now().isoformat(),
            "message": error_message,
            "details": error_details or {}
        }
        
        if not self.error_details:
            self.error_details = []
        self.error_details.append(error_entry)
        self.error_count += 1
        self.save(update_fields=["error_details", "error_count"])

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate processing duration in seconds."""
        if not self.started_at:
            return None
        
        end_time = self.completed_at or timezone.now()
        return (end_time - self.started_at).total_seconds()
    
    @property
    def estimated_completion(self) -> Optional[timezone.datetime]:
        """Estimate completion time based on current progress."""
        if (not self.started_at 
            or self.progress_percentage == 0 
            or self.status in ["completed", "failed"]):
            return None
        
        elapsed = timezone.now() - self.started_at
        total_estimated = elapsed * (100 / self.progress_percentage)
        return self.started_at + total_estimated
```

**Priority**: HIGH (critical for code quality)

## 5. Single Responsibility Violations

### MEDIUM PRIORITY: Extract quality scoring logic from QualityAssessmentService
**Location**: `/mnt/d/Python/Projects/django/HTA-projects/agent-grey/apps/results_manager/services/quality_assessment_service.py`

**Why it's a problem**:
- assess_document_quality() mixes quality calculation with formatting
- Single method handles multiple quality factors
- Hard to extend with new quality metrics

**Specific fix**:
```python
# In apps/results_manager/services/quality_assessment_service.py
class QualityAssessmentService(ServiceLoggerMixin):
    """Service for assessing result quality and calculating relevance scores."""
    
    def __init__(self):
        self.scorer = QualityScorer()
        self.formatter = QualityFormatter()
    
    def assess_document_quality(self, result) -> Dict[str, Any]:
        """Assess overall document quality indicators."""
        quality_metrics = self.scorer.calculate_all_metrics(result)
        return self.formatter.format_assessment(quality_metrics)


class QualityScorer:
    """Handles quality score calculations."""
    
    def calculate_all_metrics(self, result) -> Dict[str, Any]:
        """Calculate all quality metrics for a result."""
        metrics = {
            "full_text_score": self._score_full_text_availability(result),
            "format_score": self._score_document_format(result),
            "recency_score": self._score_publication_recency(result),
            "content_score": self._score_content_quality(result),
            "metadata_score": self._score_metadata_completeness(result)
        }
        
        metrics["total_score"] = sum(metrics.values())
        metrics["max_possible"] = QualityConstants.MAX_QUALITY_SCORE
        metrics["normalized_score"] = min(1.0, metrics["total_score"] / metrics["max_possible"])
        
        return metrics
    
    def _score_full_text_availability(self, result) -> float:
        """Score based on full text availability."""
        return QualityConstants.QUALITY_SCORES["full_text_available"] if result.has_full_text else 0.0
    
    def _score_document_format(self, result) -> float:
        """Score based on document format."""
        return QualityConstants.QUALITY_SCORES["pdf_format"] if result.is_pdf else 0.0
    
    def _score_publication_recency(self, result) -> float:
        """Score based on publication recency."""
        if not result.publication_year:
            return 0.0
        
        if result.publication_year >= QualityConstants.RECENT_PUBLICATION_THRESHOLD:
            return QualityConstants.QUALITY_SCORES["recent_publication"]
        elif result.publication_year >= QualityConstants.MODERATELY_RECENT_THRESHOLD:
            return QualityConstants.QUALITY_SCORES["moderately_recent"]
        return 0.0
    
    def _score_content_quality(self, result) -> float:
        """Score based on content quality indicators."""
        score = 0.0
        
        if result.title and len(result.title) >= QualityConstants.MIN_TITLE_LENGTH:
            score += QualityConstants.QUALITY_SCORES["good_title"]
        
        if result.snippet and len(result.snippet) >= QualityConstants.MIN_SNIPPET_LENGTH:
            score += QualityConstants.QUALITY_SCORES["good_snippet"]
        
        return score
    
    def _score_metadata_completeness(self, result) -> float:
        """Score based on metadata completeness."""
        # This could be expanded with more metadata checks
        return 0.0


class QualityFormatter:
    """Handles formatting of quality assessments."""
    
    def format_assessment(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Format quality metrics into user-friendly assessment."""
        quality_factors = self._extract_quality_factors(metrics)
        concerns = self._extract_concerns(metrics)
        
        return {
            "overall_score": metrics["normalized_score"],
            "quality_factors": quality_factors,
            "concerns": concerns,
            "detailed_scores": {
                k: v for k, v in metrics.items() 
                if k.endswith("_score") and k != "normalized_score"
            }
        }
    
    def _extract_quality_factors(self, metrics: Dict[str, Any]) -> List[str]:
        """Extract positive quality factors."""
        factors = []
        
        if metrics["full_text_score"] > 0:
            factors.append("Full text available")
        if metrics["format_score"] > 0:
            factors.append("PDF format")
        if metrics["recency_score"] > 0:
            factors.append("Recent/moderately recent publication")
        if metrics["content_score"] > 0:
            factors.append("Good title and snippet")
        
        return factors
    
    def _extract_concerns(self, metrics: Dict[str, Any]) -> List[str]:
        """Extract quality concerns."""
        concerns = []
        
        if metrics["full_text_score"] == 0:
            concerns.append("No full text available")
        if metrics["recency_score"] == 0:
            concerns.append("Older or undated publication")
        if metrics["content_score"] < QualityConstants.QUALITY_SCORES["good_title"]:
            concerns.append("Poor or missing title/snippet")
        
        return concerns
```

**Priority**: MEDIUM

## 6. Pydantic v2 Schema Improvements

### MEDIUM PRIORITY: Enhance ProcessedResultResponse schema validation
**Location**: `/mnt/d/Python/Projects/django/HTA-projects/agent-grey/apps/results_manager/schemas.py`

**Why it's a problem**:
- Schema doesn't match actual model fields
- Missing validation for URLs and dates
- No computed field validation

**Specific fix**:
```python
# In apps/results_manager/schemas.py - Update existing schema
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, computed_field
from pydantic_core import ValidationError

class ProcessedResultResponse(BaseModel):
    """Enhanced schema for processed result responses with validation."""

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    # Primary fields
    id: UUID
    session_id: UUID
    title: str = Field(..., min_length=1, max_length=2000)
    url: str = Field(..., description="Canonical URL")
    snippet: str = Field(default="", max_length=5000)
    
    # Metadata fields
    authors: List[str] = Field(default_factory=list)
    publication_date: Optional[date] = None
    publication_year: Optional[int] = Field(None, ge=1900, le=2030)
    document_type: str = Field(default="", max_length=50)
    language: str = Field(default="en", max_length=10)
    source_organization: str = Field(default="", max_length=255)
    
    # Content indicators
    full_text_url: str = Field(default="", description="Direct link to full text")
    is_pdf: bool = False
    
    # Processing metadata
    processed_at: datetime
    is_reviewed: bool = False
    
    # Relationships
    duplicate_group_id: Optional[UUID] = None
    
    # Timestamps
    created_at: datetime
    updated_at: datetime

    @field_validator('url', 'full_text_url')
    @classmethod
    def validate_urls(cls, v: str) -> str:
        """Validate URL format."""
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('URL must start with http:// or https://')
        return v

    @field_validator('publication_year')
    @classmethod
    def validate_publication_year_consistency(cls, v: Optional[int], info) -> Optional[int]:
        """Ensure publication year matches publication date if both exist."""
        if v and 'publication_date' in info.data and info.data['publication_date']:
            if v != info.data['publication_date'].year:
                raise ValueError('Publication year must match publication date year')
        return v

    @computed_field
    @property
    def has_full_text(self) -> bool:
        """Check if full text is available."""
        return self.is_pdf or bool(self.full_text_url)
    
    @computed_field  
    @property
    def display_url(self) -> str:
        """Get shortened display version of URL."""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(self.url)
            return parsed.netloc
        except Exception:
            return self.url
    
    @computed_field
    @property
    def is_duplicate(self) -> bool:
        """Check if this result is part of a duplicate group."""
        return self.duplicate_group_id is not None


class ProcessedResultCreate(BaseModel):
    """Schema for creating processed results."""
    
    session_id: UUID
    raw_result_id: Optional[UUID] = None
    title: str = Field(..., min_length=1, max_length=2000)
    url: str = Field(..., description="Canonical URL")
    snippet: str = Field(default="", max_length=5000)
    
    # Optional metadata
    authors: List[str] = Field(default_factory=list)
    publication_date: Optional[date] = None
    document_type: str = Field(default="", max_length=50)
    language: str = Field(default="en", max_length=10)
    source_organization: str = Field(default="", max_length=255)
    
    # Content indicators  
    full_text_url: str = Field(default="")
    is_pdf: bool = False

    @field_validator('url', 'full_text_url')
    @classmethod
    def validate_urls(cls, v: str) -> str:
        """Validate URL format."""
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('URL must start with http:// or https://')
        return v


class ProcessedResultUpdate(BaseModel):
    """Schema for updating processed results."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=2000)
    snippet: Optional[str] = Field(None, max_length=5000)
    authors: Optional[List[str]] = None
    publication_date: Optional[date] = None
    document_type: Optional[str] = Field(None, max_length=50)
    source_organization: Optional[str] = Field(None, max_length=255)
    is_reviewed: Optional[bool] = None
```

**Priority**: MEDIUM

## Summary Action Plan

### Immediate Actions (Complete First):
1. **Fix missing constants** - Complete DeduplicationConstants and ProcessingConstants (30 mins)
2. **Add type hints to models** - Focus on ProcessingSession methods (45 mins)
3. **Decompose DuplicateGroup.merge_results()** - Break into smaller methods (45 mins)

### Next Sprint:
1. **Extract quality scoring logic** - Separate QualityScorer and QualityFormatter (1 hour)
2. **Add comprehensive type hints** - Complete all model methods (45 mins)
3. **Enhance Pydantic schemas** - Add validation and computed fields (45 mins)

### Future Improvements:
1. Replace cross-app imports with dependency injection (1-2 hours)
2. Decompose large task functions using processor classes (1-2 hours)
3. Add service layer abstractions for better testability (2 hours)

## Validation Checklist

After each refactoring:
- [ ] Run all tests: `python manage.py test apps.results_manager`
- [ ] Check type hints: `mypy apps/results_manager/`
- [ ] Verify imports: `python -c "import apps.results_manager.models; print('OK')"`
- [ ] Run linter: `flake8 apps/results_manager/ --max-line-length=120`
- [ ] Test processing pipeline: Run a small processing task
- [ ] Verify constants: `python -c "from apps.results_manager.constants import *; print('OK')"`

## Risk Assessment

**Low Risk Refactorings**:
- Adding missing constants
- Adding type hints
- Breaking down long methods

**Medium Risk Refactorings**:
- Changing service architectures
- Modifying task orchestration
- Schema validation changes

**High Risk Refactorings**:
- Cross-app dependency injection
- Major task refactoring
- Model relationship changes

Focus on low-risk, high-impact changes first to build confidence and demonstrate value.