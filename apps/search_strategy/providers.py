"""
Provider implementations for search_strategy slice.
Implements protocols for dependency injection.
"""

from typing import Dict, Any, List
from .signals import get_session_queries_data


class QueryProviderImpl:
    """Implementation of QueryProvider protocol."""
    
    def get_session_queries(self, session_id: str) -> List[Dict[str, Any]]:
        """Get queries for a session."""
        # This would typically query SearchQuery model
        # For now, delegate to existing signal
        data = self.get_session_queries_data(session_id)
        return data.get('queries', [])
    
    def get_session_queries_data(self, session_id: str) -> Dict[str, Any]:
        """Get query data for display."""
        return get_session_queries_data(session_id)