"""
Tests for the RateLimiter service.
"""

import time
from unittest.mock import patch
from django.test import TestCase

from apps.serp_execution.services.rate_limiter import RateLimiter


class RateLimiterTests(TestCase):
    """Tests for RateLimiter class."""
    
    def setUp(self):
        # Use a high rate limit for testing
        self.rate_limiter = RateLimiter(rate_limit_per_minute=6000)  # 100 per second
    
    def test_check_rate_limit_allows_first_request(self):
        """Test that first request is always allowed."""
        self.assertTrue(self.rate_limiter.check_rate_limit())
    
    def test_record_request_increments_counter(self):
        """Test that recording a request increments the counter."""
        initial_count = self.rate_limiter.request_count
        self.rate_limiter.record_request()
        self.assertEqual(self.rate_limiter.request_count, initial_count + 1)
    
    def test_get_remaining_requests(self):
        """Test getting remaining requests in window."""
        remaining = self.rate_limiter.get_remaining_requests()
        self.assertEqual(remaining, 100)  # 6000/60 = 100 per second
        
        # Make some requests
        self.rate_limiter.record_request()
        self.rate_limiter.record_request()
        
        remaining = self.rate_limiter.get_remaining_requests()
        self.assertEqual(remaining, 98)
    
    def test_get_wait_time_when_not_limited(self):
        """Test wait time when under rate limit."""
        wait_time = self.rate_limiter.get_wait_time()
        self.assertEqual(wait_time, 0.0)
    
    @patch('time.sleep')
    def test_wait_if_needed_sleeps_when_limited(self, mock_sleep):
        """Test that wait_if_needed sleeps when rate limited."""
        # Use a very low rate limit for this test
        rate_limiter = RateLimiter(rate_limit_per_minute=60)  # 1 per second
        
        # Make two requests quickly to exceed limit
        rate_limiter.wait_if_needed()  # First request
        rate_limiter.wait_if_needed()  # Should trigger sleep
        
        # Verify sleep was called
        mock_sleep.assert_called()
    
    def test_rate_limiter_with_config_override(self):
        """Test rate limiter with custom rate limit."""
        custom_rate_limiter = RateLimiter(rate_limit_per_minute=120)
        self.assertEqual(custom_rate_limiter.rate_limit_per_minute, 120)
        self.assertEqual(custom_rate_limiter.rate_limit_per_second, 2.0)
    
    def test_window_reset(self):
        """Test that request counter resets after window."""
        # Make a request
        self.rate_limiter.record_request()
        self.assertEqual(self.rate_limiter.request_count, 1)
        
        # Simulate time passing (more than window size)
        with patch('time.time', return_value=time.time() + 2):
            # Check rate limit should reset counter
            self.assertTrue(self.rate_limiter.check_rate_limit())
            # Counter should be reset after the check
            self.assertEqual(self.rate_limiter.request_count, 0)
    
    def test_initialization_from_config(self):
        """Test rate limiter initialization using config."""
        # Create without override - should use config
        rate_limiter = RateLimiter()
        # Should have a reasonable default from config
        self.assertGreater(rate_limiter.rate_limit_per_minute, 0)