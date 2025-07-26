"""
Search strategy reporting service for reporting slice.
Business capability: Search strategy documentation and reporting.
"""

from typing import Dict, Any
from django.db import models

from apps.core.logging import ServiceLoggerMixin


class SearchStrategyReportingService(ServiceLoggerMixin):
    """Service for generating comprehensive search strategy reports."""
    
    def generate_search_strategy_report(self, session_id: str) -> Dict[str, Any]:
        """
        Generate comprehensive search strategy documentation.
        
        Args:
            session_id: UUID of the SearchSession
            
        Returns:
            Dictionary with search strategy report data
        """
        from apps.review_manager.models import SearchSession
        from apps.search_strategy.models import SearchQuery
        from apps.serp_execution.models import SearchExecution
        
        try:
            session = SearchSession.objects.get(id=session_id)
        except SearchSession.DoesNotExist:
            return {}
        
        queries = SearchQuery.objects.filter(session=session, is_active=True)
        executions = SearchExecution.objects.filter(query__session=session)
        
        report_data = {
            'session_overview': {
                'title': session.title,
                'description': session.description,
                'created_date': session.created_at.date(),
                'status': session.status
            },
            'search_framework': {
                'total_queries': queries.count(),
                'primary_queries': queries.filter(is_primary=True).count(),
                'secondary_queries': queries.filter(is_primary=False).count()
            },
            'queries': [],
            'execution_summary': {
                'total_executions': executions.count(),
                'successful_executions': executions.filter(status='completed').count(),
                'total_results_retrieved': sum(e.results_count for e in executions),
                'search_engines_used': list(set(e.search_engine for e in executions)),
                'total_cost': sum(e.estimated_cost for e in executions)
            }
        }
        
        # Detailed query information
        for query in queries:
            query_executions = executions.filter(query=query)
            
            query_data = {
                'id': str(query.id),
                'pic_framework': {
                    'population': query.population,
                    'interest': query.interest,
                    'context': query.context
                },
                'query_string': query.query_string,
                'parameters': {
                    'search_engines': query.search_engines,
                    'include_keywords': query.include_keywords,
                    'exclude_keywords': query.exclude_keywords,
                    'date_range': {
                        'from': query.date_from.isoformat() if query.date_from else None,
                        'to': query.date_to.isoformat() if query.date_to else None
                    },
                    'languages': query.languages,
                    'document_types': query.document_types,
                    'max_results': query.max_results
                },
                'execution_results': {
                    'executions_count': query_executions.count(),
                    'total_results': sum(e.results_count for e in query_executions),
                    'avg_results_per_execution': round(
                        sum(e.results_count for e in query_executions) / max(query_executions.count(), 1), 1
                    ),
                    'success_rate': round(
                        query_executions.filter(status='completed').count() / max(query_executions.count(), 1) * 100, 1
                    )
                }
            }
            
            report_data['queries'].append(query_data)
        
        return report_data
    
    def generate_query_optimization_report(self, session_id: str) -> Dict[str, Any]:
        """
        Generate report on query optimization and effectiveness.
        
        Args:
            session_id: UUID of the SearchSession
            
        Returns:
            Dictionary with query optimization analysis
        """
        from apps.search_strategy.models import SearchQuery
        from apps.serp_execution.models import SearchExecution
        from apps.results_manager.models import ProcessedResult
        
        queries = SearchQuery.objects.filter(session_id=session_id, is_active=True)
        
        optimization_data = {
            'session_id': session_id,
            'query_performance': [],
            'recommendations': [],
            'overall_metrics': {
                'avg_results_per_query': 0,
                'avg_relevance_score': 0,
                'most_effective_engines': [],
                'keyword_effectiveness': {}
            }
        }
        
        total_results = 0
        total_relevance = 0
        engine_performance = {}
        
        for query in queries:
            executions = SearchExecution.objects.filter(query=query)
            processed_results = ProcessedResult.objects.filter(
                raw_result__execution__query=query
            )
            
            query_results = sum(e.results_count for e in executions)
            query_relevance = processed_results.aggregate(
                avg_relevance=models.Avg('relevance_score')
            )['avg_relevance'] or 0
            
            query_performance = {
                'query_id': str(query.id),
                'query_string': query.query_string,
                'total_results': query_results,
                'avg_relevance': round(query_relevance, 3),
                'execution_success_rate': round(
                    executions.filter(status='completed').count() / max(executions.count(), 1) * 100, 1
                ),
                'cost_effectiveness': round(
                    query_results / max(sum(e.estimated_cost for e in executions), 0.01), 2
                )
            }
            
            optimization_data['query_performance'].append(query_performance)
            
            total_results += query_results
            total_relevance += query_relevance
            
            # Track engine performance
            for execution in executions:
                engine = execution.search_engine
                if engine not in engine_performance:
                    engine_performance[engine] = {'results': 0, 'count': 0}
                engine_performance[engine]['results'] += execution.results_count
                engine_performance[engine]['count'] += 1
        
        # Calculate overall metrics
        query_count = queries.count()
        if query_count > 0:
            optimization_data['overall_metrics']['avg_results_per_query'] = round(total_results / query_count, 1)
            optimization_data['overall_metrics']['avg_relevance_score'] = round(total_relevance / query_count, 3)
        
        # Most effective engines
        sorted_engines = sorted(
            engine_performance.items(),
            key=lambda x: x[1]['results'] / x[1]['count'],
            reverse=True
        )
        optimization_data['overall_metrics']['most_effective_engines'] = [
            {'engine': engine, 'avg_results': round(data['results'] / data['count'], 1)}
            for engine, data in sorted_engines[:3]
        ]
        
        return optimization_data