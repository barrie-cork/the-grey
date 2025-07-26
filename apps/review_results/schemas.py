"""
Pydantic schemas for review_results slice.
Simplified schemas for the SimpleReviewDecision workflow.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ReviewDecision(str, Enum):
    """Review decision choices."""

    PENDING = "pending"
    INCLUDE = "include"
    EXCLUDE = "exclude"
    MAYBE = "maybe"


class ExclusionReason(str, Enum):
    """Exclusion reason choices."""

    NOT_RELEVANT = "not_relevant"
    NOT_GREY_LIT = "not_grey_lit"
    DUPLICATE = "duplicate"
    NO_ACCESS = "no_access"
    OTHER = "other"


class SimpleReviewDecisionCreate(BaseModel):
    """Schema for creating a review decision."""

    result_id: str
    decision: ReviewDecision
    exclusion_reason: Optional[ExclusionReason] = None
    notes: Optional[str] = Field(None, max_length=2000)

    def validate_exclusion_reason(self):
        """Validate that exclusion reason is provided when excluding."""
        if self.decision == ReviewDecision.EXCLUDE and not self.exclusion_reason:
            raise ValueError("Exclusion reason is required when excluding a result")
        return self


class SimpleReviewDecisionUpdate(BaseModel):
    """Schema for updating a review decision."""

    decision: Optional[ReviewDecision] = None
    exclusion_reason: Optional[ExclusionReason] = None
    notes: Optional[str] = Field(None, max_length=2000)

    def validate_exclusion_reason(self):
        """Validate that exclusion reason is provided when excluding."""
        if self.decision == ReviewDecision.EXCLUDE and not self.exclusion_reason:
            raise ValueError("Exclusion reason is required when excluding a result")
        return self


class SimpleReviewDecisionResponse(BaseModel):
    """Schema for review decision responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    result_id: str
    reviewer_id: Optional[str]
    decision: ReviewDecision
    exclusion_reason: Optional[ExclusionReason]
    notes: Optional[str]
    reviewed_at: datetime
    updated_at: datetime


class ReviewProgressResponse(BaseModel):
    """Schema for review progress responses."""

    session_id: str
    total_results: int
    reviewed_count: int
    pending_count: int
    include_count: int
    exclude_count: int
    maybe_count: int
    completion_percentage: float


class ReviewExport(BaseModel):
    """Schema for review data export."""

    session_id: str
    format_type: str = Field(default="csv", regex="^(csv|json)$")
    filter_by_decision: Optional[ReviewDecision] = None
