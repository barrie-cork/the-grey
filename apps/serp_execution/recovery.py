"""
Error recovery manager for SERP execution.
Implements error classification and recovery strategies.
"""

import logging
import time
from typing import Dict, Any, Optional, List, Tuple, Type
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.cache import cache
from decimal import Decimal

from .services.serper_client import (
    SerperAPIError, SerperRateLimitError, 
    SerperAuthError, SerperQuotaError
)

logger = logging.getLogger(__name__)


class RecoveryStrategy:
    """Base class for recovery strategies."""
    
    def __init__(self, error: Exception, context: Dict[str, Any]):
        self.error = error
        self.context = context
        self.attempt_number = context.get('retry_count', 0) + 1
    
    def should_retry(self) -> bool:
        """Determine if retry should be attempted."""
        raise NotImplementedError
    
    def get_delay(self) -> float:
        """Get delay in seconds before retry."""
        raise NotImplementedError
    
    def modify_request(self) -> Dict[str, Any]:
        """Modify request parameters for retry."""
        return self.context.get('request_params', {})
    
    def get_notification_message(self) -> Optional[str]:
        """Get message for user notification if needed."""
        return None


class ExponentialBackoffStrategy(RecoveryStrategy):
    """Exponential backoff for transient errors."""
    
    BASE_DELAY = 1.0  # Start with 1 second
    MAX_DELAY = 300.0  # Max 5 minutes
    MAX_ATTEMPTS = 5
    
    def should_retry(self) -> bool:
        return self.attempt_number <= self.MAX_ATTEMPTS
    
    def get_delay(self) -> float:
        # Exponential backoff with jitter
        delay = min(
            self.BASE_DELAY * (2 ** (self.attempt_number - 1)),
            self.MAX_DELAY
        )
        # Add jitter (±20%)
        import random
        jitter = delay * 0.2 * (random.random() - 0.5)
        return delay + jitter


class RateLimitStrategy(RecoveryStrategy):
    """Handle rate limit errors with appropriate delays."""
    
    def should_retry(self) -> bool:
        # Always retry rate limits unless we've hit too many
        return self.attempt_number <= 3
    
    def get_delay(self) -> float:
        # Check if we have a Retry-After header
        if hasattr(self.error, 'response') and self.error.response:
            retry_after = self.error.response.headers.get('Retry-After')
            if retry_after:
                try:
                    return float(retry_after)
                except ValueError:
                    pass
        
        # Default to progressively longer delays
        delays = [60, 180, 300]  # 1min, 3min, 5min
        return delays[min(self.attempt_number - 1, len(delays) - 1)]
    
    def get_notification_message(self) -> Optional[str]:
        if self.attempt_number >= 2:
            return "Search is being rate limited. Execution will continue automatically when possible."
        return None


class QuerySimplificationStrategy(RecoveryStrategy):
    """Simplify complex queries that may be causing issues."""
    
    def should_retry(self) -> bool:
        # Only try simplification up to 3 times
        return self.attempt_number <= 3
    
    def get_delay(self) -> float:
        return 2.0  # Small delay between simplification attempts
    
    def modify_request(self) -> Dict[str, Any]:
        params = self.context.get('request_params', {}).copy()
        query = params.get('q', '')
        
        # Progressive simplification
        if self.attempt_number == 1:
            # Remove advanced operators
            query = query.replace(' AND ', ' ')
            query = query.replace(' OR ', ' ')
            query = query.replace(' NOT ', ' -')
            
        elif self.attempt_number == 2:
            # Remove parentheses and quotes
            query = query.replace('(', '').replace(')', '')
            query = query.replace('"', '')
            
        elif self.attempt_number == 3:
            # Keep only main terms (remove operators, file types, etc.)
            import re
            query = re.sub(r'[-+]?\w+:', '', query)  # Remove operators like -word or filetype:
            query = ' '.join(query.split()[:10])  # Limit to 10 words
        
        params['q'] = query.strip()
        return params
    
    def get_notification_message(self) -> Optional[str]:
        return f"Query simplified for attempt {self.attempt_number}"


class QuotaExhaustedStrategy(RecoveryStrategy):
    """Handle quota exhaustion - requires manual intervention."""
    
    def should_retry(self) -> bool:
        # Don't retry quota errors automatically
        return False
    
    def get_delay(self) -> float:
        return 0
    
    def get_notification_message(self) -> Optional[str]:
        return "API quota exhausted. Please check your Serper account or contact support."


class AuthenticationStrategy(RecoveryStrategy):
    """Handle authentication errors."""
    
    def should_retry(self) -> bool:
        # Don't retry auth errors - they need manual fix
        return False
    
    def get_delay(self) -> float:
        return 0
    
    def get_notification_message(self) -> Optional[str]:
        return "API authentication failed. Please check your API key configuration."


class NetworkErrorStrategy(ExponentialBackoffStrategy):
    """Handle network-related errors."""
    
    BASE_DELAY = 2.0  # Start with 2 seconds for network issues
    
    def get_notification_message(self) -> Optional[str]:
        if self.attempt_number >= 3:
            return "Experiencing network connectivity issues. Will continue retrying."
        return None


class ErrorRecoveryManager:
    """
    Manages error recovery for SERP execution.
    Classifies errors and applies appropriate recovery strategies.
    """
    
    # Error classification mapping
    ERROR_STRATEGIES = {
        SerperRateLimitError: RateLimitStrategy,
        SerperQuotaError: QuotaExhaustedStrategy,
        SerperAuthError: AuthenticationStrategy,
        ConnectionError: NetworkErrorStrategy,
        TimeoutError: NetworkErrorStrategy,
        # Default fallback
        SerperAPIError: ExponentialBackoffStrategy,
        Exception: QuerySimplificationStrategy
    }
    
    def __init__(self):
        self.recovery_history = {}
        self.notification_callbacks = []
    
    def classify_error(self, error: Exception) -> Type[RecoveryStrategy]:
        """
        Classify an error and return appropriate strategy class.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Recovery strategy class to use
        """
        # Check exact type matches first
        for error_type, strategy in self.ERROR_STRATEGIES.items():
            if type(error) == error_type:
                return strategy
        
        # Then check inheritance
        for error_type, strategy in self.ERROR_STRATEGIES.items():
            if isinstance(error, error_type):
                return strategy
        
        # Default fallback
        return ExponentialBackoffStrategy
    
    def get_recovery_strategy(
        self,
        error: Exception,
        execution_id: str,
        request_params: Dict[str, Any],
        retry_count: int = 0
    ) -> RecoveryStrategy:
        """
        Get recovery strategy for an error.
        
        Args:
            error: The exception that occurred
            execution_id: ID of the SearchExecution
            request_params: Original request parameters
            retry_count: Number of retries already attempted
            
        Returns:
            RecoveryStrategy instance
        """
        strategy_class = self.classify_error(error)
        
        context = {
            'execution_id': execution_id,
            'request_params': request_params,
            'retry_count': retry_count,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': timezone.now()
        }
        
        strategy = strategy_class(error, context)
        
        # Log the error and strategy
        logger.info(
            f"Error recovery for execution {execution_id}: "
            f"{type(error).__name__} -> {strategy_class.__name__}"
        )
        
        # Track in history
        self._track_recovery_attempt(execution_id, error, strategy)
        
        return strategy
    
    def _track_recovery_attempt(
        self,
        execution_id: str,
        error: Exception,
        strategy: RecoveryStrategy
    ):
        """Track recovery attempt in history."""
        if execution_id not in self.recovery_history:
            self.recovery_history[execution_id] = []
        
        self.recovery_history[execution_id].append({
            'timestamp': timezone.now(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'strategy': type(strategy).__name__,
            'attempt_number': strategy.attempt_number,
            'will_retry': strategy.should_retry()
        })
        
        # Keep only last 10 attempts per execution
        self.recovery_history[execution_id] = self.recovery_history[execution_id][-10:]
        
        # Also cache for persistence
        cache_key = f"recovery_history_{execution_id}"
        cache.set(cache_key, self.recovery_history[execution_id], 86400)  # 24 hours
    
    def should_abandon_execution(self, execution_id: str) -> bool:
        """
        Determine if execution should be abandoned based on recovery history.
        
        Args:
            execution_id: ID of the SearchExecution
            
        Returns:
            True if execution should be abandoned
        """
        history = self.recovery_history.get(execution_id, [])
        
        if not history:
            return False
        
        # Abandon if too many total attempts
        if len(history) > 15:
            return True
        
        # Abandon if same error keeps occurring
        recent_errors = [h['error_type'] for h in history[-5:]]
        if len(set(recent_errors)) == 1 and len(recent_errors) == 5:
            return True
        
        # Abandon if authentication or quota errors
        abandon_errors = ['SerperAuthError', 'SerperQuotaError']
        if any(h['error_type'] in abandon_errors for h in history):
            return True
        
        return False
    
    def get_manual_intervention_required(self, execution_id: str) -> List[Dict[str, Any]]:
        """
        Get list of issues requiring manual intervention.
        
        Args:
            execution_id: ID of the SearchExecution
            
        Returns:
            List of intervention requirements
        """
        from .models import SearchExecution
        
        interventions = []
        
        try:
            execution = SearchExecution.objects.get(id=execution_id)
        except SearchExecution.DoesNotExist:
            return interventions
        
        history = self.recovery_history.get(execution_id, [])
        
        # Check for auth errors
        if any(h['error_type'] == 'SerperAuthError' for h in history):
            interventions.append({
                'type': 'authentication',
                'severity': 'critical',
                'message': 'API authentication failed. Please verify your Serper API key.',
                'action_required': 'Update API key in settings',
                'documentation_link': '/docs/api-configuration'
            })
        
        # Check for quota errors
        if any(h['error_type'] == 'SerperQuotaError' for h in history):
            interventions.append({
                'type': 'quota',
                'severity': 'critical',
                'message': 'API quota exhausted. Additional credits needed.',
                'action_required': 'Purchase additional Serper credits or wait for quota reset',
                'documentation_link': 'https://serper.dev/pricing'
            })
        
        # Check for persistent network errors
        network_errors = [h for h in history if h['error_type'] in ['ConnectionError', 'TimeoutError']]
        if len(network_errors) >= 5:
            interventions.append({
                'type': 'network',
                'severity': 'warning',
                'message': 'Persistent network connectivity issues detected.',
                'action_required': 'Check network connection and firewall settings',
                'retry_possible': True
            })
        
        # Check for complex query issues
        if execution.retry_count >= 3 and not interventions:
            interventions.append({
                'type': 'query_complexity',
                'severity': 'info',
                'message': 'Query may be too complex for reliable execution.',
                'action_required': 'Consider simplifying search terms or splitting into multiple queries',
                'suggestions': self._get_query_simplification_suggestions(execution)
            })
        
        return interventions
    
    def _get_query_simplification_suggestions(
        self,
        execution: 'SearchExecution'
    ) -> List[str]:
        """Get suggestions for simplifying a query."""
        suggestions = []
        query = execution.api_parameters.get('q', '')
        
        if len(query) > 200:
            suggestions.append("Reduce query length by removing less important terms")
        
        if ' AND ' in query or ' OR ' in query:
            suggestions.append("Remove complex Boolean operators")
        
        if query.count('"') > 4:
            suggestions.append("Reduce number of exact phrase searches")
        
        if 'filetype:' in query:
            suggestions.append("Remove file type filters and filter results afterward")
        
        return suggestions
    
    def record_successful_recovery(self, execution_id: str):
        """
        Record that recovery was successful.
        
        Args:
            execution_id: ID of the SearchExecution
        """
        if execution_id in self.recovery_history:
            logger.info(f"Successful recovery for execution {execution_id} after {len(self.recovery_history[execution_id])} attempts")
            
            # Clear history for successful execution
            del self.recovery_history[execution_id]
            cache.delete(f"recovery_history_{execution_id}")
    
    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get statistics about recovery attempts."""
        total_recoveries = sum(len(h) for h in self.recovery_history.values())
        
        error_counts = {}
        strategy_counts = {}
        
        for history in self.recovery_history.values():
            for attempt in history:
                error_type = attempt['error_type']
                strategy = attempt['strategy']
                
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
                strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
        
        return {
            'total_recovery_attempts': total_recoveries,
            'active_executions_with_errors': len(self.recovery_history),
            'error_type_distribution': error_counts,
            'strategy_usage': strategy_counts,
            'timestamp': timezone.now()
        }


# Global instance
recovery_manager = ErrorRecoveryManager()