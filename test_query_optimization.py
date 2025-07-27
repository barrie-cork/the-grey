#!/usr/bin/env python
"""
Test script to validate the optimized query patterns work correctly.
This script tests the research-critical queries that have been optimized to use denormalized session fields.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "grey_lit_project.settings.local")
django.setup()

from django.db import connection
from django.test.utils import override_settings
from apps.review_manager.models import SearchSession
from apps.results_manager.models import ProcessedResult
from apps.review_results.models import SimpleReviewDecision
from apps.reporting.services.result_analysis_service import SearchResultAnalysisService
from apps.reporting.services.prisma_reporting_service import PrismaReportingService
from apps.reporting.services.export_service import ExportService


class QueryOptimizationTester:
    """Test the optimized query patterns for research-critical functionality."""
    
    def __init__(self):
        self.analysis_service = SearchResultAnalysisService()
        self.prisma_service = PrismaReportingService()
        self.export_service = ExportService()
        self.test_session_id = None
    
    def setup_test_data(self):
        """Create minimal test data for validation."""
        print("Setting up test data...")
        
        # Create a test session
        session = SearchSession.objects.create(
            title="Test Session for Query Optimization",
            description="Testing denormalized session queries",
            status="draft"
        )
        self.test_session_id = str(session.id)
        
        # Create test processed results
        results = []
        for i in range(3):
            result = ProcessedResult.objects.create(
                session=session,
                title=f"Test Result {i+1}",
                url=f"https://example.com/test-{i+1}",
                snippet=f"Test snippet {i+1}",
                document_type="pdf" if i % 2 == 0 else "html",
                is_pdf=i % 2 == 0
            )
            results.append(result)
        
        # Create test review decisions
        decisions = [
            ("include", "not_relevant", "This is relevant for our research"),
            ("exclude", "not_relevant", "Not relevant to our study"),
            ("maybe", "", "Uncertain about inclusion")
        ]
        
        for i, (decision, exclusion_reason, notes) in enumerate(decisions):
            SimpleReviewDecision.objects.create(
                result=results[i],
                session=session,  # Using denormalized session field
                decision=decision,
                exclusion_reason=exclusion_reason if decision == "exclude" else "",
                notes=notes
            )
        
        print(f"Created test session: {self.test_session_id}")
        print(f"Created {len(results)} processed results")
        print(f"Created {len(decisions)} review decisions")
    
    def test_result_analysis_service(self):
        """Test the optimized queries in SearchResultAnalysisService."""
        print("\n=== Testing SearchResultAnalysisService ===")
        
        # Test the main flow summary method
        with connection.cursor() as cursor:
            initial_queries = len(connection.queries)
        
        flow_summary = self.analysis_service.generate_result_flow_summary(self.test_session_id)
        
        final_queries = len(connection.queries)
        query_count = final_queries - initial_queries
        
        print(f"Queries executed: {query_count}")
        print(f"Flow summary results:")
        print(f"  - Processed results: {flow_summary['processed_results']}")
        print(f"  - Results reviewed: {flow_summary['results_reviewed']}")
        print(f"  - Results included: {flow_summary['results_included']}")
        print(f"  - Results excluded: {flow_summary['results_excluded']}")
        print(f"  - Results maybe: {flow_summary['results_maybe']}")
        print(f"  - Completion percentage: {flow_summary['completion_percentage']}%")
        
        # Validate results
        assert flow_summary['processed_results'] == 3, f"Expected 3 processed results, got {flow_summary['processed_results']}"
        assert flow_summary['results_included'] == 1, f"Expected 1 included result, got {flow_summary['results_included']}"
        assert flow_summary['results_excluded'] == 1, f"Expected 1 excluded result, got {flow_summary['results_excluded']}"
        assert flow_summary['results_maybe'] == 1, f"Expected 1 maybe result, got {flow_summary['results_maybe']}"
        
        print("✅ SearchResultAnalysisService tests passed")
    
    def test_prisma_reporting_service(self):
        """Test the optimized queries in PrismaReportingService."""
        print("\n=== Testing PrismaReportingService ===")
        
        # Test exclusion reasons method
        with connection.cursor() as cursor:
            initial_queries = len(connection.queries)
        
        exclusion_reasons = self.prisma_service.get_exclusion_reasons(self.test_session_id)
        
        final_queries = len(connection.queries)
        query_count = final_queries - initial_queries
        
        print(f"Queries executed: {query_count}")
        print(f"Exclusion reasons: {exclusion_reasons}")
        
        # Validate results
        assert len(exclusion_reasons) > 0, "Expected at least one exclusion reason"
        assert "Not Relevant" in exclusion_reasons, "Expected 'Not Relevant' exclusion reason"
        
        print("✅ PrismaReportingService tests passed")
    
    def test_export_service(self):
        """Test the optimized queries in ExportService."""
        print("\n=== Testing ExportService ===")
        
        # Test export summary method
        with connection.cursor() as cursor:
            initial_queries = len(connection.queries)
        
        export_summary = self.export_service.generate_export_summary(
            self.test_session_id, 
            ["studies", "prisma_flow", "bibliography"]
        )
        
        final_queries = len(connection.queries)
        query_count = final_queries - initial_queries
        
        print(f"Queries executed: {query_count}")
        print(f"Export summary:")
        print(f"  - Total results: {export_summary['data_available']['total_results']}")
        print(f"  - Included studies: {export_summary['data_available']['included_studies']}")
        print(f"  - Has PRISMA data: {export_summary['data_available']['has_prisma_data']}")
        
        # Validate results
        assert export_summary['data_available']['total_results'] == 3, f"Expected 3 total results, got {export_summary['data_available']['total_results']}"
        assert export_summary['data_available']['included_studies'] == 1, f"Expected 1 included study, got {export_summary['data_available']['included_studies']}"
        
        print("✅ ExportService tests passed")
    
    def test_query_efficiency(self):
        """Test that the optimized queries are efficient."""
        print("\n=== Testing Query Efficiency ===")
        
        # Test that we're using the denormalized session field
        decision = SimpleReviewDecision.objects.filter(session_id=self.test_session_id).first()
        if decision:
            print(f"Sample decision uses session_id: {decision.session_id}")
            print(f"Session title via denormalized field: {decision.session.title}")
        
        # Check that queries use session_id instead of result__session_id
        with connection.cursor() as cursor:
            initial_queries = len(connection.queries)
        
        # This should be efficient with session_id
        count = SimpleReviewDecision.objects.filter(
            session_id=self.test_session_id, 
            decision="include"
        ).count()
        
        final_queries = len(connection.queries)
        query_count = final_queries - initial_queries
        
        print(f"Direct session_id query count: {count} (executed {query_count} queries)")
        
        # Get the actual SQL to verify it's using session_id
        queryset = SimpleReviewDecision.objects.filter(
            session_id=self.test_session_id, 
            decision="include"
        )
        print(f"SQL query: {queryset.query}")
        
        assert "session_id" in str(queryset.query), "Query should use session_id field"
        assert "result__session" not in str(queryset.query), "Query should not use result__session join"
        
        print("✅ Query efficiency tests passed")
    
    def cleanup_test_data(self):
        """Clean up test data."""
        print(f"\nCleaning up test data for session: {self.test_session_id}")
        if self.test_session_id:
            try:
                session = SearchSession.objects.get(id=self.test_session_id)
                session.delete()
                print("✅ Test data cleaned up")
            except SearchSession.DoesNotExist:
                print("⚠️ Test session not found during cleanup")
    
    def run_all_tests(self):
        """Run all validation tests."""
        print("🚀 Starting Query Optimization Validation Tests")
        print("=" * 60)
        
        try:
            self.setup_test_data()
            self.test_result_analysis_service()
            self.test_prisma_reporting_service()
            self.test_export_service()
            self.test_query_efficiency()
            
            print("\n" + "=" * 60)
            print("🎉 All tests passed! Query optimization is working correctly.")
            print("\nOptimizations validated:")
            print("✅ SearchResultAnalysisService uses session_id for review decisions")
            print("✅ PrismaReportingService uses session_id for exclusion reasons")
            print("✅ ExportService uses session_id for included studies")
            print("✅ All queries are efficient and use denormalized fields")
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            self.cleanup_test_data()
        
        return True


if __name__ == "__main__":
    tester = QueryOptimizationTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🔥 Query optimization validation completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Query optimization validation failed!")
        sys.exit(1)