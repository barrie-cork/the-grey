# Generated manually for SearchStrategy model

import uuid

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("review_manager", "0001_initial"),
        ("accounts", "0002_user_created_at_user_updated_at_alter_user_email_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="SearchStrategy",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "population_terms",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=200),
                        blank=True,
                        default=list,
                        help_text="Terms describing the population (e.g., 'elderly', 'children with autism')",
                        size=None,
                    ),
                ),
                (
                    "interest_terms",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=200),
                        blank=True,
                        default=list,
                        help_text="Terms describing the intervention/interest (e.g., 'telehealth', 'cognitive therapy')",
                        size=None,
                    ),
                ),
                (
                    "context_terms",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=200),
                        blank=True,
                        default=list,
                        help_text="Terms describing the context/setting (e.g., 'rural', 'low-income countries')",
                        size=None,
                    ),
                ),
                (
                    "search_config",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Configuration for domains, file types, and search parameters",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_complete", models.BooleanField(default=False)),
                ("validation_errors", models.JSONField(blank=True, default=dict)),
                (
                    "session",
                    models.OneToOneField(
                        on_delete=models.deletion.CASCADE,
                        related_name="search_strategy",
                        to="review_manager.searchsession",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="search_strategies",
                        to="accounts.user",
                    ),
                ),
            ],
            options={
                "verbose_name": "Search Strategy",
                "verbose_name_plural": "Search Strategies",
                "db_table": "search_strategies",
            },
        ),
        migrations.CreateModel(
            name="SearchQuery",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "query_text",
                    models.TextField(help_text="The complete search query string"),
                ),
                (
                    "query_type",
                    models.CharField(
                        choices=[
                            ("domain-specific", "Domain Specific"),
                            ("general", "General Search"),
                        ],
                        max_length=50,
                    ),
                ),
                (
                    "target_domain",
                    models.CharField(
                        blank=True,
                        help_text="Domain for site-specific searches",
                        max_length=200,
                        null=True,
                    ),
                ),
                ("execution_order", models.IntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("estimated_results", models.IntegerField(default=0)),
                (
                    "strategy",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="search_queries",
                        to="search_strategy.searchstrategy",
                    ),
                ),
            ],
            options={
                "verbose_name": "Search Query",
                "verbose_name_plural": "Search Queries",
                "db_table": "search_queries",
            },
        ),
        migrations.CreateModel(
            name="QueryTemplate",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "name",
                    models.CharField(help_text="Name of the template", max_length=255),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True, help_text="Description of when to use this template"
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        blank=True,
                        help_text="Category for organizing templates",
                        max_length=100,
                    ),
                ),
                (
                    "is_public",
                    models.BooleanField(
                        default=False,
                        help_text="Whether this template is available to all users",
                    ),
                ),
                (
                    "population_template",
                    models.TextField(
                        blank=True,
                        help_text="Population template with placeholders (e.g., '{age_group} with {condition}')",
                    ),
                ),
                (
                    "interest_template",
                    models.TextField(
                        blank=True, help_text="Interest/Intervention template"
                    ),
                ),
                (
                    "context_template",
                    models.TextField(blank=True, help_text="Context template"),
                ),
                (
                    "default_keywords",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Default keywords to include",
                    ),
                ),
                (
                    "default_exclusions",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="Default keywords to exclude",
                    ),
                ),
                (
                    "default_engines",
                    models.JSONField(
                        blank=True, default=list, help_text="Default search engines"
                    ),
                ),
                (
                    "usage_count",
                    models.IntegerField(
                        default=0,
                        help_text="Number of times this template has been used",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        help_text="User who created this template",
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        related_name="query_templates",
                        to="accounts.user",
                    ),
                ),
            ],
            options={
                "db_table": "query_templates",
            },
        ),
    ]
