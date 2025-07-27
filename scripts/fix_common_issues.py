#!/usr/bin/env python3
"""
Fix Common Code Issues
Automatically fixes some common code quality issues.

python -m quality.main --fix

  1. Immediate Actions:
  # Install dependencies
  pip install pyyaml bandit autoflake black isort

  # Run first analysis
  python -m quality.main

  # Auto-fix safe issues
  python -m quality.main --fix
  
Usage:
    python scripts/fix_common_issues.py [--dry-run] [--app APP_NAME]
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import List, Tuple

class CodeFixer:
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.fixes_applied = 0
        
    def fix_file(self, filepath: Path) -> bool:
        """Fix issues in a single file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            content = original_content
            
            # Apply fixes
            content = self._fix_hardcoded_years(content, filepath)
            content = self._fix_unused_imports(content, filepath)
            content = self._fix_deprecated_comments(content, filepath)
            
            # Write back if changed
            if content != original_content:
                if not self.dry_run:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"Fixed: {filepath}")
                else:
                    print(f"Would fix: {filepath}")
                self.fixes_applied += 1
                return True
                
        except Exception as e:
            print(f"Error fixing {filepath}: {e}")
            
        return False
    
    def _fix_hardcoded_years(self, content: str, filepath: Path) -> str:
        """Replace hardcoded years with dynamic calculations"""
        lines = content.split('\n')
        new_lines = []
        
        for line in lines:
            # Skip if it's in a comment or string
            if '#' in line or 'migration' in str(filepath):
                new_lines.append(line)
                continue
                
            # Replace common patterns
            new_line = line
            
            # Pattern: year = 2024
            new_line = re.sub(
                r'\b(year\s*=\s*)202[0-9]\b',
                r'\1datetime.now().year',
                new_line
            )
            
            # Pattern: if year >= 2020
            new_line = re.sub(
                r'(\s*)(if\s+.*?)\b(202[0-9])\b',
                lambda m: f"{m.group(1)}{m.group(2)}(datetime.now().year - {datetime.now().year - int(m.group(3))})",
                new_line
            )
            
            # Add import if we made changes and it's not there
            if new_line != line and 'datetime' in new_line:
                # Check if datetime is imported
                if 'from datetime import datetime' not in content and 'import datetime' not in content:
                    # Add import at the top
                    content = 'from datetime import datetime\n' + content
            
            new_lines.append(new_line)
            
        return '\n'.join(new_lines)
    
    def _fix_unused_imports(self, content: str, filepath: Path) -> str:
        """Remove obviously unused imports"""
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return content
            
        lines = content.split('\n')
        
        # Collect all names used in the file
        used_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                used_names.add(node.attr)
                if isinstance(node.value, ast.Name):
                    used_names.add(node.value.id)
        
        # Mark lines to remove
        lines_to_remove = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                # Check each imported name
                if node.names:
                    unused_names = []
                    for alias in node.names:
                        name = alias.asname if alias.asname else alias.name
                        if name not in used_names and name != '*':
                            unused_names.append(name)
                    
                    # If all imports from this line are unused, mark for removal
                    if len(unused_names) == len(node.names):
                        lines_to_remove.add(node.lineno - 1)
        
        # Remove marked lines
        new_lines = []
        for i, line in enumerate(lines):
            if i not in lines_to_remove:
                new_lines.append(line)
            else:
                print(f"  Removing unused import: {line.strip()}")
                
        return '\n'.join(new_lines)
    
    def _fix_deprecated_comments(self, content: str, filepath: Path) -> str:
        """Clean up deprecated TODOs and FIXMEs"""
        lines = content.split('\n')
        new_lines = []
        
        for line in lines:
            # Remove TODO: Remove comments
            if re.search(r'#\s*TODO:?\s*[Rr]emove', line):
                print(f"  Removing deprecated TODO: {line.strip()}")
                continue
                
            # Remove empty DEPRECATED comments
            if re.search(r'^\s*#\s*DEPRECATED\s*$', line):
                print(f"  Removing empty DEPRECATED comment")
                continue
                
            new_lines.append(line)
            
        return '\n'.join(new_lines)


def main():
    parser = argparse.ArgumentParser(description='Fix common code issues')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Show what would be fixed without making changes')
    parser.add_argument('--fix', action='store_true',
                       help='Actually apply fixes (disables dry-run)')
    parser.add_argument('--app', type=str,
                       help='Specific app to fix')
    
    args = parser.parse_args()
    
    # Override dry_run if --fix is specified
    dry_run = not args.fix
    
    fixer = CodeFixer(dry_run=dry_run)
    
    # Determine path to scan
    if args.app:
        search_path = Path(f'apps/{args.app}')
    else:
        search_path = Path('apps')
    
    if not search_path.exists():
        print(f"Error: Path {search_path} does not exist")
        return 1
    
    print(f"{'DRY RUN - ' if dry_run else ''}Scanning {search_path} for fixes...")
    print()
    
    # Process Python files
    for py_file in search_path.rglob('*.py'):
        if 'migrations' not in str(py_file) and '__pycache__' not in str(py_file):
            fixer.fix_file(py_file)
    
    print()
    print(f"{'Would apply' if dry_run else 'Applied'} fixes to {fixer.fixes_applied} files")
    
    if dry_run and fixer.fixes_applied > 0:
        print("\nRun with --fix flag to apply these changes")
    
    return 0


if __name__ == "__main__":
    # Add import that might be needed
    from datetime import datetime
    sys.exit(main())