"""
Custom template tags for SearchQuery and PIC framework rendering.

These tags provide convenient filters and tags for displaying
query information, PIC components, and search strategy data.
"""

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from typing import Dict, Any, List

from ..models import SearchQuery, QueryTemplate
from ..utils import calculate_query_complexity, optimize_query_string

register = template.Library()


@register.filter
def pic_badge(component: str, component_type: str) -> str:
    """
    Render a badge for PIC framework components.
    
    Args:
        component: The PIC component text
        component_type: Type ('population', 'interest', 'context')
        
    Returns:
        HTML string with styled badge
    """
    if not component or not component.strip():
        return format_html('<span class="badge bg-light text-muted">Not specified</span>')
    
    colors = {
        'population': 'primary',
        'interest': 'success',
        'context': 'info'
    }
    
    color = colors.get(component_type.lower(), 'secondary')
    short_text = component[:30] + '...' if len(component) > 30 else component
    
    return format_html(
        '<span class="badge bg-{} text-wrap" title="{}">{}</span>',
        color,
        component,
        short_text
    )


@register.filter
def complexity_badge(query: SearchQuery) -> str:
    """
    Render a complexity badge for a search query.
    
    Args:
        query: SearchQuery instance
        
    Returns:
        HTML string with complexity badge
    """
    complexity = calculate_query_complexity(query)
    level = complexity['level']
    score = complexity['score']
    
    colors = {
        'Simple': 'success',
        'Moderate': 'warning',
        'Complex': 'danger',
        'Very Complex': 'dark'
    }
    
    color = colors.get(level, 'secondary')
    
    return format_html(
        '<span class="badge bg-{}" title="Complexity Score: {}">{}</span>',
        color,
        score,
        level
    )


@register.filter
def keyword_list(keywords: List[str], max_display: int = 5) -> str:
    """
    Render a list of keywords with badges.
    
    Args:
        keywords: List of keyword strings
        max_display: Maximum number of keywords to display
        
    Returns:
        HTML string with keyword badges
    """
    if not keywords:
        return '<span class="text-muted">None</span>'
    
    displayed = keywords[:max_display]
    remaining = len(keywords) - max_display
    
    html_parts = []
    for keyword in displayed:
        html_parts.append(format_html('<span class="badge bg-light text-dark me-1">{}</span>', keyword))
    
    if remaining > 0:
        html_parts.append(format_html('<span class="badge bg-secondary">+{} more</span>', remaining))
    
    return mark_safe(' '.join(html_parts))


@register.inclusion_tag('search_strategy/tags/pic_framework.html')
def pic_framework_display(query: SearchQuery):
    """
    Render the PIC framework components in a structured layout.
    
    Args:
        query: SearchQuery instance
        
    Returns:
        Context for the PIC framework template
    """
    return {
        'query': query,
        'population': query.population,
        'interest': query.interest,
        'context': query.context,
        'has_population': bool(query.population and query.population.strip()),
        'has_interest': bool(query.interest and query.interest.strip()),
        'has_context': bool(query.context and query.context.strip()),
    }


@register.simple_tag
def query_optimization_alerts(query: SearchQuery) -> str:
    """
    Generate optimization alerts for a query.
    
    Args:
        query: SearchQuery instance
        
    Returns:
        HTML string with optimization alerts
    """
    if not query.query_string:
        return ''
    
    analysis = optimize_query_string(query.query_string)
    suggestions = analysis.get('suggestions', [])
    
    if not suggestions:
        return '<div class="alert alert-success alert-sm">Query looks good!</div>'
    
    alerts_html = []
    for suggestion in suggestions[:3]:  # Limit to 3 suggestions
        alerts_html.append(
            format_html(
                '<div class="alert alert-warning alert-sm mb-1">'
                '<i class="bi bi-lightbulb me-1"></i>{}'
                '</div>',
                suggestion
            )
        )
    
    return mark_safe(''.join(alerts_html))


@register.filter
def search_engines_badges(engines: List[str]) -> str:
    """
    Render badges for search engines.
    
    Args:
        engines: List of search engine names
        
    Returns:
        HTML string with engine badges
    """
    if not engines:
        return '<span class="text-muted">None specified</span>'
    
    engine_colors = {
        'google': 'primary',
        'bing': 'info',
        'duckduckgo': 'success',
        'yahoo': 'warning',
    }
    
    badges = []
    for engine in engines:
        color = engine_colors.get(engine.lower(), 'secondary')
        badges.append(
            format_html(
                '<span class="badge bg-{} me-1">{}</span>',
                color,
                engine.title()
            )
        )
    
    return mark_safe(''.join(badges))


@register.filter
def query_status_icon(query: SearchQuery) -> str:
    """
    Render a status icon for a query.
    
    Args:
        query: SearchQuery instance
        
    Returns:
        HTML string with status icon
    """
    if not query.is_active:
        return '<i class="bi bi-pause-circle text-muted" title="Inactive"></i>'
    elif query.execution_count > 0:
        return '<i class="bi bi-check-circle text-success" title="Executed"></i>'
    else:
        return '<i class="bi bi-clock text-warning" title="Pending execution"></i>'


@register.inclusion_tag('search_strategy/tags/query_summary_card.html')
def query_summary_card(query: SearchQuery):
    """
    Render a summary card for a search query.
    
    Args:
        query: SearchQuery instance
        
    Returns:
        Context for the query summary template
    """
    complexity = calculate_query_complexity(query)
    
    return {
        'query': query,
        'complexity': complexity,
        'has_filters': bool(
            query.date_from or query.date_to or 
            query.languages or query.document_types
        ),
        'total_keywords': len(query.include_keywords) + len(query.exclude_keywords),
    }


@register.filter
def date_range_display(query: SearchQuery) -> str:
    """
    Display date range in a human-readable format.
    
    Args:
        query: SearchQuery instance
        
    Returns:
        Formatted date range string
    """
    if not query.date_from and not query.date_to:
        return 'All dates'
    
    date_from_str = query.date_from.strftime('%Y-%m-%d') if query.date_from else 'Beginning'
    date_to_str = query.date_to.strftime('%Y-%m-%d') if query.date_to else 'Present'
    
    return f"{date_from_str} to {date_to_str}"


@register.simple_tag
def template_usage_badge(template: QueryTemplate) -> str:
    """
    Render a usage count badge for a query template.
    
    Args:
        template: QueryTemplate instance
        
    Returns:
        HTML string with usage badge
    """
    if template.usage_count == 0:
        return '<span class="badge bg-light text-muted">Unused</span>'
    elif template.usage_count < 5:
        return format_html('<span class="badge bg-info">{} uses</span>', template.usage_count)
    elif template.usage_count < 20:
        return format_html('<span class="badge bg-success">{} uses</span>', template.usage_count)
    else:
        return format_html('<span class="badge bg-warning">{} uses</span>', template.usage_count)


@register.filter
def highlight_placeholders(template_text: str) -> str:
    """
    Highlight placeholders in template text.
    
    Args:
        template_text: Template text with placeholders
        
    Returns:
        HTML string with highlighted placeholders
    """
    if not template_text:
        return ''
    
    import re
    
    # Find all placeholders in format {placeholder}
    def replace_placeholder(match):
        placeholder = match.group(1)
        return format_html('<span class="badge bg-primary">{{{}}}</span>', placeholder)
    
    highlighted = re.sub(r'\{([^}]+)\}', replace_placeholder, template_text)
    return mark_safe(highlighted)


@register.simple_tag
def execution_history_icon(query: SearchQuery) -> str:
    """
    Show execution history icon with tooltip.
    
    Args:
        query: SearchQuery instance
        
    Returns:
        HTML string with history icon
    """
    if query.execution_count == 0:
        return '<i class="bi bi-clock text-muted" title="Never executed"></i>'
    
    last_executed = query.last_executed.strftime('%Y-%m-%d %H:%M') if query.last_executed else 'Unknown'
    
    return format_html(
        '<i class="bi bi-arrow-clockwise text-info" title="Executed {} times. Last: {}"></i>',
        query.execution_count,
        last_executed
    )


@register.filter
def truncate_query(query_string: str, max_length: int = 100) -> str:
    """
    Truncate query string for display.
    
    Args:
        query_string: The query string to truncate
        max_length: Maximum length before truncation
        
    Returns:
        Truncated query string
    """
    if not query_string:
        return ''
    
    if len(query_string) <= max_length:
        return query_string
    
    truncated = query_string[:max_length].rsplit(' ', 1)[0]
    return f"{truncated}..."