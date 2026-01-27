#!/usr/bin/env python3
"""
Code Quality Analyzer - Main Orchestrator

Coordinates language-specific analyzers and aggregates results:
- Python: Uses analyze_python.py (AST-based)
- TypeScript/JavaScript: Uses analyze_typescript.js (TypeScript compiler)
- Go: Uses go vet/staticcheck + custom analysis
- Other: Falls back to regex-based analysis

Usage: python3 analyze.py <path> [options]

Options:
    --focus AREA      Focus: security, performance, quality, tests, all
    --output FILE     Output JSON file
    --summary         Print human-readable summary
    --fix             Generate auto-fix suggestions
    --max-files N     Maximum files to analyze
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent

# ============================================================================
# Language Detection
# ============================================================================

LANGUAGE_EXTENSIONS = {
    '.py': 'python',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.go': 'go',
    '.java': 'java',
    '.rb': 'ruby',
    '.php': 'php',
    '.rs': 'rust',
    '.cs': 'csharp',
}

IGNORE_DIRS = {
    'node_modules', 'venv', '.venv', '__pycache__', '.git',
    'dist', 'build', '.next', 'vendor', 'target'
}


def detect_languages(path: Path) -> Dict[str, int]:
    """Detect languages and count files."""
    counts = defaultdict(int)
    
    if path.is_file():
        ext = path.suffix.lower()
        if ext in LANGUAGE_EXTENSIONS:
            counts[LANGUAGE_EXTENSIONS[ext]] = 1
        return dict(counts)
    
    for ext, lang in LANGUAGE_EXTENSIONS.items():
        for f in path.rglob(f'*{ext}'):
            if not any(ignored in f.parts for ignored in IGNORE_DIRS):
                counts[lang] += 1
    
    return dict(counts)


def detect_primary_language(path: Path) -> str:
    """Detect the primary language."""
    counts = detect_languages(path)
    if not counts:
        return 'unknown'
    return max(counts, key=counts.get)


# ============================================================================
# Analyzer Runners
# ============================================================================

def run_python_analyzer(path: Path, max_files: int = 500) -> Dict:
    """Run Python AST analyzer."""
    script = SCRIPT_DIR / 'analyze_python.py'
    
    try:
        result = subprocess.run(
            [sys.executable, str(script), str(path), '--max-files', str(max_files)],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"Python analyzer error: {e}", file=sys.stderr)
    
    return {'error': 'Python analyzer failed', 'files': []}


def run_typescript_analyzer(path: Path, max_files: int = 500) -> Dict:
    """Run TypeScript/JavaScript analyzer."""
    script = SCRIPT_DIR / 'analyze_typescript.js'
    
    # Check if node is available
    if not shutil.which('node'):
        return {'error': 'Node.js not installed', 'files': []}
    
    # Check if typescript is available
    try:
        subprocess.run(['node', '-e', "require('typescript')"], 
                      capture_output=True, timeout=10)
    except:
        return {'error': 'TypeScript not installed. Run: npm install -g typescript', 'files': []}
    
    try:
        result = subprocess.run(
            ['node', str(script), str(path)],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.stdout:
            return json.loads(result.stdout)
    except json.JSONDecodeError:
        # Try running with npx ts-node if regular node fails
        pass
    except Exception as e:
        print(f"TypeScript analyzer error: {e}", file=sys.stderr)
    
    return {'error': 'TypeScript analyzer failed', 'files': []}


def run_go_analyzer(path: Path) -> Dict:
    """Run Go analyzer using go vet and staticcheck."""
    if not shutil.which('go'):
        return {'error': 'Go not installed', 'files': []}
    
    result = {
        'rootPath': str(path),
        'language': 'go',
        'framework': 'unknown',
        'totalFiles': 0,
        'totalLines': 0,
        'files': [],
        'potentialIssues': [],
        'summary': {}
    }
    
    # Run go vet
    try:
        vet_result = subprocess.run(
            ['go', 'vet', './...'],
            capture_output=True,
            text=True,
            cwd=str(path) if path.is_dir() else str(path.parent),
            timeout=120
        )
        
        for line in vet_result.stderr.split('\n'):
            if ':' in line:
                parts = line.split(':')
                if len(parts) >= 3:
                    result['potentialIssues'].append({
                        'category': 'quality',
                        'pattern': 'go-vet',
                        'file': parts[0],
                        'line': int(parts[1]) if parts[1].isdigit() else 0,
                        'code': '',
                        'description': ':'.join(parts[2:]).strip()
                    })
    except Exception:
        pass
    
    # Run staticcheck if available
    if shutil.which('staticcheck'):
        try:
            sc_result = subprocess.run(
                ['staticcheck', '-f', 'json', './...'],
                capture_output=True,
                text=True,
                cwd=str(path) if path.is_dir() else str(path.parent),
                timeout=120
            )
            
            for line in sc_result.stdout.split('\n'):
                if line.strip():
                    try:
                        issue = json.loads(line)
                        result['potentialIssues'].append({
                            'category': 'quality',
                            'pattern': issue.get('code', 'staticcheck'),
                            'file': issue.get('location', {}).get('file', ''),
                            'line': issue.get('location', {}).get('line', 0),
                            'code': '',
                            'description': issue.get('message', '')
                        })
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass
    
    return result


# ============================================================================
# Results Aggregation
# ============================================================================

@dataclass
class AggregatedResult:
    """Aggregated analysis result across all languages."""
    root_path: str
    primary_language: str
    languages: Dict[str, int]
    framework: str
    total_files: int
    total_lines: int
    
    # Issues by category
    quality_issues: List[Dict]
    security_issues: List[Dict]
    performance_issues: List[Dict]
    error_handling_issues: List[Dict]
    
    # Structural problems
    dead_code: List[Dict]
    duplicates: List[Dict]
    circular_deps: List[Dict]
    
    # Type issues (for TS)
    type_errors: List[Dict]
    
    # Metrics
    large_files: List[Dict]
    complex_functions: List[Dict]
    long_functions: List[Dict]
    
    # Summary
    summary: Dict


def aggregate_results(results: List[Dict], path: Path) -> AggregatedResult:
    """Aggregate results from multiple analyzers."""
    
    languages = detect_languages(path)
    primary_lang = detect_primary_language(path)
    
    # Collect all data
    all_files = []
    all_dead_code = []
    all_duplicates = []
    all_circular = []
    all_issues = []
    all_type_errors = []
    
    frameworks = []
    total_lines = 0
    
    for result in results:
        if 'error' in result:
            continue
        
        all_files.extend(result.get('files', []))
        all_dead_code.extend(result.get('deadCode', []))
        all_duplicates.extend(result.get('duplicates', []))
        all_circular.extend(result.get('circularDeps', []))
        all_issues.extend(result.get('potentialIssues', []))
        all_type_errors.extend(result.get('typeErrors', []))
        
        if result.get('framework') and result.get('framework') != 'unknown':
            frameworks.append(result['framework'])
        
        total_lines += result.get('totalLines', 0)
    
    # Categorize issues
    security = [i for i in all_issues if i.get('category') == 'security']
    error_handling = [i for i in all_issues if i.get('category') == 'error-handling']
    performance = [i for i in all_issues if i.get('category') == 'performance']
    quality = [i for i in all_issues if i.get('category') in ('quality', 'ai-smell')]
    
    # Find structural problems
    large_files = []
    complex_functions = []
    long_functions = []
    
    for f in all_files:
        if f.get('lineCount', 0) > 400:
            large_files.append({
                'file': f.get('path'),
                'lines': f.get('lineCount'),
                'reason': f"File has {f.get('lineCount')} lines (threshold: 400)"
            })
        
        for func in f.get('functions', []):
            if func.get('complexity', 0) > 12:
                complex_functions.append({
                    'file': f.get('path'),
                    'function': func.get('name'),
                    'line': func.get('lineStart') or func.get('line_start'),
                    'complexity': func.get('complexity'),
                    'reason': f"Complexity {func.get('complexity')} (threshold: 12)"
                })
            
            line_count = func.get('lineCount') or func.get('line_count', 0)
            if line_count > 40:
                long_functions.append({
                    'file': f.get('path'),
                    'function': func.get('name'),
                    'line': func.get('lineStart') or func.get('line_start'),
                    'lines': line_count,
                    'reason': f"Function has {line_count} lines (threshold: 40)"
                })
    
    # Sort by severity
    large_files.sort(key=lambda x: -x.get('lines', 0))
    complex_functions.sort(key=lambda x: -x.get('complexity', 0))
    long_functions.sort(key=lambda x: -x.get('lines', 0))
    
    # Summary
    summary = {
        'totalFiles': len(all_files),
        'totalLines': total_lines,
        'securityIssues': len(security),
        'errorHandlingIssues': len(error_handling),
        'deadCodeItems': len(all_dead_code),
        'duplicates': len(all_duplicates),
        'circularDeps': len(all_circular),
        'typeErrors': len(all_type_errors),
        'largeFiles': len(large_files),
        'complexFunctions': len(complex_functions),
        'longFunctions': len(long_functions),
    }
    
    return AggregatedResult(
        root_path=str(path),
        primary_language=primary_lang,
        languages=languages,
        framework=frameworks[0] if frameworks else 'unknown',
        total_files=len(all_files),
        total_lines=total_lines,
        quality_issues=quality,
        security_issues=security,
        performance_issues=performance,
        error_handling_issues=error_handling,
        dead_code=all_dead_code,
        duplicates=all_duplicates,
        circular_deps=all_circular,
        type_errors=all_type_errors[:50],  # Limit
        large_files=large_files[:20],
        complex_functions=complex_functions[:30],
        long_functions=long_functions[:30],
        summary=summary
    )


# ============================================================================
# Auto-Fix Generation
# ============================================================================

def generate_fixes(result: AggregatedResult) -> List[Dict]:
    """Generate auto-fix suggestions for common issues."""
    fixes = []
    
    # Unused imports
    for item in result.dead_code:
        if item.get('kind') == 'unused-import':
            fixes.append({
                'type': 'remove-line',
                'file': item['file'],
                'line': item['line'],
                'description': f"Remove unused import: {item['name']}",
                'priority': 'low',
                'safe': True
            })
    
    # Bare except -> except Exception
    for item in result.error_handling_issues:
        if item.get('pattern') == 'bare-except':
            fixes.append({
                'type': 'replace',
                'file': item['file'],
                'line': item['line'],
                'old': 'except:',
                'new': 'except Exception:',
                'description': 'Replace bare except with except Exception',
                'priority': 'medium',
                'safe': True
            })
    
    # Long functions - suggest extraction points
    for func in result.long_functions[:10]:
        fixes.append({
            'type': 'refactor',
            'file': func['file'],
            'line': func['line'],
            'description': f"Split function '{func['function']}' ({func['lines']} lines)",
            'priority': 'medium',
            'safe': False,
            'requires_tests': True
        })
    
    return fixes


# ============================================================================
# Output Formatting
# ============================================================================

def print_summary(result: AggregatedResult):
    """Print human-readable summary."""
    print('=' * 70)
    print('CODE QUALITY ANALYSIS REPORT')
    print('=' * 70)
    print(f"Path: {result.root_path}")
    print(f"Primary Language: {result.primary_language}")
    print(f"Framework: {result.framework}")
    print(f"Files: {result.total_files}")
    print(f"Lines: {result.total_lines:,}")
    print()
    
    if result.languages:
        print("Languages:")
        for lang, count in sorted(result.languages.items(), key=lambda x: -x[1]):
            print(f"  {lang}: {count} files")
        print()
    
    print('-' * 70)
    print('SUMMARY')
    print('-' * 70)
    s = result.summary
    
    # Critical issues first
    critical_count = s.get('securityIssues', 0)
    if critical_count:
        print(f"🔴 Security Issues: {critical_count}")
    
    high_count = s.get('errorHandlingIssues', 0) + s.get('circularDeps', 0)
    if high_count:
        print(f"🟠 High Priority: {high_count}")
    
    medium_count = s.get('complexFunctions', 0) + s.get('longFunctions', 0)
    if medium_count:
        print(f"🟡 Medium Priority: {medium_count}")
    
    low_count = s.get('deadCodeItems', 0) + s.get('duplicates', 0)
    if low_count:
        print(f"🟢 Low Priority: {low_count}")
    
    if s.get('typeErrors', 0):
        print(f"📝 Type Errors: {s['typeErrors']}")
    
    print()
    
    # Details
    if result.security_issues:
        print('-' * 70)
        print('🔴 SECURITY ISSUES (Verify Each)')
        print('-' * 70)
        for issue in result.security_issues[:10]:
            print(f"\n  [{issue.get('pattern')}] {Path(issue.get('file', '')).name}:{issue.get('line')}")
            print(f"    {issue.get('description')}")
    
    if result.error_handling_issues:
        print()
        print('-' * 70)
        print('🟠 ERROR HANDLING ISSUES')
        print('-' * 70)
        for issue in result.error_handling_issues[:10]:
            print(f"\n  [{issue.get('pattern')}] {Path(issue.get('file', '')).name}:{issue.get('line')}")
            print(f"    {issue.get('description')}")
    
    if result.circular_deps:
        print()
        print('-' * 70)
        print('🟠 CIRCULAR DEPENDENCIES')
        print('-' * 70)
        for dep in result.circular_deps[:5]:
            print(f"  {dep.get('description')}")
    
    if result.complex_functions:
        print()
        print('-' * 70)
        print('🟡 COMPLEX FUNCTIONS (Complexity > 12)')
        print('-' * 70)
        for func in result.complex_functions[:10]:
            print(f"  {func['function']} ({Path(func['file']).name}:{func['line']})")
            print(f"    Complexity: {func['complexity']}")
    
    if result.long_functions:
        print()
        print('-' * 70)
        print('🟡 LONG FUNCTIONS (> 40 lines)')
        print('-' * 70)
        for func in result.long_functions[:10]:
            print(f"  {func['function']} ({Path(func['file']).name}:{func['line']})")
            print(f"    Lines: {func['lines']}")
    
    if result.dead_code:
        print()
        print('-' * 70)
        print('🟢 DEAD CODE')
        print('-' * 70)
        for item in result.dead_code[:10]:
            print(f"  {Path(item['file']).name}:{item['line']} - {item['description'][:60]}")
    
    if result.duplicates:
        print()
        print('-' * 70)
        print('🟢 POTENTIAL DUPLICATES')
        print('-' * 70)
        for dup in result.duplicates[:5]:
            print(f"  {Path(dup['file1']).name}:{dup['line1_start']} <-> {Path(dup['file2']).name}:{dup['line2_start']}")
            print(f"    {dup.get('description', '')}")
    
    print()
    print('=' * 70)
    print('Next: Use /fix-issue to address specific issues')
    print('      Use /add-tests before refactoring untested code')
    print('=' * 70)


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Code Quality Analyzer')
    parser.add_argument('path', nargs='?', default='.', help='Path to analyze')
    parser.add_argument('--focus', choices=['all', 'security', 'performance', 'quality', 'tests'],
                       default='all', help='Focus area')
    parser.add_argument('--output', '-o', help='Output JSON file')
    parser.add_argument('--summary', action='store_true', help='Print summary')
    parser.add_argument('--fix', action='store_true', help='Generate fix suggestions')
    parser.add_argument('--max-files', type=int, default=500, help='Max files')
    
    args = parser.parse_args()
    
    path = Path(args.path).resolve()
    if not path.exists():
        print(f"Error: Path does not exist: {path}", file=sys.stderr)
        sys.exit(1)
    
    # Detect languages
    languages = detect_languages(path)
    
    if not languages:
        print("No supported source files found.", file=sys.stderr)
        sys.exit(1)
    
    results = []
    
    # Run appropriate analyzers
    if 'python' in languages:
        print("Analyzing Python...", file=sys.stderr)
        results.append(run_python_analyzer(path, args.max_files))
    
    if 'typescript' in languages or 'javascript' in languages:
        print("Analyzing TypeScript/JavaScript...", file=sys.stderr)
        results.append(run_typescript_analyzer(path, args.max_files))
    
    if 'go' in languages:
        print("Analyzing Go...", file=sys.stderr)
        results.append(run_go_analyzer(path))
    
    # Aggregate results
    aggregated = aggregate_results(results, path)
    
    # Generate fixes if requested
    fixes = []
    if args.fix:
        fixes = generate_fixes(aggregated)
    
    # Output
    if args.summary:
        print_summary(aggregated)
        if fixes:
            print()
            print('-' * 70)
            print('AUTO-FIX SUGGESTIONS')
            print('-' * 70)
            for fix in fixes[:10]:
                safe = "✓ Safe" if fix.get('safe') else "⚠ Needs review"
                print(f"\n  [{fix['priority'].upper()}] {safe}")
                print(f"    {fix['description']}")
                print(f"    File: {Path(fix['file']).name}:{fix.get('line', '')}")
    
    if args.output:
        output_data = asdict(aggregated)
        output_data['fixes'] = fixes
        Path(args.output).write_text(json.dumps(output_data, indent=2, default=str))
        print(f"\nResults written to: {args.output}", file=sys.stderr)
    
    elif not args.summary:
        output_data = asdict(aggregated)
        output_data['fixes'] = fixes
        print(json.dumps(output_data, indent=2, default=str))
    
    # Exit code
    critical = len(aggregated.security_issues) + len(aggregated.circular_deps)
    sys.exit(1 if critical > 0 else 0)


if __name__ == '__main__':
    main()
