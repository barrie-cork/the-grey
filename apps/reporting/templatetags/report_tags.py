"""
Custom template tags for reporting and data export.

These tags provide convenient filters and tags for displaying
reports, statistics, and export functionality.
"""

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from typing import Dict, Any
import json

from ..utils import generate_prisma_flow_data, calculate_search_performance_metrics

register = template.Library()


@register.filter
def format_large_number(value: int) -> str:
    """
    Format large numbers with appropriate suffixes.
    
    Args:
        value: Number to format
        
    Returns:
        Formatted number string
    """
    if not value:
        return '0'
    
    if value >= 1000000:
        return f"{value/1000000:.1f}M"
    elif value >= 1000:
        return f"{value/1000:.1f}K"
    else:
        return str(value)


@register.filter
def percentage_badge(value: float, threshold_good: float = 75, threshold_fair: float = 50) -> str:
    """
    Render a percentage as a colored badge.
    
    Args:
        value: Percentage value
        threshold_good: Threshold for good performance
        threshold_fair: Threshold for fair performance
        
    Returns:
        HTML string with colored badge
    """
    if not value:
        value = 0
    
    if value >= threshold_good:
        color = 'success'
    elif value >= threshold_fair:
        color = 'warning'
    else:
        color = 'danger'
    
    return format_html(
        '<span class="badge bg-{}">{:.1f}%</span>',
        color,
        value
    )


@register.inclusion_tag('reporting/tags/prisma_flow_diagram.html')
def prisma_flow_diagram(session_id: str):
    """
    Render PRISMA flow diagram with data.
    
    Args:
        session_id: UUID of the SearchSession
        
    Returns:
        Context for PRISMA flow diagram template
    """
    flow_data = generate_prisma_flow_data(session_id)
    
    return {
        'session_id': session_id,
        'flow_data': flow_data,
        'has_data': bool(flow_data)
    }


@register.simple_tag
def performance_metric_card(session_id: str, metric_type: str) -> str:
    """
    Render a performance metric card.
    
    Args:
        session_id: UUID of the SearchSession
        metric_type: Type of metric ('efficiency', 'relevance', 'cost')
        
    Returns:
        HTML string with metric card
    """
    metrics = calculate_search_performance_metrics(session_id)
    
    card_configs = {
        'efficiency': {
            'title': 'Search Efficiency',
            'icon': 'bi-speedometer2',
            'value': f"{metrics.get('search_efficiency', {}).get('success_rate', 0)}%",
            'description': 'Success Rate',
            'color': 'primary'
        },
        'relevance': {
            'title': 'Relevance',
            'icon': 'bi-bullseye',
            'value': f"{metrics.get('relevance_metrics', {}).get('precision', 0)}%",
            'description': 'Precision',
            'color': 'success'
        },
        'cost': {
            'title': 'Cost Effectiveness',
            'icon': 'bi-currency-dollar',
            'value': f"${metrics.get('cost_effectiveness', {}).get('cost_per_included_study', 0):.2f}",
            'description': 'Per Included Study',
            'color': 'info'
        }
    }
    
    if metric_type not in card_configs:
        return ''
    
    config = card_configs[metric_type]
    
    return format_html(
        '<div class="card border-{} h-100">'
        '<div class="card-body text-center">'
        '<i class="bi {} text-{} fs-1 mb-3"></i>'
        '<h3 class="card-title">{}</h3>'
        '<h2 class="text-{}">{}</h2>'
        '<p class="text-muted">{}</p>'
        '</div>'
        '</div>',
        config['color'],
        config['icon'],
        config['color'],
        config['title'],
        config['color'],
        config['value'],
        config['description']
    )


@register.filter
def export_format_icon(format_type: str) -> str:
    """
    Get icon for export format.
    
    Args:
        format_type: Export format type
        
    Returns:
        HTML string with icon
    """
    icons = {
        'pdf': 'bi-file-pdf text-danger',
        'docx': 'bi-file-word text-primary',
        'xlsx': 'bi-file-excel text-success',
        'csv': 'bi-file-spreadsheet text-info',
        'json': 'bi-file-code text-warning',
        'bibtex': 'bi-file-text text-secondary'
    }
    
    icon_class = icons.get(format_type, 'bi-file text-muted')
    
    return format_html('<i class="{}"></i>', icon_class)


@register.simple_tag
def study_characteristics_summary(session_id: str) -> str:
    """
    Generate summary of study characteristics.
    
    Args:
        session_id: UUID of the SearchSession
        
    Returns:
        HTML string with characteristics summary
    """
    from ..utils import generate_study_characteristics_table
    
    characteristics = generate_study_characteristics_table(session_id)
    total_studies = characteristics['total_studies']
    
    if total_studies == 0:
        return '<p class="text-muted">No included studies to summarize.</p>'
    
    # Get year range
    years = characteristics['summary_statistics']['publication_years']
    year_range = f"{min(years.keys())}-{max(years.keys())}" if years else "Unknown"
    
    # Get document types
    doc_types = list(characteristics['summary_statistics']['document_types'].keys())[:3]
    types_text = ', '.join(doc_types) + ('...' if len(doc_types) > 3 else '')
    
    # Full text availability
    full_text_count = characteristics['summary_statistics']['full_text_availability']
    full_text_pct = round(full_text_count / total_studies * 100, 1) if total_studies > 0 else 0
    
    return format_html(
        '<div class="row">'
        '<div class="col-md-3">'
        '<h5>{}</h5>'
        '<p class="text-muted">Total Studies</p>'
        '</div>'
        '<div class="col-md-3">'
        '<h5>{}</h5>'
        '<p class="text-muted">Publication Years</p>'
        '</div>'
        '<div class="col-md-3">'
        '<h5>{}%</h5>'
        '<p class="text-muted">Full Text Available</p>'
        '</div>'
        '<div class="col-md-3">'
        '<h5>{}</h5>'
        '<p class="text-muted">Document Types</p>'
        '</div>'
        '</div>',
        total_studies,
        year_range,
        full_text_pct,
        types_text
    )


@register.simple_tag
def report_generation_status(report) -> str:
    """
    Show report generation status badge.
    
    Args:
        report: ExportReport instance
        
    Returns:
        HTML string with status badge
    """
    status_colors = {
        'pending': 'secondary',
        'generating': 'info',
        'completed': 'success',
        'failed': 'danger'
    }
    
    color = status_colors.get(getattr(report, 'status', 'pending'), 'secondary')
    status_text = getattr(report, 'status', 'pending').title()
    
    return format_html(
        '<span class="badge bg-{}">{}</span>',
        color,
        status_text
    )


@register.inclusion_tag('reporting/tags/search_summary_table.html')
def search_summary_table(session_id: str):
    """
    Render search strategy summary table.
    
    Args:
        session_id: UUID of the SearchSession
        
    Returns:
        Context for search summary table
    """
    from ..utils import generate_search_strategy_report
    
    report_data = generate_search_strategy_report(session_id)
    
    return {
        'session_id': session_id,
        'report_data': report_data,
        'queries': report_data.get('queries', []),
        'execution_summary': report_data.get('execution_summary', {})
    }


@register.filter
def format_cost(amount) -> str:
    """
    Format cost amount with currency symbol.
    
    Args:
        amount: Cost amount (Decimal or float)
        
    Returns:
        Formatted cost string
    """
    if not amount:
        return '$0.00'
    
    return f"${float(amount):.2f}"


@register.simple_tag
def export_button(session_id: str, format_type: str, report_type: str) -> str:
    """
    Render export button for specific format and report type.
    
    Args:
        session_id: UUID of the SearchSession
        format_type: Export format
        report_type: Type of report
        
    Returns:
        HTML string with export button
    """
    icon = export_format_icon(format_type)
    
    return format_html(
        '<button class="btn btn-outline-primary btn-sm me-2" '
        'onclick="exportReport(\'{}\', \'{}\', \'{}\')">'
        '{} Export {}'
        '</button>',
        session_id,
        report_type,
        format_type,
        icon,
        format_type.upper()
    )


@register.filter
def chart_data_json(data: Dict[str, Any]) -> str:
    """
    Convert data to JSON for charts.
    
    Args:
        data: Data dictionary
        
    Returns:
        JSON string
    """
    return json.dumps(data, default=str)


@register.simple_tag
def prisma_compliance_indicator(session_id: str) -> str:
    """
    Show PRISMA compliance indicator.
    
    Args:
        session_id: UUID of the SearchSession
        
    Returns:
        HTML string with compliance indicator
    """
    from ..utils import export_prisma_checklist
    
    checklist = export_prisma_checklist(session_id)
    completion_pct = checklist.get('completion_summary', {}).get('completion_percentage', 0)
    
    if completion_pct >= 90:
        color = 'success'
        icon = 'bi-check-circle-fill'
        text = 'Highly Compliant'
    elif completion_pct >= 70:
        color = 'warning'
        icon = 'bi-exclamation-triangle-fill'
        text = 'Partially Compliant'
    else:
        color = 'danger'
        icon = 'bi-x-circle-fill'
        text = 'Needs Improvement'
    
    return format_html(
        '<div class="d-flex align-items-center">'
        '<i class="bi {} text-{} me-2"></i>'
        '<span class="text-{}">{} ({}%)</span>'
        '</div>',
        icon,
        color,
        color,
        text,
        completion_pct
    )


@register.filter
def file_size_human(bytes_size: int) -> str:
    """
    Format file size in human readable format.
    
    Args:
        bytes_size: Size in bytes
        
    Returns:
        Formatted size string
    """
    if not bytes_size:
        return '0 B'
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    
    return f"{bytes_size:.1f} TB"