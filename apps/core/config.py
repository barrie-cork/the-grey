"""
Centralized configuration system using Pydantic v2.
Provides type-safe configuration management for the Thesis Grey project.
"""

from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class SearchConfig(BaseModel):
    """Search-related configuration."""
    model_config = ConfigDict(validate_assignment=True)
    
    default_num_results: int = Field(default=100, ge=1, le=100, description="Default number of search results")
    default_location: Optional[str] = Field(default=None, description="Default search location")
    default_language: str = Field(default="en", pattern="^[a-z]{2}$", description="Default search language")
    default_file_types: list[str] = Field(default_factory=lambda: ["pdf"], description="Default file types to search")


class APIConfig(BaseModel):
    """External API configuration."""
    model_config = ConfigDict(validate_assignment=True)
    
    serper_timeout: int = Field(default=30, ge=5, le=120, description="Serper API timeout in seconds")
    rate_limit_per_minute: int = Field(default=100, ge=1, le=1000, description="API rate limit per minute")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum API retry attempts")


class ProcessingConfig(BaseModel):
    """Result processing configuration."""
    model_config = ConfigDict(validate_assignment=True)
    
    batch_size: int = Field(default=50, ge=10, le=500, description="Batch size for result processing")
    cache_ttl: int = Field(default=3600, ge=60, le=86400, description="Cache TTL in seconds")
    duplicate_threshold: float = Field(default=0.85, ge=0.0, le=1.0, description="Similarity threshold for duplicates")


class SystemConfig(BaseModel):
    """System-wide configuration with validation."""
    model_config = ConfigDict(validate_assignment=True)
    
    search: SearchConfig = Field(default_factory=SearchConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    
    @classmethod
    def load_from_settings(cls) -> "SystemConfig":
        """
        Load configuration from Django settings with fallback to database.
        
        Returns:
            SystemConfig: Loaded and validated configuration
        """
        # Check Django settings first
        config_dict = getattr(settings, 'THESIS_GREY_CONFIG', {})
        
        # Try to load from Django Constance
        try:
            from constance import config as constance_config
            
            # Override with Constance values if available
            constance_overrides = {
                'search': {
                    'default_num_results': constance_config.SEARCH_DEFAULT_NUM_RESULTS,
                    'default_location': constance_config.SEARCH_DEFAULT_LOCATION or None,
                    'default_language': constance_config.SEARCH_DEFAULT_LANGUAGE,
                    'default_file_types': constance_config.SEARCH_DEFAULT_FILE_TYPES.split(',') if constance_config.SEARCH_DEFAULT_FILE_TYPES else ['pdf'],
                },
                'api': {
                    'serper_timeout': constance_config.API_SERPER_TIMEOUT,
                    'rate_limit_per_minute': constance_config.API_RATE_LIMIT_PER_MINUTE,
                    'max_retries': constance_config.API_MAX_RETRIES,
                },
                'processing': {
                    'batch_size': constance_config.PROCESSING_BATCH_SIZE,
                    'cache_ttl': constance_config.PROCESSING_CACHE_TTL,
                    'duplicate_threshold': constance_config.PROCESSING_DUPLICATE_THRESHOLD,
                }
            }
            
            # Deep merge Constance overrides
            for key, value in constance_overrides.items():
                if key in config_dict:
                    config_dict[key].update(value)
                else:
                    config_dict[key] = value
                    
        except ImportError:
            logger.debug("Django Constance not available")
        except Exception as e:
            logger.debug(f"Could not load config from Constance: {e}")
        
        # Fallback: Load from database if exists
        try:
            from apps.core.models import Configuration
            db_config = Configuration.get_config("system_config")
            if db_config and isinstance(db_config, dict):
                # Merge database config with settings (DB takes precedence)
                for key, value in db_config.items():
                    if key in config_dict and isinstance(config_dict[key], dict):
                        config_dict[key].update(value)
                    else:
                        config_dict[key] = value
        except Exception as e:
            # Database might not be ready during migrations/initial setup
            logger.debug(f"Could not load config from database: {e}")
        
        # Create nested config objects
        return cls(**config_dict)
    
    def save_to_db(self) -> None:
        """
        Save current configuration to database.
        
        Raises:
            ImportError: If models are not available
            Exception: If save fails
        """
        try:
            from apps.core.models import Configuration
            
            # Convert to dict for storage
            config_data = self.model_dump()
            
            # Save or update configuration
            Configuration.set_config("system_config", config_data)
            logger.info("Configuration saved to database")
            
        except ImportError:
            logger.error("Cannot import Configuration model")
            raise
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise


# Singleton instance
_config_instance: Optional[SystemConfig] = None


def get_config() -> SystemConfig:
    """
    Get the system configuration singleton.
    
    Returns:
        SystemConfig: System configuration instance
    """
    global _config_instance
    
    if _config_instance is None:
        _config_instance = SystemConfig.load_from_settings()
        logger.info("Configuration loaded successfully")
    
    return _config_instance


def reload_config() -> SystemConfig:
    """
    Force reload of configuration from settings/database.
    
    Returns:
        SystemConfig: Newly loaded configuration
    """
    global _config_instance
    
    _config_instance = SystemConfig.load_from_settings()
    logger.info("Configuration reloaded")
    
    return _config_instance