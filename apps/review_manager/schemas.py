"""
Pydantic schemas for review_manager slice.
VSA-compliant type safety for data contracts.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SessionStatus(str, Enum):
    """Session status choices."""

    DRAFT = "draft"
    DEFINING_SEARCH = "defining_search"
    READY_TO_EXECUTE = "ready_to_execute"
    EXECUTING = "executing"
    PROCESSING_RESULTS = "processing_results"
    READY_FOR_REVIEW = "ready_for_review"
    UNDER_REVIEW = "under_review"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class SearchSessionCreate(BaseModel):
    """Schema for creating a new search session."""

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = Field(None, max_length=5000)


class SearchSessionUpdate(BaseModel):
    """Schema for updating a search session."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    tags: Optional[List[str]] = None
    notes: Optional[str] = Field(None, max_length=5000)


class SearchSessionResponse(BaseModel):
    """Schema for search session API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    description: Optional[str]
    status: SessionStatus
    owner_id: str
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    notes: Optional[str]
    tags: List[str]
    total_queries: int
    total_results: int
    reviewed_results: int
    included_results: int
    progress_percentage: float
    inclusion_rate: float
    is_active: bool
    can_edit: bool
    can_delete: bool


class SearchSessionSummary(BaseModel):
    """Schema for session summary/card display."""

    id: str
    title: str
    status: SessionStatus
    created_at: datetime
    total_results: int
    reviewed_results: int
    progress_percentage: float


class SessionStatusTransition(BaseModel):
    """Schema for status transition requests."""

    new_status: SessionStatus
    description: Optional[str] = Field(None, max_length=500)


class SessionActivity(BaseModel):
    """Schema for session activity entries."""

    id: str
    activity_type: str
    description: str
    user_id: Optional[str]
    metadata: dict
    created_at: datetime


class SessionStatistics(BaseModel):
    """Schema for user session statistics."""

    total_sessions: int
    active_sessions: int
    completed_sessions: int
    sessions_by_status: dict
    total_results_across_sessions: int
    average_completion_time_days: float


class DashboardSummary(BaseModel):
    """Schema for dashboard summary data."""

    user_stats: SessionStatistics
    recent_sessions: List[SearchSessionSummary]
    sessions_needing_attention: List[SearchSessionSummary]
    recent_activities: List[SessionActivity]
