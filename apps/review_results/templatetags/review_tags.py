"""
Custom template tags for review results and tagging.

These tags provide convenient filters and tags for displaying
review progress, tags, and result evaluation interface.
"""

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from typing import Dict, Any

from ..models import ReviewTag, ReviewTagAssignment
from ..utils import calculate_review_progress, get_tag_usage_statistics

register = template.Library()


@register.filter
def review_status_badge(result) -> str:
    """
    Render a review status badge for a result.
    
    Args:
        result: ProcessedResult instance
        
    Returns:
        HTML string with status badge
    """
    # Check if result has any tag assignments
    has_assignments = ReviewTagAssignment.objects.filter(result=result).exists()
    
    if has_assignments:
        return '<span class="badge bg-success">Reviewed</span>'
    else:
        return '<span class="badge bg-warning">Pending Review</span>'


@register.filter
def tag_color_class(tag: ReviewTag) -> str:
    """
    Get CSS color class for tag type.
    
    Args:
        tag: ReviewTag instance
        
    Returns:
        CSS class name
    """
    color_map = {
        'quality': 'primary',
        'methodology': 'info', 
        'topic': 'success',
        'relevance': 'warning',
        'custom': 'secondary'
    }
    return color_map.get(tag.tag_type, 'secondary')


@register.inclusion_tag('review_results/tags/tag_assignment_form.html')
def tag_assignment_form(result, available_tags):
    """
    Render tag assignment form for a result.
    
    Args:
        result: ProcessedResult instance
        available_tags: QuerySet of available ReviewTag instances
        
    Returns:
        Context for tag assignment form
    """
    current_assignments = ReviewTagAssignment.objects.filter(result=result)
    assigned_tag_ids = set(current_assignments.values_list('tag_id', flat=True))
    
    return {
        'result': result,
        'available_tags': available_tags,
        'current_assignments': current_assignments,
        'assigned_tag_ids': assigned_tag_ids
    }


@register.simple_tag
def review_progress_bar(session_id: str) -> str:
    """
    Render a progress bar for review completion.
    
    Args:
        session_id: UUID of the SearchSession
        
    Returns:
        HTML string with progress bar
    """
    progress = calculate_review_progress(session_id)
    percentage = progress['completion_percentage']
    
    if percentage == 100:
        color = 'success'
    elif percentage >= 75:
        color = 'info'
    elif percentage >= 50:
        color = 'warning'
    else:
        color = 'danger'
    
    return format_html(
        '<div class="progress">'
        '<div class="progress-bar bg-{}" role="progressbar" style="width: {}%" '
        'aria-valuenow="{}" aria-valuemin="0" aria-valuemax="100">'
        '{}% Complete ({}/{})'
        '</div>'
        '</div>',
        color,
        percentage,
        percentage,
        percentage,
        progress['reviewed_results'],
        progress['total_results']
    )


@register.filter
def tag_assignments_for_result(result) -> str:
    """
    Display tag assignments for a result as badges.
    
    Args:
        result: ProcessedResult instance
        
    Returns:
        HTML string with tag badges
    """
    assignments = ReviewTagAssignment.objects.filter(result=result).select_related('tag')
    
    if not assignments:
        return '<span class="text-muted">No tags assigned</span>'
    
    badges = []
    for assignment in assignments:
        color_class = tag_color_class(assignment.tag)
        badges.append(
            format_html(
                '<span class="badge bg-{} me-1" title="{}">{}</span>',
                color_class,
                assignment.tag.description or assignment.tag.name,
                assignment.tag.name
            )
        )
    
    return mark_safe(''.join(badges))


@register.inclusion_tag('review_results/tags/review_stats_dashboard.html')
def review_stats_dashboard(session_id: str):
    """
    Render review statistics dashboard.
    
    Args:
        session_id: UUID of the SearchSession
        
    Returns:
        Context for review stats dashboard
    """
    progress = calculate_review_progress(session_id)
    tag_stats = get_tag_usage_statistics(session_id)
    
    return {
        'session_id': session_id,
        'progress': progress,
        'tag_stats': tag_stats,
        'velocity': progress.get('review_velocity', 0)
    }


@register.simple_tag
def quick_tag_buttons(result) -> str:
    """
    Render quick tag buttons (Include/Exclude/Maybe).
    
    Args:
        result: ProcessedResult instance
        
    Returns:
        HTML string with quick tag buttons
    """
    # Get current assignments
    assignments = ReviewTagAssignment.objects.filter(result=result).select_related('tag')
    current_tags = {a.tag.name for a in assignments}
    
    buttons = []
    
    # Include button
    include_class = 'btn-success' if 'Include' in current_tags else 'btn-outline-success'
    buttons.append(
        format_html(
            '<button class="btn btn-sm {} me-1" onclick="quickTag(\'{}\', \'Include\')">'
            '<i class="bi bi-check-lg"></i> Include'
            '</button>',
            include_class,
            result.id
        )
    )
    
    # Exclude button  
    exclude_class = 'btn-danger' if 'Exclude' in current_tags else 'btn-outline-danger'
    buttons.append(
        format_html(
            '<button class="btn btn-sm {} me-1" onclick="quickTag(\'{}\', \'Exclude\')">'
            '<i class="bi bi-x-lg"></i> Exclude'
            '</button>',
            exclude_class,
            result.id
        )
    )
    
    # Maybe button
    maybe_class = 'btn-warning' if 'Maybe' in current_tags else 'btn-outline-warning'
    buttons.append(
        format_html(
            '<button class="btn btn-sm {}" onclick="quickTag(\'{}\', \'Maybe\')">'
            '<i class="bi bi-question-lg"></i> Maybe'
            '</button>',
            maybe_class,
            result.id
        )
    )
    
    return mark_safe(''.join(buttons))


@register.filter
def review_notes_preview(result, max_length: int = 100) -> str:
    """
    Show preview of review notes for a result.
    
    Args:
        result: ProcessedResult instance
        max_length: Maximum length of preview
        
    Returns:
        Preview text of notes
    """
    assignments = ReviewTagAssignment.objects.filter(result=result).exclude(notes='')
    
    if not assignments:
        return 'No notes'
    
    # Combine all notes
    all_notes = ' | '.join([a.notes for a in assignments if a.notes])
    
    if len(all_notes) <= max_length:
        return all_notes
    
    return all_notes[:max_length] + '...'


@register.simple_tag
def tag_usage_chart_data(session_id: str) -> str:
    """
    Generate data for tag usage chart.
    
    Args:
        session_id: UUID of the SearchSession
        
    Returns:
        JSON string with chart data
    """
    import json
    
    tag_stats = get_tag_usage_statistics(session_id)
    tag_counts = tag_stats.get('tag_counts', {})
    
    # Prepare data for chart
    chart_data = {
        'labels': list(tag_counts.keys()),
        'data': list(tag_counts.values()),
        'backgroundColor': [
            '#007bff', '#28a745', '#ffc107', '#dc3545', '#6f42c1',
            '#fd7e14', '#20c997', '#6c757d', '#17a2b8', '#e83e8c'
        ]
    }
    
    return json.dumps(chart_data)


@register.filter
def can_exclude_with_reason(result) -> bool:
    """
    Check if result can be excluded (for showing reason modal).
    
    Args:
        result: ProcessedResult instance
        
    Returns:
        Boolean indicating if exclusion is allowed
    """
    # Check if result is not already excluded
    is_excluded = ReviewTagAssignment.objects.filter(
        result=result,
        tag__name='Exclude'
    ).exists()
    
    return not is_excluded


@register.inclusion_tag('review_results/tags/bulk_action_form.html')
def bulk_action_form(results, available_tags):
    """
    Render bulk action form for multiple results.
    
    Args:
        results: QuerySet of ProcessedResult instances
        available_tags: QuerySet of available ReviewTag instances
        
    Returns:
        Context for bulk action form
    """
    return {
        'results': results,
        'available_tags': available_tags,
        'result_count': results.count() if hasattr(results, 'count') else len(results)
    }


@register.simple_tag
def review_completion_indicator(session_id: str) -> str:
    """
    Show review completion indicator with status.
    
    Args:
        session_id: UUID of the SearchSession
        
    Returns:
        HTML string with completion indicator
    """
    progress = calculate_review_progress(session_id)
    percentage = progress['completion_percentage']
    
    if percentage == 100:
        icon = 'bi-check-circle-fill text-success'
        text = 'Review Complete'
    elif percentage >= 75:
        icon = 'bi-clock-fill text-info'
        text = 'Nearly Complete'
    elif percentage >= 25:
        icon = 'bi-play-circle-fill text-warning'
        text = 'In Progress'
    else:
        icon = 'bi-circle text-muted'
        text = 'Not Started'
    
    return format_html(
        '<div class="d-flex align-items-center">'
        '<i class="bi {} me-2"></i>'
        '<span>{} ({}%)</span>'
        '</div>',
        icon,
        text,
        percentage
    )