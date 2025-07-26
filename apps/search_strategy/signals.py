"""
Signal handlers for search strategy app.
Handles workflow transitions when search strategies are completed.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.search_strategy.models import SearchQuery
from apps.review_manager.signals import session_status_changed
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


def get_session_queries_data(session_id: str) -> List[Dict[str, Any]]:
    """
    Internal API for accessing search query data without exposing models.
    """
    queries = SearchQuery.objects.filter(session_id=session_id, is_active=True)
    return [
        {
            'id': str(query.id),
            'title': query.title,
            'query_string': query.query_string,
            'population': query.population,
            'interest': query.interest,
            'context': query.context,
            'search_engines': query.search_engines,
            'created_at': query.created_at.isoformat(),
        }
        for query in queries
    ]


def get_query_count(session_id: str) -> int:
    """Get count of active queries for a session."""
    return SearchQuery.objects.filter(session_id=session_id, is_active=True).count()


@receiver(post_save, sender=SearchQuery)
def check_strategy_completion(sender, instance, created, **kwargs):
    """
    Check if all queries for a session are defined and transition to ready_to_execute.
    
    This signal fires after a SearchQuery is saved and checks if the search
    strategy is complete (has at least one active query with proper PIC fields).
    """
    if not instance.session:
        return
    
    session = instance.session
    
    # Only process if session is in the right state
    if session.status not in ['draft', 'defining_search']:
        return
    
    # Check if we have at least one active query with PIC fields
    active_queries = session.search_queries.filter(is_active=True)
    
    if not active_queries.exists():
        return
    
    # Force refresh the query count from database
    query_count = active_queries.count()
    
    # Check if all active queries have required fields
    for query in active_queries:
        if not (query.population or query.interest or query.context):
            logger.debug(f"Query {query.id} missing PIC fields")
            return
        if not query.query_string:
            logger.debug(f"Query {query.id} missing query string")
            return
    
    # Emit signal to request status transition instead of direct import
    session_status_changed.send(
        sender=SearchQuery,
        session_id=str(session.id),
        requested_status='ready_to_execute',
        reason=f"Search strategy completed with {active_queries.count()} queries"
    )
    
    logger.info(f"Session {session.id} requested transition to ready_to_execute")


def mark_strategy_complete(session):
    """
    Manually mark a search strategy as complete and ready for execution.
    
    This can be called from views or management commands to trigger
    the workflow transition.
    
    Args:
        session: SearchSession instance
        
    Returns:
        Tuple of (success, error_message)
    """
    # Validate session has queries
    active_queries = session.search_queries.filter(is_active=True)
    
    if not active_queries.exists():
        return False, "No active search queries defined"
    
    # Validate all queries have required fields
    for query in active_queries:
        if not (query.population or query.interest or query.context):
            return False, f"Query '{query}' missing required PIC fields"
        if not query.query_string:
            return False, f"Query '{query}' missing query string"
    
    # Emit signal to request status transition
    session_status_changed.send(
        sender=session.__class__,
        session_id=str(session.id),
        requested_status='ready_to_execute',
        reason=f"Search strategy marked complete with {active_queries.count()} queries"
    )
    
    return True, None