"""
Bootstrap dependency injection container.
Registers providers from different slices.
"""

from .interfaces import container


def initialize_dependency_injection():
    """Initialize the dependency injection container with providers."""
    
    # Use dynamic imports to avoid circular dependencies
    from importlib import import_module
    
    try:
        # Dynamically import provider modules
        review_manager_providers = import_module('apps.review_manager.providers')
        search_strategy_providers = import_module('apps.search_strategy.providers')
        
        # Register providers
        container.register("session_provider", review_manager_providers.SessionProviderImpl())
        container.register("query_provider", search_strategy_providers.QueryProviderImpl())
    except ImportError as e:
        # Log the error but don't fail - providers might not be needed in all contexts
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not initialize dependency injection: {e}")


def get_dependencies():
    """Get dependencies, initializing if needed."""
    if not container._providers:
        initialize_dependency_injection()
    return container
