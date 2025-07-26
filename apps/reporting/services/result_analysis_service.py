"""
Search result analysis service for reporting slice.
Business capability: Search result flow analysis and reporting.
"""

from typing import Any, Dict

from apps.core.logging import ServiceLoggerMixin
from apps.results_manager.models import ProcessedResult
from apps.serp_execution.models import RawSearchResult
from apps.review_results.models import SimpleReviewDecision


class SearchResultAnalysisService(ServiceLoggerMixin):
    """Service for analyzing search result flow through the system."""

    def generate_result_flow_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Generate summary of search result flow through the system.

        Args:
            session_id: UUID of the SearchSession

        Returns:
            Dictionary with result flow data (raw -> processed -> reviewed)
        """
        # Raw results retrieved from search
        raw_count = RawSearchResult.objects.filter(session_id=session_id).count()
        
        # Processed results (after deduplication)
        processed_count = ProcessedResult.objects.filter(session_id=session_id).count()
        
        # Review decisions
        decisions = SimpleReviewDecision.objects.filter(result__session_id=session_id)
        included_count = decisions.filter(decision="include").count()
        excluded_count = decisions.filter(decision="exclude").count()
        maybe_count = decisions.filter(decision="maybe").count()
        reviewed_count = included_count + excluded_count + maybe_count
        pending_count = processed_count - reviewed_count

        return {
            "session_id": session_id,
            "raw_results_retrieved": raw_count,
            "processed_results": processed_count,
            "duplicates_removed": raw_count - processed_count,
            "results_reviewed": reviewed_count,
            "results_pending": pending_count,
            "results_included": included_count,
            "results_excluded": excluded_count,
            "results_maybe": maybe_count,
            "completion_percentage": round((reviewed_count / processed_count * 100), 1) if processed_count > 0 else 0,
        }

    def get_document_type_distribution(self, session_id: str) -> Dict[str, int]:
        """
        Get distribution of document types in processed results.

        Args:
            session_id: UUID of the SearchSession

        Returns:
            Dictionary with document type counts
        """
        results = ProcessedResult.objects.filter(session_id=session_id)
        
        type_counts = {}
        for result in results:
            doc_type = result.document_type or "unknown"
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
            
        return type_counts

    def get_basic_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        Get basic statistics about search results.

        Args:
            session_id: UUID of the SearchSession

        Returns:
            Dictionary with basic statistics
        """
        results = ProcessedResult.objects.filter(session_id=session_id)
        
        pdf_count = results.filter(is_pdf=True).count()
        total_count = results.count()
        
        # Publication years (if available)
        year_counts = {}
        for result in results:
            if result.publication_year:
                year = str(result.publication_year)
                year_counts[year] = year_counts.get(year, 0) + 1

        return {
            "total_results": total_count,
            "pdf_documents": pdf_count,
            "non_pdf_documents": total_count - pdf_count,
            "publication_years": year_counts,
        }