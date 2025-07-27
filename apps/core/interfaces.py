"""
Core interfaces for dependency injection and vertical slice abstraction.
Defines protocols for cross-slice communication without direct imports.
"""

from typing import Any, Dict, List, Protocol


class SessionProvider(Protocol):
    """Protocol for accessing session data across slices."""

    def get_session(self, session_id: str) -> Any:
        """Get session by ID."""
        ...

    def get_session_data(self, session_id: str) -> Dict[str, Any]:
        """Get session data for display."""
        ...

    def verify_session_ownership(self, session_id: str, user) -> bool:
        """Verify user owns the session."""
        ...


class QueryProvider(Protocol):
    """Protocol for accessing search query data across slices."""

    def get_session_queries(self, session_id: str) -> List[Dict[str, Any]]:
        """Get queries for a session."""
        ...

    def get_session_queries_data(self, session_id: str) -> Dict[str, Any]:
        """Get query data for display."""
        ...


class DependencyContainer:
    """Simple dependency injection container for cross-slice dependencies."""

    def __init__(self):
        self._providers: Dict[str, Any] = {}

    def register(self, key: str, provider: Any) -> None:
        """Register a provider."""
        self._providers[key] = provider

    def get(self, key: str) -> Any:
        """Get a provider."""
        if key not in self._providers:
            raise ValueError(f"Provider '{key}' not registered")
        return self._providers[key]

    def get_session_provider(self) -> SessionProvider:
        """Get the session provider."""
        return self.get("session_provider")

    def get_query_provider(self) -> QueryProvider:
        """Get the query provider."""
        return self.get("query_provider")


# Global container instance
container = DependencyContainer()
