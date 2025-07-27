"""
Simple result processor service for serp_execution slice.
Business capability: Basic result processing and metadata extraction.
"""

from typing import Any, Dict, List
from urllib.parse import urlparse


class ResultProcessor:
    """Simple service for processing raw search results from Serper API."""

    def process_search_results(self, raw_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process raw search results into normalized format.

        Args:
            raw_results: Raw results from Serper API

        Returns:
            List of processed results
        """
        processed_results = []
        
        # Extract organic results
        organic_results = raw_results.get("organic", [])
        
        for result in organic_results:
            processed_result = self._process_single_result(result)
            if processed_result:
                processed_results.append(processed_result)
        
        return processed_results

    def _process_single_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single search result."""
        url = result.get("link", "")
        title = result.get("title", "")
        snippet = result.get("snippet", "")
        
        # Basic metadata extraction
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower() if parsed_url.netloc else ""
        
        # Detect file type from URL
        file_type = self._detect_file_type(url)
        
        return {
            "url": url,
            "title": title.strip(),
            "snippet": snippet.strip(),
            "domain": domain,
            "file_type": file_type,
            "is_pdf": file_type == "pdf",
        }

    def _detect_file_type(self, url: str) -> str:
        """Detect file type from URL."""
        url_lower = url.lower()
        
        if ".pdf" in url_lower or "filetype:pdf" in url_lower:
            return "pdf"
        elif ".doc" in url_lower or "filetype:doc" in url_lower:
            return "doc"
        elif ".ppt" in url_lower or "filetype:ppt" in url_lower:
            return "ppt"
        else:
            return "webpage"

    def extract_metadata(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract basic metadata from a result."""
        return {
            "domain": result.get("domain", ""),
            "file_type": result.get("file_type", "webpage"),
            "has_title": bool(result.get("title", "").strip()),
            "has_snippet": bool(result.get("snippet", "").strip()),
        }