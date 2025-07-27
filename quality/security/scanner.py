"""
Security scanner integration for Django projects.
"""
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Any
import ast

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