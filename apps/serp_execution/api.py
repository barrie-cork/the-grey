"""
Internal API for serp_execution slice.
VSA-compliant data access without exposing models.
"""

from typing import Dict, List, Any


def get_session_executions_data(session_id: str) -> List[Dict[str, Any]]:
    """
    Get execution data for a session without exposing models.
    """
    from .models import SearchExecution, RawSearchResult
    
    executions = SearchExecution.objects.filter(
        query__strategy__session_id=session_id,
        status='completed'
    )
    
    return [
        {
            'id': str(execution.id),
            'query_id': str(execution.query.id),
            'status': execution.status,
            'results_count': execution.results_count,
            'execution_time': execution.execution_time,
            'api_credits_used': execution.api_credits_used,
            'started_at': execution.started_at.isoformat() if execution.started_at else None,
            'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
        }
        for execution in executions
    ]


def get_raw_results_count(session_id: str) -> int:
    """Get count of raw search results for a session."""
    from .models import RawSearchResult
    
    return RawSearchResult.objects.filter(
        execution__query__strategy__session_id=session_id
    ).count()


def get_session_execution_stats(session_id: str) -> Dict[str, Any]:
    """Get execution statistics for a session."""
    from .models import SearchExecution
    from django.db.models import Sum, Avg
    
    executions = SearchExecution.objects.filter(query__strategy__session_id=session_id)
    
    stats = executions.aggregate(
        total_executions=executions.count(),
        completed_executions=executions.filter(status='completed').count(),
        total_credits=Sum('api_credits_used'),
        avg_execution_time=Avg('execution_time'),
        total_results=Sum('results_count')
    )
    
    return {
        'total_executions': stats['total_executions'] or 0,
        'completed_executions': stats['completed_executions'] or 0,
        'total_credits_used': float(stats['total_credits'] or 0),
        'average_execution_time': float(stats['avg_execution_time'] or 0),
        'total_raw_results': stats['total_results'] or 0,
    }