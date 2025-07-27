"""
Utility functions for the serp_execution app.

This module contains validation and helper functions.
Business logic has been moved to dedicated services.
"""

from typing import List, Tuple

from .models import SearchExecution
# Removed complex services - using simplified approach
from .services.execution_service import ExecutionService

# Initialize simplified services
execution_service = ExecutionService()

# Simplified utility functions

def get_execution_statistics(session_id: str):
    """Get execution statistics."""
    return execution_service.get_execution_statistics(session_id)



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
    if execution.status not in ["pending", "failed"]:
        errors.append(f"Cannot start execution with status '{execution.status}'")

    # Check query validity
    if not execution.query.is_active:
        errors.append("Cannot execute inactive query")

    # Check API parameters
    if not execution.api_parameters:
        errors.append("API parameters are required")

    # Check search engine
    valid_engines = ["google", "bing", "duckduckgo", "yahoo"]
    if execution.search_engine not in valid_engines:
        errors.append(f"Invalid search engine: {execution.search_engine}")

    # Check retry limits
    if execution.retry_count >= 3:
        errors.append("Maximum retry attempts reached")

    return len(errors) == 0, errors
