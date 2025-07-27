# Code Quality Guide

## Quick Start

We've created tools to systematically detect and fix code quality issues based on patterns discovered during the results_manager refactoring.

### 1. Run Detection

```bash
# Quick bash-based check
./scripts/code_quality_check.sh

# Detailed Python analysis
python scripts/detect_code_issues.py

# Check specific app
python scripts/detect_code_issues.py --app review_results
```

### 2. Fix Common Issues

```bash
# See what would be fixed (dry run)
python scripts/fix_common_issues.py --app results_manager

# Apply fixes
python scripts/fix_common_issues.py --fix --app results_manager
```

### 3. Clean Imports Automatically

```bash
# Install autoflake
pip install autoflake

# Remove unused imports
autoflake --remove-all-unused-imports --in-place --recursive apps/
```

## Common Patterns Found

### 1. **Over-Engineered Fields**
- JSONFields storing simple boolean data
- FloatFields for complex scoring that could be properties
- Multiple fields tracking similar concepts

**Fix**: Convert to properties or simple boolean fields

### 2. **Unused Imports**
- Typing imports with no type annotations
- Django utilities from removed features
- Service imports from old architectures

**Fix**: Use autoflake or our fix script

### 3. **Complex Queries**
- `.extra()` with SQL fragments
- Raw SQL instead of ORM
- Missing select_related/prefetch_related

**Fix**: Rewrite using Django ORM

### 4. **Hardcoded Values**
- Years like 2024, 2025
- Magic numbers in calculations
- Fixed thresholds

**Fix**: Use dynamic calculations

### 5. **Legacy Code**
- TODO: Remove comments
- Deprecated methods still called
- Backwards compatibility layers

**Fix**: Remove if no longer needed

## Manual Review Checklist

After running automated tools, manually review:

1. **Service Classes**
   - [ ] Less than 10 methods per service
   - [ ] Clear single responsibility
   - [ ] No circular dependencies

2. **Models**
   - [ ] No more than 15 fields
   - [ ] JSONFields have clear purpose
   - [ ] Indexes on queried fields

3. **Views**
   - [ ] Separate API and template views
   - [ ] Proper query optimization
   - [ ] Clean URL patterns

4. **Tests**
   - [ ] Simple setup methods
   - [ ] No testing implementation details
   - [ ] Clear test names

## Integration with CI/CD

Add to your pre-commit hooks:

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run code quality check
python scripts/detect_code_issues.py
if [ $? -ne 0 ]; then
    echo "Code quality issues found. Please fix before committing."
    exit 1
fi
```

## Metrics to Track

1. **Import Reduction**: Aim for 30% fewer imports
2. **Query Simplification**: Zero `.extra()` queries
3. **Field Simplification**: No JSONFields for simple data
4. **Code Reduction**: 20-30% fewer lines of code
5. **Test Coverage**: Maintain 90%+

## Next Steps

1. Run detection on each app
2. Fix high-priority issues first
3. Add to CI/CD pipeline
4. Track metrics over time
5. Document patterns specific to your project