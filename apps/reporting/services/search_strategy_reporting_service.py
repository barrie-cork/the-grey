"""
Search strategy reporting service for reporting slice.
Business capability: Search strategy documentation and reporting.
"""

from typing import Any, Dict, List

from apps.core.logging import ServiceLoggerMixin
from apps.reporting.constants import PerformanceConstants, SearchStrategyConstants
from apps.results_manager.models import ProcessedResult
from apps.review_manager.models import SearchSession
from apps.search_strategy.models import SearchQuery
from apps.serp_execution.models import SearchExecution


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
        try:
            session = SearchSession.objects.get(id=session_id)
        except SearchSession.DoesNotExist:
            return {}

        queries = SearchQuery.objects.filter(session=session, is_active=True)
        executions = SearchExecution.objects.filter(query__session=session)

        report_data = {
            "session_overview": {
                "title": session.title,
                "description": session.description,
                "created_date": session.created_at.date(),
                "status": session.status,
            },
            "search_framework": {
                "total_queries": queries.count(),
                "primary_queries": queries.filter(is_primary=True).count(),
                "secondary_queries": queries.filter(is_primary=False).count(),
            },
            "queries": [],
            "execution_summary": {
                "total_executions": executions.count(),
                "successful_executions": executions.filter(
                    status=PerformanceConstants.COMPLETED_STATUS
                ).count(),
                "total_results_retrieved": sum(e.results_count for e in executions),
                "search_engines_used": list(set(e.search_engine for e in executions)),
                "total_cost": sum(e.estimated_cost for e in executions),
            },
        }

        # Detailed query information
        for query in queries:
            query_executions = executions.filter(query=query)

            query_data = {
                "id": str(query.id),
                "pic_framework": {
                    "population": query.population,
                    "interest": query.interest,
                    "context": query.context,
                },
                "query_string": query.query_string,
                "parameters": {
                    "search_engines": query.search_engines,
                    "include_keywords": query.include_keywords,
                    "exclude_keywords": query.exclude_keywords,
                    "date_range": {
                        "from": (
                            query.date_from.isoformat() if query.date_from else None
                        ),
                        "to": query.date_to.isoformat() if query.date_to else None,
                    },
                    "languages": query.languages,
                    "document_types": query.document_types,
                    "max_results": query.max_results,
                },
                "execution_results": {
                    "executions_count": query_executions.count(),
                    "total_results": sum(e.results_count for e in query_executions),
                    "avg_results_per_execution": round(
                        sum(e.results_count for e in query_executions)
                        / max(
                            query_executions.count(), PerformanceConstants.MIN_DIVISOR
                        ),
                        PerformanceConstants.DECIMAL_PLACES["ratio"],
                    ),
                    "success_rate": round(
                        query_executions.filter(
                            status=PerformanceConstants.COMPLETED_STATUS
                        ).count()
                        / max(
                            query_executions.count(), PerformanceConstants.MIN_DIVISOR
                        )
                        * PerformanceConstants.PERCENTAGE_MULTIPLIER,
                        PerformanceConstants.DECIMAL_PLACES["percentage"],
                    ),
                },
            }

            report_data["queries"].append(query_data)

        return report_data

    def _initialize_optimization_report(self, session_id: str) -> Dict[str, Any]:
        """Initialize the optimization report structure."""
        return {
            "session_id": session_id,
            "query_performance": [],
            "recommendations": [],
            "overall_metrics": {
                "avg_results_per_query": 0,
                "most_effective_engines": [],
                "keyword_effectiveness": {},
            },
        }

    def _calculate_success_rate(self, executions) -> float:
        """Calculate execution success rate."""
        if executions.count() == 0:
            return 0.0
        
        success_count = executions.filter(
            status=PerformanceConstants.COMPLETED_STATUS
        ).count()
        
        return round(
            success_count / executions.count() * PerformanceConstants.PERCENTAGE_MULTIPLIER,
            PerformanceConstants.DECIMAL_PLACES["percentage"],
        )

    def _calculate_cost_effectiveness(self, total_results: int, executions) -> float:
        """Calculate cost effectiveness (results per cost unit)."""
        total_cost = sum(e.estimated_cost for e in executions)
        if total_cost <= 0:
            total_cost = 0.01
        
        return round(
            total_results / total_cost,
            PerformanceConstants.DECIMAL_PLACES["ratio"],
        )

    def _build_query_performance(self, query, executions) -> Dict[str, Any]:
        """Build performance metrics for a single query."""
        query_results = sum(e.results_count for e in executions)
        
        return {
            "query_id": str(query.id),
            "query_string": query.query_string,
            "total_results": query_results,
            "execution_success_rate": self._calculate_success_rate(executions),
            "cost_effectiveness": self._calculate_cost_effectiveness(query_results, executions),
        }

    def _track_engine_performance(self, executions, engine_performance: Dict) -> None:
        """Track performance metrics by search engine."""
        for execution in executions:
            engine = execution.search_engine
            if engine not in engine_performance:
                engine_performance[engine] = {"results": 0, "count": 0}
            engine_performance[engine]["results"] += execution.results_count
            engine_performance[engine]["count"] += 1

    def _calculate_overall_metrics(self, total_results: int, query_count: int, 
                                  engine_performance: Dict) -> Dict[str, Any]:
        """Calculate overall optimization metrics."""
        metrics = {}
        
        # Average results per query
        if query_count > 0:
            metrics["avg_results_per_query"] = round(
                total_results / query_count,
                PerformanceConstants.DECIMAL_PLACES["ratio"],
            )
        else:
            metrics["avg_results_per_query"] = 0
        
        # Most effective engines
        metrics["most_effective_engines"] = self._get_top_engines(engine_performance)
        metrics["keyword_effectiveness"] = {}  # Placeholder for future implementation
        
        return metrics

    def _calculate_engine_average(self, data: Dict[str, int]) -> float:
        """Calculate average results per execution for an engine."""
        if data["count"] == 0:
            return 0.0
        return data["results"] / data["count"]
    
    def _format_engine_result(self, engine: str, data: Dict[str, int]) -> Dict[str, Any]:
        """Format engine performance data."""
        return {
            "engine": engine,
            "avg_results": round(
                self._calculate_engine_average(data),
                PerformanceConstants.DECIMAL_PLACES["ratio"],
            ),
        }
    
    def _get_top_engines(self, engine_performance: Dict) -> List[Dict[str, Any]]:
        """Get top performing search engines."""
        if not engine_performance:
            return []
        
        # Sort by average results per execution
        sorted_engines = sorted(
            engine_performance.items(),
            key=lambda x: self._calculate_engine_average(x[1]),
            reverse=True,
        )[:SearchStrategyConstants.TOP_ENGINES_LIMIT]
        
        return [self._format_engine_result(engine, data) for engine, data in sorted_engines]

    def generate_query_optimization_report(self, session_id: str) -> Dict[str, Any]:
        """
        Generate report on query optimization and effectiveness.

        Args:
            session_id: UUID of the SearchSession

        Returns:
            Dictionary with query optimization analysis
        """
        queries = SearchQuery.objects.filter(session_id=session_id, is_active=True)
        optimization_data = self._initialize_optimization_report(session_id)
        
        total_results = 0
        engine_performance = {}

        # Process each query
        for query in queries:
            executions = SearchExecution.objects.filter(query=query)
            
            # Build query performance metrics
            query_performance = self._build_query_performance(query, executions)
            optimization_data["query_performance"].append(query_performance)
            
            # Update totals
            total_results += query_performance["total_results"]
            
            # Track engine performance
            self._track_engine_performance(executions, engine_performance)

        # Calculate overall metrics
        optimization_data["overall_metrics"] = self._calculate_overall_metrics(
            total_results, queries.count(), engine_performance
        )

        return optimization_data
