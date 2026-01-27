#!/usr/bin/env python3
"""
Python AST Analyzer

Deep analysis using Python's AST module:
- Function metrics (length, complexity, parameters)
- Dead code detection (unused imports, functions, variables)
- Duplicate code detection (AST structure comparison)
- Circular import detection
- Security pattern detection
- Type hint coverage

Usage: python3 analyze_python.py <path> [--output file.json] [--summary]
"""

import os
import re
import sys
import ast
import json
import hashlib
import argparse
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Set, Optional, Tuple, Any
from collections import defaultdict

# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class FunctionMetrics:
    name: str
    file: str
    line_start: int
    line_end: int
    line_count: int
    parameter_count: int
    complexity: int
    nesting_depth: int
    is_async: bool
    is_method: bool
    has_docstring: bool
    has_type_hints: bool
    decorators: List[str]

@dataclass
class ClassMetrics:
    name: str
    file: str
    line_start: int
    line_end: int
    method_count: int
    has_docstring: bool

@dataclass
class FileMetrics:
    path: str
    line_count: int
    code_lines: int
    functions: List[FunctionMetrics]
    classes: List[ClassMetrics]
    imports: List[Dict]
    exports: List[str]  # Module-level names
    is_test: bool
    type_hint_coverage: float

@dataclass
class DeadCodeItem:
    file: str
    line: int
    kind: str  # unused-import, unused-function, unused-variable, unreachable
    name: str
    description: str

@dataclass
class DuplicateCandidate:
    file1: str
    line1_start: int
    line1_end: int
    file2: str
    line2_start: int  
    line2_end: int
    similarity: float
    description: str

@dataclass
class CircularDep:
    cycle: List[str]
    description: str

@dataclass
class PotentialIssue:
    category: str
    pattern: str
    file: str
    line: int
    code: str
    description: str

# ============================================================================
# Configuration
# ============================================================================

IGNORE_DIRS = {
    '__pycache__', 'venv', '.venv', 'env', '.env', 'node_modules',
    '.git', '.svn', 'dist', 'build', 'eggs', '.eggs', '.tox',
    '.mypy_cache', '.pytest_cache', 'htmlcov', 'site-packages'
}

TEST_PATTERNS = ['test_', '_test.py', 'tests/', 'test/', 'conftest']

# ============================================================================
# File Collection
# ============================================================================

def collect_files(root_path: Path, max_files: int = 500) -> List[Path]:
    """Collect Python files to analyze."""
    files = []
    
    if root_path.is_file():
        return [root_path]
    
    for filepath in root_path.rglob('*.py'):
        if any(ignored in filepath.parts for ignored in IGNORE_DIRS):
            continue
        files.append(filepath)
        if len(files) >= max_files:
            break
    
    return files

# ============================================================================
# AST Analysis
# ============================================================================

class ComplexityVisitor(ast.NodeVisitor):
    """Calculate cyclomatic complexity."""
    
    def __init__(self):
        self.complexity = 1
    
    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_With(self, node):
        self.complexity += 1
        self.generic_visit(node)
    
    def visit_BoolOp(self, node):
        self.complexity += len(node.values) - 1
        self.generic_visit(node)
    
    def visit_comprehension(self, node):
        self.complexity += 1
        self.complexity += len(node.ifs)
        self.generic_visit(node)
    
    def visit_IfExp(self, node):  # Ternary
        self.complexity += 1
        self.generic_visit(node)


class NestingVisitor(ast.NodeVisitor):
    """Calculate maximum nesting depth."""
    
    def __init__(self):
        self.max_depth = 0
        self.current_depth = 0
    
    def visit_If(self, node):
        self._enter_nested(node)
    
    def visit_For(self, node):
        self._enter_nested(node)
    
    def visit_While(self, node):
        self._enter_nested(node)
    
    def visit_With(self, node):
        self._enter_nested(node)
    
    def visit_Try(self, node):
        self._enter_nested(node)
    
    def _enter_nested(self, node):
        self.current_depth += 1
        self.max_depth = max(self.max_depth, self.current_depth)
        self.generic_visit(node)
        self.current_depth -= 1


class NameCollector(ast.NodeVisitor):
    """Collect all name usages in a scope."""
    
    def __init__(self):
        self.used_names: Set[str] = set()
        self.defined_names: Set[str] = set()
        self.imported_names: Dict[str, int] = {}  # name -> line
    
    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.used_names.add(node.id)
        elif isinstance(node.ctx, ast.Store):
            self.defined_names.add(node.id)
        self.generic_visit(node)
    
    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname or alias.name.split('.')[0]
            self.imported_names[name] = node.lineno
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node):
        for alias in node.names:
            name = alias.asname or alias.name
            self.imported_names[name] = node.lineno
        self.generic_visit(node)
    
    def visit_Attribute(self, node):
        # Track attribute access like `os.path`
        if isinstance(node.value, ast.Name):
            self.used_names.add(node.value.id)
        self.generic_visit(node)


def calculate_complexity(node: ast.AST) -> int:
    """Calculate cyclomatic complexity of a function."""
    visitor = ComplexityVisitor()
    visitor.visit(node)
    return visitor.complexity


def calculate_nesting(node: ast.AST) -> int:
    """Calculate max nesting depth of a function."""
    visitor = NestingVisitor()
    visitor.visit(node)
    return visitor.max_depth


def has_type_hints(node: ast.FunctionDef) -> bool:
    """Check if function has type hints."""
    # Check return type
    has_return = node.returns is not None
    
    # Check parameters
    has_params = any(arg.annotation is not None for arg in node.args.args)
    
    return has_return or has_params


def analyze_file(filepath: Path, content: str) -> Optional[FileMetrics]:
    """Analyze a Python file."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return None
    
    lines = content.split('\n')
    is_test = any(p in str(filepath).lower() for p in TEST_PATTERNS)
    
    functions: List[FunctionMetrics] = []
    classes: List[ClassMetrics] = []
    imports: List[Dict] = []
    module_names: List[str] = []
    
    # Collect all name usages
    collector = NameCollector()
    collector.visit(tree)
    
    type_hint_count = 0
    total_functions = 0
    
    for node in ast.walk(tree):
        # Functions
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            total_functions += 1
            
            # Skip if it's a method (will be handled with class)
            is_method = False
            for parent in ast.walk(tree):
                if isinstance(parent, ast.ClassDef):
                    for item in parent.body:
                        if item is node:
                            is_method = True
                            break
            
            decorators = []
            for dec in node.decorator_list:
                if isinstance(dec, ast.Name):
                    decorators.append(dec.id)
                elif isinstance(dec, ast.Attribute):
                    decorators.append(dec.attr)
                elif isinstance(dec, ast.Call):
                    if isinstance(dec.func, ast.Name):
                        decorators.append(dec.func.id)
                    elif isinstance(dec.func, ast.Attribute):
                        decorators.append(dec.func.attr)
            
            has_hints = has_type_hints(node)
            if has_hints:
                type_hint_count += 1
            
            params = [a.arg for a in node.args.args if a.arg not in ('self', 'cls')]
            
            func = FunctionMetrics(
                name=node.name,
                file=str(filepath),
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                line_count=(node.end_lineno or node.lineno) - node.lineno + 1,
                parameter_count=len(params),
                complexity=calculate_complexity(node),
                nesting_depth=calculate_nesting(node),
                is_async=isinstance(node, ast.AsyncFunctionDef),
                is_method=is_method,
                has_docstring=ast.get_docstring(node) is not None,
                has_type_hints=has_hints,
                decorators=decorators
            )
            functions.append(func)
            
            if not is_method:
                module_names.append(node.name)
        
        # Classes
        elif isinstance(node, ast.ClassDef):
            method_count = sum(1 for item in node.body 
                             if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)))
            
            cls = ClassMetrics(
                name=node.name,
                file=str(filepath),
                line_start=node.lineno,
                line_end=node.end_lineno or node.lineno,
                method_count=method_count,
                has_docstring=ast.get_docstring(node) is not None
            )
            classes.append(cls)
            module_names.append(node.name)
        
        # Imports
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    'module': alias.name,
                    'name': alias.asname or alias.name,
                    'line': node.lineno,
                    'is_used': (alias.asname or alias.name.split('.')[0]) in collector.used_names
                })
        
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imports.append({
                    'module': node.module or '',
                    'name': alias.asname or alias.name,
                    'line': node.lineno,
                    'is_used': (alias.asname or alias.name) in collector.used_names
                })
        
        # Module-level variables
        elif isinstance(node, ast.Assign) and node.col_offset == 0:
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    module_names.append(target.id)
    
    # Count code lines
    code_lines = 0
    in_docstring = False
    for line in lines:
        stripped = line.strip()
        if '"""' in stripped or "'''" in stripped:
            if stripped.count('"""') == 2 or stripped.count("'''") == 2:
                pass  # Single line docstring
            else:
                in_docstring = not in_docstring
        if stripped and not stripped.startswith('#') and not in_docstring:
            code_lines += 1
    
    type_coverage = type_hint_count / total_functions if total_functions > 0 else 0.0
    
    return FileMetrics(
        path=str(filepath),
        line_count=len(lines),
        code_lines=code_lines,
        functions=functions,
        classes=classes,
        imports=imports,
        exports=module_names,
        is_test=is_test,
        type_hint_coverage=round(type_coverage, 2)
    )

# ============================================================================
# Dead Code Detection
# ============================================================================

def find_dead_code(files: List[FileMetrics]) -> List[DeadCodeItem]:
    """Find unused imports, functions, and variables."""
    dead_code = []
    
    # Track all imports across files
    all_imported_from: Dict[str, Set[str]] = defaultdict(set)  # module -> names imported
    
    for file in files:
        for imp in file.imports:
            all_imported_from[imp['module']].add(imp['name'])
    
    for file in files:
        if file.is_test:
            continue
        
        # Unused imports
        for imp in file.imports:
            if not imp.get('is_used', True):
                dead_code.append(DeadCodeItem(
                    file=file.path,
                    line=imp['line'],
                    kind='unused-import',
                    name=imp['name'],
                    description=f"Import '{imp['name']}' from '{imp['module']}' is never used"
                ))
        
        # TODO: Add more dead code detection
        # - Unused functions (not called or imported elsewhere)
        # - Unused variables
        # - Unreachable code after return
    
    return dead_code

# ============================================================================
# Circular Import Detection
# ============================================================================

def find_circular_imports(files: List[FileMetrics], root_path: Path) -> List[CircularDep]:
    """Detect circular imports."""
    circular = []
    
    # Build import graph
    graph: Dict[str, Set[str]] = defaultdict(set)
    file_paths = {f.path for f in files}
    
    for file in files:
        file_module = str(Path(file.path).relative_to(root_path)).replace('/', '.').replace('\\', '.').replace('.py', '')
        
        for imp in file.imports:
            # Try to resolve to a local file
            imp_module = imp['module']
            
            # Check if it's a relative import to another analyzed file
            for other in file_paths:
                other_module = str(Path(other).relative_to(root_path)).replace('/', '.').replace('\\', '.').replace('.py', '')
                if other_module.endswith(imp_module) or imp_module.endswith(other_module.split('.')[-1]):
                    graph[file_module].add(other_module)
                    break
    
    # DFS to find cycles
    visited = set()
    rec_stack = set()
    path_stack = []
    
    def dfs(node: str) -> bool:
        visited.add(node)
        rec_stack.add(node)
        path_stack.append(node)
        
        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in rec_stack:
                # Found cycle
                cycle_start = path_stack.index(neighbor)
                cycle = path_stack[cycle_start:] + [neighbor]
                circular.append(CircularDep(
                    cycle=cycle,
                    description=f"Circular import: {' -> '.join(cycle)}"
                ))
                return True
        
        path_stack.pop()
        rec_stack.remove(node)
        return False
    
    for node in graph:
        if node not in visited:
            dfs(node)
    
    return circular

# ============================================================================
# Duplicate Detection
# ============================================================================

def hash_ast(node: ast.AST) -> str:
    """Create a structural hash of an AST node."""
    parts = []
    
    def visit(n: ast.AST, depth: int = 0):
        if depth > 15:
            return
        
        parts.append(f"{depth}:{type(n).__name__}")
        
        for child in ast.iter_child_nodes(n):
            visit(child, depth + 1)
    
    visit(node)
    return hashlib.md5(','.join(parts).encode()).hexdigest()


def find_duplicates(files: List[FileMetrics], file_contents: Dict[str, str]) -> List[DuplicateCandidate]:
    """Find duplicate code blocks using AST comparison."""
    duplicates = []
    function_hashes: Dict[str, List[Tuple[str, FunctionMetrics]]] = defaultdict(list)
    
    for file in files:
        content = file_contents.get(file.path)
        if not content:
            continue
        
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue
        
        # Build a map of function nodes
        func_nodes = {}
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_nodes[node.lineno] = node
        
        for func in file.functions:
            if func.line_count < 5:
                continue
            
            node = func_nodes.get(func.line_start)
            if node:
                h = hash_ast(node)
                function_hashes[h].append((file.path, func))
    
    # Find duplicates (same hash = similar structure)
    for h, funcs in function_hashes.items():
        if len(funcs) < 2:
            continue
        
        for i, (path1, func1) in enumerate(funcs):
            for path2, func2 in funcs[i+1:]:
                if path1 == path2:
                    continue
                
                duplicates.append(DuplicateCandidate(
                    file1=path1,
                    line1_start=func1.line_start,
                    line1_end=func1.line_end,
                    file2=path2,
                    line2_start=func2.line_start,
                    line2_end=func2.line_end,
                    similarity=0.9,
                    description=f"Functions '{func1.name}' and '{func2.name}' have similar structure"
                ))
    
    return duplicates

# ============================================================================
# Security Pattern Detection
# ============================================================================

def find_security_issues(file: FileMetrics, content: str) -> List[PotentialIssue]:
    """Find potential security issues."""
    issues = []
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return issues
    
    for node in ast.walk(tree):
        # eval/exec
        if isinstance(node, ast.Call):
            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            
            if func_name in ('eval', 'exec'):
                issues.append(PotentialIssue(
                    category='security',
                    pattern=f'{func_name}-usage',
                    file=file.path,
                    line=node.lineno,
                    code=ast.unparse(node)[:100] if hasattr(ast, 'unparse') else '',
                    description=f'{func_name}() usage - verify input is trusted'
                ))
            
            # subprocess with shell=True
            if func_name in ('system', 'popen', 'call', 'run', 'Popen'):
                for kw in node.keywords:
                    if kw.arg == 'shell' and isinstance(kw.value, ast.Constant) and kw.value.value:
                        issues.append(PotentialIssue(
                            category='security',
                            pattern='shell-command',
                            file=file.path,
                            line=node.lineno,
                            code=ast.unparse(node)[:100] if hasattr(ast, 'unparse') else '',
                            description='subprocess with shell=True - verify input is not user-controlled'
                        ))
            
            # SQL string formatting
            if func_name == 'execute':
                if node.args and isinstance(node.args[0], ast.JoinedStr):  # f-string
                    issues.append(PotentialIssue(
                        category='security',
                        pattern='sql-formatting',
                        file=file.path,
                        line=node.lineno,
                        code='execute(f"...")',
                        description='f-string in execute() - verify parameterized queries'
                    ))
            
            # pickle.loads
            if func_name in ('loads', 'load') and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == 'pickle':
                    issues.append(PotentialIssue(
                        category='security',
                        pattern='pickle-load',
                        file=file.path,
                        line=node.lineno,
                        code='pickle.load(s)',
                        description='pickle can execute arbitrary code - verify source is trusted'
                    ))
    
    return issues

# ============================================================================
# Error Handling Detection  
# ============================================================================

def find_error_handling_issues(file: FileMetrics, content: str) -> List[PotentialIssue]:
    """Find error handling issues."""
    issues = []
    
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return issues
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            # Bare except
            if node.type is None:
                issues.append(PotentialIssue(
                    category='error-handling',
                    pattern='bare-except',
                    file=file.path,
                    line=node.lineno,
                    code='except:',
                    description='Bare except catches all exceptions including KeyboardInterrupt'
                ))
            
            # except Exception: pass
            if (node.type and isinstance(node.type, ast.Name) and 
                node.type.id in ('Exception', 'BaseException')):
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    issues.append(PotentialIssue(
                        category='error-handling',
                        pattern='silent-except',
                        file=file.path,
                        line=node.lineno,
                        code='except Exception: pass',
                        description='Exception silently swallowed - errors will be hidden'
                    ))
    
    return issues

# ============================================================================
# Main Analysis
# ============================================================================

def analyze(root_path: Path, max_files: int = 500) -> Dict:
    """Run full analysis on a Python codebase."""
    files = collect_files(root_path, max_files)
    
    if not files:
        return {
            'rootPath': str(root_path),
            'language': 'python',
            'framework': 'unknown',
            'totalFiles': 0,
            'totalLines': 0,
            'files': [],
            'deadCode': [],
            'duplicates': [],
            'circularDeps': [],
            'potentialIssues': [],
            'summary': {}
        }
    
    file_metrics = []
    file_contents = {}
    all_issues = []
    
    for filepath in files:
        try:
            content = filepath.read_text(errors='ignore')
            file_contents[str(filepath)] = content
            
            metrics = analyze_file(filepath, content)
            if metrics:
                file_metrics.append(metrics)
                
                # Security issues
                all_issues.extend(find_security_issues(metrics, content))
                
                # Error handling issues
                all_issues.extend(find_error_handling_issues(metrics, content))
        except Exception:
            continue
    
    # Dead code
    dead_code = find_dead_code(file_metrics)
    
    # Duplicates
    duplicates = find_duplicates(file_metrics, file_contents)
    
    # Circular imports
    circular = find_circular_imports(file_metrics, root_path)
    
    # Detect framework
    framework = detect_framework(file_metrics)
    
    # Calculate summary
    all_functions = [f for file in file_metrics for f in file.functions]
    complexities = [f.complexity for f in all_functions]
    lengths = [f.line_count for f in all_functions]
    type_coverages = [f.type_hint_coverage for f in file_metrics]
    
    summary = {
        'avgComplexity': round(sum(complexities) / len(complexities), 1) if complexities else 0,
        'maxComplexity': max(complexities) if complexities else 0,
        'avgFunctionLength': round(sum(lengths) / len(lengths), 1) if lengths else 0,
        'maxFunctionLength': max(lengths) if lengths else 0,
        'totalFunctions': len(all_functions),
        'asyncFunctions': sum(1 for f in all_functions if f.is_async),
        'typeHintCoverage': round(sum(type_coverages) / len(type_coverages), 2) if type_coverages else 0,
        'unusedImports': sum(1 for d in dead_code if d.kind == 'unused-import'),
        'circularDeps': len(circular)
    }
    
    return {
        'rootPath': str(root_path),
        'language': 'python',
        'framework': framework,
        'totalFiles': len(file_metrics),
        'totalLines': sum(f.line_count for f in file_metrics),
        'files': [asdict(f) for f in file_metrics],
        'deadCode': [asdict(d) for d in dead_code],
        'duplicates': [asdict(d) for d in duplicates],
        'circularDeps': [asdict(c) for c in circular],
        'potentialIssues': [asdict(i) for i in all_issues],
        'summary': summary
    }


def detect_framework(files: List[FileMetrics]) -> str:
    """Detect Python framework."""
    all_imports = set()
    for f in files:
        for imp in f.imports:
            all_imports.add(imp['module'])
    
    if 'django' in all_imports or any('django' in m for m in all_imports):
        return 'django'
    if 'flask' in all_imports:
        return 'flask'
    if 'fastapi' in all_imports:
        return 'fastapi'
    if 'starlette' in all_imports:
        return 'starlette'
    if 'tornado' in all_imports:
        return 'tornado'
    if 'pyramid' in all_imports:
        return 'pyramid'
    
    return 'unknown'


def print_summary(result: Dict):
    """Print human-readable summary."""
    print('=' * 60)
    print('PYTHON ANALYSIS')
    print('=' * 60)
    print(f"Path: {result['rootPath']}")
    print(f"Framework: {result['framework']}")
    print(f"Files: {result['totalFiles']}")
    print(f"Lines: {result['totalLines']:,}")
    print()
    
    s = result['summary']
    print('Summary:')
    print(f"  Avg complexity: {s.get('avgComplexity', 0)}")
    print(f"  Max complexity: {s.get('maxComplexity', 0)}")
    print(f"  Avg function length: {s.get('avgFunctionLength', 0)} lines")
    print(f"  Max function length: {s.get('maxFunctionLength', 0)} lines")
    print(f"  Type hint coverage: {s.get('typeHintCoverage', 0)*100:.0f}%")
    print(f"  Async functions: {s.get('asyncFunctions', 0)}")
    print()
    
    if result['deadCode']:
        print(f"Dead Code: {len(result['deadCode'])} items")
        for d in result['deadCode'][:5]:
            print(f"  {Path(d['file']).name}:{d['line']} - {d['description'][:50]}")
        print()
    
    if result['circularDeps']:
        print(f"Circular Dependencies: {len(result['circularDeps'])}")
        for c in result['circularDeps'][:3]:
            print(f"  {c['description']}")
        print()
    
    if result['duplicates']:
        print(f"Potential Duplicates: {len(result['duplicates'])}")
        for d in result['duplicates'][:3]:
            print(f"  {Path(d['file1']).name}:{d['line1_start']} <-> {Path(d['file2']).name}:{d['line2_start']}")
        print()
    
    if result['potentialIssues']:
        print(f"Potential Issues: {len(result['potentialIssues'])}")
        for i in result['potentialIssues'][:5]:
            print(f"  {Path(i['file']).name}:{i['line']} - {i['pattern']}")
    
    print('=' * 60)


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Python AST Analyzer')
    parser.add_argument('path', nargs='?', default='.', help='Path to analyze')
    parser.add_argument('--output', '-o', help='Output JSON file')
    parser.add_argument('--summary', action='store_true', help='Print summary')
    parser.add_argument('--max-files', type=int, default=500, help='Max files')
    
    args = parser.parse_args()
    
    root_path = Path(args.path).resolve()
    if not root_path.exists():
        print(f"Error: Path does not exist: {root_path}", file=sys.stderr)
        sys.exit(1)
    
    result = analyze(root_path, args.max_files)
    
    if args.summary:
        print_summary(result)
    
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2))
        print(f"Results written to: {args.output}")
    elif not args.summary:
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
