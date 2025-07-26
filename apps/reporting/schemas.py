"""
Pydantic schemas for reporting slice.
VSA-compliant type safety for PRISMA reports and data export.
"""

from pydantic import BaseModel, Field, ConfigDict, validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


class ReportFormat(str, Enum):
    """Report export format choices."""
    PDF = 'pdf'
    DOCX = 'docx'
    HTML = 'html'
    JSON = 'json'
    CSV = 'csv'
    EXCEL = 'excel'


class ReportType(str, Enum):
    """Report type classifications."""
    PRISMA_FLOW = 'prisma_flow'
    SEARCH_STRATEGY = 'search_strategy'
    STUDY_CHARACTERISTICS = 'study_characteristics'
    QUALITY_ASSESSMENT = 'quality_assessment'
    PERFORMANCE_METRICS = 'performance_metrics'
    CUSTOM = 'custom'


class PRISMAFlowData(BaseModel):
    """Schema for PRISMA flow diagram data."""
    identification: Dict[str, Any]
    screening: Dict[str, Any]
    eligibility: Dict[str, Any]
    included: Dict[str, Any]
    metadata: Dict[str, Any]


class ExclusionReason(BaseModel):
    """Schema for exclusion reasons."""
    reason: str
    count: int
    percentage: float
    examples: List[str]


class ReviewPeriod(BaseModel):
    """Schema for review period information."""
    start_date: date
    end_date: date
    duration_days: int
    active_review_days: int


class SearchStrategyReport(BaseModel):
    """Schema for search strategy reports."""
    session_id: str
    search_approach: str
    databases_searched: List[str]
    search_terms: List[str]
    search_queries: List[Dict[str, Any]]
    date_ranges: Dict[str, str]
    language_restrictions: List[str]
    inclusion_criteria: List[str]
    exclusion_criteria: List[str]
    search_validation: Dict[str, Any]


class StudyCharacteristics(BaseModel):
    """Schema for study characteristics table."""
    session_id: str
    total_studies: int
    study_types: Dict[str, int]
    publication_years: Dict[str, int]
    geographical_distribution: Dict[str, int]
    language_distribution: Dict[str, int]
    methodology_distribution: Dict[str, int]
    sample_size_distribution: Dict[str, int]


class PerformanceMetrics(BaseModel):
    """Schema for search performance metrics."""
    session_id: str
    search_efficiency: float
    precision_estimate: float
    recall_estimate: float
    time_to_completion: int
    cost_per_relevant_result: float
    search_coverage: float
    duplicate_detection_rate: float


class ReportRequest(BaseModel):
    """Schema for report generation requests."""
    session_id: str
    report_type: ReportType
    format: ReportFormat
    include_methodology: bool = Field(default=True)
    include_appendices: bool = Field(default=True)
    custom_sections: List[str] = Field(default_factory=list)
    template_id: Optional[str] = None


class ReportResponse(BaseModel):
    """Schema for report generation responses."""
    report_id: str
    session_id: str
    report_type: ReportType
    format: ReportFormat
    file_path: str
    file_size_bytes: int
    generated_at: datetime
    expires_at: datetime
    download_url: str


class PRISMAChecklist(BaseModel):
    """Schema for PRISMA checklist compliance."""
    session_id: str
    checklist_items: List[Dict[str, Any]]
    compliance_score: float
    missing_items: List[str]
    recommendations: List[str]
    is_compliant: bool


class ReportTemplate(BaseModel):
    """Schema for report templates."""
    id: str
    name: str
    description: str
    report_type: ReportType
    template_sections: List[Dict[str, Any]]
    default_format: ReportFormat
    is_system_template: bool
    usage_count: int


class ExportConfiguration(BaseModel):
    """Schema for data export configuration."""
    session_id: str
    data_types: List[str]
    format: ReportFormat
    include_raw_data: bool = Field(default=False)
    include_metadata: bool = Field(default=True)
    date_range_filter: Optional[Dict[str, date]] = None
    tag_filter: Optional[List[str]] = None
    quality_filter: Optional[Dict[str, Any]] = None


class ReportMetadata(BaseModel):
    """Schema for report metadata."""
    report_id: str
    title: str
    author: str
    organization: Optional[str]
    version: str
    generated_date: datetime
    review_period: ReviewPeriod
    methodology_summary: str
    key_findings: List[str]
    limitations: List[str]


class ReportSchedule(BaseModel):
    """Schema for scheduled report generation."""
    session_id: str
    report_type: ReportType
    schedule_frequency: str  # 'daily', 'weekly', 'monthly'
    recipients: List[str]
    next_generation: datetime
    is_active: bool


class QualityAssessment(BaseModel):
    """Schema for quality assessment reports."""
    session_id: str
    assessment_criteria: List[str]
    study_quality_scores: Dict[str, float]
    quality_distribution: Dict[str, int]
    risk_of_bias: Dict[str, Any]
    recommendations: List[str]