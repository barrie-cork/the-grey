#!/usr/bin/env python3
"""
Code Quality Issue Detector
Detects common code quality issues based on patterns from results_manager refactoring.

Usage:
    python scripts/detect_code_issues.py [--fix] [--app APP_NAME]
"""

import argparse
import ast
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Tuple

class IssueDetector:
    def __init__(self, root_dir: str = "apps/", fix_mode: bool = False):
        self.root_dir = Path(root_dir)
        self.fix_mode = fix_mode
        self.issues = defaultdict(list)
        self.stats = defaultdict(int)
        
    def scan(self, app_name: str = None):
        """Scan for issues in the specified app or all apps"""
        search_path = self.root_dir / app_name if app_name else self.root_dir
        
        if not search_path.exists():
            print(f"Error: Path {search_path} does not exist")
            return
            
        print(f"Scanning {search_path}...")
        
        # Scan Python files
        for py_file in search_path.rglob("*.py"):
            if self._should_skip_file(py_file):
                continue
            self._scan_python_file(py_file)
        
        # Scan templates
        template_path = Path("templates")
        if template_path.exists():
            for html_file in template_path.rglob("*.html"):
                self._scan_template_file(html_file)
    
    def _should_skip_file(self, filepath: Path) -> bool:
        """Check if file should be skipped"""
        skip_patterns = ['migrations', '__pycache__', '.pyc', 'test_']
        return any(pattern in str(filepath) for pattern in skip_patterns)
    
    def _scan_python_file(self, filepath: Path):
        """Scan a Python file for various issues"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            try:
                tree = ast.parse(content)
                self._check_unused_imports(tree, content, filepath)
                self._check_complex_methods(tree, filepath)
            except SyntaxError:
                self.issues['syntax_error'].append(str(filepath))
                return
            
            # Content-based checks
            self._check_deprecated_patterns(content, filepath)
            self._check_complex_queries(content, filepath)
            self._check_hardcoded_values(content, filepath)
            self._check_json_field_usage(content, filepath)
            self._check_float_field_scores(content, filepath)
            
            self.stats['files_scanned'] += 1
            
        except Exception as e:
            self.issues['scan_error'].append(f"{filepath}: {str(e)}")
    
    def _scan_template_file(self, filepath: Path):
        """Scan template files for issues"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for removed field references
            removed_fields = ['relevance_score', 'quality_indicators', 'quality_score']
            for field in removed_fields:
                if field in content:
                    self.issues['template_removed_field'].append(
                        f"{filepath}: References removed field '{field}'"
                    )
            
            # Check for hardcoded years
            years = re.findall(r'\b202[0-9]\b', content)
            if years:
                self.issues['template_hardcoded_year'].append(
                    f"{filepath}: Hardcoded years: {', '.join(set(years))}"
                )
                
        except Exception as e:
            self.issues['scan_error'].append(f"{filepath}: {str(e)}")
    
    def _check_unused_imports(self, tree: ast.AST, content: str, filepath: Path):
        """Check for potentially unused imports"""
        imports = []
        
        # Collect imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    imports.append((name, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        name = alias.asname if alias.asname else alias.name
                        imports.append((name, node.lineno))
        
        # Check usage
        for import_name, line_no in imports:
            # Count occurrences (excluding the import line)
            lines = content.split('\n')
            count = sum(1 for i, line in enumerate(lines) 
                       if i != line_no - 1 and import_name in line)
            
            if count == 0:
                self.issues['unused_import'].append(
                    f"{filepath}:{line_no} - Unused import: {import_name}"
                )
                self.stats['unused_imports'] += 1
    
    def _check_complex_methods(self, tree: ast.AST, filepath: Path):
        """Check for overly complex methods"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_complexity(node)
                if complexity > 10:
                    self.issues['complex_method'].append(
                        f"{filepath}:{node.lineno} - Complex method '{node.name}' (complexity: {complexity})"
                    )
                    self.stats['complex_methods'] += 1
    
    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity
    
    def _check_deprecated_patterns(self, content: str, filepath: Path):
        """Check for deprecated patterns"""
        patterns = [
            (r'#\s*TODO:?\s*[Rr]emove', 'TODO remove'),
            (r'#\s*DEPRECATED', 'Deprecated code'),
            (r'warnings\.warn\(["\'].*deprecated', 'Deprecation warning'),
            (r'#\s*FIXME', 'FIXME comment'),
            (r'#\s*HACK', 'HACK comment'),
        ]
        
        lines = content.split('\n')
        for i, line in enumerate(lines):
            for pattern, desc in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    self.issues['deprecated_pattern'].append(
                        f"{filepath}:{i+1} - {desc}: {line.strip()}"
                    )
                    self.stats['deprecated_patterns'] += 1
    
    def _check_complex_queries(self, content: str, filepath: Path):
        """Check for complex database queries"""
        # Check for .extra() usage
        if '.extra(' in content:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if '.extra(' in line:
                    self.issues['complex_query'].append(
                        f"{filepath}:{i+1} - Uses .extra() query method"
                    )
                    self.stats['complex_queries'] += 1
        
        # Check for raw SQL
        if re.search(r'\.raw\(|cursor\.execute\(', content):
            self.issues['raw_sql'].append(f"{filepath} - Contains raw SQL")
            self.stats['raw_sql'] += 1
    
    def _check_hardcoded_values(self, content: str, filepath: Path):
        """Check for hardcoded values"""
        # Check for hardcoded years
        lines = content.split('\n')
        for i, line in enumerate(lines):
            # Skip comments and strings in migrations
            if 'migration' in str(filepath).lower():
                continue
                
            years = re.findall(r'\b202[0-9]\b', line)
            if years and not any(skip in line for skip in ['#', 'migration', '__']):
                self.issues['hardcoded_year'].append(
                    f"{filepath}:{i+1} - Hardcoded year: {years[0]}"
                )
                self.stats['hardcoded_years'] += 1
    
    def _check_json_field_usage(self, content: str, filepath: Path):
        """Check for potentially over-engineered JSONField usage"""
        if 'models.JSONField' in content:
            # Look for quality/score related JSONFields
            context_keywords = ['quality', 'score', 'metric', 'indicator', 'rating']
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'models.JSONField' in line:
                    # Check surrounding lines for context
                    context = ' '.join(lines[max(0, i-3):min(len(lines), i+3)])
                    if any(keyword in context.lower() for keyword in context_keywords):
                        self.issues['json_overuse'].append(
                            f"{filepath}:{i+1} - JSONField used for {'/'.join(k for k in context_keywords if k in context.lower())}"
                        )
                        self.stats['json_overuse'] += 1
    
    def _check_float_field_scores(self, content: str, filepath: Path):
        """Check for FloatField used for scores that could be simplified"""
        if 'models.FloatField' in content:
            score_keywords = ['score', 'rating', 'quality', 'relevance']
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'models.FloatField' in line:
                    if any(keyword in line.lower() for keyword in score_keywords):
                        self.issues['float_score'].append(
                            f"{filepath}:{i+1} - FloatField for score/rating - consider simplification"
                        )
                        self.stats['float_scores'] += 1
    
    def report(self):
        """Generate a report of all issues found"""
        print("\n" + "="*60)
        print("CODE QUALITY REPORT")
        print("="*60)
        
        # Summary statistics
        print(f"\nFiles scanned: {self.stats['files_scanned']}")
        print(f"Total issues found: {sum(len(v) for v in self.issues.values())}")
        
        # Group issues by severity
        severity_map = {
            'high': ['syntax_error', 'raw_sql', 'complex_query'],
            'medium': ['unused_import', 'deprecated_pattern', 'json_overuse', 'float_score'],
            'low': ['hardcoded_year', 'complex_method', 'template_removed_field']
        }
        
        for severity, issue_types in severity_map.items():
            issues_in_severity = []
            for issue_type in issue_types:
                if issue_type in self.issues:
                    issues_in_severity.extend([
                        (issue_type, issue) for issue in self.issues[issue_type]
                    ])
            
            if issues_in_severity:
                print(f"\n{severity.upper()} SEVERITY ISSUES ({len(issues_in_severity)}):")
                print("-" * 40)
                
                # Group by type
                by_type = defaultdict(list)
                for issue_type, issue in issues_in_severity:
                    by_type[issue_type].append(issue)
                
                for issue_type, items in by_type.items():
                    print(f"\n{issue_type.replace('_', ' ').title()} ({len(items)}):")
                    for item in items[:5]:  # Show first 5
                        print(f"  - {item}")
                    if len(items) > 5:
                        print(f"  ... and {len(items) - 5} more")
        
        # Recommendations
        print("\n" + "="*60)
        print("RECOMMENDATIONS:")
        print("="*60)
        
        if self.stats['unused_imports'] > 10:
            print("- Run 'autoflake --remove-all-unused-imports' to clean up imports")
        
        if self.stats['complex_queries'] > 0:
            print("- Replace .extra() queries with Django ORM methods")
        
        if self.stats['json_overuse'] > 0:
            print("- Consider replacing JSONFields with specific model fields or properties")
        
        if self.stats['hardcoded_years'] > 0:
            print("- Replace hardcoded years with dynamic date calculations")
        
        if self.stats['deprecated_patterns'] > 0:
            print("- Address or remove deprecated code and TODO comments")
        
        print("\nRun with --fix flag to attempt automatic fixes for some issues.")


def main():
    parser = argparse.ArgumentParser(description='Detect code quality issues')
    parser.add_argument('--fix', action='store_true', help='Attempt to fix issues automatically')
    parser.add_argument('--app', type=str, help='Specific app to scan')
    parser.add_argument('--root', type=str, default='apps/', help='Root directory to scan')
    
    args = parser.parse_args()
    
    detector = IssueDetector(root_dir=args.root, fix_mode=args.fix)
    detector.scan(app_name=args.app)
    detector.report()
    
    # Return exit code based on issues found
    total_issues = sum(len(v) for v in detector.issues.values())
    return 1 if total_issues > 0 else 0


if __name__ == "__main__":
    sys.exit(main())