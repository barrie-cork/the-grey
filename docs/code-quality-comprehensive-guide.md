# Comprehensive Guide to Code Quality Automation System

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Installation & Setup](#installation--setup)
4. [Core Components](#core-components)
5. [Usage Guide](#usage-guide)
6. [Analyzers in Detail](#analyzers-in-detail)
7. [Integration Points](#integration-points)
8. [Practical Examples](#practical-examples)
9. [Customization](#customization)
10. [Troubleshooting](#troubleshooting)
11. [Best Practices](#best-practices)
12. [Advanced Topics](#advanced-topics)

## Overview

The Code Quality Automation System is a comprehensive solution that transforms manual code quality checks into an automated, intelligent system that integrates seamlessly with your development workflow. It provides:

- **Automated Detection**: Finds issues before they reach production
- **Django-Specific Intelligence**: Understands Django patterns and anti-patterns
- **Security Scanning**: Proactive vulnerability detection
- **Auto-Fix Capabilities**: Fixes common issues automatically
- **Seamless Integration**: Works with Git, CI/CD, and IDEs

### Key Benefits

1. **Reduce Code Review Time by 50%**: Catch issues automatically
2. **Improve Code Quality**: Consistent standards across the team
3. **Enhance Security**: Proactive vulnerability scanning
4. **Boost Performance**: Detect N+1 queries and inefficient patterns
5. **Save Developer Time**: Auto-fix common issues

## Architecture

```
quality/
├── core/
│   └── __init__.py          # Base framework (Issue, Analyzer, Registry)
├── django/
│   └── analyzer.py          # Django-specific pattern detection
├── security/
│   └── scanner.py           # Security vulnerability scanning
├── reports/
│   └── generator.py         # Report generation (extensible)
├── metrics/
│   └── tracker.py           # Metrics tracking (extensible)
├── rules/                   # Custom rules directory
├── config.yaml             # Configuration file
├── main.py                 # Main entry point
└── README.md               # System documentation

Additional files:
.github/workflows/code-quality.yml  # CI/CD integration
.git/hooks/pre-commit              # Git hook
.vscode/settings.json             # VSCode integration
```

### Core Design Principles

1. **Pluggable Architecture**: Easy to add new analyzers
2. **AST-Based Analysis**: Deep understanding vs simple pattern matching
3. **Configuration-Driven**: Flexible without code changes
4. **Safe Auto-Fix**: Only applies proven, safe fixes
5. **Progressive Enhancement**: Start simple, add complexity as needed

## Installation & Setup

### Prerequisites

- Python 3.8+
- Django project
- Git (for hooks)
- pip

### Step 1: Install Dependencies

```bash
# Core dependencies
pip install pyyaml

# Analysis tools
pip install bandit             # Security scanning
pip install autoflake          # Import cleanup
pip install black              # Code formatting
pip install isort              # Import sorting
pip install mypy               # Type checking

# Optional but recommended
pip install semgrep            # Advanced pattern matching
```

### Step 2: Verify Installation

```bash
# Test core components
python -c "from quality.core import AnalyzerRegistry; print('✅ Core installed')"
python -c "from quality.django.analyzer import DjangoPatternAnalyzer; print('✅ Django analyzer ready')"
python -c "from quality.security.scanner import SecurityAnalyzer; print('✅ Security scanner ready')"
```

### Step 3: Initial Configuration

The system comes with sensible defaults in `quality/config.yaml`. Review and adjust:

```yaml
# Key settings to review
general:
  include_paths:
    - apps/           # Your Django apps directory
  exclude_paths:
    - "*/migrations/*"  # Don't analyze migrations

analyzers:
  django:
    enabled: true     # Enable Django-specific checks
  security:
    enabled: true     # Enable security scanning

severity:
  fail_on:
    - error          # CI/CD fails on errors only
```

### Step 4: Enable Integrations

```bash
# Git pre-commit hook (already created)
chmod +x .git/hooks/pre-commit

# Test the hook
echo "Testing pre-commit hook..."
.git/hooks/pre-commit

# VSCode (settings already configured)
# Just open VSCode in the project root
```

## Core Components

### 1. Issue Class

Represents a code quality issue:

```python
@dataclass
class Issue:
    file: Path                    # File containing the issue
    line: int                     # Line number
    column: int                   # Column number
    severity: str                 # 'error', 'warning', 'info'
    category: str                 # Issue category
    message: str                  # Human-readable description
    fix_available: bool = False   # Can be auto-fixed?
    fix_description: Optional[str] = None  # Fix description
```

### 2. Analyzer Base Class

All analyzers inherit from this:

```python
class Analyzer(ABC):
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
```

### 3. AnalyzerRegistry

Manages all available analyzers:

```python
registry = AnalyzerRegistry()
registry.register('django', DjangoPatternAnalyzer())
registry.register('security', SecurityAnalyzer())
```

## Usage Guide

### Basic Usage

```bash
# Run analysis on entire codebase
python -m quality.main

# Analyze specific app
python -m quality.main --app results_manager

# Auto-fix issues
python -m quality.main --fix

# Dry run (see what would be fixed)
python -m quality.main --fix --dry-run

# Different output format
python -m quality.main --format json > report.json
```

### Command Line Options

```
usage: main.py [-h] [--config CONFIG] [--fix] [--auto-commit] 
               [--format {console,json,github}]

options:
  -h, --help            Show help message
  --config CONFIG       Config file path (default: quality/config.yaml)
  --fix                 Apply available fixes
  --auto-commit         Commit fixes automatically
  --format              Output format (default: console)
```

### Understanding Output

#### Console Output
```
============================================================
CODE QUALITY REPORT
============================================================

Files analyzed: 45
Total issues: 12
  - Errors: 2
  - Warnings: 7
  - Info: 3
Fixable issues: 8
Analysis time: 1.2s

Top issues:
🔴 apps/results_manager/views.py:115 - Use of .extra() query method
🟡 apps/results_manager/models.py:25 - Missing select_related() optimization
🔵 apps/accounts/views.py:10 - Unused import: JsonResponse
```

#### JSON Output
```json
{
  "stats": {
    "files_analyzed": 45,
    "total_issues": 12,
    "errors": 2,
    "warnings": 7,
    "info": 3,
    "fixable_issues": 8,
    "analysis_time": 1.2
  },
  "issues": [
    {
      "file": "apps/results_manager/views.py",
      "line": 115,
      "column": 12,
      "severity": "warning",
      "category": "maintainability",
      "message": "Use of .extra() is discouraged",
      "fix_available": false
    }
  ]
}
```

## Analyzers in Detail

### Django Analyzer

Detects Django-specific anti-patterns and issues.

#### N+1 Query Detection

```python
# Detected pattern:
for result in results:
    print(result.user.profile.name)  # N+1 query!

# Issue reported:
"Potential N+1 query detected. Consider using select_related() or prefetch_related()"

# Suggested fix:
results = results.select_related('user__profile')
for result in results:
    print(result.user.profile.name)  # Efficient!
```

#### Missing Query Optimizations

```python
# Detected:
posts = Post.objects.filter(published=True)
# Later accessing foreign keys

# Suggested:
posts = Post.objects.filter(published=True).select_related('author')
```

#### Inefficient Query Patterns

```python
# Detected - .extra() usage:
queryset.extra(
    where=["LOWER(name) LIKE %s"],
    params=['%john%']
)

# Suggested - Django ORM:
queryset.filter(name__icontains='john')
```

#### Security Issues

```python
# Detected patterns:
@csrf_exempt  # CSRF protection disabled
def my_view(request):
    pass

# Template issues:
{{ user_input|safe }}  # Unsafe rendering
```

#### Deprecated Patterns

```python
# Detected:
from django.conf.urls import url  # Deprecated

# Auto-fixed to:
from django.urls import path
```

### Security Analyzer

Integrates Bandit and adds custom security checks.

#### Hardcoded Secrets

```python
# Detected:
API_KEY = "sk_live_abcd1234"  # Hardcoded secret!

# Suggested:
API_KEY = os.environ.get('API_KEY')
```

#### Unsafe YAML Loading

```python
# Detected:
data = yaml.load(file_content)  # Unsafe!

# Auto-fixed to:
data = yaml.safe_load(file_content)  # Safe!
```

#### Debug in Production

```python
# Detected in production.py:
DEBUG = True  # Security risk!

# Auto-fixed to:
DEBUG = False
```

## Integration Points

### 1. Pre-commit Hook

Located at `.git/hooks/pre-commit`:

```bash
#!/bin/bash
echo "🔍 Running code quality checks..."
python -m quality.main --config quality/config.yaml

if [ $? -ne 0 ]; then
    echo "❌ Code quality issues found!"
    echo "Run 'python -m quality.main --fix' to auto-fix issues"
    exit 1
fi

echo "✅ Code quality checks passed!"
exit 0
```

To bypass temporarily:
```bash
git commit --no-verify -m "Emergency fix"
```

### 2. GitHub Actions

The workflow (`.github/workflows/code-quality.yml`) runs on:
- All pushes to main, develop, feature/*
- All pull requests

Features:
- Runs quality checks
- Posts PR comments with results
- Can auto-fix and commit
- Runs security scans
- Fails CI on critical issues

### 3. VSCode Integration

Settings in `.vscode/settings.json`:
- Real-time linting
- Format on save
- Custom tasks
- Problem matching

VSCode Tasks:
- `Ctrl+Shift+P` → "Run Quality Check"
- `Ctrl+Shift+P` → "Fix Quality Issues"

### 4. Manual CLI

For on-demand analysis:
```bash
# Full analysis
python -m quality.main

# Quick fix
python -m quality.main --fix --app myapp
```

## Practical Examples

### Example 1: Fixing N+1 Queries

**Problem Code:**
```python
# views.py
def get_results(request):
    results = ProcessedResult.objects.filter(session_id=session_id)
    
    for result in results:
        # This causes N+1 queries!
        duplicate_count = result.duplicate_group.results.count()
```

**Detection:**
```
🟡 apps/results_manager/views.py:125 - Potential N+1 query detected
   Consider using select_related() or prefetch_related()
```

**Fix:**
```python
# views.py
def get_results(request):
    results = ProcessedResult.objects.filter(
        session_id=session_id
    ).select_related('duplicate_group').prefetch_related(
        'duplicate_group__results'
    )
    
    for result in results:
        # Now efficient!
        duplicate_count = result.duplicate_group.results.count()
```

### Example 2: Replacing .extra() Queries

**Problem Code:**
```python
# Complex .extra() query
queryset = queryset.extra(
    where=["LOWER(SUBSTRING(url FROM 'https?://([^/]+)')) LIKE %s"],
    params=[f"%{domain.lower()}%"]
)
```

**Better Approach:**
```python
# Option 1: Simple contains
queryset = queryset.filter(url__icontains=domain)

# Option 2: Regex
queryset = queryset.filter(
    url__iregex=rf"https?://[^/]*{domain}"
)

# Option 3: Annotation
from django.db.models.functions import Substr, Lower
queryset = queryset.annotate(
    domain=Lower(Substr('url', 9))  # Skip 'https://'
).filter(domain__contains=domain.lower())
```

### Example 3: Security Fix

**Problem Code:**
```python
# Unsafe deserialization
import yaml
config = yaml.load(open('config.yml'))
```

**Auto-fixed:**
```python
# Safe deserialization
import yaml
config = yaml.safe_load(open('config.yml'))
```

## Customization

### Adding Custom Rules

Edit `quality/config.yaml`:

```yaml
rules:
  project_rules:
    - id: use_uuid_pk
      pattern: "id = models.AutoField"
      message: "Use UUIDField for primary keys per project standard"
      severity: error
      
    - id: require_docstrings
      pattern: "def \\w+\\([^)]*\\):\\s*[^\"']"
      message: "Functions must have docstrings"
      severity: warning
```

### Creating a Custom Analyzer

```python
# quality/custom/my_analyzer.py
from quality.core import Analyzer, Issue
import ast

class MyProjectAnalyzer(Analyzer):
    """Custom analyzer for project-specific patterns."""
    
    def analyze(self, file_path, content, ast_tree):
        issues = []
        
        # Example: Detect print statements
        for node in ast.walk(ast_tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'print':
                    issues.append(Issue(
                        file=file_path,
                        line=node.lineno,
                        column=node.col_offset,
                        severity='warning',
                        category='debug',
                        message='Remove print statement before committing',
                        fix_available=True,
                        fix_description='Remove line'
                    ))
        
        return issues
    
    def can_fix(self, issue):
        return issue.fix_available
    
    def fix(self, file_path, issue):
        # Implementation of fix
        pass

# Register in main.py
from quality.custom.my_analyzer import MyProjectAnalyzer
registry.register('custom', MyProjectAnalyzer())
```

### Adjusting Severity Levels

```yaml
severity:
  mappings:
    # Upgrade specific issues
    n_plus_one_query: error      # Was warning
    missing_docstring: warning   # Was info
    
  # Change failure criteria
  fail_on:
    - error
    - warning  # Now fails on warnings too
```

## Troubleshooting

### Common Issues

#### 1. ModuleNotFoundError: yaml

**Solution:**
```bash
pip install pyyaml
```

#### 2. Bandit not found

**Solution:**
```bash
pip install bandit
# Or disable in config:
# analyzers.security.enabled: false
```

#### 3. Permission denied on pre-commit

**Solution:**
```bash
chmod +x .git/hooks/pre-commit
```

#### 4. Too many false positives

**Solution:**
```yaml
# Adjust config.yaml
severity:
  max_warnings: 100  # Increase threshold
  
# Or exclude specific patterns
general:
  exclude_paths:
    - "*/tests/*"  # Don't analyze tests
```

#### 5. Slow analysis

**Solution:**
```yaml
# Increase workers
general:
  workers: 8  # Use more CPU cores
  
# Or limit scope
general:
  include_paths:
    - apps/critical/  # Only critical apps
```

### Debug Mode

For troubleshooting:
```bash
# Verbose output
python -m quality.main --verbose

# Debug specific file
python -m quality.main --debug --file apps/myapp/views.py

# Check configuration
python -m quality.main --show-config
```

## Best Practices

### 1. Progressive Adoption

```bash
# Week 1: Warning only
severity:
  fail_on: []  # Don't fail CI

# Week 2: Fix existing issues
python -m quality.main --fix

# Week 3: Enable failures
severity:
  fail_on: [error]

# Week 4: Strict mode
severity:
  fail_on: [error, warning]
```

### 2. Team Onboarding

1. **Training Session**: Demo the tools
2. **Pilot Project**: Start with one app
3. **Gradual Rollout**: Enable per team
4. **Feedback Loop**: Adjust rules based on feedback

### 3. Configuration Management

```yaml
# Use different configs per environment
# quality/config.dev.yaml - Lenient
# quality/config.prod.yaml - Strict

# Override via environment
QUALITY_CONFIG=quality/config.prod.yaml python -m quality.main
```

### 4. Custom Rules Strategy

1. **Document patterns**: What and why
2. **Test thoroughly**: Avoid false positives
3. **Provide fixes**: Make it easy to comply
4. **Review regularly**: Rules can become outdated

## Advanced Topics

### 1. Performance Optimization

```python
# Parallel analysis (config.yaml)
general:
  workers: auto  # Uses CPU count
  cache_enabled: true
  cache_ttl: 3600

# File-based caching
quality/
  .cache/  # AST cache directory
```

### 2. CI/CD Optimization

```yaml
# Only analyze changed files
- name: Get changed files
  id: changed-files
  uses: tj-actions/changed-files@v35

- name: Run quality check
  run: |
    python -m quality.main --files ${{ steps.changed-files.outputs.all_changed_files }}
```

### 3. Metrics and Reporting

```python
# Track quality over time
quality/metrics/
  2024-01-15.json
  2024-01-16.json
  
# Generate trend report
python -m quality.metrics.trend --days 30
```

### 4. Integration with Other Tools

```yaml
# SonarQube integration
reporting:
  destinations:
    sonarqube:
      enabled: true
      url: https://sonar.company.com
      token: ${SONAR_TOKEN}
```

### 5. Machine Learning Integration

```python
# Future: Learn from code reviews
quality/ml/
  pattern_learner.py  # Learns new patterns
  fix_suggester.py    # Suggests fixes
```

## Conclusion

The Code Quality Automation System provides a comprehensive solution for maintaining high code standards. By combining AST-based analysis, Django-specific intelligence, security scanning, and seamless integrations, it transforms code quality from a manual chore into an automated assistant.

Key takeaways:
- Start simple, expand gradually
- Customize for your project's needs
- Use automation to enforce standards
- Focus on education, not punishment
- Measure and improve continuously

For support or contributions, see the project README and contributing guidelines.