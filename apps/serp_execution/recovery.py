"""
Simplified error recovery for SERP execution.
Basic retry logic with fixed delays for MVP.
"""

import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SimpleRecoveryManager:
    """
    Simple recovery manager for MVP.
    Uses fixed delays based on error type.
    """
    
    # Fixed delays for different error types
    RATE_LIMIT_DELAY = 60  # 1 minute for rate limits
    NETWORK_ERROR_DELAY = 10  # 10 seconds for network errors
    DEFAULT_DELAY = 5  # 5 seconds for other errors
    MAX_RETRIES = 3  # Maximum retry attempts
    
    def should_retry(self, error: Exception, retry_count: int) -> bool:
        """
        Determine if retry should be attempted.
        
        Args:
            error: The exception that occurred
            retry_count: Number of retries already attempted
            
        Returns:
            True if should retry, False otherwise
        """
        # Don't retry if max attempts reached
        if retry_count >= self.MAX_RETRIES:
            return False
            
        # Don't retry authentication errors
        error_message = str(error).lower()
        if "auth" in error_message or "api key" in error_message:
            return False
            
        # Don't retry quota errors
        if "quota" in error_message:
            return False
            
        # Retry everything else
        return True
    
    def get_retry_delay(self, error: Exception) -> int:
        """
        Get delay in seconds before retry.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Delay in seconds
        """
        error_message = str(error).lower()
        
        # Check for rate limit errors
        if "rate limit" in error_message or "429" in error_message:
            return self.RATE_LIMIT_DELAY
            
        # Check for network errors
        if any(term in error_message for term in ["timeout", "connection", "network"]):
            return self.NETWORK_ERROR_DELAY
            
        # Default delay for other errors
        return self.DEFAULT_DELAY
    
    def get_error_category(self, error_message: str) -> str:
        """
        Categorize error for display purposes.
        
        Args:
            error_message: The error message
            
        Returns:
            Error category string
        """
        error_lower = error_message.lower()
        
        if "rate limit" in error_lower or "429" in error_lower:
            return "rate_limit"
        elif any(term in error_lower for term in ["timeout", "connection", "network"]):
            return "network"
        elif "auth" in error_lower or "api key" in error_lower:
            return "authentication"
        elif "quota" in error_lower:
            return "quota"
        else:
            return "general"


# Global instance
recovery_manager = SimpleRecoveryManager()