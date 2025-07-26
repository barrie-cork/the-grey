"""
Query builder service for constructing optimized search queries.
Converts PIC framework terms into effective search strings with proper Boolean logic.
"""

import logging
import re
from typing import List, Optional, Tuple
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


class QueryBuilder:
    """
    Service for building and optimizing search queries from PIC framework.
    Handles Boolean operators, file type filtering, and query optimization.
    """

    # Maximum query length for most search engines
    MAX_QUERY_LENGTH = 2048

    # Common stop words to potentially remove if query is too long
    STOP_WORDS = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "as",
        "is",
        "was",
        "are",
        "were",
        "been",
        "be",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
    }

    # File type mappings
    FILE_TYPE_EXTENSIONS = {
        "pdf": "pdf",
        "doc": "doc",
        "docx": "docx",
        "ppt": "ppt",
        "pptx": "pptx",
        "xls": "xls",
        "xlsx": "xlsx",
        "report": "pdf",  # Most reports are PDFs
        "thesis": "pdf",  # Most theses are PDFs
        "dissertation": "pdf",
    }

    # Academic site patterns for grey literature
    ACADEMIC_DOMAINS = [
        "edu",
        "ac.uk",
        "edu.au",
        "edu.ca",
        "ac.in",
        "edu.cn",
        "univ",
        "university",
        "college",
        "institute",
        "academia.edu",
        "researchgate.net",
        "arxiv.org",
        "ssrn.com",
        "nih.gov",
        "gov",
        "org",
        "ngo",
    ]

    def __init__(self):
        """Initialize the query builder."""
        self.query_cache = {}

    def build_query(
        self,
        population: str,
        interest: str,
        context: str,
        include_keywords: Optional[List[str]] = None,
        exclude_keywords: Optional[List[str]] = None,
        file_types: Optional[List[str]] = None,
        academic_only: bool = False,
        exact_phrases: Optional[List[str]] = None,
    ) -> str:
        """
        Build an optimized search query from PIC framework components.

        Args:
            population: Target population terms
            interest: Interest/intervention terms
            context: Context/setting terms
            include_keywords: Additional keywords to include
            exclude_keywords: Keywords to exclude
            file_types: List of file types to filter (pdf, doc, etc.)
            academic_only: Whether to limit to academic sources
            exact_phrases: Phrases that must appear exactly

        Returns:
            Optimized search query string
        """
        try:
            # Start with PIC components
            query_parts = []

            # Process each PIC component
            if population:
                query_parts.append(self._process_component(population, "population"))

            if interest:
                query_parts.append(self._process_component(interest, "interest"))

            if context:
                query_parts.append(self._process_component(context, "context"))

            # Join PIC components with AND
            base_query = self._join_with_operator(query_parts, "AND")

            # Add exact phrases
            if exact_phrases:
                phrase_parts = [f'"{phrase}"' for phrase in exact_phrases]
                base_query = (
                    f"{base_query} {' '.join(phrase_parts)}"
                    if base_query
                    else " ".join(phrase_parts)
                )

            # Add included keywords
            if include_keywords:
                keyword_parts = []
                for keyword in include_keywords:
                    if self._contains_boolean_operators(keyword):
                        keyword_parts.append(f"({keyword})")
                    else:
                        keyword_parts.append(keyword)

                if keyword_parts:
                    keywords_string = self._join_with_operator(keyword_parts, "OR")
                    base_query = (
                        f"{base_query} ({keywords_string})"
                        if base_query
                        else keywords_string
                    )

            # Add exclusions
            if exclude_keywords:
                exclusions = " ".join(
                    [
                        f'-"{word}"' if " " in word else f"-{word}"
                        for word in exclude_keywords
                    ]
                )
                base_query = f"{base_query} {exclusions}"

            # Add file type filters
            if file_types:
                file_filter = self._build_file_type_filter(file_types)
                if file_filter:
                    base_query = f"{base_query} {file_filter}"

            # Add academic source filter
            if academic_only:
                academic_filter = self._build_academic_filter()
                base_query = f"{base_query} {academic_filter}"

            # Optimize query length
            optimized_query = self._optimize_query_length(base_query)

            # Validate and clean
            final_query = self._clean_query(optimized_query)

            logger.info(f"Built query: {final_query[:100]}...")
            return final_query

        except Exception as e:
            logger.error(f"Error building query: {str(e)}")
            # Return a simple concatenation as fallback
            fallback = " ".join(filter(None, [population, interest, context]))
            return self._clean_query(fallback)

    def _process_component(self, component: str, component_type: str) -> str:
        """
        Process a PIC component, handling Boolean operators and phrases.

        Args:
            component: The component text
            component_type: Type of component (population, interest, context)

        Returns:
            Processed component string
        """
        # Check if component already has Boolean operators
        if self._contains_boolean_operators(component):
            # Already has structure, just ensure it's properly formatted
            return f"({component})"

        # Check if it's a phrase (contains spaces but no operators)
        if " " in component and not any(
            op in component.upper() for op in ["AND", "OR", "NOT"]
        ):
            # For multi-word components without operators, use phrase search
            return f'"{component}"'

        # Single word or simple component
        return component

    def _contains_boolean_operators(self, text: str) -> bool:
        """Check if text contains Boolean operators."""
        boolean_pattern = r"\b(AND|OR|NOT)\b"
        return bool(re.search(boolean_pattern, text.upper()))

    def _join_with_operator(self, parts: List[str], operator: str) -> str:
        """Join query parts with specified Boolean operator."""
        # Filter out empty parts
        valid_parts = [p for p in parts if p and p.strip()]

        if not valid_parts:
            return ""

        if len(valid_parts) == 1:
            return valid_parts[0]

        # Join with operator, adding parentheses if needed
        return f" {operator} ".join(valid_parts)

    def _build_file_type_filter(self, file_types: List[str]) -> str:
        """
        Build file type filter string.

        Args:
            file_types: List of file types

        Returns:
            File type filter string
        """
        filters = []

        for file_type in file_types:
            # Get the actual extension
            ext = self.FILE_TYPE_EXTENSIONS.get(file_type.lower(), file_type.lower())
            filters.append(f"filetype:{ext}")

        if not filters:
            return ""

        # Join with OR for multiple file types
        if len(filters) == 1:
            return filters[0]
        else:
            return f"({' OR '.join(filters)})"

    def _build_academic_filter(self) -> str:
        """Build filter for academic sources."""
        # Create site filters for academic domains
        site_filters = []

        # Add top-level domains
        for domain in self.ACADEMIC_DOMAINS[:10]:  # Limit to avoid query being too long
            if "." in domain:
                site_filters.append(f"site:{domain}")
            else:
                site_filters.append(f"site:*.{domain}")

        return f"({' OR '.join(site_filters)})"

    def _optimize_query_length(self, query: str) -> str:
        """
        Optimize query length to fit within search engine limits.

        Args:
            query: The query to optimize

        Returns:
            Optimized query
        """
        if len(query) <= self.MAX_QUERY_LENGTH:
            return query

        logger.warning(f"Query too long ({len(query)} chars), optimizing...")

        # Try various optimization strategies
        optimized = query

        # 1. Remove redundant spaces
        optimized = " ".join(optimized.split())

        if len(optimized) <= self.MAX_QUERY_LENGTH:
            return optimized

        # 2. Remove stop words from non-phrase parts
        optimized = self._remove_stop_words(optimized)

        if len(optimized) <= self.MAX_QUERY_LENGTH:
            return optimized

        # 3. Simplify academic filter if present
        if "site:" in optimized:
            optimized = re.sub(r"\(site:.*?\)", "", optimized)
            logger.info("Removed academic filter to reduce query length")

        if len(optimized) <= self.MAX_QUERY_LENGTH:
            return optimized

        # 4. If still too long, truncate intelligently
        return self._truncate_query(optimized)

    def _remove_stop_words(self, query: str) -> str:
        """Remove stop words from query while preserving structure."""
        # Don't remove from quoted phrases
        phrases = re.findall(r'"[^"]*"', query)
        temp_query = query

        # Replace phrases with placeholders
        for i, phrase in enumerate(phrases):
            temp_query = temp_query.replace(phrase, f"__PHRASE_{i}__")

        # Remove stop words from remaining text
        words = temp_query.split()
        filtered_words = []

        for word in words:
            if (
                word.upper() in ["AND", "OR", "NOT"]
                or word.startswith("-")
                or word.startswith("site:")
                or word.startswith("filetype:")
                or word.startswith("__PHRASE_")
                or word.lower() not in self.STOP_WORDS
            ):
                filtered_words.append(word)

        # Reconstruct query
        result = " ".join(filtered_words)

        # Restore phrases
        for i, phrase in enumerate(phrases):
            result = result.replace(f"__PHRASE_{i}__", phrase)

        return result

    def _truncate_query(self, query: str) -> str:
        """Truncate query intelligently to fit length limit."""
        if len(query) <= self.MAX_QUERY_LENGTH:
            return query

        # Find a good truncation point (end of word, before operator, etc.)
        truncate_at = self.MAX_QUERY_LENGTH - 10  # Leave some buffer

        # Look for good break points
        for i in range(truncate_at, truncate_at - 100, -1):
            if i < len(query) and query[i] in " )":
                truncated = query[:i].strip()
                # Ensure parentheses are balanced
                if truncated.count("(") == truncated.count(")"):
                    logger.warning(f"Truncated query at position {i}")
                    return truncated

        # Fallback: hard truncate
        return query[: self.MAX_QUERY_LENGTH - 10].strip()

    def _clean_query(self, query: str) -> str:
        """
        Clean and validate the final query.

        Args:
            query: Query to clean

        Returns:
            Cleaned query
        """
        # Remove extra spaces
        cleaned = " ".join(query.split())

        # Fix common issues
        cleaned = cleaned.replace("( ", "(").replace(" )", ")")
        cleaned = re.sub(r"\s+([AND|OR|NOT])\s+", r" \1 ", cleaned)

        # Ensure balanced quotes
        if cleaned.count('"') % 2 != 0:
            # Remove last quote to balance
            cleaned = cleaned[::-1].replace('"', "", 1)[::-1]

        # Ensure balanced parentheses
        open_parens = cleaned.count("(")
        close_parens = cleaned.count(")")

        if open_parens > close_parens:
            cleaned += ")" * (open_parens - close_parens)
        elif close_parens > open_parens:
            # Remove extra closing parentheses from the end
            for _ in range(close_parens - open_parens):
                cleaned = cleaned[::-1].replace(")", "", 1)[::-1]

        # Remove empty parentheses
        cleaned = re.sub(r"\(\s*\)", "", cleaned)

        # Remove trailing operators
        cleaned = re.sub(r"\s+(AND|OR|NOT)\s*$", "", cleaned)

        return cleaned.strip()

    def validate_query(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a search query.

        Args:
            query: Query to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not query or not query.strip():
            return False, "Query cannot be empty"

        if len(query) > self.MAX_QUERY_LENGTH:
            return False, f"Query too long (max {self.MAX_QUERY_LENGTH} characters)"

        # Check for balanced quotes
        if query.count('"') % 2 != 0:
            return False, "Unbalanced quotes in query"

        # Check for balanced parentheses
        if query.count("(") != query.count(")"):
            return False, "Unbalanced parentheses in query"

        # Check for invalid operator usage
        if re.search(r"(^|\s)(AND|OR|NOT)($|\s+(AND|OR|NOT))", query):
            return False, "Invalid Boolean operator usage"

        return True, None

    def encode_for_url(self, query: str) -> str:
        """
        Encode query for use in URLs.

        Args:
            query: Query to encode

        Returns:
            URL-encoded query
        """
        return quote_plus(query)

    def extract_key_terms(self, query: str) -> List[str]:
        """
        Extract key terms from a query for tracking/analysis.

        Args:
            query: Query to analyze

        Returns:
            List of key terms
        """
        # Extract quoted phrases
        phrases = re.findall(r'"([^"]+)"', query)

        # Remove quotes and operators to get remaining terms
        clean_query = re.sub(r'"[^"]+"', "", query)
        clean_query = re.sub(r"\b(AND|OR|NOT|-)\b", " ", clean_query)
        clean_query = re.sub(r"(site:|filetype:)\S+", "", clean_query)
        clean_query = re.sub(r'[()"]', " ", clean_query)

        # Split and filter terms
        terms = [
            term.strip()
            for term in clean_query.split()
            if term.strip() and len(term.strip()) > 2
        ]

        # Combine phrases and terms
        all_terms = phrases + terms

        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in all_terms:
            term_lower = term.lower()
            if term_lower not in seen and term_lower not in self.STOP_WORDS:
                seen.add(term_lower)
                unique_terms.append(term)

        return unique_terms[:20]  # Limit to top 20 terms
