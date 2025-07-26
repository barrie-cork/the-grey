# PRP: Fix Results Manager Refactoring Issues

## Goal
Complete the results_manager app refactoring by fixing all critical issues identified in code review #2, including missing migrations, broken references, and test updates.

## Why
The current refactoring is incomplete and will cause runtime errors. We need to:
- Generate missing database migration for removed fields
- Fix all broken references to removed fields
- Update tests to match the simplified approach
- Ensure backwards compatibility and zero downtime deployment

## Context

### Current State
The refactoring simplified the results_manager app by removing:
- `has_full_text` field (BooleanField) - needs to become a property
- `quality_indicators` field (JSONField)
- `relevance_score` field (FloatField)
- `calculate_relevance_score` function

### Critical Issues Found
1. **Missing Migration**: Model changes require migration generation
2. **Broken References**: 40+ files still reference removed fields
3. **Import Errors**: Non-existent functions being imported
4. **Test Failures**: Tests create objects with removed fields

### Migration Patterns in Codebase
Reference existing migrations:
- `/mnt/d/Python/Projects/django/HTA-projects/agent-grey/apps/results_manager/migrations/0003_remove_resultmetadata_result_and_more.py`
- `/mnt/d/Python/Projects/django/HTA-projects/agent-grey/apps/review_results/migrations/0002_simplify_review_models.py`

### Django Best Practices
- Use multi-step deployment for zero downtime
- RemoveField includes CASCADE clause
- Properties cannot have same name as field in same deployment
- Reference: https://docs.djangoproject.com/en/5.2/ref/migration-operations/

## Implementation

### Task List

1. **Fix ProcessedResult Model** - Add has_full_text property
2. **Generate Migration** - Create migration for field removals
3. **Fix Import Errors** - Remove/update broken imports
4. **Update Service Methods** - Fix all service queries
5. **Update Templates** - Fix template references
6. **Update Tests** - Remove field references from test data
7. **Fix ReviewRecommendationService** - Update complex SQL queries
8. **Update API Responses** - Ensure API compatibility
9. **Run Validation** - Execute all tests and linting

### 1. Fix ProcessedResult Model

**File**: `apps/results_manager/models.py`

Add property after removing the field:
```python
@property
def has_full_text(self) -> bool:
    """Check if full text is available based on PDF status or full_text_url."""
    return bool(self.is_pdf or self.full_text_url)
```

### 2. Generate Migration

**Command**: 
```bash
python manage.py makemigrations results_manager -n remove_complex_metadata_fields
```

Expected migration operations:
- RemoveField for has_full_text
- RemoveField for quality_indicators
- RemoveField for relevance_score
- RemoveIndex for fields that use relevance_score

### 3. Fix Import Errors

**File**: `apps/results_manager/tasks.py`
- Remove line importing `calculate_relevance_score`
- Remove references to `ResultMetadata` model
- Fix undefined `metadata` variable around line 312

### 4. Update Service Methods

**Critical Files**:

#### apps/results_manager/services/quality_assessment_service.py
- Remove deprecated `calculate_relevance_score` method entirely
- Update `assess_document_quality` to not reference `has_full_text` field

#### apps/results_manager/services/processing_analytics_service.py
- Update all callers of renamed method `get_results_for_review`
- Remove relevance score calculations from statistics

#### apps/review_results/services/review_recommendation_service.py
- Lines 50-60: Update SQL query removing relevance_score calculations
- Lines 103-105: Remove CASE statements for removed fields
- Use simplified ordering: `order_by('duplicate_group_id', '-publication_year')`

#### apps/reporting/services/study_analysis_service.py
- Lines 57-59: Remove quality_indicators references
- Lines 148-161: Remove peer_reviewed, has_doi checks
- Update to use only `is_pdf` indicator

### 5. Update Templates

**File**: `apps/results_manager/templates/results_manager/results_overview.html`
- Line 219: Change `result.has_full_text` to property call
- Lines 212-215: Remove relevance_score display

### 6. Update Tests

**Pattern to Follow**:
```python
# Remove these fields from test data creation:
ProcessedResult.objects.create(
    session=self.session,
    title='Test Result',
    url='https://example.com',
    snippet='Test snippet',
    # has_full_text=True,  # REMOVE THIS
    # relevance_score=0.85,  # REMOVE THIS
    # quality_indicators={'peer_reviewed': True},  # REMOVE THIS
    is_pdf=True,  # Keep this
    publication_year=2024  # Keep this
)
```

**Files to Update**:
- apps/results_manager/tests/test_models.py
- apps/results_manager/tests/services/test_quality_assessment_service.py
- apps/results_manager/tests/services/test_processing_analytics_service.py
- apps/reporting/tests/services/test_study_analysis_service.py
- apps/review_results/tests/services/test_review_analytics_service.py
- apps/review_results/tests/services/test_review_recommendation_service.py

### 7. Fix Complex Queries

**File**: `apps/review_results/services/review_recommendation_service.py`

Replace complex extra() query with simplified version:
```python
recommendations = unreviewed.order_by(
    models.F('duplicate_group_id').asc(nulls_first=True),
    '-publication_year',
    '-processed_at'
)[:limit]
```

### 8. API Compatibility

**File**: `apps/results_manager/api.py`
- Line 25: Already updated to use property - verify it works

### Pseudocode Approach

```
1. START with model fix:
   - Add has_full_text property to ProcessedResult
   - Ensure it returns bool based on is_pdf OR full_text_url

2. GENERATE migration:
   - Run makemigrations
   - Review generated operations
   - Add any custom data migration if needed

3. FIX each broken import/reference:
   - For each file in the reference list
   - Remove field usage or replace with property
   - Update queries to use simplified approach

4. UPDATE all tests:
   - Remove field assignments
   - Update assertions
   - Ensure tests pass

5. VALIDATE everything:
   - Run full test suite
   - Check for deprecation warnings
   - Lint code
```

### Error Handling Strategy

1. **Migration Rollback Plan**: Keep backup of database before applying
2. **Feature Flag**: Consider adding flag to toggle simplified approach
3. **Logging**: Add debug logging for property access
4. **Monitoring**: Watch for 500 errors after deployment

## Validation

```bash
# 1. Generate and review migration
python manage.py makemigrations results_manager --dry-run
python manage.py makemigrations results_manager -n remove_complex_metadata_fields

# 2. Check migration SQL
python manage.py sqlmigrate results_manager 0004

# 3. Run tests for affected apps
python manage.py test apps.results_manager -v 2
python manage.py test apps.review_results -v 2
python manage.py test apps.reporting -v 2

# 4. Check for remaining references
grep -r "has_full_text" apps/ --include="*.py" | grep -v "@property"
grep -r "quality_indicators" apps/ --include="*.py"
grep -r "relevance_score" apps/ --include="*.py"
grep -r "calculate_relevance_score" apps/ --include="*.py"

# 5. Linting
flake8 apps/results_manager/ --max-line-length=120
flake8 apps/review_results/ --max-line-length=120
flake8 apps/reporting/ --max-line-length=120

# 6. Type checking
mypy apps/results_manager/
mypy apps/review_results/

# 7. Template validation
python manage.py validate_templates

# 8. Run development server and test UI
python manage.py runserver
# Navigate to results overview page and verify display

# 9. Check API endpoints
python manage.py test apps.results_manager.tests.test_api -v 2
```

## Success Criteria

- [ ] All tests pass (90%+ coverage maintained)
- [ ] No import errors or undefined variables
- [ ] Migration applies cleanly
- [ ] API maintains backwards compatibility
- [ ] Templates display results correctly
- [ ] No references to removed fields remain
- [ ] Code passes linting and type checking

## References

- Django RemoveField: https://docs.djangoproject.com/en/5.2/ref/migration-operations/#removefield
- Zero Downtime Migrations: https://medium.com/3yourmind/keeping-django-database-migrations-backward-compatible-727820260dbb
- Existing migration: `apps/review_results/migrations/0002_simplify_review_models.py`
- Test patterns: `apps/results_manager/tests/test_models.py`

## Notes

- This is a breaking change that requires careful deployment
- Consider using Django's SeparateDatabaseAndState for zero-downtime deployment
- The simplified approach improves performance by removing JSON field queries
- Backwards compatibility is maintained through the has_full_text property

## PRP Confidence Score: 9/10

High confidence due to:
- Comprehensive research of all affected files
- Clear migration patterns from existing code
- Detailed validation gates
- Specific line numbers and file paths
- Django best practices incorporated

Minor uncertainty (-1) for:
- Potential edge cases in complex SQL queries
- Possible additional template references not found in search