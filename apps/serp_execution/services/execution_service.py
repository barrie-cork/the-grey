"""
Simple execution service for serp_execution slice.
Business capability: Basic execution coordination.
"""

from typing import Any, Dict


class ExecutionService:
    """Simple service for managing search execution."""

    def get_execution_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get basic execution statistics for a session."""
        from ..models import SearchExecution

        executions = SearchExecution.objects.filter(
            query__strategy__session_id=session_id
        )

        if not executions.exists():
            return self._empty_stats()

        total_executions = executions.count()
        successful_executions = executions.filter(status="completed").count()
        failed_executions = executions.filter(status="failed").count()
        
        success_rate = (
            (successful_executions / total_executions * 100) 
            if total_executions > 0 else 0
        )

        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "failed_executions": failed_executions,
            "success_rate": round(success_rate, 1),
        }

    def _empty_stats(self) -> Dict[str, Any]:
        """Return empty statistics structure."""
        return {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "success_rate": 0,
        }