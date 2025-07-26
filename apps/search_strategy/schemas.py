"""
Pydantic schemas for search_strategy slice.
VSA-compliant type safety for PIC framework and search queries.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, validator


class SearchQueryCreate(BaseModel):
    """Schema for creating a search query."""

    title: str = Field(..., min_length=1, max_length=255)
    population: str = Field(..., min_length=1, max_length=1000)
    interest: str = Field(..., min_length=1, max_length=1000)
    context: str = Field(..., min_length=1, max_length=1000)
    query_string: str = Field(..., min_length=1, max_length=2000)
    search_engines: List[str] = Field(default=["google"])
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    language_codes: List[str] = Field(default=["en"])
    excluded_terms: List[str] = Field(default_factory=list)
    max_results: int = Field(default=100, ge=1, le=1000)
    notes: Optional[str] = Field(None, max_length=2000)

    @validator("search_engines")
    def validate_search_engines(cls, v):
        allowed_engines = ["google", "bing", "duckduckgo"]
        for engine in v:
            if engine not in allowed_engines:
                raise ValueError(f"Invalid search engine: {engine}")
        return v


class SearchQueryUpdate(BaseModel):
    """Schema for updating a search query."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    population: Optional[str] = Field(None, min_length=1, max_length=1000)
    interest: Optional[str] = Field(None, min_length=1, max_length=1000)
    context: Optional[str] = Field(None, min_length=1, max_length=1000)
    query_string: Optional[str] = Field(None, min_length=1, max_length=2000)
    search_engines: Optional[List[str]] = None
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    language_codes: Optional[List[str]] = None
    excluded_terms: Optional[List[str]] = None
    max_results: Optional[int] = Field(None, ge=1, le=1000)
    notes: Optional[str] = Field(None, max_length=2000)
    is_active: Optional[bool] = None


class SearchQueryResponse(BaseModel):
    """Schema for search query API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    title: str
    population: str
    interest: str
    context: str
    query_string: str
    search_engines: List[str]
    date_range_start: Optional[datetime]
    date_range_end: Optional[datetime]
    language_codes: List[str]
    excluded_terms: List[str]
    max_results: int
    notes: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    complexity_score: int
    estimated_results: int


class PICValidation(BaseModel):
    """Schema for PIC framework validation results."""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]


class QueryVariation(BaseModel):
    """Schema for query variations/suggestions."""

    variation_type: str
    title: str
    query_string: str
    rationale: str
    estimated_additional_results: int


class QueryOptimization(BaseModel):
    """Schema for query optimization results."""

    optimized_query: str
    optimization_score: int
    changes_made: List[str]
    potential_impact: str


class QueryComplexity(BaseModel):
    """Schema for query complexity analysis."""

    complexity_score: int
    factors: Dict[str, Any]
    recommendations: List[str]
    estimated_execution_time: int


class SearchStrategyTemplate(BaseModel):
    """Schema for search strategy templates."""

    id: str
    name: str
    description: str
    population_template: str
    interest_template: str
    context_template: str
    query_template: str
    use_count: int
    success_rate: float


class SessionQueryStatistics(BaseModel):
    """Schema for session query statistics."""

    total_queries: int
    active_queries: int
    average_complexity: float
    total_estimated_results: int
    queries_by_engine: Dict[str, int]
    pic_completeness: Dict[str, bool]
