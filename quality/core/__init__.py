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