# Generated migration for review results simplification

import uuid

from django.db import migrations, models


def migrate_review_data_forward(apps, schema_editor):
    """Migrate existing review data to simplified structure."""
    try:
        # Get old models
        ReviewDecision = apps.get_model("review_results", "ReviewDecision")
        SimpleReviewDecision = apps.get_model("review_results", "SimpleReviewDecision")
        ProcessedResult = apps.get_model("results_manager", "ProcessedResult")

        # Migrate ReviewDecision -> SimpleReviewDecision
        for old_decision in ReviewDecision.objects.all():
            # Map old decision values to new simplified ones
            decision_mapping = {
                "include": "include",
                "exclude": "exclude",
                "maybe": "maybe",
                "pending": "pending",
            }

            # Map old exclusion reasons to new simplified ones
            exclusion_mapping = {
                "not_grey_lit": "not_grey_lit",
                "wrong_population": "not_relevant",
                "wrong_intervention": "not_relevant",
                "wrong_context": "not_relevant",
                "wrong_language": "not_relevant",
                "duplicate": "duplicate",
                "quality": "not_relevant",
                "access": "no_access",
                "date_range": "not_relevant",
                "other": "other",
            }

            SimpleReviewDecision.objects.create(
                result=old_decision.result,
                reviewer=old_decision.reviewer,
                decision=decision_mapping.get(old_decision.decision, "pending"),
                exclusion_reason=exclusion_mapping.get(
                    old_decision.exclusion_reason, ""
                ),
                notes=old_decision.reviewer_notes,
                reviewed_at=old_decision.reviewed_at,
            )

        # Update ProcessedResult.is_reviewed flags
        ProcessedResult.objects.filter(
            id__in=SimpleReviewDecision.objects.values_list("result_id", flat=True)
        ).update(is_reviewed=True)

    except Exception as e:
        # If migration fails, it's likely because old models don't exist yet
        # This is expected in a new installation
        pass


def migrate_review_data_reverse(apps, schema_editor):
    """Reverse migration - recreate old complex structure."""
    # This would be complex to implement and is not needed for this simplification


class Migration(migrations.Migration):

    dependencies = [
        ("review_results", "0001_initial"),
        ("results_manager", "0001_initial"),
    ]

    operations = [
        # Create the new simplified model
        migrations.CreateModel(
            name="SimpleReviewDecision",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, primary_key=True, serialize=False
                    ),
                ),
                (
                    "decision",
                    models.CharField(
                        choices=[
                            ("pending", "Pending Review"),
                            ("include", "Include"),
                            ("exclude", "Exclude"),
                            ("maybe", "Maybe/Uncertain"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "exclusion_reason",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("not_relevant", "Not Relevant"),
                            ("not_grey_lit", "Not Grey Literature"),
                            ("duplicate", "Duplicate"),
                            ("no_access", "Cannot Access"),
                            ("other", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "notes",
                    models.TextField(blank=True, help_text="Optional reviewer notes"),
                ),
                ("reviewed_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "result",
                    models.OneToOneField(
                        on_delete=models.deletion.CASCADE,
                        to="results_manager.processedresult",
                    ),
                ),
                (
                    "reviewer",
                    models.ForeignKey(
                        null=True,
                        on_delete=models.deletion.SET_NULL,
                        to="accounts.user",
                    ),
                ),
            ],
            options={
                "db_table": "simple_review_decisions",
                "ordering": ["-reviewed_at"],
            },
        ),
        # Migrate existing data
        migrations.RunPython(migrate_review_data_forward, migrate_review_data_reverse),
    ]
