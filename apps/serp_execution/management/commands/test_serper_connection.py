"""
Management command to test Serper API connection.
"""

import json
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from apps.serp_execution.services import SerperClient, CacheManager, UsageTracker


class Command(BaseCommand):
    help = 'Test Serper API connection and basic functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--query',
            type=str,
            default='grey literature systematic review',
            help='Test query to execute'
        )
        parser.add_argument(
            '--num-results',
            type=int,
            default=10,
            help='Number of results to retrieve'
        )
        parser.add_argument(
            '--no-cache',
            action='store_true',
            help='Disable cache for this test'
        )
        parser.add_argument(
            '--check-usage',
            action='store_true',
            help='Check API usage statistics'
        )

    def handle(self, *args, **options):
        """Execute the test command."""
        self.stdout.write(self.style.NOTICE('Testing Serper API connection...\n'))
        
        # Check if API key is configured
        if not hasattr(settings, 'SERPER_API_KEY') or not settings.SERPER_API_KEY:
            raise CommandError(
                'SERPER_API_KEY not configured in settings. '
                'Please add it to your environment variables or settings file.'
            )
        
        # Initialize services
        try:
            client = SerperClient()
            cache_manager = CacheManager()
            usage_tracker = UsageTracker()
        except Exception as e:
            raise CommandError(f'Failed to initialize services: {str(e)}')
        
        # Check usage if requested
        if options['check_usage']:
            self.check_usage_stats(client, usage_tracker)
            return
        
        # Test query validation
        query = options['query']
        is_valid, error = client.validate_query(query)
        if not is_valid:
            raise CommandError(f'Invalid query: {error}')
        
        self.stdout.write(f'Query: {query}')
        self.stdout.write(f'Number of results: {options["num_results"]}')
        self.stdout.write(f'Cache enabled: {not options["no_cache"]}\n')
        
        # Check rate limits
        rate_status = client.check_rate_limits()
        self.stdout.write(
            f'Rate limit status: {rate_status["requests_in_window"]}/{rate_status["rate_limit"]} requests'
        )
        
        # Execute search
        try:
            self.stdout.write(self.style.NOTICE('\nExecuting search...\n'))
            
            results, metadata = client.search(
                query=query,
                num_results=options['num_results'],
                use_cache=not options['no_cache']
            )
            
            # Display metadata
            self.stdout.write(self.style.SUCCESS('Search completed successfully!\n'))
            self.stdout.write(f'Cache hit: {metadata.get("cache_hit", False)}')
            self.stdout.write(f'Credits used: {metadata.get("credits_used", 0)}')
            self.stdout.write(f'Total results available: {metadata.get("total_results", "Unknown")}')
            self.stdout.write(f'Time taken: {metadata.get("time_taken", 0)}s')
            self.stdout.write(f'Request ID: {metadata.get("request_id", "N/A")}\n')
            
            # Display results
            if 'organic' in results:
                self.stdout.write(f'Results retrieved: {len(results["organic"])}\n')
                
                for i, result in enumerate(results['organic'][:5], 1):
                    self.stdout.write(f'\n{i}. {result.get("title", "No title")}')
                    self.stdout.write(f'   URL: {result.get("link", "No URL")}')
                    snippet = result.get("snippet", "No snippet")
                    if len(snippet) > 100:
                        snippet = snippet[:100] + '...'
                    self.stdout.write(f'   Snippet: {snippet}')
                
                if len(results['organic']) > 5:
                    self.stdout.write(f'\n... and {len(results["organic"]) - 5} more results')
            else:
                self.stdout.write(self.style.WARNING('No organic results found in response'))
            
            # Display cache stats
            if not options['no_cache']:
                cache_stats = cache_manager.get_cache_stats()
                savings = cache_manager.estimate_cache_savings()
                
                self.stdout.write(self.style.NOTICE('\nCache Statistics:'))
                self.stdout.write(f'Hit rate: {cache_stats["hit_rate"]}%')
                self.stdout.write(f'Total requests: {cache_stats["total_requests"]}')
                self.stdout.write(f'Estimated savings: ${savings["estimated_savings_usd"]:.4f}')
            
            # Display cost estimate
            cost = client.estimate_cost(options['num_results'])
            self.stdout.write(f'\nEstimated cost for this query: ${cost:.4f}')
            
        except Exception as e:
            raise CommandError(f'Search failed: {str(e)}')
    
    def check_usage_stats(self, client, usage_tracker):
        """Check and display API usage statistics."""
        self.stdout.write(self.style.NOTICE('Checking API usage statistics...\n'))
        
        # Get usage from API
        try:
            api_stats = client.get_usage_stats()
            self.stdout.write('API Usage (from Serper):')
            self.stdout.write(f'  Credits remaining: {api_stats["credits_remaining"]}')
            self.stdout.write(f'  Credits used today: {api_stats["credits_used_today"]}')
            self.stdout.write(f'  Requests today: {api_stats["requests_today"]}')
            self.stdout.write(f'  Average response time: {api_stats["average_response_time"]}s\n')
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Could not get API stats: {str(e)}\n'))
        
        # Get local usage tracking
        budget_status = usage_tracker.check_budget_status()
        analytics = usage_tracker.get_usage_analytics(days=7)
        
        self.stdout.write('Budget Status:')
        self.stdout.write(f'  Daily: ${budget_status["daily"]["used"]:.2f} / ${budget_status["daily"]["budget"]:.2f} ({budget_status["daily"]["percentage"]:.1%})')
        self.stdout.write(f'  Monthly: ${budget_status["monthly"]["used"]:.2f} / ${budget_status["monthly"]["budget"]:.2f} ({budget_status["monthly"]["percentage"]:.1%})\n')
        
        self.stdout.write('7-Day Analytics:')
        self.stdout.write(f'  Total queries: {analytics["total_queries"]}')
        self.stdout.write(f'  Success rate: {analytics["success_rate"]}%')
        self.stdout.write(f'  Total cost: ${analytics["total_cost"]:.2f}')
        self.stdout.write(f'  Daily average: ${analytics["daily_avg_cost"]:.2f} ({analytics["daily_avg_queries"]} queries)')
        self.stdout.write(f'  Average execution time: {analytics["avg_execution_time"]}s')
        
        # Check if we can execute more queries
        can_execute, reason = usage_tracker.can_execute_queries(10)
        if can_execute:
            self.stdout.write(self.style.SUCCESS('\nBudget allows for more queries'))
        else:
            self.stdout.write(self.style.WARNING(f'\nBudget restriction: {reason}'))