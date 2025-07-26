"""
Django-specific code quality analyzer.
"""
import ast
from pathlib import Path
from typing import List, Set, Dict, Any

from quality.core import Analyzer, Issue

class DjangoPatternAnalyzer(Analyzer):
    """Detects Django-specific antipatterns and issues."""
    
    def __init__(self):
        self.django_patterns = {
            'n_plus_one': self._check_n_plus_one,
            'missing_select_related': self._check_missing_select_related,
            'inefficient_queries': self._check_inefficient_queries,
            'security_issues': self._check_security_issues,
            'deprecated_patterns': self._check_deprecated_patterns,
        }
    
    def analyze(self, file_path: Path, content: str, ast_tree: ast.AST) -> List[Issue]:
        """Analyze Django-specific patterns."""
        issues = []
        
        # Skip non-Django files
        if not self._is_django_file(file_path, content):
            return issues
        
        # Run all pattern checks
        for pattern_name, checker in self.django_patterns.items():
            issues.extend(checker(file_path, content, ast_tree))
        
        return issues
    
    def _is_django_file(self, file_path: Path, content: str) -> bool:
        """Check if this is a Django-related file."""
        django_imports = [
            'from django', 'import django',
            'from apps.', 'import apps.'
        ]
        return any(imp in content for imp in django_imports)
    
    def _check_n_plus_one(self, file_path: Path, content: str, tree: ast.AST) -> List[Issue]:
        """Check for potential N+1 query problems."""
        issues = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                # Check if iterating over queryset
                if self._is_queryset_iteration(node):
                    # Check for model access inside loop
                    for inner in ast.walk(node):
                        if self._is_related_access(inner):
                            issues.append(Issue(
                                file=file_path,
                                line=inner.lineno,
                                column=inner.col_offset,
                                severity='warning',
                                category='performance',
                                message='Potential N+1 query detected. Consider using select_related() or prefetch_related()',
                                fix_available=True,
                                fix_description='Add select_related() to queryset'
                            ))
        
        return issues
    
    def _check_missing_select_related(self, file_path: Path, content: str, tree: ast.AST) -> List[Issue]:
        """Check for missing select_related/prefetch_related."""
        issues = []
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                # Check for .objects.filter/all/get without optimization
                if (node.func.attr in ['filter', 'all', 'get'] and
                    self._is_objects_call(node) and
                    not self._has_optimization(lines[node.lineno - 1])):
                    
                    # Check if there's foreign key access nearby
                    if self._has_fk_access_nearby(tree, node):
                        issues.append(Issue(
                            file=file_path,
                            line=node.lineno,
                            column=node.col_offset,
                            severity='info',
                            category='performance',
                            message='Consider adding select_related() or prefetch_related() for better performance',
                            fix_available=False
                        ))
        
        return issues
    
    def _check_inefficient_queries(self, file_path: Path, content: str, tree: ast.AST) -> List[Issue]:
        """Check for inefficient query patterns."""
        issues = []
        
        for node in ast.walk(tree):
            # Check for .extra() usage
            if (isinstance(node, ast.Call) and 
                isinstance(node.func, ast.Attribute) and
                node.func.attr == 'extra'):
                issues.append(Issue(
                    file=file_path,
                    line=node.lineno,
                    column=node.col_offset,
                    severity='warning',
                    category='maintainability',
                    message='Use of .extra() is discouraged. Consider using Django ORM methods instead',
                    fix_available=False
                ))
            
            # Check for raw SQL
            if (isinstance(node, ast.Call) and
                isinstance(node.func, ast.Attribute) and
                node.func.attr in ['raw', 'execute']):
                issues.append(Issue(
                    file=file_path,
                    line=node.lineno,
                    column=node.col_offset,
                    severity='warning',
                    category='security',
                    message='Raw SQL detected. Ensure proper parameterization to prevent SQL injection',
                    fix_available=False
                ))
        
        return issues
    
    def _check_security_issues(self, file_path: Path, content: str, tree: ast.AST) -> List[Issue]:
        """Check for Django security issues."""
        issues = []
        
        # Check for disabled CSRF
        if '@csrf_exempt' in content:
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == 'csrf_exempt':
                    issues.append(Issue(
                        file=file_path,
                        line=node.lineno,
                        column=node.col_offset,
                        severity='warning',
                        category='security',
                        message='CSRF protection disabled. Ensure this is intentional',
                        fix_available=False
                    ))
        
        # Check for unsafe template rendering
        if 'mark_safe' in content or '|safe' in content:
            issues.append(Issue(
                file=file_path,
                line=1,
                column=0,
                severity='warning',
                category='security',
                message='Unsafe template rendering detected. Ensure content is properly escaped',
                fix_available=False
            ))
        
        return issues
    
    def _check_deprecated_patterns(self, file_path: Path, content: str, tree: ast.AST) -> List[Issue]:
        """Check for deprecated Django patterns."""
        issues = []
        
        deprecated_imports = {
            'django.conf.urls': 'Use django.urls instead',
            'django.utils.translation.ugettext': 'Use gettext instead',
            'django.contrib.staticfiles.templatetags.staticfiles': 'Use django.templatetags.static',
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module in deprecated_imports:
                    issues.append(Issue(
                        file=file_path,
                        line=node.lineno,
                        column=node.col_offset,
                        severity='warning',
                        category='deprecation',
                        message=f'Deprecated import: {deprecated_imports[node.module]}',
                        fix_available=True,
                        fix_description='Update to non-deprecated import'
                    ))
        
        return issues
    
    # Helper methods
    def _is_queryset_iteration(self, node: ast.For) -> bool:
        """Check if a for loop is iterating over a queryset."""
        if isinstance(node.iter, ast.Call):
            return self._is_objects_call(node.iter)
        return False
    
    def _is_objects_call(self, node: ast.Call) -> bool:
        """Check if a call is on Model.objects."""
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Attribute):
                return node.func.value.attr == 'objects'
        return False
    
    def _is_related_access(self, node: ast.AST) -> bool:
        """Check if accessing a related model."""
        if isinstance(node, ast.Attribute):
            # Simple heuristic: attributes ending with _set or foreign key patterns
            return (node.attr.endswith('_set') or 
                    node.attr in ['user', 'author', 'category', 'tags'])
        return False
    
    def _has_optimization(self, line: str) -> bool:
        """Check if line has select_related or prefetch_related."""
        return 'select_related' in line or 'prefetch_related' in line
    
    def _has_fk_access_nearby(self, tree: ast.AST, query_node: ast.AST) -> bool:
        """Check if there's foreign key access near the query."""
        # Simplified check - in real implementation would be more sophisticated
        return True
    
    def can_fix(self, issue: Issue) -> bool:
        """Check if we can fix this issue."""
        return issue.fix_available
    
    def fix(self, file_path: Path, issue: Issue) -> str:
        """Apply fix for the issue."""
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Implement specific fixes based on issue type
        if 'Deprecated import' in issue.message:
            # Replace deprecated imports
            old_imports = {
                'django.conf.urls': 'django.urls',
                'django.utils.translation.ugettext': 'django.utils.translation.gettext',
            }
            for old, new in old_imports.items():
                content = content.replace(f'from {old}', f'from {new}')
        
        return content