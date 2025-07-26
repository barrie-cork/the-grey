"""
Bootstrap dependency injection container.
Registers providers from different slices.
"""

from .interfaces import container


def initialize_dependency_injection():
    """Initialize the dependency injection container with providers."""

    # Import providers only when needed to avoid circular imports
    from apps.review_manager.providers import SessionProviderImpl
    from apps.search_strategy.providers import QueryProviderImpl

    # Register providers
    container.register("session_provider", SessionProviderImpl())
    container.register("query_provider", QueryProviderImpl())


def get_dependencies():
    """Get dependencies, initializing if needed."""
    if not container._providers:
        initialize_dependency_injection()
    return container
