"""
Dependency injection for serp_execution slice.
Provides abstracted access to other slices without direct imports.
"""

from typing import Any, Dict


class SerpExecutionDependencies:
    """Dependency injection service for SERP execution views and services."""

    def __init__(self, session_provider, query_provider):
        self.session_provider = session_provider
        self.query_provider = query_provider

    def get_session(self, session_id: str) -> Any:
        """Get session through abstracted provider."""
        return self.session_provider.get_session(session_id)

    def get_session_data(self, session_id: str) -> Dict[str, Any]:
        """Get session data through abstracted provider."""
        return self.session_provider.get_session_data(session_id)

    def verify_session_ownership(self, session_id: str, user) -> bool:
        """Verify session ownership through abstracted provider."""
        return self.session_provider.verify_session_ownership(session_id, user)

    def get_session_queries_data(self, session_id: str) -> Dict[str, Any]:
        """Get query data through abstracted provider."""
        return self.query_provider.get_session_queries_data(session_id)
