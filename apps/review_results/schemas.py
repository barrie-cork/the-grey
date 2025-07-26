"""
Pydantic schemas for review_results slice.
VSA-compliant type safety for result review and tagging.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TagType(str, Enum):
    """Review tag type classifications."""

    INCLUSION = "inclusion"
    EXCLUSION = "exclusion"
    METHODOLOGY = "methodology"
    QUALITY = "quality"
    RELEVANCE = "relevance"
    CUSTOM = "custom"


class ReviewDecision(str, Enum):
    """Review decision choices."""

    INCLUDE = "include"
    EXCLUDE = "exclude"
    UNCERTAIN = "uncertain"
    PENDING = "pending"


class ReviewTagCreate(BaseModel):
    """Schema for creating review tags."""

    name: str = Field(..., min_length=1, max_length=100)
    tag_type: TagType
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, regex="^#[0-9a-fA-F]{6}$")
    is_system_tag: bool = Field(default=False)


class ReviewTagUpdate(BaseModel):
    """Schema for updating review tags."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    color: Optional[str] = Field(None, regex="^#[0-9a-fA-F]{6}$")
    is_active: Optional[bool] = None


class ReviewTagResponse(BaseModel):
    """Schema for review tag responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    tag_type: TagType
    description: Optional[str]
    color: Optional[str]
    is_system_tag: bool
    is_active: bool
    usage_count: int
    created_at: datetime


class ReviewTagAssignmentCreate(BaseModel):
    """Schema for creating tag assignments."""

    result_id: str
    tag_ids: List[str] = Field(..., min_items=1)
    notes: Optional[str] = Field(None, max_length=2000)
    confidence_level: Optional[int] = Field(None, ge=1, le=5)


class ReviewTagAssignmentUpdate(BaseModel):
    """Schema for updating tag assignments."""

    notes: Optional[str] = Field(None, max_length=2000)
    confidence_level: Optional[int] = Field(None, ge=1, le=5)


class ReviewTagAssignmentResponse(BaseModel):
    """Schema for tag assignment responses."""

    id: str
    result_id: str
    tag_id: str
    tag_name: str
    tag_type: TagType
    notes: Optional[str]
    confidence_level: Optional[int]
    assigned_by_id: str
    created_at: datetime
    updated_at: datetime


class BulkTagRequest(BaseModel):
    """Schema for bulk tagging requests."""

    result_ids: List[str] = Field(..., min_items=1, max_items=100)
    tag_ids: List[str] = Field(..., min_items=1)
    notes: Optional[str] = Field(None, max_length=2000)
    confidence_level: Optional[int] = Field(None, ge=1, le=5)


class ReviewProgressResponse(BaseModel):
    """Schema for review progress responses."""

    session_id: str
    total_results: int
    reviewed_results: int
    pending_results: int
    completion_percentage: float
    included_results: int
    excluded_results: int
    uncertain_results: int
    review_velocity: float
    estimated_completion_date: Optional[datetime]


class ReviewRecommendation(BaseModel):
    """Schema for review recommendations."""

    result_id: str
    title: str
    url: str
    quality_indicator: float  # Simplified quality indicator
    recommendation_reason: str
    similar_reviewed_results: List[str]


class TagUsageStatistics(BaseModel):
    """Schema for tag usage statistics."""

    session_id: str
    tag_counts: Dict[str, int]
    most_used_tags: List[Dict[str, Any]]
    tag_distribution: Dict[TagType, int]
    average_tags_per_result: float


class ReviewVelocity(BaseModel):
    """Schema for review velocity analysis."""

    session_id: str
    reviewer_id: str
    results_reviewed_today: int
    results_reviewed_week: int
    average_daily_velocity: float
    peak_velocity_day: Optional[datetime]
    velocity_trend: str  # 'increasing', 'decreasing', 'stable'


class ReviewComment(BaseModel):
    """Schema for review comments."""

    id: str
    result_id: str
    reviewer_id: str
    comment_text: str
    comment_type: str
    is_public: bool
    created_at: datetime
    updated_at: datetime


class ReviewExport(BaseModel):
    """Schema for review data export."""

    session_id: str
    format_type: str = Field(..., regex="^(csv|json|excel|prisma)$")
    include_tags: bool = Field(default=True)
    include_comments: bool = Field(default=True)
    include_metadata: bool = Field(default=True)
    filter_by_decision: Optional[ReviewDecision] = None
    filter_by_tag: Optional[str] = None


class ReviewValidation(BaseModel):
    """Schema for review completeness validation."""

    session_id: str
    is_complete: bool
    missing_reviews: int
    inconsistent_reviews: int
    validation_errors: List[str]
    recommendations: List[str]
    completeness_score: float
