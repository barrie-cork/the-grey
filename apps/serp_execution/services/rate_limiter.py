"""
Rate limiting service for API requests.
Implements configurable rate limiting with sliding window algorithm.
"""

import logging
import time
from typing import Optional

from apps.core.config import get_config

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter using sliding window algorithm.
    Configurable through central configuration system.
    """
    
    def __init__(self, rate_limit_per_minute: Optional[int] = None):
        """
        Initialize rate limiter.
        
        Args:
            rate_limit_per_minute: Override for rate limit (uses config if None)
        """
        config = get_config()
        self.rate_limit_per_minute = rate_limit_per_minute or config.api.rate_limit_per_minute
        self.rate_limit_per_second = self.rate_limit_per_minute / 60.0
        
        # Tracking variables
        self.last_request_time = 0
        self.request_count = 0
        self.window_size = 1.0  # 1 second sliding window
        
    def check_rate_limit(self) -> bool:
        """
        Check if request can be made within rate limit.
        
        Returns:
            bool: True if request can proceed, False if rate limited
        """
        current_time = time.time()
        
        # Reset counter if window has passed
        if current_time - self.last_request_time >= self.window_size:
            self.request_count = 0
            self.last_request_time = current_time
            
        # Check if within limit
        return self.request_count < self.rate_limit_per_second
    
    def wait_if_needed(self) -> None:
        """
        Wait if rate limit has been reached.
        Blocks until request can proceed.
        """
        current_time = time.time()
        
        # Reset counter if window has passed
        if current_time - self.last_request_time >= self.window_size:
            self.request_count = 0
            self.last_request_time = current_time
        
        # Check if we need to wait
        if self.request_count >= self.rate_limit_per_second:
            sleep_time = self.window_size - (current_time - self.last_request_time)
            if sleep_time > 0:
                logger.info(f"Rate limit reached, sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
                self.request_count = 0
                self.last_request_time = time.time()
        
        self.request_count += 1
    
    def record_request(self) -> None:
        """Record that a request was made."""
        self.request_count += 1
    
    def get_remaining_requests(self) -> int:
        """
        Get number of requests remaining in current window.
        
        Returns:
            int: Number of requests that can be made
        """
        current_time = time.time()
        
        # Reset if window has passed
        if current_time - self.last_request_time >= self.window_size:
            return int(self.rate_limit_per_second)
            
        return max(0, int(self.rate_limit_per_second - self.request_count))
    
    def get_wait_time(self) -> float:
        """
        Get time to wait before next request can be made.
        
        Returns:
            float: Seconds to wait (0 if no wait needed)
        """
        if self.request_count < self.rate_limit_per_second:
            return 0.0
            
        current_time = time.time()
        sleep_time = self.window_size - (current_time - self.last_request_time)
        return max(0.0, sleep_time)