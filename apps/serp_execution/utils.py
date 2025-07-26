"""
Utility functions for the serp_execution app.

This module contains validation and helper functions.
Business logic has been moved to dedicated services.
"""

from typing import List, Tuple
from .models import SearchExecution

# Service imports for backward compatibility
from .services.cost_service import CostService
from .services.execution_service import ExecutionService
from .services.content_analysis_service import ContentAnalysisService
from .services.monitoring_service import MonitoringService

# Initialize services for backward compatibility
cost_service = CostService()
execution_service = ExecutionService()
content_analysis_service = ContentAnalysisService()
monitoring_service = MonitoringService()

# Legacy function proxies for backward compatibility
calculate_api_cost = cost_service.calculate_api_cost
estimate_execution_time = execution_service.estimate_execution_time
detect_content_type = content_analysis_service.detect_content_type
extract_publication_date = content_analysis_service.extract_publication_date
get_execution_statistics = monitoring_service.get_execution_statistics
get_failed_executions_with_analysis = monitoring_service.get_failed_executions_with_analysis
categorize_failure = monitoring_service.categorize_failure
suggest_retry_action = monitoring_service.suggest_retry_action
calculate_search_coverage = monitoring_service.calculate_search_coverage
optimize_retry_strategy = monitoring_service.optimize_retry_strategy
get_engine_performance_comparison = monitoring_service.get_engine_performance_comparison
format_execution_status = monitoring_service.format_execution_status
get_execution_timeline = monitoring_service.get_execution_timeline
calculate_session_cost_estimate = cost_service.calculate_session_cost_estimate


def validate_search_execution(execution: SearchExecution) -> Tuple[bool, List[str]]:
    """
    Validate search execution parameters and state.
    
    Args:
        execution: SearchExecution instance
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    # Check if execution can be started
    if execution.status not in ['pending', 'failed']:
        errors.append(f"Cannot start execution with status '{execution.status}'")
    
    # Check query validity
    if not execution.query.is_active:
        errors.append("Cannot execute inactive query")
    
    # Check API parameters
    if not execution.api_parameters:
        errors.append("API parameters are required")
    
    # Check search engine
    valid_engines = ['google', 'bing', 'duckduckgo', 'yahoo']
    if execution.search_engine not in valid_engines:
        errors.append(f"Invalid search engine: {execution.search_engine}")
    
    # Check retry limits
    if execution.retry_count >= 3:
        errors.append("Maximum retry attempts reached")
    
    return len(errors) == 0, errors