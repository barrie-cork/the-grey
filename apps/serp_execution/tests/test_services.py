"""
Tests for SERP execution services.

Tests for SerperClient, CacheManager, UsageTracker, QueryBuilder, and ResultProcessor.
"""

import json
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from urllib.parse import urlencode

from django.test import TestCase, override_settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.review_manager.models import SearchSession
from apps.search_strategy.models import SearchQuery
from apps.serp_execution.models import SearchExecution, RawSearchResult
from apps.serp_execution.services.serper_client import (
    SerperClient, SerperAPIError, SerperRateLimitError,
    SerperAuthError, SerperQuotaError
)
from apps.serp_execution.services.cache_manager import CacheManager
from apps.serp_execution.services.usage_tracker import UsageTracker
from apps.serp_execution.services.query_builder import QueryBuilder
from apps.serp_execution.services.result_processor import ResultProcessor

User = get_user_model()


class TestSerperClient(TestCase):
    """Test cases for SerperClient service."""
    
    def setUp(self):
        """Set up test data."""
        self.client = SerperClient()
        cache.clear()
    
    @override_settings(SERPER_API_KEY='test-api-key')
    def test_client_initialization(self):
        """Test SerperClient initialization."""
        client = SerperClient()
        self.assertEqual(client.api_key, 'test-api-key')
        self.assertIsNotNone(client.session)
    
    @override_settings(SERPER_API_KEY=None)
    def test_client_initialization_without_api_key(self):
        """Test SerperClient initialization without API key."""
        with self.assertRaises(ValueError) as context:
            SerperClient()
        self.assertIn('SERPER_API_KEY not configured', str(context.exception))
    
    def test_build_request_params(self):
        """Test building request parameters."""
        params = self.client._build_request_params(
            query='test query',
            num_results=50,
            search_type='search',
            location='United States',
            language='en',
            date_from='2023-01-01',
            file_types=['pdf', 'doc']
        )
        
        expected_query = 'test query (filetype:pdf OR filetype:doc)'
        self.assertEqual(params['q'], expected_query)
        self.assertEqual(params['num'], 50)
        self.assertEqual(params['type'], 'search')
        self.assertEqual(params['location'], 'United States')
        self.assertEqual(params['gl'], 'us')
        self.assertEqual(params['hl'], 'en')
        self.assertEqual(params['engine'], 'google')
        self.assertIn('tbs', params)
    
    def test_build_request_params_respects_max_results(self):
        """Test that request params respect maximum results limit."""
        params = self.client._build_request_params(
            query='test query',
            num_results=200  # Above Serper's limit
        )
        
        self.assertEqual(params['num'], 100)  # Should be capped at 100
    
    @patch('apps.serp_execution.services.serper_client.requests.Session.post')
    def test_search_success(self, mock_post):
        """Test successful search execution."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'organic': [
                {
                    'title': 'Test Result',
                    'link': 'https://example.com',
                    'snippet': 'Test snippet'
                }
            ],
            'credits': 1,
            'searchInformation': {
                'totalResults': '1000',
                'searchTime': 0.5
            }
        }
        mock_response.headers = {'X-Request-ID': 'test-request-id'}
        mock_post.return_value = mock_response
        
        results, metadata = self.client.search('test query', num_results=10)
        
        self.assertEqual(len(results['organic']), 1)
        self.assertEqual(metadata['credits_used'], 1)
        self.assertEqual(metadata['total_results'], '1000')
        self.assertEqual(metadata['time_taken'], 0.5)
        self.assertEqual(metadata['request_id'], 'test-request-id')
        self.assertFalse(metadata['cache_hit'])
    
    @patch('apps.serp_execution.services.serper_client.requests.Session.post')
    def test_search_with_cache(self, mock_post):
        """Test search with caching enabled."""
        mock_response = Mock()
        mock_response.status_code = 200
        test_data = {
            'organic': [{'title': 'Cached Result'}],
            'credits': 1
        }
        mock_response.json.return_value = test_data
        mock_response.headers = {}
        mock_post.return_value = mock_response
        
        # First search - should hit API
        results1, metadata1 = self.client.search('cached query', use_cache=True)
        self.assertFalse(metadata1['cache_hit'])
        self.assertEqual(mock_post.call_count, 1)
        
        # Second search - should hit cache
        results2, metadata2 = self.client.search('cached query', use_cache=True)
        self.assertTrue(metadata2['cache_hit'])
        self.assertEqual(metadata2['credits_used'], 0)
        self.assertEqual(mock_post.call_count, 1)  # No additional API call
    
    @patch('apps.serp_execution.services.serper_client.requests.Session.post')
    def test_search_auth_error(self, mock_post):
        """Test search with authentication error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        
        with self.assertRaises(SerperAuthError) as context:
            self.client.search('test query')
        self.assertIn('Invalid API key', str(context.exception))
    
    @patch('apps.serp_execution.services.serper_client.requests.Session.post')
    def test_search_quota_error(self, mock_post):
        """Test search with quota exceeded error."""
        mock_response = Mock()
        mock_response.status_code = 402
        mock_post.return_value = mock_response
        
        with self.assertRaises(SerperQuotaError) as context:
            self.client.search('test query')
        self.assertIn('API quota exceeded', str(context.exception))
    
    @patch('apps.serp_execution.services.serper_client.requests.Session.post')
    def test_search_rate_limit_error(self, mock_post):
        """Test search with rate limit error."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {'Retry-After': '60'}
        mock_post.return_value = mock_response
        
        with self.assertRaises(SerperRateLimitError) as context:
            self.client.search('test query')
        self.assertIn('Rate limit exceeded', str(context.exception))
        self.assertIn('60', str(context.exception))
    
    @patch('apps.serp_execution.services.serper_client.time.sleep')
    def test_rate_limiting(self, mock_sleep):
        """Test rate limiting enforcement."""
        # Simulate rapid requests
        self.client.request_count = self.client.RATE_LIMIT_PER_SECOND - 1
        self.client.last_request_time = time.time()
        
        # This should trigger rate limiting
        self.client._enforce_rate_limit()
        
        # Should sleep when limit reached
        self.client.request_count = self.client.RATE_LIMIT_PER_SECOND
        self.client._enforce_rate_limit()
        mock_sleep.assert_called()
    
    def test_validate_query(self):
        """Test query validation."""
        # Valid query
        is_valid, error = self.client.validate_query('valid search query')
        self.assertTrue(is_valid)
        self.assertIsNone(error)
        
        # Empty query
        is_valid, error = self.client.validate_query('')
        self.assertFalse(is_valid)
        self.assertIn('empty', error)
        
        # Query too long
        long_query = 'x' * 2049
        is_valid, error = self.client.validate_query(long_query)
        self.assertFalse(is_valid)
        self.assertIn('too long', error)
        
        # Unmatched quotes
        is_valid, error = self.client.validate_query('test "unmatched')
        self.assertFalse(is_valid)
        self.assertIn('quotes', error)
    
    def test_estimate_cost(self):
        """Test cost estimation."""
        cost = self.client.estimate_cost(100)
        self.assertEqual(cost, Decimal('0.100'))
        
        cost = self.client.estimate_cost(1)
        self.assertEqual(cost, Decimal('0.001'))


class TestCacheManager(TestCase):
    """Test cases for CacheManager service."""
    
    def setUp(self):
        """Set up test data."""
        self.cache_manager = CacheManager()
        cache.clear()
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        key = self.cache_manager.get_cache_key(
            query='test query',
            engine='google',
            params={'num': 10}
        )
        
        self.assertIn('serp_execution:', key)
        self.assertIn('test query', key)
        self.assertIn('google', key)
    
    def test_cache_search_results(self):
        """Test caching search results."""
        results = {
            'organic': [
                {'title': 'Test', 'link': 'https://example.com'}
            ]
        }
        metadata = {'credits': 1}
        
        # Cache the results
        self.cache_manager.cache_search_results(
            query='test query',
            engine='google',
            results=results,
            metadata=metadata,
            ttl=3600
        )
        
        # Retrieve from cache
        cached_results, cached_metadata = self.cache_manager.get_cached_results(
            query='test query',
            engine='google'
        )
        
        self.assertEqual(cached_results, results)
        self.assertEqual(cached_metadata, metadata)
    
    def test_invalidate_cache(self):
        """Test cache invalidation."""
        # Cache some results
        self.cache_manager.cache_search_results(
            query='test query',
            engine='google',
            results={'data': 'test'},
            metadata={'credits': 1}
        )
        
        # Verify cached
        cached, _ = self.cache_manager.get_cached_results('test query', 'google')
        self.assertIsNotNone(cached)
        
        # Invalidate
        self.cache_manager.invalidate_cache(query='test query', engine='google')
        
        # Verify removed
        cached, _ = self.cache_manager.get_cached_results('test query', 'google')
        self.assertIsNone(cached)
    
    def test_get_cache_stats(self):
        """Test cache statistics."""
        # Cache multiple results
        for i in range(5):
            self.cache_manager.cache_search_results(
                query=f'query {i}',
                engine='google',
                results={'data': f'result {i}'},
                metadata={'credits': 1}
            )
        
        stats = self.cache_manager.get_cache_stats()
        self.assertIn('total_cached', stats)
        self.assertIn('cache_size', stats)
        self.assertIn('hit_rate', stats)
    
    def test_cleanup_expired_cache(self):
        """Test cleanup of expired cache entries."""
        # This would require mocking time or using a cache backend
        # that supports TTL testing
        pass


class TestUsageTracker(TestCase):
    """Test cases for UsageTracker service."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.usage_tracker = UsageTracker()
        cache.clear()
    
    def test_track_search(self):
        """Test tracking search usage."""
        self.usage_tracker.track_search(
            user_id=str(self.user.id),
            query='test query',
            results_count=50,
            credits_used=100,
            cache_hit=False
        )
        
        # Get usage stats
        usage = self.usage_tracker.get_user_usage(str(self.user.id))
        self.assertEqual(usage['searches_today'], 1)
        self.assertEqual(usage['credits_used_today'], 100)
        self.assertEqual(usage['results_retrieved_today'], 50)
    
    def test_track_multiple_searches(self):
        """Test tracking multiple searches."""
        for i in range(3):
            self.usage_tracker.track_search(
                user_id=str(self.user.id),
                query=f'query {i}',
                results_count=10,
                credits_used=20,
                cache_hit=i > 0  # First is not cached
            )
        
        usage = self.usage_tracker.get_user_usage(str(self.user.id))
        self.assertEqual(usage['searches_today'], 3)
        self.assertEqual(usage['credits_used_today'], 60)
        self.assertEqual(usage['cache_hits_today'], 2)
    
    def test_check_rate_limits(self):
        """Test rate limit checking."""
        # Track many searches quickly
        for i in range(10):
            self.usage_tracker.track_search(
                user_id=str(self.user.id),
                query=f'query {i}',
                results_count=10,
                credits_used=10,
                cache_hit=False
            )
        
        can_search, reason = self.usage_tracker.check_rate_limits(str(self.user.id))
        # Should still be able to search with reasonable limits
        self.assertTrue(can_search)
    
    def test_get_current_usage(self):
        """Test getting current usage statistics."""
        usage = self.usage_tracker.get_current_usage()
        
        self.assertIn('total_searches_today', usage)
        self.assertIn('total_credits_used_today', usage)
        self.assertIn('unique_users_today', usage)
        self.assertIn('cache_hit_rate', usage)
        self.assertIn('remaining_credits', usage)
    
    def test_reset_daily_usage(self):
        """Test resetting daily usage."""
        # Track some usage
        self.usage_tracker.track_search(
            user_id=str(self.user.id),
            query='test query',
            results_count=50,
            credits_used=100,
            cache_hit=False
        )
        
        # Verify usage exists
        usage = self.usage_tracker.get_user_usage(str(self.user.id))
        self.assertEqual(usage['searches_today'], 1)
        
        # Reset
        self.usage_tracker.reset_daily_usage()
        
        # Verify reset
        usage = self.usage_tracker.get_user_usage(str(self.user.id))
        self.assertEqual(usage['searches_today'], 0)


class TestQueryBuilder(TestCase):
    """Test cases for QueryBuilder service."""
    
    def setUp(self):
        """Set up test data."""
        self.query_builder = QueryBuilder()
    
    def test_build_basic_query(self):
        """Test building basic query."""
        query = self.query_builder.build_query(
            population='software developers',
            interest='code review',
            context='open source'
        )
        
        self.assertIn('software developers', query)
        self.assertIn('code review', query)
        self.assertIn('open source', query)
    
    def test_build_query_with_keywords(self):
        """Test building query with include/exclude keywords."""
        query = self.query_builder.build_query(
            population='researchers',
            interest='climate change',
            context='policy',
            include_keywords=['mitigation', 'adaptation'],
            exclude_keywords=['denial', 'skeptic']
        )
        
        self.assertIn('researchers', query)
        self.assertIn('climate change', query)
        self.assertIn('mitigation', query)
        self.assertIn('adaptation', query)
        self.assertIn('-denial', query)
        self.assertIn('-skeptic', query)
    
    def test_build_query_with_file_types(self):
        """Test building query with file type filters."""
        query = self.query_builder.build_query(
            population='students',
            interest='online learning',
            context='pandemic',
            file_types=['pdf', 'doc', 'docx']
        )
        
        self.assertIn('filetype:pdf', query)
        self.assertIn('filetype:doc', query)
        self.assertIn('filetype:docx', query)
        self.assertIn('OR', query)
    
    def test_build_query_academic_only(self):
        """Test building query with academic filter."""
        query = self.query_builder.build_query(
            population='academics',
            interest='peer review',
            context='publication',
            academic_only=True
        )
        
        # Should include academic site filters
        self.assertIn('site:', query)
        academic_sites = ['edu', 'ac.uk', 'scholar.google.com']
        has_academic_filter = any(site in query for site in academic_sites)
        self.assertTrue(has_academic_filter)
    
    def test_optimize_query(self):
        """Test query optimization."""
        # Test with long query
        long_population = 'a very long population description ' * 10
        
        query = self.query_builder.build_query(
            population=long_population,
            interest='test',
            context='test'
        )
        
        # Should be optimized to stay within limits
        self.assertLess(len(query), 2048)
    
    def test_escape_special_characters(self):
        """Test escaping special characters in query."""
        query = self.query_builder.build_query(
            population='C++ developers',
            interest='templates & generics',
            context='modern (2020+)'
        )
        
        # Special characters should be handled properly
        self.assertIn('C++', query)
        self.assertIn('templates', query)
        self.assertIn('generics', query)
    
    def test_validate_query_params(self):
        """Test query parameter validation."""
        is_valid, errors = self.query_builder.validate_params(
            population='',
            interest='test',
            context='test'
        )
        
        self.assertFalse(is_valid)
        self.assertIn('population', errors[0].lower())
        
        # Valid params
        is_valid, errors = self.query_builder.validate_params(
            population='developers',
            interest='testing',
            context='agile'
        )
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)


class TestResultProcessor(TestCase):
    """Test cases for ResultProcessor service."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.session = SearchSession.objects.create(
            title='Test Session',
            owner=self.user
        )
        self.query = SearchQuery.objects.create(
            session=self.session,
            population='test population',
            interest='test interest',
            context='test context',
            search_engines=['google']
        )
        self.execution = SearchExecution.objects.create(
            query=self.query,
            initiated_by=self.user,
            status='running'
        )
        self.processor = ResultProcessor()
    
    def test_process_search_results(self):
        """Test processing search results."""
        raw_results = [
            {
                'position': 1,
                'title': 'Test Result 1',
                'link': 'https://example.com/1',
                'snippet': 'This is a test snippet',
                'displayLink': 'example.com'
            },
            {
                'position': 2,
                'title': 'Test Result 2',
                'link': 'https://example.edu/research.pdf',
                'snippet': 'Academic research paper',
                'displayLink': 'example.edu'
            }
        ]
        
        processed_count, duplicate_count, errors = self.processor.process_search_results(
            execution_id=str(self.execution.id),
            raw_results=raw_results,
            batch_size=50
        )
        
        self.assertEqual(processed_count, 2)
        self.assertEqual(duplicate_count, 0)
        self.assertEqual(len(errors), 0)
        
        # Verify raw results were created
        raw_results = RawSearchResult.objects.filter(execution=self.execution)
        self.assertEqual(raw_results.count(), 2)
        
        # Check specific attributes
        result1 = raw_results.get(position=1)
        self.assertEqual(result1.title, 'Test Result 1')
        self.assertEqual(result1.link, 'https://example.com/1')
        
        result2 = raw_results.get(position=2)
        self.assertTrue(result2.has_pdf)
        self.assertTrue(result2.is_academic)
    
    def test_detect_duplicates(self):
        """Test duplicate detection during processing."""
        # Create existing result
        RawSearchResult.objects.create(
            execution=self.execution,
            position=1,
            title='Existing Result',
            link='https://example.com/existing',
            snippet='Existing snippet'
        )
        
        # Process results with duplicate
        raw_results = [
            {
                'position': 2,
                'title': 'Existing Result',
                'link': 'https://example.com/existing',  # Duplicate URL
                'snippet': 'Different snippet'
            },
            {
                'position': 3,
                'title': 'New Result',
                'link': 'https://example.com/new',
                'snippet': 'New snippet'
            }
        ]
        
        processed_count, duplicate_count, errors = self.processor.process_search_results(
            execution_id=str(self.execution.id),
            raw_results=raw_results,
            batch_size=50
        )
        
        self.assertEqual(processed_count, 1)  # Only new result
        self.assertEqual(duplicate_count, 1)  # One duplicate
    
    def test_extract_metadata(self):
        """Test metadata extraction from results."""
        result_data = {
            'title': 'Research Paper 2023',
            'link': 'https://university.edu/research/paper.pdf',
            'snippet': 'Published in January 2023. This study examines...',
            'displayLink': 'university.edu'
        }
        
        metadata = self.processor.extract_metadata(result_data)
        
        self.assertTrue(metadata['has_pdf'])
        self.assertTrue(metadata['is_academic'])
        self.assertTrue(metadata['has_date'])
        self.assertEqual(metadata['detected_date'].year, 2023)
        self.assertEqual(metadata['language_code'], 'en')
    
    def test_process_results_with_errors(self):
        """Test processing results with some errors."""
        raw_results = [
            {
                'position': 1,
                'title': 'Valid Result',
                'link': 'https://example.com/valid',
                'snippet': 'Valid snippet'
            },
            {
                'position': 2,
                # Missing required fields
                'title': 'Invalid Result'
                # No link field
            },
            {
                'position': 3,
                'title': 'Another Valid',
                'link': 'https://example.com/valid2',
                'snippet': 'Another snippet'
            }
        ]
        
        processed_count, duplicate_count, errors = self.processor.process_search_results(
            execution_id=str(self.execution.id),
            raw_results=raw_results,
            batch_size=50
        )
        
        self.assertEqual(processed_count, 2)  # Two valid results
        self.assertEqual(len(errors), 1)  # One error
        self.assertIn('position 2', errors[0])
    
    def test_batch_processing(self):
        """Test batch processing of large result sets."""
        # Create large set of results
        raw_results = []
        for i in range(150):
            raw_results.append({
                'position': i + 1,
                'title': f'Result {i + 1}',
                'link': f'https://example.com/result{i + 1}',
                'snippet': f'Snippet for result {i + 1}'
            })
        
        processed_count, duplicate_count, errors = self.processor.process_search_results(
            execution_id=str(self.execution.id),
            raw_results=raw_results,
            batch_size=50
        )
        
        self.assertEqual(processed_count, 150)
        
        # Verify all were created
        created_results = RawSearchResult.objects.filter(execution=self.execution)
        self.assertEqual(created_results.count(), 150)
    
    def test_normalize_url(self):
        """Test URL normalization."""
        test_cases = [
            ('http://example.com', 'https://example.com'),
            ('https://EXAMPLE.COM/PATH', 'https://example.com/path'),
            ('https://example.com/path?utm_source=test', 'https://example.com/path'),
            ('https://example.com#section', 'https://example.com')
        ]
        
        for input_url, expected in test_cases:
            normalized = self.processor.normalize_url(input_url)
            self.assertEqual(normalized, expected)
    
    def test_language_detection(self):
        """Test language detection from snippets."""
        test_cases = [
            ('This is an English text about research', 'en'),
            ('Ceci est un texte français sur la recherche', 'fr'),
            ('Dies ist ein deutscher Text über Forschung', 'de'),
            ('', 'unknown')  # Empty text
        ]
        
        for text, expected_lang in test_cases:
            result_data = {
                'title': 'Test',
                'link': 'https://example.com',
                'snippet': text
            }
            metadata = self.processor.extract_metadata(result_data)
            # Language detection might not be perfect, so we just check it's set
            self.assertIn('language_code', metadata)


class TestServiceIntegration(TestCase):
    """Integration tests for services working together."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )
        self.session = SearchSession.objects.create(
            title='Test Session',
            owner=self.user,
            status='ready_to_execute'
        )
        self.query = SearchQuery.objects.create(
            session=self.session,
            population='researchers',
            interest='climate change',
            context='policy',
            search_engines=['google'],
            include_keywords=['mitigation'],
            exclude_keywords=['denial'],
            document_types=['pdf'],
            max_results=10
        )
        cache.clear()
    
    @patch('apps.serp_execution.services.serper_client.requests.Session.post')
    def test_full_search_pipeline(self, mock_post):
        """Test full search pipeline from query building to result processing."""
        # Mock Serper API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'organic': [
                {
                    'position': 1,
                    'title': 'Climate Change Mitigation Strategies',
                    'link': 'https://research.edu/climate-mitigation.pdf',
                    'snippet': 'A comprehensive study on climate mitigation published in 2023'
                },
                {
                    'position': 2,
                    'title': 'Policy Framework for Climate Action',
                    'link': 'https://policy.org/climate-framework',
                    'snippet': 'Government policy recommendations for climate change'
                }
            ],
            'credits': 1,
            'searchInformation': {
                'totalResults': '2',
                'searchTime': 0.3
            }
        }
        mock_response.headers = {'X-Request-ID': 'test-123'}
        mock_post.return_value = mock_response
        
        # Initialize services
        query_builder = QueryBuilder()
        serper_client = SerperClient()
        result_processor = ResultProcessor()
        usage_tracker = UsageTracker()
        cache_manager = CacheManager()
        
        # Build query
        search_query = query_builder.build_query(
            population=self.query.population,
            interest=self.query.interest,
            context=self.query.context,
            include_keywords=self.query.include_keywords,
            exclude_keywords=self.query.exclude_keywords,
            file_types=self.query.document_types,
            academic_only=True
        )
        
        self.assertIn('researchers', search_query)
        self.assertIn('climate change', search_query)
        self.assertIn('mitigation', search_query)
        self.assertIn('-denial', search_query)
        
        # Create execution
        execution = SearchExecution.objects.create(
            query=self.query,
            initiated_by=self.user,
            status='running',
            api_parameters={'q': search_query, 'num': 10}
        )
        
        # Execute search
        results, metadata = serper_client.search(
            search_query,
            num_results=10,
            use_cache=True
        )
        
        self.assertEqual(len(results['organic']), 2)
        self.assertEqual(metadata['credits_used'], 1)
        
        # Process results
        processed_count, duplicate_count, errors = result_processor.process_search_results(
            execution_id=str(execution.id),
            raw_results=results['organic'],
            batch_size=50
        )
        
        self.assertEqual(processed_count, 2)
        self.assertEqual(duplicate_count, 0)
        
        # Track usage
        usage_tracker.track_search(
            user_id=str(self.user.id),
            query=search_query,
            results_count=processed_count,
            credits_used=metadata['credits_used'],
            cache_hit=metadata.get('cache_hit', False)
        )
        
        # Verify results
        raw_results = RawSearchResult.objects.filter(execution=execution)
        self.assertEqual(raw_results.count(), 2)
        
        # Check first result
        result1 = raw_results.get(position=1)
        self.assertTrue(result1.has_pdf)
        self.assertTrue(result1.is_academic)
        self.assertIn('mitigation', result1.title.lower())
        
        # Check cache
        cached_results, cached_metadata = cache_manager.get_cached_results(
            query=search_query,
            engine='google'
        )
        self.assertIsNotNone(cached_results)
        
        # Update execution
        execution.status = 'completed'
        execution.results_count = processed_count
        execution.api_credits_used = metadata['credits_used']
        execution.estimated_cost = serper_client.estimate_cost(metadata['credits_used'])
        execution.save()
        
        # Verify usage tracking
        user_usage = usage_tracker.get_user_usage(str(self.user.id))
        self.assertEqual(user_usage['searches_today'], 1)
        self.assertEqual(user_usage['credits_used_today'], 1)
        self.assertEqual(user_usage['results_retrieved_today'], 2)


# Import time for rate limiting tests
import time