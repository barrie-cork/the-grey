"""
Core models for configuration and shared functionality.
"""

from django.db import models
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import json
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class Configuration(models.Model):
    """
    Runtime editable configuration stored in database.
    Allows for dynamic configuration changes without code deployment.
    """
    
    key = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique configuration key"
    )
    value = models.JSONField(
        encoder=DjangoJSONEncoder,
        help_text="Configuration value (JSON format)"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of what this configuration controls"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last update timestamp"
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='configuration_changes',
        help_text="User who last updated this configuration"
    )
    
    class Meta:
        db_table = 'core_configuration'
        ordering = ['key']
        verbose_name = "Configuration"
        verbose_name_plural = "Configurations"
    
    def __str__(self):
        return f"{self.key}: {self.get_value_preview()}"
    
    def get_value_preview(self, max_length=50):
        """Get a preview of the value for display purposes."""
        value_str = json.dumps(self.value)
        if len(value_str) > max_length:
            return f"{value_str[:max_length]}..."
        return value_str
    
    def clean(self):
        """Validate the configuration value."""
        if not isinstance(self.value, (dict, list, str, int, float, bool, type(None))):
            raise ValidationError({
                'value': 'Configuration value must be JSON-serializable'
            })
    
    @classmethod
    def get_config(cls, key: str, default=None):
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        try:
            config = cls.objects.get(key=key)
            return config.value
        except cls.DoesNotExist:
            logger.debug(f"Configuration key '{key}' not found, using default")
            return default
    
    @classmethod
    def set_config(cls, key: str, value, description: str = "", user=None):
        """
        Set configuration value by key.
        
        Args:
            key: Configuration key
            value: Configuration value (must be JSON-serializable)
            description: Optional description
            user: User making the change
            
        Returns:
            Configuration: The created/updated configuration
        """
        config, created = cls.objects.update_or_create(
            key=key,
            defaults={
                'value': value,
                'description': description,
                'updated_by': user
            }
        )
        
        action = "created" if created else "updated"
        logger.info(f"Configuration '{key}' {action}")
        
        return config
    
    @classmethod
    def delete_config(cls, key: str):
        """
        Delete configuration by key.
        
        Args:
            key: Configuration key to delete
            
        Returns:
            bool: True if deleted, False if not found
        """
        try:
            config = cls.objects.get(key=key)
            config.delete()
            logger.info(f"Configuration '{key}' deleted")
            return True
        except cls.DoesNotExist:
            logger.warning(f"Configuration '{key}' not found for deletion")
            return False
    
    @classmethod
    def list_configs(cls):
        """
        List all configurations.
        
        Returns:
            QuerySet: All configuration objects
        """
        return cls.objects.all()
    
    @classmethod
    def bulk_update(cls, configs: dict, user=None):
        """
        Bulk update multiple configurations.
        
        Args:
            configs: Dict of {key: value} pairs
            user: User making the changes
            
        Returns:
            tuple: (created_count, updated_count)
        """
        created_count = 0
        updated_count = 0
        
        for key, value in configs.items():
            config, created = cls.objects.update_or_create(
                key=key,
                defaults={
                    'value': value,
                    'updated_by': user
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        logger.info(f"Bulk config update: {created_count} created, {updated_count} updated")
        return created_count, updated_count