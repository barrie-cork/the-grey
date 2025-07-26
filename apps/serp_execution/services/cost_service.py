"""
Cost calculation and budget management service for serp_execution slice.
Business capability: Cost tracking and budget management.
"""

from decimal import Decimal
from typing import Dict, List, Any
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime, timedelta

from apps.core.logging import ServiceLoggerMixin


class CostService(ServiceLoggerMixin):
    """Service for handling all cost-related calculations and budget tracking."""
    
    def calculate_api_cost(self, credits_used: int, rate_per_credit: Decimal = Decimal('0.001')) -> Decimal:
        """
        Calculate the estimated cost for API usage.
        
        Args:
            credits_used: Number of API credits consumed
            rate_per_credit: Cost per credit in USD
            
        Returns:
            Estimated cost in USD
        """
        return Decimal(credits_used) * rate_per_credit
    
    def estimate_session_cost(self, session_id: str) -> Dict[str, Any]:
        """
        Estimate total cost for a session based on planned executions.
        """
        from apps.search_strategy.signals import get_query_count
        from ..models import SearchExecution
        
        query_count = get_query_count(session_id)
        avg_cost_per_query = self._get_average_cost_per_query()
        
        estimated_total = avg_cost_per_query * query_count
        
        return {
            'estimated_total_cost': estimated_total,
            'cost_per_query': avg_cost_per_query,
            'query_count': query_count,
            'currency': 'USD'
        }
    
    def get_actual_session_cost(self, session_id: str) -> Dict[str, Any]:
        """
        Get actual costs for a session based on completed executions.
        """
        from ..models import SearchExecution
        
        executions = SearchExecution.objects.filter(
            query__session_id=session_id,
            status='completed'
        )
        
        total_credits = executions.aggregate(
            total=Sum('api_credits_used')
        )['total'] or 0
        
        total_cost = self.calculate_api_cost(total_credits)
        
        return {
            'total_cost': total_cost,
            'total_credits_used': total_credits,
            'executions_count': executions.count(),
            'average_cost_per_execution': total_cost / executions.count() if executions.count() > 0 else 0
        }
    
    def check_budget_status(self, session_id: str, budget_limit: Decimal) -> Dict[str, Any]:
        """
        Check budget status and provide warnings if needed.
        """
        current_cost = self.get_actual_session_cost(session_id)['total_cost']
        estimated_total = self.estimate_session_cost(session_id)['estimated_total_cost']
        
        remaining_budget = budget_limit - current_cost
        budget_utilization = (current_cost / budget_limit) * 100 if budget_limit > 0 else 0
        
        return {
            'current_cost': current_cost,
            'estimated_total_cost': estimated_total,
            'budget_limit': budget_limit,
            'remaining_budget': remaining_budget,
            'budget_utilization_percent': round(budget_utilization, 1),
            'is_over_budget': current_cost > budget_limit,
            'warning_threshold_reached': budget_utilization > 80,
        }
    
    def calculate_session_cost_estimate(self, session_id: str) -> Dict[str, Any]:
        """
        Calculate comprehensive cost estimate for a search session.
        
        Args:
            session_id: UUID of the SearchSession
            
        Returns:
            Dictionary with cost estimates and breakdown
        """
        from apps.search_strategy.signals import get_session_queries_data
        
        queries_data = get_session_queries_data(session_id)
        
        if not queries_data:
            return {
                'total_queries': 0,
                'total_engines': 0,
                'estimated_api_calls': 0,
                'estimated_credits': 0,
                'estimated_cost': Decimal('0.00'),
                'cost_breakdown': {},
                'query_details': []
            }
        
        total_queries = len(queries_data)
        engines_by_query = {}
        query_details = []
        
        for query in queries_data:
            engines = query.get('search_engines', [])
            query_detail = {
                'id': query.get('id'),
                'query_string': query.get('query_string', '')[:50] + '...' if len(query.get('query_string', '')) > 50 else query.get('query_string', ''),
                'engines': engines,
                'results_per_page': query.get('results_per_page', 100),
                'estimated_credits': len(engines) * 100
            }
            query_details.append(query_detail)
            
            for engine in engines:
                if engine not in engines_by_query:
                    engines_by_query[engine] = 0
                engines_by_query[engine] += 1
        
        # Calculate totals
        total_api_calls = sum(len(q.get('search_engines', [])) for q in queries_data)
        estimated_credits = total_api_calls * 100  # 100 credits per search
        estimated_cost = self.calculate_api_cost(estimated_credits)
        
        # Cost breakdown by engine
        cost_breakdown = {}
        for engine, count in engines_by_query.items():
            engine_credits = count * 100
            engine_cost = self.calculate_api_cost(engine_credits)
            cost_breakdown[engine] = {
                'queries': count,
                'credits': engine_credits,
                'cost': float(engine_cost)
            }
        
        return {
            'total_queries': total_queries,
            'total_engines': len(engines_by_query),
            'estimated_api_calls': total_api_calls,
            'estimated_credits': estimated_credits,
            'estimated_cost': estimated_cost,
            'cost_breakdown': cost_breakdown,
            'query_details': query_details
        }
    
    def _get_average_cost_per_query(self) -> Decimal:
        """Get historical average cost per query."""
        from ..models import SearchExecution
        
        # Get last 30 days of executions for better estimate
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_executions = SearchExecution.objects.filter(
            completed_at__gte=thirty_days_ago,
            status='completed'
        )
        
        if not recent_executions.exists():
            return Decimal('0.10')  # Default estimate
        
        total_credits = recent_executions.aggregate(
            total=Sum('api_credits_used')
        )['total'] or 0
        
        avg_credits_per_execution = total_credits / recent_executions.count()
        return self.calculate_api_cost(int(avg_credits_per_execution))