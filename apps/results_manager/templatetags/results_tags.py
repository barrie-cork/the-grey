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
from ..utils import get_processing_statistics

register = template.Library()


@register.filter
def document_type_badge(doc_type: str) -> str:
    """
    Render a badge for document type.
    
    Args:
        doc_type: Document type string
        
    Returns:
        HTML string with styled badge
    """
    type_colors = {
        'pdf': 'danger',
        'report': 'info',
        'thesis': 'warning',
        'working_paper': 'secondary',
        'webpage': 'light',
        'unknown': 'outline-secondary'
    }
    
    color = type_colors.get(doc_type or 'unknown', 'secondary')
    display_name = doc_type.replace('_', ' ').title() if doc_type else 'Unknown'
    
    return format_html(
        '<span class="badge bg-{}">{}</span>',
        color,
        display_name
    )


@register.filter
def relevance_score_bar(score: float) -> str:
    """
    Render a progress bar for relevance score.
    
    Args:
        score: Relevance score (0-1)
        
    Returns:
        HTML string with progress bar
    """
    if not score:
        score = 0
    
    percentage = int(score * 100)
    
    if percentage >= 80:
        color = 'success'
    elif percentage >= 60:
        color = 'info'
    elif percentage >= 40:
        color = 'warning'
    else:
        color = 'danger'
    
    return format_html(
        '<div class="progress" style="height: 8px;">'
        '<div class="progress-bar bg-{}" role="progressbar" style="width: {}%" title="Relevance: {}%">'
        '</div>'
        '</div>',
        color,
        percentage,
        percentage
    )


@register.filter
def quality_indicators(result: ProcessedResult) -> str:
    """
    Render quality indicator icons.
    
    Args:
        result: ProcessedResult instance
        
    Returns:
        HTML string with quality icons
    """
    indicators = []
    
    if result.has_full_text:
        indicators.append('<i class="bi bi-file-text text-success" title="Full text available"></i>')
    
    if result.is_pdf:
        indicators.append('<i class="bi bi-file-pdf text-danger" title="PDF document"></i>')
    
    if result.quality_indicators.get('peer_reviewed'):
        indicators.append('<i class="bi bi-award text-warning" title="Peer reviewed"></i>')
    
    if result.quality_indicators.get('has_doi'):
        indicators.append('<i class="bi bi-link-45deg text-info" title="Has DOI"></i>')
    
    if result.duplicate_group:
        indicators.append('<i class="bi bi-files text-secondary" title="Duplicate group"></i>')
    
    return mark_safe(' '.join(indicators))


@register.simple_tag
def processing_stats_card(session_id: str, stat_type: str) -> str:
    """
    Render a statistics card for processing metrics.
    
    Args:
        session_id: UUID of the SearchSession
        stat_type: Type of statistic to display
        
    Returns:
        HTML string with stats card
    """
    stats = get_processing_statistics(session_id)
    
    stat_configs = {
        'total': {
            'value': stats['total_results'],
            'label': 'Total Results',
            'icon': 'bi-list-ul',
            'color': 'primary'
        },
        'unique': {
            'value': stats['unique_results'],
            'label': 'Unique Results',
            'icon': 'bi-check2-square',
            'color': 'success'
        },
        'duplicates': {
            'value': stats['duplicate_groups'],
            'label': 'Duplicate Groups',
            'icon': 'bi-files',
            'color': 'warning'
        },
        'academic': {
            'value': f"{stats['academic_percentage']}%",
            'label': 'Academic Sources',
            'icon': 'bi-mortarboard',
            'color': 'info'
        }
    }
    
    if stat_type not in stat_configs:
        return ''
    
    config = stat_configs[stat_type]
    
    return format_html(
        '<div class="card border-{} h-100">'
        '<div class="card-body text-center">'
        '<i class="bi {} text-{} fs-1"></i>'
        '<h3 class="mt-2 mb-0">{}</h3>'
        '<p class="text-muted mb-0">{}</p>'
        '</div>'
        '</div>',
        config['color'],
        config['icon'],
        config['color'],
        config['value'],
        config['label']
    )


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
        'has_metadata': hasattr(result, 'metadata'),
        'quality_score': result.relevance_score or 0,
    }


@register.filter
def publication_year_badge(year: int) -> str:
    """
    Render a badge for publication year with recency indication.
    
    Args:
        year: Publication year
        
    Returns:
        HTML string with year badge
    """
    if not year:
        return '<span class="badge bg-light text-muted">Unknown</span>'
    
    current_year = 2024  # This should be dynamic
    years_old = current_year - year
    
    if years_old <= 2:
        color = 'success'
        title = 'Very recent'
    elif years_old <= 5:
        color = 'info'
        title = 'Recent'
    elif years_old <= 10:
        color = 'warning'
        title = 'Somewhat recent'
    else:
        color = 'secondary'
        title = 'Older publication'
    
    return format_html(
        '<span class="badge bg-{}" title="{}">{}</span>',
        color,
        title,
        year
    )


@register.simple_tag
def duplicate_group_info(group: DuplicateGroup) -> str:
    """
    Render information about a duplicate group.
    
    Args:
        group: DuplicateGroup instance
        
    Returns:
        HTML string with group information
    """
    similarity_icons = {
        'exact_url': 'bi-link text-success',
        'normalized_url': 'bi-link-45deg text-info',
        'title_match': 'bi-type text-warning',
        'content_hash': 'bi-hash text-primary',
        'fuzzy_match': 'bi-search text-secondary'
    }
    
    icon = similarity_icons.get(group.similarity_type, 'bi-files')
    
    return format_html(
        '<div class="d-flex align-items-center">'
        '<i class="bi {} me-2"></i>'
        '<div>'
        '<strong>{} results</strong><br>'
        '<small class="text-muted">{} match</small>'
        '</div>'
        '</div>',
        icon,
        group.result_count,
        group.get_similarity_type_display()
    )


@register.filter
def metadata_completeness(result: ProcessedResult) -> str:
    """
    Show metadata completeness indicator.
    
    Args:
        result: ProcessedResult instance
        
    Returns:
        HTML string with completeness indicator
    """
    score = 0
    total = 7
    
    if result.title:
        score += 1
    if result.snippet:
        score += 1
    if result.authors:
        score += 1
    if result.publication_date:
        score += 1
    if result.document_type and result.document_type != 'unknown':
        score += 1
    if result.source_organization:
        score += 1
    if result.has_full_text:
        score += 1
    
    percentage = int((score / total) * 100)
    
    if percentage >= 80:
        color = 'success'
        text = 'Complete'
    elif percentage >= 60:
        color = 'info'
        text = 'Good'
    elif percentage >= 40:
        color = 'warning'
        text = 'Partial'
    else:
        color = 'danger'
        text = 'Minimal'
    
    return format_html(
        '<span class="badge bg-{}" title="{}% complete">{}</span>',
        color,
        percentage,
        text
    )


@register.simple_tag
def processing_timeline_item(result: ProcessedResult) -> str:
    """
    Render a timeline item for result processing.
    
    Args:
        result: ProcessedResult instance
        
    Returns:
        HTML string with timeline item
    """
    return format_html(
        '<div class="timeline-item">'
        '<div class="timeline-marker">'
        '<i class="bi bi-gear text-primary"></i>'
        '</div>'
        '<div class="timeline-content">'
        '<h6 class="mb-1">Result Processed</h6>'
        '<p class="mb-1">{}</p>'
        '<small class="text-muted">{}</small>'
        '</div>'
        '</div>',
        result.title[:50] + '...' if len(result.title) > 50 else result.title,
        result.processed_at.strftime('%Y-%m-%d %H:%M')
    )


@register.filter
def format_file_size(bytes_size: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        bytes_size: Size in bytes
        
    Returns:
        Formatted size string
    """
    if not bytes_size:
        return 'Unknown'
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    
    return f"{bytes_size:.1f} TB"