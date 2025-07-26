"""
Provider implementations for review_manager slice.
Implements protocols for dependency injection.
"""

from typing import Dict, Any
from django.shortcuts import get_object_or_404
from .models import SearchSession
from .signals import get_session_data


class SessionProviderImpl:
    """Implementation of SessionProvider protocol."""
    
    def get_session(self, session_id: str) -> SearchSession:
        """Get session by ID."""
        return get_object_or_404(SearchSession, id=session_id)
    
    def get_session_data(self, session_id: str) -> Dict[str, Any]:
        """Get session data for display."""
        return get_session_data(session_id)
    
    def verify_session_ownership(self, session_id: str, user) -> bool:
        """Verify user owns the session."""
        session = self.get_session(session_id)
        return session.owner == user