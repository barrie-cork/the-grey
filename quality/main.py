"""
Main entry point for code quality analysis.
"""
import argparse
import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add the parent directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml

from quality.core import AnalyzerRegistry, Issue
from quality.django.analyzer import DjangoPatternAnalyzer
from quality.security.scanner import SecurityAnalyzer
# from quality.reports.generator import ReportGenerator  # Not implemented yet

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