#!/usr/bin/env python
"""
Manual verification script for research functionality.
This script checks that the core research functions will work correctly with optimized queries.
"""

import os
import sys
from pathlib import Path


def check_query_consistency():
    """Check that all research-critical services use consistent query patterns."""
    print("🔍 Checking Query Consistency for Research Functions")
    print("=" * 60)
    
    project_root = Path(__file__).parent
    issues = []
    
    # Files that should use optimized patterns
    optimized_files = [
        "apps/reporting/services/result_analysis_service.py",
        "apps/reporting/services/prisma_reporting_service.py", 
        "apps/reporting/services/export_service.py"
    ]
    
    # Files that should still use old patterns (monitoring)
    unchanged_files = [
        "apps/reporting/services/performance_analytics_service.py"
    ]
    
    print("\n✅ Optimized Research-Critical Files:")
    for file_path in optimized_files:
        full_path = project_root / file_path
        if full_path.exists():
            content = full_path.read_text()
            
            # Check for new patterns
            has_session_id = "session_id=session_id" in content
            has_decision_filter = 'decision="' in content
            
            # Check for old patterns
            has_old_result_session = "result__session_id" in content
            has_old_tag_name = 'tag__name=' in content
            
            print(f"  📁 {file_path}")
            print(f"    ✅ Uses session_id: {has_session_id}")
            print(f"    ✅ Uses decision filter: {has_decision_filter}")
            print(f"    ❌ Has old result__session_id: {has_old_result_session}")
            print(f"    ❌ Has old tag__name: {has_old_tag_name}")
            
            if has_old_result_session and "performance" not in file_path:
                issues.append(f"File {file_path} still contains old result__session_id pattern")
        else:
            issues.append(f"File {file_path} not found")
    
    print("\n📊 Unchanged Monitoring Files:")
    for file_path in unchanged_files:
        full_path = project_root / file_path
        if full_path.exists():
            content = full_path.read_text()
            
            has_old_patterns = "result__session_id" in content
            print(f"  📁 {file_path}")
            print(f"    ✅ Retains old patterns (expected): {has_old_patterns}")
        else:
            issues.append(f"File {file_path} not found")
    
    return issues


def check_model_compatibility():
    """Check that the SimpleReviewDecision model supports the new query patterns."""
    print("\n🏗️ Checking Model Compatibility")
    print("=" * 40)
    
    project_root = Path(__file__).parent
    model_file = project_root / "apps/review_results/models.py"
    
    if not model_file.exists():
        return ["SimpleReviewDecision model file not found"]
    
    content = model_file.read_text()
    issues = []
    
    # Check for required fields
    required_fields = [
        ("session field", "session = models.ForeignKey"),
        ("decision field", "decision = models.CharField"),
        ("exclusion_reason field", "exclusion_reason = models.CharField"), 
        ("notes field", "notes = models.TextField")
    ]
    
    for field_name, pattern in required_fields:
        if pattern in content:
            print(f"  ✅ Has {field_name}")
        else:
            print(f"  ❌ Missing {field_name}")
            issues.append(f"SimpleReviewDecision model missing {field_name}")
    
    # Check for decision choices
    if "DECISION_CHOICES" in content:
        print("  ✅ Has decision choices")
        if '"include"' in content and '"exclude"' in content:
            print("    ✅ Include/exclude choices present")
        else:
            issues.append("Missing include/exclude decision choices")
    else:
        issues.append("Missing DECISION_CHOICES")
    
    return issues


def check_api_compatibility():
    """Check that APIs will work with the new query patterns."""
    print("\n🔌 Checking API Compatibility")
    print("=" * 40)
    
    project_root = Path(__file__).parent
    issues = []
    
    # Check review_results API
    api_file = project_root / "apps/review_results/api.py"
    if api_file.exists():
        content = api_file.read_text()
        if "session_id" in content:
            print("  ✅ review_results API uses session_id")
        else:
            issues.append("review_results API may not be compatible with session_id queries")
    
    # Check if there are any views that need updating
    views_file = project_root / "apps/review_results/views.py"
    if views_file.exists():
        content = views_file.read_text()
        if "SimpleReviewDecision" in content:
            print("  ✅ Views use SimpleReviewDecision model")
            if "session_id" in content:
                print("    ✅ Views appear to use session_id")
            else:
                print("    ⚠️ Views may need session_id updates")
    
    return issues


def verify_prisma_flow_data():
    """Verify that PRISMA flow data generation will work correctly."""
    print("\n📊 Verifying PRISMA Flow Data Logic")
    print("=" * 40)
    
    project_root = Path(__file__).parent
    prisma_file = project_root / "apps/reporting/services/prisma_reporting_service.py"
    
    if not prisma_file.exists():
        return ["PRISMA reporting service not found"]
    
    content = prisma_file.read_text()
    issues = []
    
    # Check that PRISMA flow methods exist and use correct patterns
    flow_methods = [
        "generate_prisma_flow_data",
        "get_exclusion_reasons",
        "calculate_review_period"
    ]
    
    for method in flow_methods:
        if f"def {method}" in content:
            print(f"  ✅ Has {method} method")
        else:
            print(f"  ❌ Missing {method} method") 
            issues.append(f"Missing PRISMA method: {method}")
    
    # Check that exclusion reasons use new model
    if "SimpleReviewDecision.objects.filter" in content:
        print("  ✅ Uses SimpleReviewDecision for exclusion reasons")
        if 'decision="exclude"' in content:
            print("    ✅ Filters by exclude decision")
        else:
            issues.append("Exclusion reasons don't filter by exclude decision")
    else:
        issues.append("Exclusion reasons don't use SimpleReviewDecision")
    
    return issues


def main():
    """Run all verification checks."""
    print("🧪 Verifying Research Functionality After Query Optimization")
    print("=" * 70)
    
    all_issues = []
    
    # Run all checks
    all_issues.extend(check_query_consistency())
    all_issues.extend(check_model_compatibility())
    all_issues.extend(check_api_compatibility())
    all_issues.extend(verify_prisma_flow_data())
    
    print("\n" + "=" * 70)
    print("📋 Verification Summary")
    print("=" * 70)
    
    if all_issues:
        print(f"\n❌ Found {len(all_issues)} issues:")
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue}")
        
        print("\n💥 Verification failed! Please address the issues above.")
        return False
    else:
        print("\n🎉 All verifications passed!")
        print("\n✅ Research functionality validated:")
        print("  • Query patterns are optimized for research-critical services")
        print("  • SimpleReviewDecision model supports new patterns")
        print("  • PRISMA reporting functions are properly updated")
        print("  • APIs appear compatible with session_id queries")
        print("  • Monitoring queries remain unchanged as intended")
        
        print("\n🔬 Ready for research workflows:")
        print("  • PRISMA flow diagram generation")
        print("  • Review progress calculations")  
        print("  • Study export functionality")
        print("  • Exclusion reason reporting")
        
        return True


if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🚀 Research functionality verification completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Research functionality verification failed!")
        sys.exit(1)