#!/usr/bin/env python
"""
Validate query patterns in the optimized code.
This script checks that the code uses optimized query patterns without requiring a database connection.
"""

import os
import sys
import re
from pathlib import Path


class QueryPatternValidator:
    """Validate that query patterns use optimized denormalized fields."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.errors = []
        self.warnings = []
        self.successes = []
    
    def check_file_patterns(self, file_path: Path, expected_patterns: list, forbidden_patterns: list):
        """Check a file for expected and forbidden query patterns."""
        if not file_path.exists():
            self.errors.append(f"File not found: {file_path}")
            return
        
        content = file_path.read_text()
        
        # Check for expected patterns
        for pattern_name, pattern in expected_patterns:
            if re.search(pattern, content):
                self.successes.append(f"✅ {file_path.name}: Found expected pattern '{pattern_name}'")
            else:
                self.warnings.append(f"⚠️ {file_path.name}: Missing expected pattern '{pattern_name}'")
        
        # Check for forbidden patterns
        for pattern_name, pattern in forbidden_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            if matches:
                self.errors.append(f"❌ {file_path.name}: Found forbidden pattern '{pattern_name}': {matches}")
            else:
                self.successes.append(f"✅ {file_path.name}: No forbidden pattern '{pattern_name}'")
    
    def validate_result_analysis_service(self):
        """Validate SearchResultAnalysisService optimizations."""
        print("=== Validating SearchResultAnalysisService ===")
        
        file_path = self.project_root / "apps/reporting/services/result_analysis_service.py"
        
        expected_patterns = [
            ("optimized session_id filter", r"SimpleReviewDecision\.objects\.filter\(session_id=session_id\)"),
        ]
        
        forbidden_patterns = [
            ("old result__session_id pattern", r"result__session_id=session_id"),
        ]
        
        self.check_file_patterns(file_path, expected_patterns, forbidden_patterns)
    
    def validate_prisma_reporting_service(self):
        """Validate PrismaReportingService optimizations."""
        print("=== Validating PrismaReportingService ===")
        
        file_path = self.project_root / "apps/reporting/services/prisma_reporting_service.py"
        
        expected_patterns = [
            ("SimpleReviewDecision import", r"from apps\.review_results\.models import SimpleReviewDecision"),
            ("optimized exclusion query", r"SimpleReviewDecision\.objects\.filter\(\s*session_id=session_id"),
            ("decision exclude filter", r"decision=\"exclude\""),
        ]
        
        forbidden_patterns = [
            ("old ReviewTagAssignment", r"ReviewTagAssignment\.objects\.filter"),
            ("old result__session_id pattern", r"result__session_id=session_id"),
            ("old tag__name pattern", r"tag__name=PRISMAConstants\.EXCLUDE_TAG"),
        ]
        
        self.check_file_patterns(file_path, expected_patterns, forbidden_patterns)
    
    def validate_export_service(self):
        """Validate ExportService optimizations."""
        print("=== Validating ExportService ===")
        
        file_path = self.project_root / "apps/reporting/services/export_service.py"
        
        expected_patterns = [
            ("optimized include query", r"SimpleReviewDecision\.objects\.filter\(\s*session_id=session_id"),
            ("decision include filter", r"decision=\"include\""),
        ]
        
        forbidden_patterns = [
            ("old result__session_id pattern", r"result__session_id=session_id"),
            ("old tag__name pattern", r"tag__name=\"Include\""),
        ]
        
        self.check_file_patterns(file_path, expected_patterns, forbidden_patterns)
    
    def check_performance_analytics_unchanged(self):
        """Ensure performance analytics service was NOT changed (as intended)."""
        print("=== Validating PerformanceAnalyticsService (should be unchanged) ===")
        
        file_path = self.project_root / "apps/reporting/services/performance_analytics_service.py"
        
        # These patterns should still exist (we intentionally didn't change this file)
        expected_patterns = [
            ("still uses result__session_id", r"result__session_id=session_id"),
            ("still uses tag__name", r"tag__name=\"Include\""),
        ]
        
        forbidden_patterns = []  # No forbidden patterns for this file
        
        self.check_file_patterns(file_path, expected_patterns, forbidden_patterns)
    
    def validate_models_have_denormalized_fields(self):
        """Check that SimpleReviewDecision model has the denormalized session field."""
        print("=== Validating Model Denormalization ===")
        
        file_path = self.project_root / "apps/review_results/models.py"
        
        expected_patterns = [
            ("denormalized session field", r"session = models\.ForeignKey"),
            ("session help text", r"Denormalized session reference for performance"),
            ("exclusion_reason field", r"exclusion_reason = models\.CharField"),
            ("notes field", r"notes = models\.TextField"),
        ]
        
        forbidden_patterns = []
        
        self.check_file_patterns(file_path, expected_patterns, forbidden_patterns)
    
    def check_remaining_old_patterns(self):
        """Check for any remaining old query patterns in the codebase."""
        print("=== Checking for Remaining Old Patterns ===")
        
        # Search all Python files for old patterns
        for file_path in self.project_root.rglob("*.py"):
            # Skip files we don't want to check
            if any(skip in str(file_path) for skip in ["migrations", "venv", "__pycache__", "test_", "validate_"]):
                continue
            
            content = file_path.read_text()
            
            # Look for old patterns that should have been updated
            old_patterns = [
                r"SimpleReviewDecision\.objects\.filter\([^)]*result__session_id=",
                r"result__session_id=session_id[^,)]*tag__name=",
            ]
            
            for pattern in old_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    # Check if this is in a file we expect to still have these patterns
                    if "performance_analytics_service.py" in str(file_path):
                        self.successes.append(f"✅ {file_path.name}: Contains expected old pattern (monitoring query)")
                    else:
                        self.warnings.append(f"⚠️ {file_path.name}: Still contains old pattern: {matches}")
    
    def run_validation(self):
        """Run all validation checks."""
        print("🔍 Validating Query Pattern Optimizations")
        print("=" * 60)
        
        self.validate_result_analysis_service()
        self.validate_prisma_reporting_service()
        self.validate_export_service()
        self.check_performance_analytics_unchanged()
        self.validate_models_have_denormalized_fields()
        self.check_remaining_old_patterns()
        
        print("\n" + "=" * 60)
        print("📊 Validation Results")
        print("=" * 60)
        
        if self.successes:
            print(f"\n✅ Successes ({len(self.successes)}):")
            for success in self.successes:
                print(f"  {success}")
        
        if self.warnings:
            print(f"\n⚠️ Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  {warning}")
        
        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  {error}")
        
        print(f"\n📈 Summary: {len(self.successes)} successes, {len(self.warnings)} warnings, {len(self.errors)} errors")
        
        if self.errors:
            print("\n💥 Validation failed due to errors!")
            return False
        elif self.warnings:
            print("\n⚠️ Validation completed with warnings.")
            return True
        else:
            print("\n🎉 All validations passed!")
            return True


def main():
    """Main validation function."""
    validator = QueryPatternValidator()
    success = validator.run_validation()
    
    if success:
        print("\n🔥 Query pattern validation completed successfully!")
        if validator.warnings:
            print("Note: Some warnings were found but they may be expected.")
        sys.exit(0)
    else:
        print("\n💥 Query pattern validation failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()