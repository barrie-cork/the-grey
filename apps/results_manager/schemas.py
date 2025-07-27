"""
Basic schemas for results_manager - simplified approach.
Type definitions for result processing and deduplication.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict
from uuid import UUID


class ProcessedResultDict(TypedDict, total=False):
    """Basic type definition for processed result data."""
    
    id: str
    session_id: str
    title: str
    url: str
    snippet: str
    authors: List[str]
    publication_year: Optional[int]
    document_type: str
    language: str
    source_organization: str
    is_pdf: bool
    processed_at: str
    is_reviewed: bool
    duplicate_group_id: Optional[str]
    created_at: str
    updated_at: str


class DuplicateGroupDict(TypedDict, total=False):
    """Basic type definition for duplicate group data."""
    
    id: str
    session_id: str
    canonical_url: str
    similarity_type: str
    result_count: int
    created_at: str


class ProcessingStatsDict(TypedDict, total=False):
    """Basic type definition for processing statistics."""
    
    session_id: str
    total_results: int
    processed_results: int
    duplicate_groups: int
    unique_results: int
    document_types: Dict[str, int]
    publication_years: Dict[str, int]
    pdf_count: int


class ExportRequestDict(TypedDict, total=False):
    """Basic type definition for export requests."""
    
    session_id: str
    format_type: str  # 'csv', 'json', or 'excel'
    include_duplicates: bool


