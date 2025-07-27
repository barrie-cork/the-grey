"""
Pydantic schemas for serp_execution slice.
VSA-compliant type safety for search execution and API integration.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ExecutionStatus(str, Enum):
    """Search execution status choices."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class SearchExecutionCreate(BaseModel):
    """Schema for creating a search execution."""

    query_id: str
    search_engines: List[str] = Field(default=["google"])
    max_results: int = Field(default=100, ge=1, le=1000)
    priority: int = Field(default=5, ge=1, le=10)


class SearchExecutionResponse(BaseModel):
    """Schema for search execution API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    query_id: str
    status: ExecutionStatus
    search_engine: str
    results_count: int
    api_credits_used: int
    execution_time: Optional[float]
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    retry_count: int
    metadata: Dict[str, Any]


class RawSearchResultResponse(BaseModel):
    """Schema for raw search result responses."""

    id: str
    execution_id: str
    position: int
    title: str
    url: str
    snippet: str
    source_metadata: Dict[str, Any]
    created_at: datetime




class ExecutionConfirmation(BaseModel):
    """Schema for execution confirmation requests."""

    confirmed: bool = Field(True)
    estimated_cost: Optional[Decimal] = None
    estimated_time: Optional[int] = None
    notes: Optional[str] = Field(None, max_length=1000)


class ExecutionStatusUpdate(BaseModel):
    """Schema for execution status updates."""

    status: ExecutionStatus
    error_message: Optional[str] = None
    results_count: Optional[int] = None
    execution_time: Optional[float] = None


class ExecutionRetry(BaseModel):
    """Schema for execution retry requests."""

    retry_reason: str = Field(..., min_length=1, max_length=500)
    max_retries: int = Field(default=3, ge=1, le=5)
    retry_delay_seconds: int = Field(default=60, ge=30, le=3600)




class ExecutionProgress(BaseModel):
    """Schema for execution progress updates."""

    session_id: str
    total_executions: int
    completed_executions: int
    failed_executions: int
    running_executions: int
    progress_percentage: float
    estimated_completion: Optional[datetime]


class FailureAnalysis(BaseModel):
    """Schema for execution failure analysis."""

    execution_id: str
    failure_category: str
    failure_reason: str
    retry_recommended: bool
    suggested_action: str
    similar_failures: int


class RetryStrategy(BaseModel):
    """Schema for retry strategy recommendations."""

    execution_id: str
    recommended_delay: int
    max_retries: int
    priority_adjustment: int
    parameter_changes: Dict[str, Any]


class SearchCoverage(BaseModel):
    """Schema for search coverage analysis."""

    session_id: str
    total_queries: int
    executed_queries: int
    coverage_percentage: float
    missing_engines: List[str]
    estimated_missing_results: int


class EnginePerformance(BaseModel):
    """Schema for search engine performance comparison."""

    engine_name: str
    total_executions: int
    success_rate: float
    average_response_time: float
    average_results_count: int
    reliability_score: float
