"""
Utility functions for the search_strategy app.

This module contains helper functions for PIC framework implementation,
query construction, template management, and search strategy optimization.
"""

import re
from typing import Any, Dict, List, Tuple

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet

from .models import QueryTemplate, SearchQuery

User = get_user_model()


def validate_pic_framework(
    population: str, interest: str, context: str
) -> Tuple[bool, List[str]]:
    """
    Validate PIC framework components for completeness and quality.

    Args:
        population: Population component
        interest: Interest/Intervention component
        context: Context component

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    # Check if at least one component is provided
    if not any([population.strip(), interest.strip(), context.strip()]):
        errors.append("At least one PIC component must be provided")

    # Check minimum length for provided components
    min_length = 3
    if population.strip() and len(population.strip()) < min_length:
        errors.append(f"Population must be at least {min_length} characters")
    if interest.strip() and len(interest.strip()) < min_length:
        errors.append(f"Interest must be at least {min_length} characters")
    if context.strip() and len(context.strip()) < min_length:
        errors.append(f"Context must be at least {min_length} characters")

    # Check for excessive length
    max_length = 500
    if len(population) > max_length:
        errors.append(f"Population must not exceed {max_length} characters")
    if len(interest) > max_length:
        errors.append(f"Interest must not exceed {max_length} characters")
    if len(context) > max_length:
        errors.append(f"Context must not exceed {max_length} characters")

    return len(errors) == 0, errors


def generate_query_variations(
    base_query: SearchQuery, variation_count: int = 3
) -> List[Dict[str, Any]]:
    """
    Generate variations of a search query using different keyword combinations.

    Args:
        base_query: The base SearchQuery instance
        variation_count: Number of variations to generate

    Returns:
        List of dictionaries containing query variations
    """
    variations = []

    # Original PIC components
    base_population = base_query.population
    base_interest = base_query.interest
    base_context = base_query.context

    # Generate variations by modifying components
    for i in range(variation_count):
        variation = {
            "population": base_population,
            "interest": base_interest,
            "context": base_context,
            "include_keywords": base_query.include_keywords.copy(),
            "exclude_keywords": base_query.exclude_keywords.copy(),
            "variation_type": f"Variation {i + 1}",
        }

        # Apply different modification strategies
        if i == 0:  # Broader search
            variation["variation_type"] = "Broader Search"
            # Remove some specific terms
            variation["population"] = _broaden_term(base_population)
            variation["interest"] = _broaden_term(base_interest)

        elif i == 1:  # Narrower search
            variation["variation_type"] = "Narrower Search"
            # Add more specific terms
            if base_query.include_keywords:
                variation["include_keywords"].extend(["specific", "detailed"])

        elif i == 2:  # Alternative terms
            variation["variation_type"] = "Alternative Terms"
            # Use synonyms where possible
            variation["population"] = _add_synonyms(base_population)
            variation["interest"] = _add_synonyms(base_interest)

        variations.append(variation)

    return variations


def _broaden_term(term: str) -> str:
    """Helper function to broaden search terms."""
    if not term:
        return term

    # Remove specific adjectives that might narrow results
    broad_term = re.sub(
        r"\b(specific|particular|exact|precise|detailed)\s+",
        "",
        term,
        flags=re.IGNORECASE,
    )
    return broad_term.strip()


def _add_synonyms(term: str) -> str:
    """Helper function to add common synonyms."""
    if not term:
        return term

    # Simple synonym mapping (can be expanded)
    synonyms = {
        "elderly": "elderly OR seniors OR older adults",
        "children": "children OR kids OR pediatric",
        "adults": "adults OR people OR individuals",
        "students": "students OR learners OR pupils",
        "workers": "workers OR employees OR staff",
        "healthcare": "healthcare OR medical OR clinical",
        "education": "education OR learning OR academic",
        "technology": "technology OR digital OR IT",
    }

    # Apply synonym replacements
    modified_term = term
    for word, replacement in synonyms.items():
        if word.lower() in term.lower():
            modified_term = re.sub(
                r"\b" + re.escape(word) + r"\b",
                replacement,
                modified_term,
                flags=re.IGNORECASE,
            )
            break  # Only apply one synonym replacement per term

    return modified_term


def optimize_query_string(query_string: str) -> Dict[str, Any]:
    """
    Analyze and optimize a search query string.

    Args:
        query_string: The search query string to optimize

    Returns:
        Dictionary containing optimization suggestions
    """
    analysis = {
        "original_query": query_string,
        "word_count": len(query_string.split()),
        "character_count": len(query_string),
        "has_quotes": '"' in query_string,
        "has_boolean_operators": any(
            op in query_string.upper() for op in ["AND", "OR", "NOT"]
        ),
        "has_wildcards": "*" in query_string or "?" in query_string,
        "suggestions": [],
    }

    # Generate optimization suggestions
    if analysis["word_count"] > 15:
        analysis["suggestions"].append(
            "Consider shortening the query - very long queries may be too specific"
        )

    if analysis["word_count"] < 3:
        analysis["suggestions"].append(
            "Consider adding more descriptive terms to improve precision"
        )

    if not analysis["has_quotes"] and analysis["word_count"] > 5:
        analysis["suggestions"].append(
            "Consider using quotes around key phrases for exact matches"
        )

    if not analysis["has_boolean_operators"] and analysis["word_count"] > 8:
        analysis["suggestions"].append(
            "Consider using AND/OR operators to structure complex queries"
        )

    # Check for common issues
    if re.search(
        r"\b(a|an|the|is|are|was|were|be|been|being)\b", query_string, re.IGNORECASE
    ):
        analysis["suggestions"].append(
            "Consider removing common stop words (a, an, the, is, are, etc.)"
        )

    return analysis


def get_template_suggestions(
    population: str, interest: str, context: str, user: User
) -> QuerySet:
    """
    Get relevant query templates based on PIC components.

    Args:
        population: Population component
        interest: Interest component
        context: Context component
        user: User requesting suggestions

    Returns:
        QuerySet of relevant QueryTemplate instances
    """
    # Start with templates available to the user
    templates = QueryTemplate.objects.filter(Q(is_public=True) | Q(created_by=user))

    # Filter based on similarity to provided components
    search_terms = []
    if population:
        search_terms.extend(population.lower().split())
    if interest:
        search_terms.extend(interest.lower().split())
    if context:
        search_terms.extend(context.lower().split())

    if search_terms:
        # Build a query to find templates with matching content
        query = Q()
        for term in search_terms:
            query |= (
                Q(population_template__icontains=term)
                | Q(interest_template__icontains=term)
                | Q(context_template__icontains=term)
                | Q(description__icontains=term)
            )
        templates = templates.filter(query)

    return templates.order_by("-usage_count", "name")[:10]


def calculate_query_complexity(query: SearchQuery) -> Dict[str, Any]:
    """
    Calculate complexity metrics for a search query.

    Args:
        query: SearchQuery instance

    Returns:
        Dictionary containing complexity metrics
    """
    complexity = {"score": 0, "level": "Simple", "factors": []}

    # Base complexity from PIC components
    pic_score = 0
    if query.population:
        pic_score += len(query.population.split())
    if query.interest:
        pic_score += len(query.interest.split())
    if query.context:
        pic_score += len(query.context.split())

    complexity["score"] += pic_score

    # Additional keywords complexity
    if query.include_keywords:
        complexity["score"] += len(query.include_keywords) * 2
        complexity["factors"].append(
            f"{len(query.include_keywords)} additional keywords"
        )

    if query.exclude_keywords:
        complexity["score"] += len(query.exclude_keywords) * 1.5
        complexity["factors"].append(
            f"{len(query.exclude_keywords)} exclusion keywords"
        )

    # Date filters
    if query.date_from or query.date_to:
        complexity["score"] += 3
        complexity["factors"].append("Date range filters")

    # Language filters
    if query.languages:
        complexity["score"] += len(query.languages)
        complexity["factors"].append(f"{len(query.languages)} language filters")

    # Document type filters
    if query.document_types:
        complexity["score"] += len(query.document_types)
        complexity["factors"].append(
            f"{len(query.document_types)} document type filters"
        )

    # Multiple search engines
    if len(query.search_engines) > 1:
        complexity["score"] += len(query.search_engines) - 1
        complexity["factors"].append(f"{len(query.search_engines)} search engines")

    # Determine complexity level
    if complexity["score"] <= 10:
        complexity["level"] = "Simple"
    elif complexity["score"] <= 20:
        complexity["level"] = "Moderate"
    elif complexity["score"] <= 35:
        complexity["level"] = "Complex"
    else:
        complexity["level"] = "Very Complex"

    return complexity


def get_session_query_statistics(session_id: str) -> Dict[str, Any]:
    """
    Get statistics for all queries in a session.

    Args:
        session_id: UUID of the SearchSession

    Returns:
        Dictionary containing query statistics
    """
    queries = SearchQuery.objects.filter(session_id=session_id)

    stats = {
        "total_queries": queries.count(),
        "active_queries": queries.filter(is_active=True).count(),
        "primary_queries": queries.filter(is_primary=True).count(),
        "executed_queries": queries.filter(execution_count__gt=0).count(),
        "avg_max_results": 0,
        "total_max_results": 0,
        "complexity_distribution": {
            "Simple": 0,
            "Moderate": 0,
            "Complex": 0,
            "Very Complex": 0,
        },
        "search_engines_used": set(),
        "has_date_filters": 0,
        "has_language_filters": 0,
    }

    if queries.exists():
        # Calculate averages and totals
        max_results_list = list(queries.values_list("max_results", flat=True))
        stats["avg_max_results"] = sum(max_results_list) / len(max_results_list)
        stats["total_max_results"] = sum(max_results_list)

        # Analyze each query
        for query in queries:
            complexity = calculate_query_complexity(query)
            stats["complexity_distribution"][complexity["level"]] += 1

            stats["search_engines_used"].update(query.search_engines)

            if query.date_from or query.date_to:
                stats["has_date_filters"] += 1

            if query.languages:
                stats["has_language_filters"] += 1

        # Convert set to list for JSON serialization
        stats["search_engines_used"] = list(stats["search_engines_used"])

    return stats


def export_queries_to_dict(session_id: str) -> List[Dict[str, Any]]:
    """
    Export all queries from a session to a list of dictionaries.

    Args:
        session_id: UUID of the SearchSession

    Returns:
        List of dictionaries containing query data
    """
    queries = SearchQuery.objects.filter(session_id=session_id).order_by(
        "order", "created_at"
    )

    exported_queries = []
    for query in queries:
        query_dict = {
            "id": str(query.id),
            "pic_framework": {
                "population": query.population,
                "interest": query.interest,
                "context": query.context,
            },
            "query_string": query.query_string,
            "parameters": {
                "search_engines": query.search_engines,
                "include_keywords": query.include_keywords,
                "exclude_keywords": query.exclude_keywords,
                "max_results": query.max_results,
            },
            "filters": {
                "date_from": query.date_from.isoformat() if query.date_from else None,
                "date_to": query.date_to.isoformat() if query.date_to else None,
                "languages": query.languages,
                "document_types": query.document_types,
            },
            "metadata": {
                "is_primary": query.is_primary,
                "is_active": query.is_active,
                "order": query.order,
                "execution_count": query.execution_count,
                "last_executed": (
                    query.last_executed.isoformat() if query.last_executed else None
                ),
            },
            "created_at": query.created_at.isoformat(),
            "updated_at": query.updated_at.isoformat(),
        }
        exported_queries.append(query_dict)

    return exported_queries
