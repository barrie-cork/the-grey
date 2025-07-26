"""
Search execution management service for serp_execution slice.
Business capability: Core search execution logic and coordination.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q, Count, Avg

from apps.core.logging import ServiceLoggerMixin


class ExecutionService(ServiceLoggerMixin):
    """Service for managing search execution lifecycle and coordination."""
    
    def estimate_execution_time(self, query_complexity: int, search_engines: List[str]) -> int:
        """
        Estimate execution time based on query parameters.
        
        Args:
            query_complexity: Complexity score of the query
            search_engines: List of search engines to query
            
        Returns:
            Estimated time in seconds
        """
        base_time = 5  # Base time per search engine
        complexity_multiplier = 1 + (query_complexity / 20)  # Scale based on complexity
        engine_count = len(search_engines)
        
        estimated_time = int(base_time * complexity_multiplier * engine_count)
        return max(estimated_time, 10)  # Minimum 10 seconds
    
    def get_execution_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        Get comprehensive execution statistics for a session.
        """
        from ..models import SearchExecution, RawSearchResult
        
        executions = SearchExecution.objects.filter(query__strategy__session_id=session_id)
        
        if not executions.exists():
            return self._empty_stats()
        
        completed_executions = executions.filter(status='completed')
        failed_executions = executions.filter(status='failed')
        
        stats = executions.aggregate(
            total_executions=Count('id'),
            avg_execution_time=Avg('execution_time'),
            total_results=Count('raw_results'),
        )
        
        return {
            'total_executions': stats['total_executions'],
            'completed_executions': completed_executions.count(),
            'failed_executions': failed_executions.count(),
            'success_rate': round(
                (completed_executions.count() / stats['total_executions']) * 100, 1
            ) if stats['total_executions'] > 0 else 0,
            'average_execution_time': round(stats['avg_execution_time'] or 0, 2),
            'total_results_found': stats['total_results'],
            'execution_status_breakdown': self._get_status_breakdown(executions),
        }
    
    def validate_execution_readiness(self, session_id: str) -> Dict[str, Any]:
        """
        Validate if a session is ready for execution.
        """
        from apps.search_strategy.signals import get_session_queries_data
        from apps.review_manager.signals import get_session_data
        
        session_data = get_session_data(session_id)
        queries_data = get_session_queries_data(session_id)
        
        validation_result = {
            'is_ready': True,
            'issues': [],
            'warnings': []
        }
        
        # Check session status
        if session_data.get('status') != 'ready_to_execute':
            validation_result['is_ready'] = False
            validation_result['issues'].append(
                f"Session status is '{session_data.get('status')}', must be 'ready_to_execute'"
            )
        
        # Check queries
        if not queries_data:
            validation_result['is_ready'] = False
            validation_result['issues'].append("No active queries found")
        
        # Validate each query
        for query in queries_data:
            if not query.get('query_string'):
                validation_result['is_ready'] = False
                validation_result['issues'].append(f"Query '{query.get('title')}' has no query string")
            
            if not query.get('search_engines'):
                validation_result['warnings'].append(f"Query '{query.get('title')}' has no search engines specified")
        
        return validation_result
    
    def calculate_search_coverage(self, session_id: str) -> Dict[str, Any]:
        """
        Calculate search coverage analysis for a session.
        """
        from ..models import SearchExecution
        from apps.search_strategy.signals import get_session_queries_data
        
        queries_data = get_session_queries_data(session_id)
        executions = SearchExecution.objects.filter(query__strategy__session_id=session_id)
        
        total_queries = len(queries_data)
        executed_queries = executions.values('query_id').distinct().count()
        
        # Calculate engine coverage
        planned_engines = set()
        for query in queries_data:
            planned_engines.update(query.get('search_engines', []))
        
        executed_engines = set(
            executions.filter(status='completed').values_list('search_engine', flat=True)
        )
        
        return {
            'total_planned_queries': total_queries,
            'executed_queries': executed_queries,
            'query_coverage_percentage': round(
                (executed_queries / total_queries) * 100, 1
            ) if total_queries > 0 else 0,
            'planned_engines': list(planned_engines),
            'executed_engines': list(executed_engines),
            'missing_engines': list(planned_engines - executed_engines),
            'engine_coverage_percentage': round(
                (len(executed_engines) / len(planned_engines)) * 100, 1
            ) if planned_engines else 0,
        }
    
    def get_execution_timeline(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get execution timeline for visualization.
        """
        from ..models import SearchExecution
        
        executions = SearchExecution.objects.filter(
            query__strategy__session_id=session_id
        ).order_by('started_at')
        
        timeline = []
        for execution in executions:
            timeline.append({
                'execution_id': str(execution.id),
                'query_title': execution.query.title if hasattr(execution, 'query') else 'Unknown',
                'search_engine': execution.search_engine,
                'status': execution.status,
                'started_at': execution.started_at.isoformat() if execution.started_at else None,
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                'duration_seconds': execution.execution_time,
                'results_count': execution.results_count,
            })
        
        return timeline
    
    def _empty_stats(self) -> Dict[str, Any]:
        """Return empty statistics structure."""
        return {
            'total_executions': 0,
            'completed_executions': 0,
            'failed_executions': 0,
            'success_rate': 0,
            'average_execution_time': 0,
            'total_results_found': 0,
            'execution_status_breakdown': {},
        }
    
    def _get_status_breakdown(self, executions) -> Dict[str, int]:
        """Get breakdown of execution statuses."""
        status_counts = executions.values('status').annotate(count=Count('status'))
        return {item['status']: item['count'] for item in status_counts}