import uuid
from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models

User = get_user_model()


class SimpleReviewDecision(models.Model):
    """Simple Include/Exclude decision with optional notes."""

    DECISION_CHOICES = [
        ("pending", "Pending Review"),
        ("include", "Include"),
        ("exclude", "Exclude"),
        ("maybe", "Maybe/Uncertain"),
    ]

    EXCLUSION_REASONS = [
        ("not_relevant", "Not Relevant"),
        ("not_grey_lit", "Not Grey Literature"),
        ("duplicate", "Duplicate"),
        ("no_access", "Cannot Access"),
        ("other", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    result = models.OneToOneField(
        "results_manager.ProcessedResult", on_delete=models.CASCADE
    )
    # Denormalized for performance - direct reference to session
    session = models.ForeignKey(
        "review_manager.SearchSession",
        on_delete=models.CASCADE,
        related_name="review_decisions_denorm",
        help_text="Denormalized session reference for performance",
    )
    reviewer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    decision = models.CharField(
        max_length=20, choices=DECISION_CHOICES, default="pending"
    )
    exclusion_reason = models.CharField(
        max_length=20, choices=EXCLUSION_REASONS, blank=True
    )
    notes = models.TextField(blank=True, help_text="Optional reviewer notes")

    reviewed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "simple_review_decisions"
        ordering = ["-reviewed_at"]

    def __str__(self) -> str:
        return f"{self.get_decision_display()} - {self.result.title[:50]}..."

    def clean(self) -> None:
        """Validate exclusion reason is provided when excluding."""
        if self.decision == "exclude" and not self.exclusion_reason:
            raise ValidationError(
                "Exclusion reason is required when excluding a result"
            )

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Update result review status."""
        self.full_clean()
        super().save(*args, **kwargs)

        # Update the processed result's review status
        if self.result:
            self.result.is_reviewed = self.decision != "pending"
            self.result.save(update_fields=["is_reviewed"])
