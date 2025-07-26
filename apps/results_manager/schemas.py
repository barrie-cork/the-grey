"""
Pydantic schemas for results_manager slice.
VSA-compliant type safety for result processing and deduplication.
"""

from pydantic import BaseModel, Field, ConfigDict, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ContentType(str, Enum):
    """Content type classifications."""
    PDF = 'pdf'
    WEB_PAGE = 'web_page'
    ACADEMIC_PAPER = 'academic_paper'
    REPORT = 'report'
    PRESENTATION = 'presentation'
    THESIS = 'thesis'
    BOOK = 'book'
    NEWS_ARTICLE = 'news_article'
    BLOG_POST = 'blog_post'
    OTHER = 'other'


class SourceType(str, Enum):
    """Source type classifications."""
    ACADEMIC = 'academic'
    GOVERNMENT = 'government'
    COMMERCIAL = 'commercial'
    NONPROFIT = 'nonprofit'
    PERSONAL = 'personal'
    NEWS = 'news'
    REPOSITORY = 'repository'
    UNKNOWN = 'unknown'


class ProcessedResultResponse(BaseModel):
    """Schema for processed result responses."""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    session_id: str
    raw_result_id: str
    title: str
    url: str
    snippet: str
    normalized_url: str
    content_type: ContentType
    source_type: SourceType
    publication_date: Optional[datetime]
    author: Optional[str]
    source_organization: Optional[str]
    language: str
    word_count: Optional[int]
    duplicate_group_id: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class DuplicateGroupResponse(BaseModel):
    """Schema for duplicate group responses."""
    id: str
    session_id: str
    representative_result_id: str
    duplicate_count: int
    similarity_threshold: float
    group_type: str
    detection_method: str
    created_at: datetime


class ResultSimilarity(BaseModel):
    """Schema for result similarity analysis."""
    result_id_1: str
    result_id_2: str
    similarity_score: float
    similarity_factors: Dict[str, float]
    is_duplicate: bool
    confidence_level: float


class DeduplicationRequest(BaseModel):
    """Schema for deduplication requests."""
    session_id: str
    similarity_threshold: float = Field(default=0.85, ge=0.1, le=1.0)
    methods: List[str] = Field(default=["title", "url", "content"])
    auto_group: bool = Field(default=True)


class DeduplicationResult(BaseModel):
    """Schema for deduplication results."""
    session_id: str
    total_results: int
    duplicate_groups_found: int
    duplicates_removed: int
    unique_results_remaining: int
    processing_time_seconds: float
    methods_used: List[str]


class ProcessingStatistics(BaseModel):
    """Schema for processing statistics."""
    session_id: str
    total_raw_results: int
    processed_results: int
    failed_processing: int
    processing_rate: float
    average_processing_time: float
    content_type_distribution: Dict[str, int]
    source_type_distribution: Dict[str, int]
    language_distribution: Dict[str, int]


class ResultPrioritization(BaseModel):
    """Schema for result prioritization."""
    result_id: str
    priority_score: float
    ranking_factors: Dict[str, float]
    recommended_review_order: int


class ResultMetadata(BaseModel):
    """Schema for extracted result metadata."""
    title_keywords: List[str]
    content_keywords: List[str]
    named_entities: List[str]
    topics: List[str]
    readability_score: Optional[float]
    academic_citations: Optional[int]
    publication_venue: Optional[str]


class SimilarResultsResponse(BaseModel):
    """Schema for similar results recommendations."""
    target_result_id: str
    similar_results: List[Dict[str, Any]]
    similarity_method: str
    max_results: int


class ResultExport(BaseModel):
    """Schema for result export requests."""
    session_id: str
    format_type: str = Field(..., regex="^(csv|json|excel|bibtex)$")
    include_metadata: bool = Field(default=True)
    include_duplicates: bool = Field(default=False)
    filter_by_status: Optional[str] = None


class QualityMetrics(BaseModel):
    """Schema for result quality metrics."""
    session_id: str
    quality_score: float  # Simplified quality metric instead of relevance score
    content_completeness: float
    metadata_completeness: float
    duplicate_detection_accuracy: float
    processing_error_rate: float