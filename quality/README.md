# Code Quality Automation System

## Overview

This is a comprehensive automated code quality system that transforms manual code quality checks into a fully automated, CI/CD-integrated system. It proactively detects, reports, and fixes code quality issues across the Django codebase.

## Features

### 🔍 Advanced Analysis
- **AST-based pattern detection** - Deep code analysis using Python's Abstract Syntax Tree
- **Django-specific checks** - N+1 queries, missing select_related, deprecated patterns
- **Security scanning** - Integration with Bandit and custom security checks
- **Performance analysis** - Inefficient query detection and optimization suggestions

### 🤖 Automation
- **GitHub Actions integration** - Automated checks on every PR
- **Pre-commit hooks** - Catch issues before they're committed
- **Auto-fix capabilities** - Automatic fixes for common issues
- **VSCode integration** - Real-time feedback in your editor

### 📊 Reporting
- **Multiple output formats** - Console, JSON, HTML, GitHub PR comments
- **Quality metrics tracking** - Historical trends and team metrics
- **Severity-based filtering** - Focus on what matters most

## Quick Start

### Installation

1. Install dependencies:
```bash
pip install pyyaml bandit autoflake black isort
```

2. Run quality check:
```bash
python -m quality.main
```

3. Auto-fix issues:
```bash
python -m quality.main --fix
```

### Configuration

Edit `quality/config.yaml` to customize:
- Which analyzers to run
- Severity levels
- Auto-fix behavior
- Integration settings

## Architecture

```
quality/
├── core/              # Core framework
│   └── __init__.py    # Base classes (Issue, Analyzer, Registry)
├── django/            # Django-specific
│   └── analyzer.py    # Django pattern detection
├── security/          # Security scanning
│   └── scanner.py     # Bandit integration + custom checks
├── reports/           # Report generation
│   └── generator.py   # (To be implemented)
├── config.yaml        # Configuration
└── main.py           # Entry point
```

### Core Components

1. **Analyzer Framework**
   - Base `Analyzer` class for creating custom analyzers
   - `Issue` dataclass for representing problems
   - `AnalyzerRegistry` for managing analyzers

2. **Django Analyzer**
   - Detects N+1 query problems
   - Finds missing query optimizations
   - Identifies deprecated Django patterns
   - Checks for security issues (CSRF, unsafe templates)

3. **Security Scanner**
   - Integrates with Bandit for Python security
   - Custom checks for hardcoded secrets
   - Unsafe YAML loading detection
   - Production DEBUG=True detection

4. **Main Runner**
   - Loads configuration
   - Collects files to analyze
   - Runs all registered analyzers
   - Applies fixes when requested
   - Generates reports

## CI/CD Integration

### GitHub Actions

The system includes a comprehensive GitHub Actions workflow that:
1. Runs quality checks on every PR
2. Comments with quality report
3. Runs security scans with Bandit and Semgrep
4. Auto-fixes issues on PRs when possible

### Pre-commit Hook

Automatically runs quality checks before commits:
```bash
# Already installed at .git/hooks/pre-commit
```

## VSCode Integration

The system integrates with VSCode to provide:
- Real-time linting feedback
- Custom tasks for quality checks
- Problem matcher for parsing output
- Format on save with Black

## Extending the System

### Adding a New Analyzer

```python
from quality.core import Analyzer, Issue

class MyAnalyzer(Analyzer):
    def analyze(self, file_path, content, ast_tree):
        issues = []
        # Your analysis logic here
        return issues
    
    def can_fix(self, issue):
        return issue.fix_available
    
    def fix(self, file_path, issue):
        # Your fix logic here
        return fixed_content
```

### Adding Custom Rules

Edit `quality/config.yaml`:
```yaml
rules:
  custom_rules:
    - id: my_rule
      pattern: "pattern_to_match"
      message: "Issue description"
      severity: warning
```

## Detected Issues

### Django-Specific
- **N+1 Queries** - Detects potential database performance issues
- **Missing Optimizations** - Suggests select_related/prefetch_related
- **Inefficient Queries** - Flags .extra() and raw SQL usage
- **Security Issues** - CSRF exemptions, unsafe template rendering
- **Deprecated Patterns** - Old Django imports and patterns

### Security
- **Hardcoded Secrets** - API keys, passwords, secret keys
- **Unsafe YAML** - yaml.load() without safe loader
- **Debug in Production** - DEBUG=True in production settings

### General Python
- **Unused Imports** - Can be auto-fixed
- **Syntax Errors** - Parse-time detection
- **Complexity** - Overly complex methods

## Metrics and Success Criteria

- **Detection Rate**: 90% of issues caught before review
- **Fix Rate**: 70% of issues auto-fixable
- **Performance**: <2 minutes for full scan
- **Adoption**: 100% of PRs using system

## Roadmap

- [ ] Add performance profiling integration
- [ ] ML-based issue prediction
- [ ] Integration with code review tools
- [ ] Custom rule learning from reviews
- [ ] Real-time IDE feedback improvements

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError: yaml**
   - Install PyYAML: `pip install pyyaml`

2. **Bandit not found**
   - Install Bandit: `pip install bandit`

3. **Permission denied on pre-commit**
   - Make executable: `chmod +x .git/hooks/pre-commit`

## Contributing

1. Add analyzers in their own module
2. Follow the Analyzer base class interface
3. Add tests for new checks
4. Update configuration schema
5. Document new features

## License

This quality system is part of the Thesis Grey project.