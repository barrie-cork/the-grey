# Systematic Code Quality Improvement Approach

## Overview
This document provides a systematic approach to proactively identify and fix code quality issues based on patterns discovered during the results_manager refactoring.

## Phase 1: Discovery and Analysis

### 1.1 Field and Model Analysis
```bash
# Find all JSONField usage (often over-engineered)
grep -r "models.JSONField" apps/ --include="*.py" | grep -v migrations

# Find all FloatField that might be computed scores
grep -r "models.FloatField" apps/ --include="*.py" | grep -v migrations | grep -i "score\|rating\|quality"

# Find complex model Meta options
grep -r "class Meta:" apps/ -A 10 --include="*.py" | grep -i "ordering.*-" | grep -i "score\|relevance"

# Find models with many fields (potential for simplification)
for file in $(find apps/ -name "models.py" | grep -v migrations); do
    echo "=== $file ==="
    grep -c "models\." "$file" | xargs -I {} echo "Field count: {}"
done
```

### 1.2 Import Analysis
```bash
# Find unused typing imports
echo "=== Files with typing imports ==="
grep -l "from typing import" apps/**/*.py | while read file; do
    echo "\nChecking $file:"
    # Extract typing imports
    typing_imports=$(grep "from typing import" "$file" | sed 's/from typing import //;s/,/ /g')
    # Check each import
    for import in $typing_imports; do
        # Look for usage (accounting for List[, Dict[, etc.)
        count=$(grep -c "${import}\[" "$file" || echo 0)
        if [ "$count" -eq 0 ]; then
            echo "  - Unused: $import"
        fi
    done
done

# Find potentially unused Django imports
grep -r "from django.shortcuts import render" apps/ --include="*.py" | while IFS=: read -r file line; do
    if ! grep -q "render(" "$file"; then
        echo "Unused render import in: $file"
    fi
done

# Find all import statements and count usage
find apps/ -name "*.py" -type f | xargs -I {} sh -c '
    echo "=== {} ==="
    grep "^import \|^from .* import" {} | wc -l | xargs -I COUNT echo "Total imports: COUNT"
'
```

### 1.3 Service Method Analysis
```bash
# Find deprecated methods
grep -r "@deprecated\|DEPRECATED\|warnings.warn" apps/ --include="*.py"

# Find methods with "calculate_" prefix (often complex algorithms)
grep -r "def calculate_" apps/ --include="*.py" | grep -v test

# Find service classes with many methods
for file in $(find apps/ -path "*/services/*.py" -type f); do
    method_count=$(grep -c "def " "$file" 2>/dev/null || echo 0)
    if [ "$method_count" -gt 10 ]; then
        echo "$file has $method_count methods"
    fi
done
```

### 1.4 SQL and Query Analysis
```bash
# Find complex extra() queries
grep -r "\.extra(" apps/ --include="*.py" | grep -v migrations

# Find raw SQL
grep -r "raw(" apps/ --include="*.py"
grep -r "cursor.execute" apps/ --include="*.py"

# Find complex Q objects
grep -r "from django.db.models import Q" apps/ --include="*.py" -A 20 | grep -E "Q\(.*\) [&|] Q\("

# Find potential N+1 queries (missing select_related/prefetch_related)
grep -r "\.objects\.filter\|\.objects\.all\|\.objects\.get" apps/ --include="*.py" | grep -v "select_related\|prefetch_related" | head -20
```

### 1.5 Template and Static File Analysis
```bash
# Find template variables that might reference removed fields
grep -r "relevance_score\|quality_indicators\|quality_score" templates/ --include="*.html"

# Find hardcoded years
grep -r "202[0-9]" apps/ templates/ --include="*.py" --include="*.html" | grep -v migration

# Find commented-out template code
grep -r "{#\|<!--" templates/ --include="*.html" | grep -v "DOCTYPE"
```

## Phase 2: Pattern-Based Detection

### 2.1 Create Detection Scripts

```python
#!/usr/bin/env python3
"""
code_quality_detector.py
Detects common code quality issues based on patterns
"""

import ast
import os
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple

class CodeQualityDetector:
    def __init__(self, root_dir: str = "apps/"):
        self.root_dir = Path(root_dir)
        self.issues = []
        
    def scan_all(self):
        """Run all detection methods"""
        for py_file in self.root_dir.rglob("*.py"):
            if "migrations" not in str(py_file):
                self.scan_file(py_file)
        return self.issues
    
    def scan_file(self, filepath: Path):
        """Scan a single Python file for issues"""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
                tree = ast.parse(content)
                
            # Run detectors
            self.detect_unused_imports(tree, filepath, content)
            self.detect_complex_methods(tree, filepath)
            self.detect_json_fields(content, filepath)
            self.detect_deprecated_patterns(content, filepath)
            self.detect_complex_queries(content, filepath)
            
        except Exception as e:
            print(f"Error scanning {filepath}: {e}")
    
    def detect_unused_imports(self, tree: ast.AST, filepath: Path, content: str):
        """Detect potentially unused imports"""
        imports = []
        
        # Collect all imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.append(alias.name)
        
        # Check usage
        for import_name in imports:
            # Simple check - can be improved
            if content.count(import_name) == 1:  # Only in import statement
                self.issues.append({
                    'file': str(filepath),
                    'type': 'unused_import',
                    'description': f'Potentially unused import: {import_name}'
                })
    
    def detect_complex_methods(self, tree: ast.AST, filepath: Path):
        """Detect overly complex methods"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Count complexity indicators
                complexity = 0
                for child in ast.walk(node):
                    if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                        complexity += 1
                
                if complexity > 10:
                    self.issues.append({
                        'file': str(filepath),
                        'type': 'complex_method',
                        'description': f'Complex method: {node.name} (complexity: {complexity})'
                    })
    
    def detect_json_fields(self, content: str, filepath: Path):
        """Detect JSONField usage that might be over-engineered"""
        if 'models.JSONField' in content:
            # Check if it's used for quality indicators or scores
            if any(term in content.lower() for term in ['quality', 'score', 'indicator', 'metric']):
                self.issues.append({
                    'file': str(filepath),
                    'type': 'json_field_overuse',
                    'description': 'JSONField used for quality/score data - consider simplification'
                })
    
    def detect_deprecated_patterns(self, content: str, filepath: Path):
        """Detect deprecated patterns and TODOs"""
        patterns = [
            (r'#\s*TODO:?\s*[Rr]emove', 'todo_remove'),
            (r'#\s*DEPRECATED', 'deprecated_code'),
            (r'warnings\.warn\(', 'deprecation_warning'),
            (r'#\s*Legacy', 'legacy_code'),
            (r'#\s*FIXME', 'fixme_comment')
        ]
        
        for pattern, issue_type in patterns:
            if re.search(pattern, content):
                self.issues.append({
                    'file': str(filepath),
                    'type': issue_type,
                    'description': f'Found {issue_type.replace("_", " ")}'
                })
    
    def detect_complex_queries(self, content: str, filepath: Path):
        """Detect complex database queries"""
        if '.extra(' in content:
            self.issues.append({
                'file': str(filepath),
                'type': 'complex_query',
                'description': 'Uses .extra() query - consider ORM alternative'
            })
        
        if 'raw(' in content and 'models' in content:
            self.issues.append({
                'file': str(filepath),
                'type': 'raw_sql',
                'description': 'Uses raw SQL - consider ORM alternative'
            })

# Usage
if __name__ == "__main__":
    detector = CodeQualityDetector()
    issues = detector.scan_all()
    
    # Group by type
    by_type = {}
    for issue in issues:
        issue_type = issue['type']
        if issue_type not in by_type:
            by_type[issue_type] = []
        by_type[issue_type].append(issue)
    
    # Report
    for issue_type, items in by_type.items():
        print(f"\n=== {issue_type.upper().replace('_', ' ')} ({len(items)} found) ===")
        for item in items[:5]:  # Show first 5
            print(f"  - {item['file']}: {item['description']}")
        if len(items) > 5:
            print(f"  ... and {len(items) - 5} more")
```

### 2.2 Test-Specific Detection

```bash
# Find test files with complex setup
find apps/ -path "*/tests/*" -name "*.py" -type f | while read file; do
    setup_lines=$(grep -A 20 "def setUp\|def test_" "$file" | wc -l)
    if [ "$setup_lines" -gt 100 ]; then
        echo "Complex test setup in: $file ($setup_lines lines)"
    fi
done

# Find tests creating objects with many fields
grep -r "\.objects\.create(" apps/*/tests/ --include="*.py" -A 10 | grep -E "=.*," | wc -l
```

## Phase 3: Automated Fixes

### 3.1 Import Cleanup Script

```python
#!/usr/bin/env python3
"""
clean_imports.py
Automatically remove unused imports
"""

import ast
import astor
from pathlib import Path

def remove_unused_imports(filepath: Path):
    """Remove unused imports from a Python file"""
    with open(filepath, 'r') as f:
        content = f.read()
        tree = ast.parse(content)
    
    # Collect all names used in the file
    used_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            used_names.add(node.attr)
    
    # Filter imports
    new_body = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            new_names = []
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                if name in used_names or name.split('.')[0] in used_names:
                    new_names.append(alias)
            if new_names:
                node.names = new_names
                new_body.append(node)
        elif isinstance(node, ast.ImportFrom):
            new_names = []
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                if name in used_names:
                    new_names.append(alias)
            if new_names:
                node.names = new_names
                new_body.append(node)
        else:
            new_body.append(node)
    
    tree.body = new_body
    
    # Write back
    cleaned_code = astor.to_source(tree)
    with open(filepath, 'w') as f:
        f.write(cleaned_code)

# Usage
if __name__ == "__main__":
    for py_file in Path("apps/").rglob("*.py"):
        if "migrations" not in str(py_file):
            print(f"Cleaning {py_file}")
            remove_unused_imports(py_file)
```

### 3.2 JSONField to Property Converter

```python
#!/usr/bin/env python3
"""
json_to_property.py
Convert JSONField quality indicators to properties
"""

def generate_property_replacement(field_name: str, json_keys: List[str]) -> str:
    """Generate property methods to replace JSONField"""
    properties = []
    
    for key in json_keys:
        property_code = f'''
    @property
    def {key}(self) -> bool:
        """Check if {key.replace('_', ' ')} is available."""
        # Simplified logic based on actual data
        return bool(self.is_pdf or self.document_type == 'journal_article')
'''
        properties.append(property_code)
    
    return '\n'.join(properties)
```

## Phase 4: Validation and Testing

### 4.1 Pre-Change Validation
```bash
# Capture current test results
python manage.py test > test_results_before.txt

# Run linting
flake8 apps/ --max-line-length=120 > lint_results_before.txt

# Check current coverage
coverage run --source='.' manage.py test
coverage report > coverage_before.txt
```

### 4.2 Post-Change Validation
```bash
# Compare test results
python manage.py test > test_results_after.txt
diff test_results_before.txt test_results_after.txt

# Verify no new lint errors
flake8 apps/ --max-line-length=120 > lint_results_after.txt
diff lint_results_before.txt lint_results_after.txt

# Ensure coverage hasn't dropped
coverage run --source='.' manage.py test
coverage report > coverage_after.txt
```

## Phase 5: Continuous Monitoring

### 5.1 Git Hooks
```bash
# .git/hooks/pre-commit
#!/bin/bash
# Check for common issues before commit

# No hardcoded years
if git diff --cached --name-only | xargs grep -l "2024\|2025" 2>/dev/null; then
    echo "Error: Hardcoded year found. Use dynamic dates."
    exit 1
fi

# No complex extra() queries in new code
if git diff --cached --name-only | xargs grep -l "\.extra(" 2>/dev/null; then
    echo "Warning: .extra() query found. Consider using ORM."
fi

# Check for unused imports
python scripts/detect_unused_imports.py
```

### 5.2 CI/CD Integration
```yaml
# .github/workflows/code-quality.yml
name: Code Quality Check

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Check for deprecated patterns
        run: |
          ! grep -r "DEPRECATED\|TODO: Remove" apps/ --include="*.py"
      
      - name: Check for complex queries
        run: |
          ! grep -r "\.extra(" apps/ --include="*.py" | grep -v migrations
      
      - name: Run import checker
        run: python scripts/code_quality_detector.py
```

## Implementation Priority

1. **High Priority** (Do immediately):
   - Remove unused imports
   - Fix hardcoded dates/years
   - Remove deprecated methods with no callers

2. **Medium Priority** (Next sprint):
   - Simplify JSONField usage
   - Convert complex scores to boolean properties
   - Replace .extra() queries with ORM

3. **Low Priority** (Technical debt backlog):
   - Refactor complex methods
   - Clean up test fixtures
   - Remove commented code

## Success Metrics

- 30% reduction in lines of code
- 50% reduction in import statements
- 0 uses of .extra() queries
- 90%+ test coverage maintained
- No JSONFields for simple boolean data
- All TODOs addressed or ticketed

## Rollback Plan

1. Commit each type of change separately
2. Tag releases before major refactoring
3. Keep deprecated methods for one release cycle
4. Monitor error logs for unexpected issues
5. Have feature flags for major changes