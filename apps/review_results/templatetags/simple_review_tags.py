"""
Simple template tags for review results.
Provides basic filters and tags for displaying simple Include/Exclude interface.
"""

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import format_html

from ..models import SimpleReviewDecision
from ..services.simple_review_progress_service import SimpleReviewProgressService

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
    try:
        decision = SimpleReviewDecision.objects.get(result=result)
        if decision.decision == 'include':
            return '<span class="badge bg-success">Include</span>'
        elif decision.decision == 'exclude':
            return '<span class="badge bg-danger">Exclude</span>'
        elif decision.decision == 'maybe':
            return '<span class="badge bg-warning">Maybe</span>'
        else:
            return '<span class="badge bg-secondary">Pending</span>'
    except SimpleReviewDecision.DoesNotExist:
        return '<span class="badge bg-secondary">Pending</span>'


@register.simple_tag
def review_progress_bar(session_id: str) -> str:
    """
    Render a simple progress bar for review completion.
    
    Args:
        session_id: UUID of the SearchSession
        
    Returns:
        HTML string with progress bar
    """
    service = SimpleReviewProgressService()
    progress = service.get_progress_summary(session_id)
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
        progress['reviewed_count'],
        progress['total_results']
    )


@register.simple_tag
def quick_decision_buttons(result) -> str:
    """
    Render quick decision buttons (Include/Exclude/Maybe).
    
    Args:
        result: ProcessedResult instance
        
    Returns:
        HTML string with decision buttons
    """
    try:
        decision = SimpleReviewDecision.objects.get(result=result)
        current_decision = decision.decision
    except SimpleReviewDecision.DoesNotExist:
        current_decision = 'pending'
    
    buttons = []
    
    # Include button
    include_class = 'btn-success' if current_decision == 'include' else 'btn-outline-success'
    buttons.append(
        format_html(
            '<button class="btn btn-sm {} me-1" onclick="makeDecision(\'{}\', \'include\')">'
            '<i class="bi bi-check-lg"></i> Include'
            '</button>',
            include_class,
            result.id
        )
    )
    
    # Exclude button  
    exclude_class = 'btn-danger' if current_decision == 'exclude' else 'btn-outline-danger'
    buttons.append(
        format_html(
            '<button class="btn btn-sm {} me-1" onclick="makeDecision(\'{}\', \'exclude\')">'
            '<i class="bi bi-x-lg"></i> Exclude'
            '</button>',
            exclude_class,
            result.id
        )
    )
    
    # Maybe button
    maybe_class = 'btn-warning' if current_decision == 'maybe' else 'btn-outline-warning'
    buttons.append(
        format_html(
            '<button class="btn btn-sm {}" onclick="makeDecision(\'{}\', \'maybe\')">'
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
    try:
        decision = SimpleReviewDecision.objects.get(result=result)
        notes = decision.notes
        
        if not notes:
            return 'No notes'
        
        if len(notes) <= max_length:
            return notes
        
        return notes[:max_length] + '...'
    except SimpleReviewDecision.DoesNotExist:
        return 'No notes'


@register.simple_tag
def review_completion_indicator(session_id: str) -> str:
    """
    Show review completion indicator with status.
    
    Args:
        session_id: UUID of the SearchSession
        
    Returns:
        HTML string with completion indicator
    """
    service = SimpleReviewProgressService()
    progress = service.get_progress_summary(session_id)
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


@register.inclusion_tag('review_results/tags/simple_review_stats.html')
def simple_review_stats(session_id: str):
    """
    Render simple review statistics.
    
    Args:
        session_id: UUID of the SearchSession
        
    Returns:
        Context for simple review stats
    """
    service = SimpleReviewProgressService()
    progress = service.get_progress_summary(session_id)
    
    return {
        'session_id': session_id,
        'progress': progress
    }