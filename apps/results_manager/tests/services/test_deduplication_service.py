"""
Tests for DeduplicationService.

Tests result deduplication and grouping functionality.
"""

from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.review_manager.models import SearchSession
from apps.serp_execution.models import SearchExecution, RawSearchResult
from apps.results_manager.models import ProcessedResult, DuplicateGroup
from apps.results_manager.services.deduplication_service import DeduplicationService


User = get_user_model()


class TestDeduplicationService(TestCase):
    """Test cases for DeduplicationService."""
    
    def setUp(self):
        """Set up test data."""
        self.service = DeduplicationService()
        
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test session
        self.session = SearchSession.objects.create(
            title='Test Deduplication Session',
            description='Testing deduplication',
            owner=self.user,
            status='processing_results'
        )
        
        # Create raw search results with duplicates
        self.raw_results = []
        
        # Exact URL duplicates
        for i in range(3):
            result = RawSearchResult.objects.create(
                execution_id=f'exec-{i}',
                title='Duplicate Article Title',
                link='https://example.com/article/123',
                snippet='This is the same article appearing multiple times',
                position=i + 1
            )
            self.raw_results.append(result)
        
        # Similar titles with different URLs
        for i in range(2):
            result = RawSearchResult.objects.create(
                execution_id='exec-similar',
                title=f'Similar Article Title - Version {i+1}',
                link=f'https://different-site.com/article/{i}',
                snippet='Very similar content with slight variations',
                position=i + 4
            )
            self.raw_results.append(result)
        
        # Unique results
        unique_titles = [
            'Unique Research Paper on AI',
            'Different Study on Healthcare',
            'Another Distinct Article'
        ]
        
        for i, title in enumerate(unique_titles):
            result = RawSearchResult.objects.create(
                execution_id='exec-unique',
                title=title,
                link=f'https://unique-site.com/paper/{i}',
                snippet=f'Unique content about {title.lower()}',
                position=i + 6
            )
            self.raw_results.append(result)
    
    def test_identify_duplicates_by_url(self):
        """Test identification of duplicates by URL."""
        duplicates = self.service.identify_duplicates_by_url(self.raw_results)
        
        self.assertIsInstance(duplicates, dict)
        self.assertIn('https://example.com/article/123', duplicates)
        
        # Check that URL duplicates are grouped
        url_group = duplicates['https://example.com/article/123']
        self.assertEqual(len(url_group), 3)
        self.assertTrue(all(r.link == 'https://example.com/article/123' for r in url_group))
    
    def test_identify_duplicates_by_title_similarity(self):
        """Test identification of duplicates by title similarity."""
        duplicates = self.service.identify_duplicates_by_title_similarity(
            self.raw_results, 
            similarity_threshold=0.8
        )
        
        self.assertIsInstance(duplicates, list)
        
        # Should find similar titles
        similar_found = False
        for group in duplicates:
            titles = [r.title for r in group]
            if any('Similar Article Title' in title for title in titles):
                similar_found = True
                self.assertTrue(len(group) >= 2)
                break
        
        self.assertTrue(similar_found)
    
    def test_calculate_title_similarity(self):
        """Test title similarity calculation."""
        title1 = "Effects of AI on Healthcare Outcomes"
        title2 = "Effects of Artificial Intelligence on Healthcare Outcomes"
        title3 = "Completely Different Topic About Finance"
        
        sim1_2 = self.service.calculate_title_similarity(title1, title2)
        sim1_3 = self.service.calculate_title_similarity(title1, title3)
        
        self.assertGreater(sim1_2, 0.8)  # High similarity
        self.assertLess(sim1_3, 0.3)     # Low similarity
    
    def test_deduplicate_results(self):
        """Test full deduplication process."""
        deduplicated = self.service.deduplicate_results(
            self.raw_results, 
            str(self.session.id)
        )
        
        self.assertIsInstance(deduplicated, list)
        # Should have fewer results than original (3 URL duplicates -> 1)
        self.assertLess(len(deduplicated), len(self.raw_results))
        
        # Check that each result has required fields
        for result in deduplicated:
            self.assertIn('raw_result', result)
            self.assertIn('is_duplicate', result)
            self.assertIn('duplicate_group_id', result)
            self.assertIn('confidence_score', result)
    
    def test_create_duplicate_groups(self):
        """Test creation of duplicate groups in database."""
        groups = self.service.create_duplicate_groups(
            self.raw_results, 
            str(self.session.id)
        )
        
        self.assertIsInstance(groups, list)
        self.assertTrue(len(groups) > 0)
        
        # Check group structure
        for group in groups:
            self.assertIsInstance(group, DuplicateGroup)
            self.assertEqual(group.session_id, self.session.id)
            self.assertGreater(group.member_count, 1)
            self.assertIsNotNone(group.representative_result_id)
    
    def test_select_best_representative(self):
        """Test selection of best result from duplicate group."""
        # Create results with different quality indicators
        results = [
            RawSearchResult.objects.create(
                execution_id='exec-1',
                title='Short title',
                link='https://example.com/1',
                snippet='Short snippet',
                position=5
            ),
            RawSearchResult.objects.create(
                execution_id='exec-2',
                title='Much Better and More Descriptive Title for the Article',
                link='https://example.com/2',
                snippet='This is a much more detailed snippet with lots of information about the content',
                position=1
            ),
            RawSearchResult.objects.create(
                execution_id='exec-3',
                title='Medium length title here',
                link='https://example.com/3',
                snippet='Medium length snippet with some details',
                position=3
            )
        ]
        
        best = self.service.select_best_representative(results)
        
        # Should select the one with better title/snippet and position
        self.assertEqual(best.position, 1)
        self.assertIn('Better and More Descriptive', best.title)
    
    def test_merge_duplicate_metadata(self):
        """Test merging of metadata from duplicate results."""
        # Create results with different metadata
        results = []
        for i in range(3):
            result = RawSearchResult.objects.create(
                execution_id=f'exec-{i}',
                title='Same Article',
                link='https://example.com/article',
                snippet=f'Snippet version {i}',
                position=i + 1,
                metadata={
                    'source': f'source_{i}',
                    'date': f'2024-0{i+1}-01',
                    'common_field': 'same_value'
                }
            )
            results.append(result)
        
        merged = self.service.merge_duplicate_metadata(results)
        
        self.assertIsInstance(merged, dict)
        self.assertIn('sources', merged)
        self.assertIn('dates', merged)
        self.assertIn('positions', merged)
        self.assertIn('common_field', merged)
        
        # Check that all sources are captured
        self.assertEqual(len(merged['sources']), 3)
        self.assertEqual(len(merged['positions']), 3)
    
    def test_calculate_deduplication_statistics(self):
        """Test calculation of deduplication statistics."""
        # Run deduplication first
        self.service.deduplicate_results(self.raw_results, str(self.session.id))
        
        stats = self.service.calculate_deduplication_statistics(str(self.session.id))
        
        self.assertIsInstance(stats, dict)
        self.assertIn('total_raw_results', stats)
        self.assertIn('unique_results', stats)
        self.assertIn('duplicate_groups', stats)
        self.assertIn('deduplication_rate', stats)
        self.assertIn('duplicate_distribution', stats)
        
        # Check statistics make sense
        self.assertEqual(stats['total_raw_results'], len(self.raw_results))
        self.assertLess(stats['unique_results'], stats['total_raw_results'])
        self.assertGreater(stats['deduplication_rate'], 0)
    
    def test_fuzzy_url_matching(self):
        """Test fuzzy URL matching for similar URLs."""
        urls = [
            'https://example.com/article?id=123',
            'https://example.com/article?id=123&utm_source=google',
            'https://www.example.com/article?id=123',
            'http://example.com/article?id=123',
            'https://example.com/different-article?id=456'
        ]
        
        # Create results with these URLs
        results = []
        for i, url in enumerate(urls):
            result = RawSearchResult.objects.create(
                execution_id=f'exec-{i}',
                title='Same Article',
                link=url,
                snippet='Same content',
                position=i + 1
            )
            results.append(result)
        
        duplicates = self.service.identify_duplicates_by_fuzzy_url(results)
        
        # First 4 URLs should be grouped together
        self.assertTrue(len(duplicates) > 0)
        main_group = max(duplicates, key=len)
        self.assertEqual(len(main_group), 4)
    
    def test_content_based_deduplication(self):
        """Test deduplication based on content similarity."""
        # Create results with similar content
        base_snippet = "This research examines the impact of artificial intelligence on healthcare outcomes"
        
        results = []
        for i in range(3):
            # Add slight variations
            snippet = base_snippet
            if i == 1:
                snippet = "This study examines the impact of AI on healthcare outcomes"
            elif i == 2:
                snippet = "This research investigates the effect of artificial intelligence on health outcomes"
            
            result = RawSearchResult.objects.create(
                execution_id=f'exec-{i}',
                title=f'AI Healthcare Study {i}',
                link=f'https://site{i}.com/paper',
                snippet=snippet,
                position=i + 1
            )
            results.append(result)
        
        duplicates = self.service.identify_duplicates_by_content(
            results, 
            content_threshold=0.7
        )
        
        self.assertTrue(len(duplicates) > 0)
        # All three should be grouped due to high content similarity
        self.assertEqual(len(duplicates[0]), 3)
    
    def test_handle_empty_results(self):
        """Test handling of empty result sets."""
        empty_results = []
        
        deduplicated = self.service.deduplicate_results(
            empty_results, 
            str(self.session.id)
        )
        
        self.assertEqual(len(deduplicated), 0)
        
        stats = self.service.calculate_deduplication_statistics(str(self.session.id))
        self.assertEqual(stats['total_raw_results'], 0)
        self.assertEqual(stats['unique_results'], 0)
    
    def test_preserve_result_priority(self):
        """Test that deduplication preserves priority results."""
        # Create results with priority markers
        priority_result = RawSearchResult.objects.create(
            execution_id='exec-priority',
            title='Important Priority Result',
            link='https://priority.com/article',
            snippet='This is a priority result',
            position=1,
            metadata={'priority': 'high', 'source': 'trusted'}
        )
        
        duplicate_result = RawSearchResult.objects.create(
            execution_id='exec-duplicate',
            title='Important Priority Result (Duplicate)',
            link='https://other-site.com/same-article',
            snippet='This is the same priority result from another source',
            position=10,
            metadata={'priority': 'low', 'source': 'unknown'}
        )
        
        results = [priority_result, duplicate_result]
        
        # When selecting representative, should choose the priority one
        best = self.service.select_best_representative(results)
        self.assertEqual(best.id, priority_result.id)
    
    def test_logging_in_deduplication(self):
        """Test that deduplication operations are properly logged."""
        with self.assertLogs('apps.results_manager.services.deduplication_service', level='INFO') as cm:
            self.service.deduplicate_results(self.raw_results, str(self.session.id))
        
        self.assertTrue(any('Starting deduplication' in msg for msg in cm.output))
        self.assertTrue(any('Deduplication completed' in msg for msg in cm.output))
        self.assertTrue(any('identified' in msg for msg in cm.output))