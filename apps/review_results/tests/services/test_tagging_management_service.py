"""
Tests for TaggingManagementService.

Tests tag management, consistency, and analysis functionality.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.results_manager.models import ProcessedResult
from apps.review_manager.models import SearchSession
from apps.review_results.models import ReviewTag, ReviewTagAssignment
from apps.review_results.services.tagging_management_service import (
    TaggingManagementService,
)

User = get_user_model()


class TestTaggingManagementService(TestCase):
    """Test cases for TaggingManagementService."""

    def setUp(self):
        """Set up test data."""
        self.service = TaggingManagementService()

        # Create test users
        self.user1 = User.objects.create_user(
            username="reviewer1", email="reviewer1@example.com", password="testpass123"
        )

        self.user2 = User.objects.create_user(
            username="reviewer2", email="reviewer2@example.com", password="testpass123"
        )

        self.user3 = User.objects.create_user(
            username="reviewer3", email="reviewer3@example.com", password="testpass123"
        )

        # Create test session
        self.session = SearchSession.objects.create(
            title="Test Tagging Management",
            description="Testing tag management",
            owner=self.user1,
            status="under_review",
        )

        # Create tags
        self.tag_include = ReviewTag.objects.create(
            name="Include", description="Include in final review", color="#28a745"
        )
        self.tag_exclude = ReviewTag.objects.create(
            name="Exclude", description="Exclude from review", color="#dc3545"
        )
        self.tag_maybe = ReviewTag.objects.create(
            name="Maybe", description="Requires further review", color="#ffc107"
        )
        self.tag_high_quality = ReviewTag.objects.create(
            name="High Quality", description="High quality source", color="#17a2b8"
        )

        # Create test results
        self.results = []
        for i in range(25):
            result = ProcessedResult.objects.create(
                session=self.session,
                title=f"Result {i}: Research Study",
                url=f"https://journal.com/article/{i}",
                snippet=f"Abstract for research study {i}",
                is_pdf=i % 2 == 0,
                publication_year=2020 + (i % 5),
                document_type="journal_article" if i % 3 == 0 else "report",
            )
            self.results.append(result)

        # Create tag assignments with various patterns
        self._create_tag_assignments()

    def _create_tag_assignments(self):
        """Create tag assignments with patterns for testing."""
        # Single tags
        for i in range(10):
            tag = self.tag_include if i < 5 else self.tag_exclude
            ReviewTagAssignment.objects.create(
                result=self.results[i],
                tag=tag,
                assigned_by=self.user1,
                notes=f"Review note {i}",
            )

        # Multiple tags on same result
        for i in range(10, 15):
            ReviewTagAssignment.objects.create(
                result=self.results[i], tag=self.tag_include, assigned_by=self.user1
            )
            ReviewTagAssignment.objects.create(
                result=self.results[i],
                tag=self.tag_high_quality,
                assigned_by=self.user1,
            )

        # Multiple reviewers on same result
        for i in range(15, 20):
            # User 1 and 2 agree
            ReviewTagAssignment.objects.create(
                result=self.results[i], tag=self.tag_include, assigned_by=self.user1
            )
            ReviewTagAssignment.objects.create(
                result=self.results[i], tag=self.tag_include, assigned_by=self.user2
            )

            # User 3 disagrees on some
            if i > 17:
                ReviewTagAssignment.objects.create(
                    result=self.results[i], tag=self.tag_exclude, assigned_by=self.user3
                )

    def test_get_tag_usage_statistics(self):
        """Test calculation of tag usage statistics."""
        stats = self.service.get_tag_usage_statistics(str(self.session.id))

        self.assertIsInstance(stats, dict)
        self.assertIn("total_assignments", stats)
        self.assertIn("unique_results_tagged", stats)
        self.assertIn("tag_counts", stats)
        self.assertIn("tag_combinations", stats)
        self.assertIn("reviewer_tag_distribution", stats)

        # Check tag counts
        tag_counts = stats["tag_counts"]
        self.assertIn("Include", tag_counts)
        self.assertIn("Exclude", tag_counts)
        self.assertGreater(tag_counts["Include"], 0)

        # Check tag combinations
        combinations = stats["tag_combinations"]
        self.assertTrue(
            any("Include + High Quality" in combo for combo in combinations)
        )

    def test_get_tag_consistency_analysis(self):
        """Test analysis of tagging consistency between reviewers."""
        analysis = self.service.get_tag_consistency_analysis(str(self.session.id))

        self.assertIsInstance(analysis, dict)
        self.assertIn("inter_reviewer_agreement", analysis)
        self.assertIn("agreement_rate", analysis)
        self.assertIn("disagreement_details", analysis)
        self.assertIn("cohen_kappa", analysis)

        # Check agreement rate
        self.assertGreaterEqual(analysis["agreement_rate"], 0)
        self.assertLessEqual(analysis["agreement_rate"], 100)

        # Check disagreement details
        disagreements = analysis["disagreement_details"]
        self.assertIsInstance(disagreements, list)

        # Should find disagreements for results 18-19
        self.assertTrue(len(disagreements) > 0)

        for disagreement in disagreements:
            self.assertIn("result_id", disagreement)
            self.assertIn("reviewers", disagreement)
            self.assertIn("tags_assigned", disagreement)

    def test_manage_tag_hierarchy(self):
        """Test management of tag hierarchy and relationships."""
        # Create parent-child tag relationship
        parent_tag = ReviewTag.objects.create(
            name="Quality", description="Quality indicators"
        )

        self.tag_high_quality.parent = parent_tag
        self.tag_high_quality.save()

        hierarchy = self.service.manage_tag_hierarchy(str(self.session.id))

        self.assertIsInstance(hierarchy, dict)
        self.assertIn("root_tags", hierarchy)
        self.assertIn("tag_tree", hierarchy)
        self.assertIn("usage_by_level", hierarchy)

        # Check that hierarchy is properly structured
        self.assertIn("Quality", hierarchy["tag_tree"])
        self.assertIn("High Quality", hierarchy["tag_tree"]["Quality"]["children"])

    def test_bulk_tag_operations(self):
        """Test bulk tagging operations."""
        # Select untagged results
        untagged_ids = [str(r.id) for r in self.results[20:25]]

        # Bulk apply tags
        operation_result = self.service.bulk_apply_tags(
            result_ids=untagged_ids,
            tag_names=["Maybe"],
            user_id=self.user1.id,
            notes="Bulk tagged for review",
        )

        self.assertIsInstance(operation_result, dict)
        self.assertIn("success_count", operation_result)
        self.assertIn("failed_count", operation_result)
        self.assertIn("created_assignments", operation_result)

        self.assertEqual(operation_result["success_count"], 5)
        self.assertEqual(operation_result["failed_count"], 0)

        # Verify tags were applied
        for result_id in untagged_ids:
            assignment = ReviewTagAssignment.objects.filter(
                result_id=result_id, tag=self.tag_maybe
            ).first()
            self.assertIsNotNone(assignment)
            self.assertEqual(assignment.notes, "Bulk tagged for review")

    def test_tag_removal_operations(self):
        """Test tag removal and cleanup operations."""
        result = self.results[10]

        # Remove specific tag
        removal_result = self.service.remove_tag_assignment(
            result_id=str(result.id), tag_name="High Quality", user_id=self.user1.id
        )

        self.assertTrue(removal_result["success"])
        self.assertEqual(removal_result["removed_count"], 1)

        # Verify tag was removed
        remaining = ReviewTagAssignment.objects.filter(
            result=result, tag=self.tag_high_quality
        ).count()
        self.assertEqual(remaining, 0)

        # Include tag should still exist
        include_assignment = ReviewTagAssignment.objects.filter(
            result=result, tag=self.tag_include
        ).first()
        self.assertIsNotNone(include_assignment)

    def test_tag_conflict_detection(self):
        """Test detection of conflicting tags."""
        # Add conflicting tags to a result
        result = self.results[21]

        ReviewTagAssignment.objects.create(
            result=result, tag=self.tag_include, assigned_by=self.user1
        )

        ReviewTagAssignment.objects.create(
            result=result, tag=self.tag_exclude, assigned_by=self.user1
        )

        conflicts = self.service.detect_tag_conflicts(str(self.session.id))

        self.assertIsInstance(conflicts, list)
        self.assertTrue(len(conflicts) > 0)

        # Check conflict structure
        for conflict in conflicts:
            self.assertIn("result_id", conflict)
            self.assertIn("conflicting_tags", conflict)
            self.assertIn("severity", conflict)
            self.assertIn("resolution_suggestion", conflict)

        # Should detect Include/Exclude conflict
        result_conflict = next(
            c for c in conflicts if str(c["result_id"]) == str(result.id)
        )
        self.assertIn("Include", result_conflict["conflicting_tags"])
        self.assertIn("Exclude", result_conflict["conflicting_tags"])
        self.assertEqual(result_conflict["severity"], "high")

    def test_tag_history_tracking(self):
        """Test tracking of tag assignment history."""
        result = self.results[0]

        # Create multiple tag changes
        assignment = ReviewTagAssignment.objects.get(
            result=result, tag=self.tag_include
        )

        # Update notes multiple times
        for i in range(3):
            assignment.notes = f"Updated note version {i+1}"
            assignment.save()

        history = self.service.get_tag_history(str(result.id))

        self.assertIsInstance(history, list)
        self.assertTrue(len(history) > 0)

        # Check history entry structure
        for entry in history:
            self.assertIn("timestamp", entry)
            self.assertIn("user", entry)
            self.assertIn("action", entry)
            self.assertIn("tag", entry)
            self.assertIn("details", entry)

    def test_generate_tagging_report(self):
        """Test generation of comprehensive tagging report."""
        report = self.service.generate_tagging_report(str(self.session.id))

        self.assertIsInstance(report, dict)
        self.assertIn("summary", report)
        self.assertIn("tag_distribution", report)
        self.assertIn("reviewer_performance", report)
        self.assertIn("consistency_metrics", report)
        self.assertIn("recommendations", report)

        # Check summary
        summary = report["summary"]
        self.assertIn("total_results", summary)
        self.assertIn("tagged_results", summary)
        self.assertIn("tagging_completion", summary)
        self.assertIn("active_reviewers", summary)

        # Check recommendations
        recommendations = report["recommendations"]
        self.assertIsInstance(recommendations, list)

    def test_tag_export_import(self):
        """Test export and import of tag data."""
        # Export tags
        export_data = self.service.export_tag_data(str(self.session.id))

        self.assertIsInstance(export_data, dict)
        self.assertIn("tags", export_data)
        self.assertIn("assignments", export_data)
        self.assertIn("metadata", export_data)

        # Check export format
        self.assertEqual(len(export_data["tags"]), 4)  # All tags used
        self.assertTrue(len(export_data["assignments"]) > 0)

        # Test import to new session
        new_session = SearchSession.objects.create(
            title="Import Test Session",
            description="Testing tag import",
            owner=self.user1,
            status="under_review",
        )

        import_result = self.service.import_tag_data(
            str(new_session.id),
            export_data,
            map_results=False,  # Don't map to actual results for test
        )

        self.assertTrue(import_result["success"])
        self.assertIn("imported_tags", import_result)
        self.assertIn("imported_assignments", import_result)

    def test_tag_recommendation_rules(self):
        """Test tag recommendation based on rules."""
        # Define rules
        rules = [
            {
                "condition": "relevance_score > 0.8",
                "recommended_tags": ["Include", "High Quality"],
            },
            {
                "condition": 'document_type == "blog_post"',
                "recommended_tags": ["Exclude"],
            },
        ]

        # Test with high relevance result
        high_relevance_result = self.results[20]
        high_relevance_result.is_pdf = True
        high_relevance_result.publication_year = 2024
        high_relevance_result.save()

        recommendations = self.service.apply_tag_recommendation_rules(
            str(high_relevance_result.id), rules
        )

        self.assertIsInstance(recommendations, list)
        self.assertIn("Include", recommendations)
        self.assertIn("High Quality", recommendations)

    def test_tag_usage_trends(self):
        """Test analysis of tag usage trends over time."""
        # Add time-distributed tag assignments
        base_time = timezone.now() - timedelta(days=7)

        for day in range(7):
            for i in range(3):
                result_idx = 20 + (day * 3) + i
                if result_idx < len(self.results):
                    assignment = ReviewTagAssignment.objects.create(
                        result=self.results[result_idx],
                        tag=self.tag_include if day < 4 else self.tag_exclude,
                        assigned_by=self.user1,
                        created_at=base_time + timedelta(days=day),
                    )
                    # Update created_at
                    assignment.created_at = base_time + timedelta(days=day)
                    assignment.save()

        trends = self.service.analyze_tag_usage_trends(str(self.session.id), days=7)

        self.assertIsInstance(trends, dict)
        self.assertIn("daily_tag_counts", trends)
        self.assertIn("tag_velocity", trends)
        self.assertIn("trend_direction", trends)
        self.assertIn("peak_tagging_times", trends)

    def test_custom_tag_creation(self):
        """Test creation and management of custom tags."""
        # Create custom tag
        custom_tag_data = {
            "name": "Methodology Issue",
            "description": "Issues with research methodology",
            "color": "#6c757d",
            "category": "quality",
            "allow_multiple": True,
        }

        new_tag = self.service.create_custom_tag(
            tag_data=custom_tag_data, created_by=self.user1.id
        )

        self.assertIsInstance(new_tag, ReviewTag)
        self.assertEqual(new_tag.name, "Methodology Issue")

        # Test tag validation
        invalid_tag_data = {
            "name": "Include",  # Duplicate name
            "description": "Another include tag",
        }

        with self.assertRaises(ValueError):
            self.service.create_custom_tag(invalid_tag_data, self.user1.id)

    def test_tag_merge_operations(self):
        """Test merging of similar tags."""
        # Create similar tags
        tag1 = ReviewTag.objects.create(name="Low Quality")
        tag2 = ReviewTag.objects.create(name="Poor Quality")

        # Assign to different results
        ReviewTagAssignment.objects.create(
            result=self.results[22], tag=tag1, assigned_by=self.user1
        )

        ReviewTagAssignment.objects.create(
            result=self.results[23], tag=tag2, assigned_by=self.user1
        )

        # Merge tags
        merge_result = self.service.merge_tags(
            source_tag_id=tag2.id, target_tag_id=tag1.id, delete_source=True
        )

        self.assertTrue(merge_result["success"])
        self.assertEqual(merge_result["assignments_migrated"], 1)

        # Verify merge
        self.assertFalse(ReviewTag.objects.filter(id=tag2.id).exists())
        assignments = ReviewTagAssignment.objects.filter(tag=tag1).count()
        self.assertEqual(assignments, 2)

    def test_logging_in_tagging(self):
        """Test that tagging operations are properly logged."""
        with self.assertLogs(
            "apps.review_results.services.tagging_management_service", level="INFO"
        ) as cm:
            self.service.get_tag_usage_statistics(str(self.session.id))

        self.assertTrue(
            any("Calculating tag usage statistics" in msg for msg in cm.output)
        )
        self.assertTrue(any("Tag statistics calculated" in msg for msg in cm.output))
