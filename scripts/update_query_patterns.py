#!/usr/bin/env python3
"""
Script to systematically update query patterns to use denormalized session fields.
This script identifies and updates the most common problematic query patterns.
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add the Django project to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

# Query pattern mappings: (old_pattern, new_pattern, description)
QUERY_PATTERNS = [
    # RawSearchResult patterns
    (
        r'RawSearchResult\.objects\.filter\(execution__query__strategy__session_id=([^)]+)\)',
        r'RawSearchResult.objects.filter(session_id=\1)',
        'RawSearchResult session query simplification'
    ),
    (
        r'RawSearchResult\.objects\.filter\(execution__query__strategy__session=([^)]+)\)',
        r'RawSearchResult.objects.filter(session=\1)',
        'RawSearchResult session object query simplification'
    ),
    
    # SearchExecution patterns  
    (
        r'SearchExecution\.objects\.filter\(query__strategy__session_id=([^)]+)\)',
        r'SearchExecution.objects.filter(session_id=\1)',
        'SearchExecution session query simplification'
    ),
    (
        r'SearchExecution\.objects\.filter\(query__strategy__session=([^)]+)\)',
        r'SearchExecution.objects.filter(session=\1)',
        'SearchExecution session object query simplification'
    ),
    
    # SearchQuery patterns
    (
        r'SearchQuery\.objects\.filter\(strategy__session_id=([^)]+)\)',
        r'SearchQuery.objects.filter(session_id=\1)',
        'SearchQuery session query simplification'
    ),
    (
        r'SearchQuery\.objects\.filter\(strategy__session=([^)]+)\)',
        r'SearchQuery.objects.filter(session=\1)',
        'SearchQuery session object query simplification'
    ),
    
    # SimpleReviewDecision patterns
    (
        r'SimpleReviewDecision\.objects\.filter\(result__session_id=([^)]+)\)',
        r'SimpleReviewDecision.objects.filter(session_id=\1)',
        'SimpleReviewDecision session query simplification'
    ),
    (
        r'SimpleReviewDecision\.objects\.filter\(result__session=([^)]+)\)',
        r'SimpleReviewDecision.objects.filter(session=\1)',
        'SimpleReviewDecision session object query simplification'
    ),
]

# Files to exclude from automatic updates
EXCLUDE_FILES = [
    'migrations/',
    '__pycache__/',
    '.git/',
    'venv/',
    'node_modules/',
    '.pyc',
    'test_',  # Test files might need manual review
]

def should_exclude_file(file_path: str) -> bool:
    """Check if file should be excluded from updates."""
    return any(exclude in file_path for exclude in EXCLUDE_FILES)

def find_python_files(directory: Path) -> List[Path]:
    """Find all Python files in directory and subdirectories."""
    python_files = []
    for file_path in directory.rglob("*.py"):
        if not should_exclude_file(str(file_path)):
            python_files.append(file_path)
    return python_files

def update_file_patterns(file_path: Path) -> Tuple[int, List[str]]:
    """Update query patterns in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        updates_made = []
        
        # Apply each pattern replacement
        for old_pattern, new_pattern, description in QUERY_PATTERNS:
            if re.search(old_pattern, content):
                content = re.sub(old_pattern, new_pattern, content)
                updates_made.append(description)
        
        # Write back if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return len(updates_made), updates_made
        
        return 0, []
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return 0, []

def main():
    """Main function to update query patterns across the codebase."""
    print("🔄 Starting query pattern updates...")
    print("=" * 60)
    
    # Find all Python files in the apps directory
    apps_dir = PROJECT_ROOT / "apps"
    if not apps_dir.exists():
        print(f"❌ Apps directory not found: {apps_dir}")
        return
    
    python_files = find_python_files(apps_dir)
    print(f"📁 Found {len(python_files)} Python files to process")
    
    total_files_updated = 0
    total_patterns_updated = 0
    update_summary = {}
    
    # Process each file
    for file_path in python_files:
        updates_count, updates_made = update_file_patterns(file_path)
        
        if updates_count > 0:
            total_files_updated += 1
            total_patterns_updated += updates_count
            relative_path = file_path.relative_to(PROJECT_ROOT)
            update_summary[str(relative_path)] = updates_made
            print(f"✅ Updated {relative_path}: {updates_count} patterns")
            for update in updates_made:
                print(f"   - {update}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 UPDATE SUMMARY")
    print("=" * 60)
    print(f"Files processed: {len(python_files)}")
    print(f"Files updated: {total_files_updated}")
    print(f"Total patterns updated: {total_patterns_updated}")
    
    if update_summary:
        print("\n🔍 DETAILED CHANGES:")
        for file_path, updates in update_summary.items():
            print(f"\n📄 {file_path}:")
            for update in updates:
                print(f"   ✓ {update}")
    
    if total_files_updated == 0:
        print("\n✨ No files needed updates - patterns are already optimized!")
    else:
        print(f"\n🎉 Successfully updated {total_files_updated} files!")
        print("\n⚠️  NEXT STEPS:")
        print("1. Review the changes in git diff")
        print("2. Run tests to ensure functionality")
        print("3. Update any remaining manual patterns")
        print("4. Run database migrations")

if __name__ == "__main__":
    main()