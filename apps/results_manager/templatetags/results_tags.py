"""
Custom template tags for ProcessedResult rendering.

These tags provide convenient filters and tags for displaying
results, metadata, and processing statistics.
"""

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from typing import Dict, Any

from ..models import ProcessedResult, DuplicateGroup

register = template.Library()


@register.filter
def document_type_badge(doc_type: str) -> str:
    """
    Simple document type badge.
    """
    display_name = doc_type.replace('_', ' ').title() if doc_type else 'Unknown'
    
    return format_html(
        '<span class="badge bg-secondary">{}</span>',
        display_name
    )




@register.filter
def document_indicators(result: ProcessedResult) -> str:
    """
    Render simple document type indicators.
    
    Args:
        result: ProcessedResult instance
        
    Returns:
        HTML string with document indicators
    """
    indicators = []
    
    if result.is_pdf:
        indicators.append('<i class="bi bi-file-pdf text-danger" title="PDF document"></i>')
    else:
        indicators.append('<i class="bi bi-globe text-info" title="Webpage"></i>')
    
    if result.duplicate_group:
        indicators.append('<i class="bi bi-files text-secondary" title="Part of duplicate group"></i>')
    
    return mark_safe(' '.join(indicators))




@register.filter
def truncate_title(title: str, max_length: int = 80) -> str:
    """
    Truncate title for display.
    
    Args:
        title: Original title
        max_length: Maximum length before truncation
        
    Returns:
        Truncated title
    """
    if not title:
        return ''
    
    if len(title) <= max_length:
        return title
    
    truncated = title[:max_length].rsplit(' ', 1)[0]
    return f"{truncated}..."


@register.inclusion_tag('results_manager/tags/result_card.html')
def result_summary_card(result: ProcessedResult):
    """
    Render a summary card for a processed result.
    
    Args:
        result: ProcessedResult instance
        
    Returns:
        Context for the result card template
    """
    return {
        'result': result,
        'domain': result.get_display_url(),
        'is_pdf': result.is_pdf,
        'is_duplicate': bool(result.duplicate_group),
    }


@register.filter
def publication_year_badge(year: int) -> str:
    """
    Simple publication year badge.
    """
    if not year:
        return '<span class="badge bg-light text-muted">Unknown</span>'
    
    return format_html(
        '<span class="badge bg-secondary">{}</span>',
        year
    )


@register.simple_tag
def duplicate_group_info(group: DuplicateGroup) -> str:
    """
    Simple duplicate group indicator.
    """
    return format_html(
        '<span class="text-muted">{} duplicates</span>',
        group.result_count - 1  # Show number of duplicates, not total count
    )




