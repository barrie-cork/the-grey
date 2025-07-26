from django import template
from django.utils.html import format_html

register = template.Library()


@register.filter
def status_color(status):
    """Return Bootstrap color class for session status."""
    status_colors = {
        'draft': 'secondary',
        'defining_search': 'info',
        'ready_to_execute': 'primary',
        'executing': 'warning',
        'processing_results': 'warning',
        'ready_for_review': 'success',
        'under_review': 'success',
        'completed': 'dark',
        'archived': 'secondary',
    }
    return status_colors.get(status, 'secondary')


@register.filter
def status_badge(status):
    """Render a colored status badge."""
    from ..models import SearchSession
    
    color = status_color(status)
    display = dict(SearchSession.STATUS_CHOICES).get(status, status)
    
    return format_html(
        '<span class="badge bg-{}">{}</span>',
        color,
        display
    )


@register.filter
def status_icon(status):
    """Helper to get icon for status."""
    icons = {
        'draft': 'bi-file-earmark',
        'defining_search': 'bi-pencil',
        'ready_to_execute': 'bi-play-circle',
        'executing': 'bi-hourglass-split',
        'processing_results': 'bi-gear-wide-connected',
        'ready_for_review': 'bi-journal-check',
        'under_review': 'bi-journal-bookmark',
        'completed': 'bi-check-circle',
        'archived': 'bi-archive',
    }
    return icons.get(status, 'bi-circle')