"""
Management command to test Serper API connection.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.serp_execution.services import CacheManager, SerperClient
# from apps.serp_execution.services import UsageTracker  # Removed for simplification


class Command(BaseCommand):
    help = "Test Serper API connection and basic functionality"

    def add_arguments(self, parser):
        parser.add_argument(
            "--query",
            type=str,
            default="grey literature systematic review",
            help="Test query to execute",
        )
        parser.add_argument(
            "--num-results", type=int, default=10, help="Number of results to retrieve"
        )
        parser.add_argument(
            "--no-cache", action="store_true", help="Disable cache for this test"
        )
        parser.add_argument(
            "--check-usage", action="store_true", help="Check API usage statistics"
        )

    def handle(self, *args, **options):
        """Execute the test command."""
        self.stdout.write(self.style.NOTICE("Testing Serper API connection...\n"))

        # Check if API key is configured
        if not hasattr(settings, "SERPER_API_KEY") or not settings.SERPER_API_KEY:
            raise CommandError(
                "SERPER_API_KEY not configured in settings. "
                "Please add it to your environment variables or settings file."
            )

        # Initialize services
        try:
            client = SerperClient()
            cache_manager = CacheManager()
            # usage_tracker = UsageTracker()  # Removed for simplification
        except Exception as e:
            raise CommandError(f"Failed to initialize services: {str(e)}")

        # Check usage if requested
        if options["check_usage"]:
            self.stdout.write("Usage tracking disabled for simplification")
            return

        # Test query validation
        query = options["query"]
        is_valid, error = client.validate_query(query)
        if not is_valid:
            raise CommandError(f"Invalid query: {error}")

        self.stdout.write(f"Query: {query}")
        self.stdout.write(f'Number of results: {options["num_results"]}')
        self.stdout.write(f'Cache enabled: {not options["no_cache"]}\n')

        # Check rate limits
        rate_status = client.check_rate_limits()
        self.stdout.write(
            f'Rate limit status: {rate_status["requests_in_window"]}/{rate_status["rate_limit"]} requests'
        )

        # Execute search
        try:
            self.stdout.write(self.style.NOTICE("\nExecuting search...\n"))

            results, metadata = client.search(
                query=query,
                num_results=options["num_results"],
                use_cache=not options["no_cache"],
            )

            # Display metadata
            self.stdout.write(self.style.SUCCESS("Search completed successfully!\n"))
            self.stdout.write(f'Cache hit: {metadata.get("cache_hit", False)}')
            self.stdout.write(f'Credits used: {metadata.get("credits_used", 0)}')
            self.stdout.write(
                f'Total results available: {metadata.get("total_results", "Unknown")}'
            )
            self.stdout.write(f'Time taken: {metadata.get("time_taken", 0)}s')
            self.stdout.write(f'Request ID: {metadata.get("request_id", "N/A")}\n')

            # Display results
            if "organic" in results:
                self.stdout.write(f'Results retrieved: {len(results["organic"])}\n')

                for i, result in enumerate(results["organic"][:5], 1):
                    self.stdout.write(f'\n{i}. {result.get("title", "No title")}')
                    self.stdout.write(f'   URL: {result.get("link", "No URL")}')
                    snippet = result.get("snippet", "No snippet")
                    if len(snippet) > 100:
                        snippet = snippet[:100] + "..."
                    self.stdout.write(f"   Snippet: {snippet}")

                if len(results["organic"]) > 5:
                    self.stdout.write(
                        f'\n... and {len(results["organic"]) - 5} more results'
                    )
            else:
                self.stdout.write(
                    self.style.WARNING("No organic results found in response")
                )

            # Display cache stats
            if not options["no_cache"]:
                cache_stats = cache_manager.get_cache_stats()
                savings = cache_manager.estimate_cache_savings()

                self.stdout.write(self.style.NOTICE("\nCache Statistics:"))
                self.stdout.write(f'Hit rate: {cache_stats["hit_rate"]}%')
                self.stdout.write(f'Total requests: {cache_stats["total_requests"]}')
                self.stdout.write(
                    f'Estimated savings: ${savings["estimated_savings_usd"]:.4f}'
                )


        except Exception as e:
            raise CommandError(f"Search failed: {str(e)}")

    # Usage tracking methods removed for simplification
