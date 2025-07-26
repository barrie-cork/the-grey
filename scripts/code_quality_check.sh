#!/bin/bash
#
# Comprehensive Code Quality Check Script
# Based on patterns from results_manager refactoring
#

echo "======================================"
echo "CODE QUALITY CHECK"
echo "======================================"
echo ""

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Initialize counters
TOTAL_ISSUES=0

# Function to print section headers
print_section() {
    echo ""
    echo -e "${GREEN}=== $1 ===${NC}"
    echo ""
}

# Function to count and display issues
count_issues() {
    local count=$1
    local description=$2
    if [ "$count" -gt 0 ]; then
        echo -e "${RED}Found $count $description${NC}"
        TOTAL_ISSUES=$((TOTAL_ISSUES + count))
    else
        echo -e "${GREEN}No $description found${NC}"
    fi
}

# 1. Check for unused imports
print_section "CHECKING FOR UNUSED IMPORTS"
echo "Detecting potentially unused typing imports..."
unused_typing=$(grep -r "from typing import" apps/ --include="*.py" | grep -v migrations | wc -l)
echo "Files with typing imports: $unused_typing"

# 2. Check for deprecated patterns
print_section "CHECKING FOR DEPRECATED PATTERNS"
deprecated_count=$(grep -r "DEPRECATED\|TODO.*[Rr]emove\|FIXME" apps/ --include="*.py" | grep -v migrations | wc -l)
count_issues $deprecated_count "deprecated patterns"

# 3. Check for complex queries
print_section "CHECKING FOR COMPLEX DATABASE QUERIES"
extra_queries=$(grep -r "\.extra(" apps/ --include="*.py" | grep -v migrations | wc -l)
count_issues $extra_queries "uses of .extra() queries"

raw_sql=$(grep -r "\.raw(\|cursor\.execute" apps/ --include="*.py" | grep -v migrations | wc -l)
count_issues $raw_sql "uses of raw SQL"

# 4. Check for JSONField overuse
print_section "CHECKING FOR JSONFIELD OVERUSE"
json_fields=$(grep -r "models\.JSONField" apps/ --include="*.py" | grep -v migrations | wc -l)
echo "Total JSONFields: $json_fields"
json_quality=$(grep -r "models\.JSONField" apps/ --include="*.py" | grep -v migrations | grep -i "quality\|score\|indicator" | wc -l)
count_issues $json_quality "JSONFields for quality/score data"

# 5. Check for FloatField scores
print_section "CHECKING FOR FLOAT FIELD SCORES"
float_scores=$(grep -r "models\.FloatField" apps/ --include="*.py" | grep -v migrations | grep -i "score\|rating\|quality" | wc -l)
count_issues $float_scores "FloatFields for scores/ratings"

# 6. Check for hardcoded years
print_section "CHECKING FOR HARDCODED YEARS"
hardcoded_years=$(grep -r "202[0-9]" apps/ --include="*.py" --include="*.html" | grep -v migrations | grep -v "__" | wc -l)
count_issues $hardcoded_years "hardcoded year references"

# 7. Check for complex methods (files with many methods)
print_section "CHECKING FOR COMPLEX SERVICE CLASSES"
echo "Service classes with many methods:"
for file in $(find apps/ -path "*/services/*.py" -type f); do
    method_count=$(grep -c "def " "$file" 2>/dev/null || echo 0)
    if [ "$method_count" -gt 15 ]; then
        echo -e "${YELLOW}  $file: $method_count methods${NC}"
        TOTAL_ISSUES=$((TOTAL_ISSUES + 1))
    fi
done

# 8. Check for missing select_related/prefetch_related
print_section "CHECKING FOR POTENTIAL N+1 QUERIES"
potential_n1=$(grep -r "\.objects\." apps/ --include="*.py" | grep -v "select_related\|prefetch_related" | grep -v migrations | grep -v test | wc -l)
echo "Queries without select_related/prefetch_related: $potential_n1"
echo "(Manual review needed to identify actual N+1 issues)"

# 9. Check for template issues
print_section "CHECKING TEMPLATES FOR REMOVED FIELDS"
if [ -d "templates/" ]; then
    template_issues=$(grep -r "relevance_score\|quality_indicators\|quality_score" templates/ --include="*.html" | wc -l)
    count_issues $template_issues "references to removed fields in templates"
fi

# 10. Check for test complexity
print_section "CHECKING TEST COMPLEXITY"
echo "Test files with complex setup (>100 lines):"
complex_tests=0
for file in $(find apps/ -path "*/tests/*" -name "*.py" -type f); do
    if [ -f "$file" ]; then
        setup_lines=$(grep -A 50 "def setUp\|def test_" "$file" 2>/dev/null | wc -l)
        if [ "$setup_lines" -gt 100 ]; then
            echo -e "${YELLOW}  $file${NC}"
            complex_tests=$((complex_tests + 1))
        fi
    fi
done
TOTAL_ISSUES=$((TOTAL_ISSUES + complex_tests))

# Summary
echo ""
echo "======================================"
echo "SUMMARY"
echo "======================================"
echo ""

if [ "$TOTAL_ISSUES" -eq 0 ]; then
    echo -e "${GREEN}Excellent! No major code quality issues found.${NC}"
else
    echo -e "${RED}Total issues found: $TOTAL_ISSUES${NC}"
    echo ""
    echo "Recommendations:"
    echo "1. Run: python scripts/detect_code_issues.py for detailed analysis"
    echo "2. Install autoflake: pip install autoflake"
    echo "3. Clean imports: autoflake --remove-all-unused-imports --in-place --recursive apps/"
    echo "4. Review and address deprecated patterns"
    echo "5. Replace .extra() queries with Django ORM"
fi

# Run Python detector if available
if [ -f "scripts/detect_code_issues.py" ]; then
    echo ""
    echo "======================================"
    echo "RUNNING DETAILED PYTHON ANALYSIS"
    echo "======================================"
    python scripts/detect_code_issues.py
fi

exit $TOTAL_ISSUES