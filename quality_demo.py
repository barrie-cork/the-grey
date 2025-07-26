#!/usr/bin/env python3
"""
Demo script to run quality checks on specific files.
"""
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from quality.core import AnalyzerRegistry
from quality.django.analyzer import DjangoPatternAnalyzer
from quality.security.scanner import SecurityAnalyzer
import ast

def analyze_file(file_path: str):
    """Analyze a single file and display results."""
    path = Path(file_path)
    
    if not path.exists():
        print(f"❌ File not found: {file_path}")
        return
    
    print(f"\n📄 Analyzing: {file_path}")
    print("=" * 60)
    
    # Create registry and register analyzers
    registry = AnalyzerRegistry()
    registry.register('django', DjangoPatternAnalyzer())
    registry.register('security', SecurityAnalyzer())
    
    # Read file content
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse AST
        tree = ast.parse(content)
        
        # Run all analyzers
        all_issues = []
        for name, analyzer in registry.get_all().items():
            print(f"\n🔍 Running {name} analyzer...")
            issues = analyzer.analyze(path, content, tree)
            all_issues.extend(issues)
            
            if issues:
                for issue in issues:
                    severity_symbol = {
                        'error': '🔴',
                        'warning': '🟡',
                        'info': '🔵'
                    }.get(issue.severity, '⚪')
                    
                    print(f"{severity_symbol} Line {issue.line}: {issue.message}")
                    if issue.fix_available:
                        print(f"   ✅ Auto-fix available: {issue.fix_description}")
            else:
                print("   ✨ No issues found!")
        
        # Summary
        print(f"\n📊 Summary:")
        print(f"   Total issues: {len(all_issues)}")
        print(f"   Fixable issues: {sum(1 for i in all_issues if i.fix_available)}")
        
        # Apply fixes if any
        if any(i.fix_available for i in all_issues):
            response = input("\n🔧 Apply available fixes? (y/n): ")
            if response.lower() == 'y':
                for name, analyzer in registry.get_all().items():
                    for issue in all_issues:
                        if analyzer.can_fix(issue):
                            try:
                                fixed_content = analyzer.fix(path, issue)
                                with open(path, 'w') as f:
                                    f.write(fixed_content)
                                print(f"✅ Fixed: {issue.message}")
                            except Exception as e:
                                print(f"❌ Error fixing: {e}")
                
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Demo with problematic file
        print("Usage: python quality_demo.py <file_path>")
        print("\nDemo mode - analyzing known problematic file...")
        analyze_file("apps/results_manager/views.py")
    else:
        analyze_file(sys.argv[1])