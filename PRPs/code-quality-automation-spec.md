# PRP: Systematic Code Quality Error Detection Implementation

## Goal
Transform the current manual code quality approach into a fully automated, CI/CD-integrated system that proactively detects, reports, and fixes code quality issues across the Django codebase.

## Why
- Current approach relies on manual script execution
- No integration with development workflow
- Limited coverage of Django-specific patterns
- No historical tracking of code quality metrics
- Missing advanced AST analysis capabilities

## Current State Assessment

```yaml
current_state:
  files:
    - /scripts/detect_code_issues.py (basic AST analysis)
    - /scripts/code_quality_check.sh (bash-based detection)
    - /scripts/fix_common_issues.py (limited auto-fix)
    - /docs/code-quality-guide.md (manual guide)
    - /PRPs/code-quality-systematic-approach.md (methodology)
  
  behavior:
    - Manual execution required
    - Basic pattern matching with grep
    - Simple AST analysis for imports
    - No Django-specific checks
    - No CI/CD integration
    - Limited fix capabilities
  
  issues:
    - No automated execution
    - Missing security analysis
    - No framework-specific patterns
    - Limited performance analysis
    - No metrics tracking
    - No IDE integration
```

## Desired State Specification

```yaml
desired_state:
  files:
    - /quality/core/analyzers/ (pluggable analyzers)
    - /quality/django/patterns.py (Django-specific)
    - /quality/security/scanner.py (security checks)
    - /quality/reports/generator.py (reporting)
    - /.github/workflows/quality.yml (CI/CD)
    - /quality/config.yaml (configuration)
    - /quality/rules/ (custom rules)
    - /quality/metrics/tracker.py (metrics)
  
  behavior:
    - Automated on every commit/PR
    - Django-aware pattern detection
    - Security vulnerability scanning
    - Performance analysis
    - Progressive metrics tracking
    - IDE real-time feedback
    - Auto-fix with review
  
  benefits:
    - 50% reduction in code review time
    - Zero security vulnerabilities in production
    - 90% automated issue detection
    - Historical quality trending
    - Developer productivity increase
```

## Hierarchical Objectives

### 1. High-Level: Automated Quality Assurance System
Create a comprehensive automated code quality system that integrates with the development workflow.

### 2. Mid-Level Milestones

#### 2.1 Core Analysis Engine
- Pluggable analyzer architecture
- AST-based pattern detection
- Django-specific understanding

#### 2.2 Security Integration
- Bandit integration for security
- Django security checklist
- OWASP compliance checks

#### 2.3 CI/CD Pipeline
- GitHub Actions workflow
- Pre-commit hooks
- PR quality gates

#### 2.4 Reporting & Metrics
- Quality dashboards
- Trend analysis
- Team metrics

### 3. Low-Level Tasks

## Implementation Tasks

### Task 1: Create Core Analysis Framework

```yaml
task_name: core_analysis_framework
action: CREATE
file: quality/core/__init__.py
changes: |
  """
  Core analysis framework for code quality checks.
  """
  from abc import ABC, abstractmethod
  from dataclasses import dataclass
  from typing import List, Dict, Any, Optional
  from pathlib import Path
  import ast
  
  @dataclass
  class Issue:
      file: Path
      line: int
      column: int
      severity: str  # 'error', 'warning', 'info'
      category: str
      message: str
      fix_available: bool = False
      fix_description: Optional[str] = None
  
  class Analyzer(ABC):
      """Base class for all analyzers."""
      
      @abstractmethod
      def analyze(self, file_path: Path, content: str, ast_tree: ast.AST) -> List[Issue]:
          """Analyze a file and return issues found."""
          pass
      
      @abstractmethod
      def can_fix(self, issue: Issue) -> bool:
          """Check if this analyzer can fix the given issue."""
          pass
      
      @abstractmethod
      def fix(self, file_path: Path, issue: Issue) -> str:
          """Return fixed content for the file."""
          pass
  
  class AnalyzerRegistry:
      """Registry for all available analyzers."""
      
      def __init__(self):
          self._analyzers: Dict[str, Analyzer] = {}
      
      def register(self, name: str, analyzer: Analyzer):
          """Register an analyzer."""
          self._analyzers[name] = analyzer
      
      def get_all(self) -> Dict[str, Analyzer]:
          """Get all registered analyzers."""
          return self._analyzers
      
      def get(self, name: str) -> Optional[Analyzer]:
          """Get a specific analyzer."""
          return self._analyzers.get(name)
validation:
  - command: "python -m quality.core"
  - expect: "Module loads without errors"
```

### Task 2: Django-Specific Analyzer

```yaml
task_name: django_analyzer
action: CREATE
file: quality/django/analyzer.py
changes: |
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
validation:
  - command: "python -c 'from quality.django.analyzer import DjangoPatternAnalyzer; print(\"Django analyzer loaded\")'"
  - expect: "Django analyzer loaded"
```

### Task 3: Security Scanner Integration

```yaml
task_name: security_scanner
action: CREATE
file: quality/security/scanner.py
changes: |
  """
  Security scanner integration for Django projects.
  """
  import subprocess
  import json
  from pathlib import Path
  from typing import List, Dict, Any
  
  from quality.core import Analyzer, Issue
  
  class SecurityAnalyzer(Analyzer):
      """Integrates Bandit and custom security checks."""
      
      def __init__(self):
          self.bandit_path = self._find_bandit()
          self.custom_checks = {
              'hardcoded_secrets': self._check_hardcoded_secrets,
              'unsafe_yaml': self._check_unsafe_yaml,
              'debug_enabled': self._check_debug_enabled,
          }
      
      def _find_bandit(self) -> str:
          """Find bandit executable."""
          try:
              result = subprocess.run(['which', 'bandit'], capture_output=True, text=True)
              return result.stdout.strip() or 'bandit'
          except:
              return 'bandit'
      
      def analyze(self, file_path: Path, content: str, ast_tree: ast.AST) -> List[Issue]:
          """Run security analysis."""
          issues = []
          
          # Run Bandit
          if file_path.suffix == '.py':
              issues.extend(self._run_bandit(file_path))
          
          # Run custom checks
          for check_name, checker in self.custom_checks.items():
              issues.extend(checker(file_path, content))
          
          return issues
      
      def _run_bandit(self, file_path: Path) -> List[Issue]:
          """Run Bandit security scanner."""
          issues = []
          
          try:
              result = subprocess.run(
                  [self.bandit_path, '-f', 'json', str(file_path)],
                  capture_output=True,
                  text=True
              )
              
              if result.returncode == 0:
                  return issues
              
              data = json.loads(result.stdout)
              for finding in data.get('results', []):
                  issues.append(Issue(
                      file=file_path,
                      line=finding['line_number'],
                      column=finding.get('col_offset', 0),
                      severity=self._map_severity(finding['issue_severity']),
                      category='security',
                      message=f"{finding['issue_text']} (CWE-{finding.get('cwe', 'unknown')})",
                      fix_available=False
                  ))
          
          except Exception as e:
              # If Bandit fails, continue with custom checks
              pass
          
          return issues
      
      def _check_hardcoded_secrets(self, file_path: Path, content: str) -> List[Issue]:
          """Check for hardcoded secrets."""
          issues = []
          patterns = [
              (r'["\']?[Aa][Pp][Ii][_-]?[Kk][Ee][Yy]["\']?\s*[:=]\s*["\'][^"\']+["\']', 'API key'),
              (r'["\']?[Ss][Ee][Cc][Rr][Ee][Tt][_-]?[Kk][Ee][Yy]["\']?\s*[:=]\s*["\'][^"\']+["\']', 'Secret key'),
              (r'["\']?[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]["\']?\s*[:=]\s*["\'][^"\']+["\']', 'Password'),
          ]
          
          import re
          lines = content.split('\n')
          
          for line_no, line in enumerate(lines, 1):
              for pattern, secret_type in patterns:
                  if re.search(pattern, line) and not any(skip in line for skip in ['os.', 'env.', 'config(']):
                      issues.append(Issue(
                          file=file_path,
                          line=line_no,
                          column=0,
                          severity='error',
                          category='security',
                          message=f'Potential hardcoded {secret_type} detected',
                          fix_available=True,
                          fix_description='Move to environment variables'
                      ))
          
          return issues
      
      def _check_unsafe_yaml(self, file_path: Path, content: str) -> List[Issue]:
          """Check for unsafe YAML loading."""
          issues = []
          
          if 'yaml.load(' in content and 'Loader=' not in content:
              lines = content.split('\n')
              for line_no, line in enumerate(lines, 1):
                  if 'yaml.load(' in line and 'Loader=' not in line:
                      issues.append(Issue(
                          file=file_path,
                          line=line_no,
                          column=line.find('yaml.load'),
                          severity='error',
                          category='security',
                          message='Unsafe yaml.load() usage. Use yaml.safe_load() or specify Loader',
                          fix_available=True,
                          fix_description='Replace with yaml.safe_load()'
                      ))
          
          return issues
      
      def _check_debug_enabled(self, file_path: Path, content: str) -> List[Issue]:
          """Check for DEBUG=True in production settings."""
          issues = []
          
          if 'settings' in str(file_path) and 'production' in str(file_path):
              if 'DEBUG = True' in content or 'DEBUG=True' in content:
                  issues.append(Issue(
                      file=file_path,
                      line=1,
                      column=0,
                      severity='error',
                      category='security',
                      message='DEBUG enabled in production settings',
                      fix_available=True,
                      fix_description='Set DEBUG = False'
                  ))
          
          return issues
      
      def _map_severity(self, bandit_severity: str) -> str:
          """Map Bandit severity to our severity levels."""
          mapping = {
              'HIGH': 'error',
              'MEDIUM': 'warning',
              'LOW': 'info'
          }
          return mapping.get(bandit_severity.upper(), 'info')
      
      def can_fix(self, issue: Issue) -> bool:
          """Check if we can fix this issue."""
          return issue.fix_available
      
      def fix(self, file_path: Path, issue: Issue) -> str:
          """Apply security fixes."""
          with open(file_path, 'r') as f:
              content = f.read()
          
          if 'yaml.load()' in issue.message:
              content = content.replace('yaml.load(', 'yaml.safe_load(')
          elif 'DEBUG enabled' in issue.message:
              content = content.replace('DEBUG = True', 'DEBUG = False')
              content = content.replace('DEBUG=True', 'DEBUG = False')
          
          return content
validation:
  - command: "python -c 'from quality.security.scanner import SecurityAnalyzer; print(\"Security analyzer loaded\")'"
  - expect: "Security analyzer loaded"
```

### Task 4: GitHub Actions Workflow

```yaml
task_name: github_actions_workflow
action: CREATE
file: .github/workflows/code-quality.yml
changes: |
  name: Code Quality Analysis
  
  on:
    push:
      branches: [ main, develop, feature/* ]
    pull_request:
      branches: [ main, develop ]
  
  jobs:
    quality-check:
      runs-on: ubuntu-latest
      
      services:
        postgres:
          image: postgres:15
          env:
            POSTGRES_USER: postgres
            POSTGRES_PASSWORD: postgres
            POSTGRES_DB: test_db
          options: >-
            --health-cmd pg_isready
            --health-interval 10s
            --health-timeout 5s
            --health-retries 5
          ports:
            - 5432:5432
      
      steps:
      - uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Full history for better analysis
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements/local.txt
          pip install bandit semgrep autoflake black isort mypy
      
      - name: Run Quality Analysis
        run: |
          python -m quality.main --format json > quality-report.json
        env:
          DATABASE_URL: postgres://postgres:postgres@localhost:5432/test_db
      
      - name: Upload Quality Report
        uses: actions/upload-artifact@v3
        with:
          name: quality-report
          path: quality-report.json
      
      - name: Comment PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = JSON.parse(fs.readFileSync('quality-report.json', 'utf8'));
            
            let comment = '## 📊 Code Quality Report\n\n';
            
            // Summary
            comment += `**Total Issues**: ${report.total_issues}\n`;
            comment += `- 🔴 Errors: ${report.errors}\n`;
            comment += `- 🟡 Warnings: ${report.warnings}\n`;
            comment += `- 🔵 Info: ${report.info}\n\n`;
            
            // Top issues
            if (report.issues.length > 0) {
              comment += '### Top Issues\n\n';
              report.issues.slice(0, 5).forEach(issue => {
                const emoji = issue.severity === 'error' ? '🔴' : 
                             issue.severity === 'warning' ? '🟡' : '🔵';
                comment += `${emoji} **${issue.file}:${issue.line}** - ${issue.message}\n`;
              });
              
              if (report.issues.length > 5) {
                comment += `\n... and ${report.issues.length - 5} more issues\n`;
              }
            } else {
              comment += '✅ **No issues found!**\n';
            }
            
            // Metrics
            comment += '\n### Metrics\n\n';
            comment += `- **Files Analyzed**: ${report.files_analyzed}\n`;
            comment += `- **Analysis Time**: ${report.analysis_time}s\n`;
            comment += `- **Auto-fixable Issues**: ${report.fixable_issues}\n`;
            
            // Post comment
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
      
      - name: Fail if critical issues
        run: |
          if [ $(jq '.errors' quality-report.json) -gt 0 ]; then
            echo "❌ Critical issues found!"
            exit 1
          fi
  
    security-scan:
      runs-on: ubuntu-latest
      needs: quality-check
      
      steps:
      - uses: actions/checkout@v3
      
      - name: Run Bandit Security Scan
        uses: gaurav-nelson/bandit-action@v1
        with:
          path: "apps/"
          level: "medium"
          confidence: "medium"
          exit_zero: false
      
      - name: Run Semgrep
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/security-audit
            p/django
            p/python
  
    auto-fix:
      runs-on: ubuntu-latest
      if: github.event_name == 'pull_request'
      needs: quality-check
      
      steps:
      - uses: actions/checkout@v3
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          ref: ${{ github.event.pull_request.head.ref }}
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -r requirements/local.txt
          pip install autoflake black isort
      
      - name: Auto-fix Issues
        run: |
          # Remove unused imports
          autoflake --remove-all-unused-imports --in-place --recursive apps/
          
          # Format code
          black apps/ --line-length 120
          
          # Sort imports
          isort apps/ --profile django
          
          # Run custom fixes
          python -m quality.main --fix --auto-commit
      
      - name: Commit fixes
        run: |
          git config --local user.email "action@github.com"
          git config --local user.name "GitHub Action"
          git add -A
          if git diff --staged --quiet; then
            echo "No changes to commit"
          else
            git commit -m "🤖 Auto-fix code quality issues"
            git push
          fi
validation:
  - command: "cat .github/workflows/code-quality.yml | head -20"
  - expect: "name: Code Quality Analysis"
```

### Task 5: Configuration System

```yaml
task_name: configuration_system
action: CREATE
file: quality/config.yaml
changes: |
  # Code Quality Configuration
  
  # General settings
  general:
    # Paths to analyze
    include_paths:
      - apps/
    
    # Paths to exclude
    exclude_paths:
      - "*/migrations/*"
      - "*/__pycache__/*"
      - "*/tests/fixtures/*"
    
    # File patterns
    file_patterns:
      - "*.py"
    
    # Parallel processing
    workers: 4
  
  # Analyzer settings
  analyzers:
    # Core Python analysis
    python:
      enabled: true
      checks:
        - unused_imports
        - undefined_names
        - syntax_errors
        - complexity
    
    # Django-specific
    django:
      enabled: true
      checks:
        - n_plus_one_queries
        - missing_migrations
        - security_middleware
        - template_errors
        - model_validation
    
    # Security
    security:
      enabled: true
      bandit:
        level: medium
        confidence: medium
      custom_checks:
        - hardcoded_secrets
        - sql_injection
        - xss_vulnerabilities
    
    # Performance
    performance:
      enabled: true
      checks:
        - slow_queries
        - missing_indexes
        - cache_usage
  
  # Severity settings
  severity:
    # Fail CI/CD on these
    fail_on:
      - error
    
    # Warning threshold
    max_warnings: 50
    
    # Severity mappings
    mappings:
      security_issue: error
      syntax_error: error
      undefined_name: error
      performance_issue: warning
      style_issue: info
  
  # Auto-fix settings
  auto_fix:
    enabled: true
    
    # Safe fixes to apply automatically
    safe_fixes:
      - remove_unused_imports
      - fix_indentation
      - add_missing_commas
      - update_deprecated_imports
    
    # Fixes requiring review
    review_required:
      - change_logic
      - modify_queries
      - update_security_settings
  
  # Reporting
  reporting:
    # Output formats
    formats:
      - console
      - json
      - html
      - github_pr_comment
    
    # Metrics to track
    metrics:
      - total_issues
      - issues_by_severity
      - issues_by_category
      - files_with_issues
      - fix_rate
      - trend_over_time
    
    # Report destinations
    destinations:
      console:
        enabled: true
        verbose: false
      
      file:
        enabled: true
        path: "quality-report.json"
      
      github:
        enabled: true
        comment_on_pr: true
        status_check: true
  
  # Integration settings
  integrations:
    # Git hooks
    pre_commit:
      enabled: true
      fix_before_commit: true
      
    # IDE
    vscode:
      enabled: true
      real_time: true
      
    # CI/CD
    github_actions:
      enabled: true
      fail_on_error: true
      auto_fix_pr: true
  
  # Custom rules
  rules:
    # Django-specific rules
    django_rules:
      - id: no_raw_sql
        pattern: ".raw\\(|cursor\\.execute"
        message: "Avoid raw SQL, use Django ORM"
        severity: warning
        
      - id: require_atomic
        pattern: "def \\w+\\(.*\\):.*\\.save\\("
        message: "Consider using @transaction.atomic"
        severity: info
    
    # Project-specific rules
    project_rules:
      - id: use_uuid_pk
        pattern: "id = models\\.AutoField"
        message: "Use UUIDField for primary keys"
        severity: error
validation:
  - command: "python -c 'import yaml; yaml.safe_load(open(\"quality/config.yaml\"))'"
  - expect: "No errors"
```

### Task 6: Main Execution Entry Point

```yaml
task_name: main_execution
action: CREATE
file: quality/main.py
changes: |
  """
  Main entry point for code quality analysis.
  """
  import argparse
  import json
  import sys
  import time
  from pathlib import Path
  from typing import List, Dict, Any
  
  import yaml
  
  from quality.core import AnalyzerRegistry, Issue
  from quality.django.analyzer import DjangoPatternAnalyzer
  from quality.security.scanner import SecurityAnalyzer
  from quality.reports.generator import ReportGenerator
  
  class QualityRunner:
      """Main runner for quality analysis."""
      
      def __init__(self, config_path: str = "quality/config.yaml"):
          self.config = self._load_config(config_path)
          self.registry = AnalyzerRegistry()
          self._register_analyzers()
          self.issues: List[Issue] = []
          self.stats = {
              'files_analyzed': 0,
              'total_issues': 0,
              'errors': 0,
              'warnings': 0,
              'info': 0,
              'fixable_issues': 0,
              'analysis_time': 0
          }
      
      def _load_config(self, config_path: str) -> Dict[str, Any]:
          """Load configuration from YAML."""
          with open(config_path, 'r') as f:
              return yaml.safe_load(f)
      
      def _register_analyzers(self):
          """Register all available analyzers."""
          # Register based on config
          if self.config['analyzers']['django']['enabled']:
              self.registry.register('django', DjangoPatternAnalyzer())
          
          if self.config['analyzers']['security']['enabled']:
              self.registry.register('security', SecurityAnalyzer())
      
      def run(self, fix: bool = False, auto_commit: bool = False) -> int:
          """Run quality analysis."""
          start_time = time.time()
          
          # Collect files to analyze
          files = self._collect_files()
          
          # Analyze each file
          for file_path in files:
              self._analyze_file(file_path)
              self.stats['files_analyzed'] += 1
          
          # Apply fixes if requested
          if fix:
              self._apply_fixes(auto_commit)
          
          # Calculate stats
          self.stats['analysis_time'] = round(time.time() - start_time, 2)
          self.stats['total_issues'] = len(self.issues)
          
          for issue in self.issues:
              if issue.severity == 'error':
                  self.stats['errors'] += 1
              elif issue.severity == 'warning':
                  self.stats['warnings'] += 1
              else:
                  self.stats['info'] += 1
              
              if issue.fix_available:
                  self.stats['fixable_issues'] += 1
          
          # Generate report
          self._generate_report()
          
          # Return exit code
          if self.stats['errors'] > 0:
              return 1
          return 0
      
      def _collect_files(self) -> List[Path]:
          """Collect files to analyze."""
          files = []
          
          for include_path in self.config['general']['include_paths']:
              path = Path(include_path)
              if path.exists():
                  for pattern in self.config['general']['file_patterns']:
                      files.extend(path.rglob(pattern))
          
          # Filter excluded paths
          filtered_files = []
          for file_path in files:
              exclude = False
              for exclude_pattern in self.config['general']['exclude_paths']:
                  if exclude_pattern.replace('*', '') in str(file_path):
                      exclude = True
                      break
              if not exclude:
                  filtered_files.append(file_path)
          
          return filtered_files
      
      def _analyze_file(self, file_path: Path):
          """Analyze a single file."""
          try:
              with open(file_path, 'r', encoding='utf-8') as f:
                  content = f.read()
              
              # Parse AST
              import ast
              try:
                  tree = ast.parse(content)
              except SyntaxError as e:
                  self.issues.append(Issue(
                      file=file_path,
                      line=e.lineno or 1,
                      column=e.offset or 0,
                      severity='error',
                      category='syntax',
                      message=f'Syntax error: {e.msg}',
                      fix_available=False
                  ))
                  return
              
              # Run all analyzers
              for name, analyzer in self.registry.get_all().items():
                  issues = analyzer.analyze(file_path, content, tree)
                  self.issues.extend(issues)
          
          except Exception as e:
              print(f"Error analyzing {file_path}: {e}")
      
      def _apply_fixes(self, auto_commit: bool):
          """Apply available fixes."""
          fixed_files = set()
          
          for issue in self.issues:
              if issue.fix_available:
                  analyzer_name = self._find_analyzer_for_issue(issue)
                  if analyzer_name:
                      analyzer = self.registry.get(analyzer_name)
                      if analyzer and analyzer.can_fix(issue):
                          try:
                              fixed_content = analyzer.fix(issue.file, issue)
                              with open(issue.file, 'w') as f:
                                  f.write(fixed_content)
                              fixed_files.add(issue.file)
                              print(f"Fixed: {issue.file}:{issue.line} - {issue.message}")
                          except Exception as e:
                              print(f"Error fixing {issue.file}: {e}")
          
          if auto_commit and fixed_files:
              self._commit_fixes(fixed_files)
      
      def _find_analyzer_for_issue(self, issue: Issue) -> str:
          """Find which analyzer can fix an issue."""
          for name, analyzer in self.registry.get_all().items():
              if analyzer.can_fix(issue):
                  return name
          return None
      
      def _commit_fixes(self, fixed_files: set):
          """Commit fixes to git."""
          import subprocess
          
          try:
              # Add fixed files
              for file_path in fixed_files:
                  subprocess.run(['git', 'add', str(file_path)])
              
              # Commit
              subprocess.run([
                  'git', 'commit', '-m', 
                  '🤖 Auto-fix code quality issues\n\nFixed by quality automation system'
              ])
          except Exception as e:
              print(f"Error committing fixes: {e}")
      
      def _generate_report(self):
          """Generate quality report."""
          report_data = {
              'stats': self.stats,
              'issues': [
                  {
                      'file': str(issue.file),
                      'line': issue.line,
                      'column': issue.column,
                      'severity': issue.severity,
                      'category': issue.category,
                      'message': issue.message,
                      'fix_available': issue.fix_available
                  }
                  for issue in sorted(self.issues, key=lambda i: (i.severity, str(i.file), i.line))
              ]
          }
          
          # Console output
          if 'console' in self.config['reporting']['formats']:
              self._print_console_report(report_data)
          
          # JSON output
          if 'json' in self.config['reporting']['formats']:
              output_path = self.config['reporting']['destinations']['file']['path']
              with open(output_path, 'w') as f:
                  json.dump(report_data, f, indent=2)
      
      def _print_console_report(self, report_data: Dict[str, Any]):
          """Print report to console."""
          print("\n" + "="*60)
          print("CODE QUALITY REPORT")
          print("="*60)
          
          stats = report_data['stats']
          print(f"\nFiles analyzed: {stats['files_analyzed']}")
          print(f"Total issues: {stats['total_issues']}")
          print(f"  - Errors: {stats['errors']}")
          print(f"  - Warnings: {stats['warnings']}")
          print(f"  - Info: {stats['info']}")
          print(f"Fixable issues: {stats['fixable_issues']}")
          print(f"Analysis time: {stats['analysis_time']}s")
          
          if report_data['issues']:
              print("\nTop issues:")
              for issue in report_data['issues'][:10]:
                  severity_symbol = {'error': '🔴', 'warning': '🟡', 'info': '🔵'}.get(issue['severity'], '⚪')
                  print(f"{severity_symbol} {issue['file']}:{issue['line']} - {issue['message']}")
  
  
  def main():
      """Main entry point."""
      parser = argparse.ArgumentParser(description='Code Quality Analysis')
      parser.add_argument('--config', default='quality/config.yaml', help='Config file path')
      parser.add_argument('--fix', action='store_true', help='Apply available fixes')
      parser.add_argument('--auto-commit', action='store_true', help='Commit fixes automatically')
      parser.add_argument('--format', default='console', choices=['console', 'json', 'github'], 
                          help='Output format')
      
      args = parser.parse_args()
      
      runner = QualityRunner(args.config)
      exit_code = runner.run(fix=args.fix, auto_commit=args.auto_commit)
      
      sys.exit(exit_code)
  
  
  if __name__ == '__main__':
      main()
validation:
  - command: "python -m quality.main --help"
  - expect: "usage: main.py"
```

### Task 7: Pre-commit Hook

```yaml
task_name: precommit_hook
action: CREATE
file: .git/hooks/pre-commit
changes: |
  #!/bin/bash
  # Pre-commit hook for code quality checks
  
  echo "🔍 Running code quality checks..."
  
  # Run quality analysis
  python -m quality.main --config quality/config.yaml
  
  if [ $? -ne 0 ]; then
      echo "❌ Code quality issues found!"
      echo "Run 'python -m quality.main --fix' to auto-fix issues"
      exit 1
  fi
  
  echo "✅ Code quality checks passed!"
  exit 0
validation:
  - command: "chmod +x .git/hooks/pre-commit"
  - expect: "No errors"
```

### Task 8: VSCode Integration

```yaml
task_name: vscode_integration
action: CREATE  
file: .vscode/settings.json
changes: |
  {
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": false,
    "python.linting.mypyEnabled": true,
    
    "python.linting.pylintArgs": [
      "--load-plugins=quality.vscode_plugin"
    ],
    
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length", "120"],
    
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    },
    
    "files.watcherExclude": {
      "**/__pycache__/**": true,
      "**/migrations/**": true
    },
    
    "python.analysis.extraPaths": [
      "./quality"
    ],
    
    "python.analysis.diagnosticSeverityOverrides": {
      "reportMissingImports": "error",
      "reportUndefinedVariable": "error",
      "reportUnusedImport": "warning"
    },
    
    "tasks": {
      "version": "2.0.0",
      "tasks": [
        {
          "label": "Run Quality Check",
          "type": "shell",
          "command": "python -m quality.main",
          "group": {
            "kind": "test",
            "isDefault": true
          },
          "presentation": {
            "reveal": "always",
            "panel": "dedicated"
          },
          "problemMatcher": {
            "owner": "python",
            "fileLocation": ["relative", "${workspaceFolder}"],
            "pattern": {
              "regexp": "^(.+):(\\d+):(\\d+):\\s+(error|warning|info):\\s+(.+)$",
              "file": 1,
              "line": 2,
              "column": 3,
              "severity": 4,
              "message": 5
            }
          }
        },
        {
          "label": "Fix Quality Issues",
          "type": "shell",
          "command": "python -m quality.main --fix",
          "group": "build"
        }
      ]
    }
  }
validation:
  - command: "cat .vscode/settings.json | head -10"
  - expect: "python.linting.enabled"
```

## Implementation Strategy

### Phase 1: Foundation (Week 1)
1. CREATE core framework (Task 1)
2. CREATE Django analyzer (Task 2)
3. CREATE security scanner (Task 3)
4. Test basic functionality

### Phase 2: Integration (Week 2)
1. CREATE GitHub Actions (Task 4)
2. CREATE configuration (Task 5)
3. CREATE main runner (Task 6)
4. Test CI/CD pipeline

### Phase 3: Developer Experience (Week 3)
1. CREATE pre-commit hook (Task 7)
2. CREATE VSCode integration (Task 8)
3. CREATE documentation
4. Team training

### Phase 4: Metrics & Optimization (Week 4)
1. MODIFY to add metrics tracking
2. CREATE dashboard
3. Optimize performance
4. Gather feedback

## Rollback Strategy

### Immediate Rollback
```bash
# Disable GitHub Actions
mv .github/workflows/code-quality.yml .github/workflows/code-quality.yml.disabled

# Remove pre-commit hook
rm .git/hooks/pre-commit

# Keep code for future use
git tag quality-system-v1
```

### Gradual Rollback
1. Disable auto-fix first
2. Keep reporting only
3. Remove CI/CD integration
4. Archive code

## Risk Mitigation

### Identified Risks
1. **False positives** → Configurable severity levels
2. **Performance impact** → Parallel processing, caching
3. **Team resistance** → Gradual rollout, training
4. **Breaking builds** → Warning-only mode initially

### Mitigation Plan
- Start with warning-only mode
- Whitelist known issues initially
- Provide escape hatches
- Regular review of rules

## Success Metrics

1. **Detection Rate**: 90% of issues caught before review
2. **Fix Rate**: 70% of issues auto-fixable
3. **Performance**: <2 minutes for full scan
4. **Adoption**: 100% of PRs using system
5. **Quality Trend**: 30% reduction in production issues

## Validation Gates

### Gate 1: Core Functionality
```bash
# Test analyzer registration
python -c "from quality.core import AnalyzerRegistry; print('Core working')"

# Test Django analyzer
python -c "from quality.django.analyzer import DjangoPatternAnalyzer; print('Django analyzer working')"

# Test security scanner
python -c "from quality.security.scanner import SecurityAnalyzer; print('Security working')"
```

### Gate 2: Integration Tests
```bash
# Run on sample file
echo "from django.db import models\nclass Test(models.Model):\n    objects.filter(user__profile__name='test')" > test.py
python -m quality.main
rm test.py
```

### Gate 3: CI/CD
- Create test PR
- Verify GitHub Actions run
- Check PR comment
- Verify quality gates

### Gate 4: Developer Experience
- Test pre-commit hook
- Test VSCode integration
- Verify auto-fix works
- Check performance

## Next Steps

1. Review objectives with team
2. Confirm priority order
3. Identify any missing requirements
4. Begin Phase 1 implementation
5. Schedule training sessions

## Dependencies

- Python 3.12+
- Django 4.2+
- Bandit
- Semgrep (optional)
- GitHub Actions
- VSCode (for IDE integration)

## Configuration Customization

Teams can customize by:
1. Editing quality/config.yaml
2. Adding custom rules in quality/rules/
3. Creating project-specific analyzers
4. Adjusting severity mappings

## Long-term Vision

This system will evolve to:
1. ML-based issue prediction
2. Auto-learning from code reviews
3. Integration with code review tools
4. Performance profiling integration
5. Security vulnerability database