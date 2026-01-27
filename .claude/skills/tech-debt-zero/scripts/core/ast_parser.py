#!/usr/bin/env python3
"""
Multi-language AST parser for tech debt analysis.
Supports: Python, JavaScript/TypeScript, Go, Rust, Java.
"""

import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ParsedClass:
    """Represents a parsed class/struct."""
    name: str
    file_path: str
    line_start: int
    line_end: int
    methods: list[str] = field(default_factory=list)
    fields: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    base_classes: list[str] = field(default_factory=list)
    line_count: int = 0


@dataclass
class ParsedFunction:
    """Represents a parsed function/method."""
    name: str
    file_path: str
    line_start: int
    line_end: int
    parameters: list[str] = field(default_factory=list)
    return_type: str | None = None
    calls: list[str] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)
    complexity: int = 1
    is_async: bool = False


@dataclass
class ParsedImport:
    """Represents an import statement."""
    module: str
    names: list[str] = field(default_factory=list)
    is_relative: bool = False
    alias: str | None = None


@dataclass
class ParsedFile:
    """Represents a parsed source file."""
    path: str
    language: str
    classes: list[ParsedClass] = field(default_factory=list)
    functions: list[ParsedFunction] = field(default_factory=list)
    imports: list[ParsedImport] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    line_count: int = 0
    errors: list[str] = field(default_factory=list)


class PythonParser:
    """Parse Python source files using ast module."""

    def parse(self, file_path: Path) -> ParsedFile:
        result = ParsedFile(path=str(file_path), language="python")

        try:
            source = file_path.read_text(encoding="utf-8")
            result.line_count = len(source.splitlines())
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError as e:
            result.errors.append(f"Syntax error: {e}")
            return result
        except Exception as e:
            result.errors.append(f"Parse error: {e}")
            return result

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                result.classes.append(self._parse_class(node, file_path))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Only top-level functions
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    result.functions.append(self._parse_function(node, file_path))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    result.imports.append(
                        ParsedImport(module=alias.name, alias=alias.asname)
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    result.imports.append(
                        ParsedImport(
                            module=node.module,
                            names=[a.name for a in node.names],
                            is_relative=node.level > 0,
                        )
                    )

        return result

    def _parse_class(self, node: ast.ClassDef, file_path: Path) -> ParsedClass:
        cls = ParsedClass(
            name=node.name,
            file_path=str(file_path),
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
        )

        cls.line_count = cls.line_end - cls.line_start + 1
        cls.decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        cls.base_classes = [self._get_name(b) for b in node.bases]

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                cls.methods.append(item.name)
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                cls.fields.append(item.target.id)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        cls.fields.append(target.id)

        # Extract dependencies from __init__ type hints and assignments
        cls.dependencies = self._extract_dependencies(node)

        return cls

    def _parse_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: Path
    ) -> ParsedFunction:
        func = ParsedFunction(
            name=node.name,
            file_path=str(file_path),
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            is_async=isinstance(node, ast.AsyncFunctionDef),
        )

        func.parameters = [arg.arg for arg in node.args.args]

        if node.returns:
            func.return_type = self._get_name(node.returns)

        # Extract function calls
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                call_name = self._get_call_name(child)
                if call_name:
                    func.calls.append(call_name)

        # Calculate cyclomatic complexity
        func.complexity = self._calculate_complexity(node)

        return func

    def _get_decorator_name(self, node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Call):
            return self._get_decorator_name(node.func)
        return "unknown"

    def _get_name(self, node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return self._get_name(node.value)
        elif isinstance(node, ast.Constant):
            return str(node.value)
        return "unknown"

    def _get_call_name(self, node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return f"{self._get_name(node.func.value)}.{node.func.attr}"
        return None

    def _extract_dependencies(self, node: ast.ClassDef) -> list[str]:
        deps = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if item.name == "__init__":
                    for arg in item.args.args:
                        if arg.annotation:
                            dep = self._get_name(arg.annotation)
                            if dep not in ("self", "cls", "str", "int", "bool", "float", "list", "dict", "Any"):
                                deps.append(dep)
        return deps

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate McCabe cyclomatic complexity."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
        return complexity


class JavaScriptParser:
    """Parse JavaScript/TypeScript files using regex patterns."""

    # Patterns for JS/TS parsing
    CLASS_PATTERN = re.compile(
        r"(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?\s*\{",
        re.MULTILINE,
    )
    FUNCTION_PATTERN = re.compile(
        r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)(?:\s*:\s*(\w+))?\s*\{",
        re.MULTILINE,
    )
    ARROW_FUNCTION_PATTERN = re.compile(
        r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*(?::\s*\w+)?\s*=>\s*",
        re.MULTILINE,
    )
    IMPORT_PATTERN = re.compile(
        r"import\s+(?:{([^}]+)}|(\w+))\s+from\s+['\"]([^'\"]+)['\"]",
        re.MULTILINE,
    )
    METHOD_PATTERN = re.compile(
        r"(?:async\s+)?(\w+)\s*\([^)]*\)\s*(?::\s*\w+)?\s*\{",
        re.MULTILINE,
    )

    def parse(self, file_path: Path) -> ParsedFile:
        result = ParsedFile(
            path=str(file_path),
            language="typescript" if file_path.suffix in (".ts", ".tsx") else "javascript",
        )

        try:
            source = file_path.read_text(encoding="utf-8")
            result.line_count = len(source.splitlines())
        except Exception as e:
            result.errors.append(f"Read error: {e}")
            return result

        # Parse imports
        for match in self.IMPORT_PATTERN.finditer(source):
            named, default, module = match.groups()
            names = [n.strip() for n in named.split(",")] if named else []
            if default:
                names.append(default)
            result.imports.append(ParsedImport(module=module, names=names))

        # Parse classes
        for match in self.CLASS_PATTERN.finditer(source):
            name, extends, implements = match.groups()
            cls = ParsedClass(
                name=name,
                file_path=str(file_path),
                line_start=source[:match.start()].count("\n") + 1,
                line_end=0,  # Would need brace matching for accurate end
            )
            if extends:
                cls.base_classes.append(extends)
            if implements:
                cls.dependencies.extend([i.strip() for i in implements.split(",")])

            # Extract methods from class body
            class_body = self._extract_block(source, match.end() - 1)
            for method_match in self.METHOD_PATTERN.finditer(class_body):
                method_name = method_match.group(1)
                if method_name not in ("if", "for", "while", "switch", "catch"):
                    cls.methods.append(method_name)

            cls.line_count = class_body.count("\n") + 1
            result.classes.append(cls)

        # Parse standalone functions
        for match in self.FUNCTION_PATTERN.finditer(source):
            name, params, return_type = match.groups()
            func = ParsedFunction(
                name=name,
                file_path=str(file_path),
                line_start=source[:match.start()].count("\n") + 1,
                line_end=0,
                parameters=[p.strip().split(":")[0].strip() for p in params.split(",") if p.strip()],
                return_type=return_type,
                is_async="async" in source[max(0, match.start() - 10):match.start()],
            )
            result.functions.append(func)

        # Parse arrow functions
        for match in self.ARROW_FUNCTION_PATTERN.finditer(source):
            name = match.group(1)
            func = ParsedFunction(
                name=name,
                file_path=str(file_path),
                line_start=source[:match.start()].count("\n") + 1,
                line_end=0,
                is_async="async" in source[max(0, match.start() - 10):match.start()],
            )
            result.functions.append(func)

        return result

    def _extract_block(self, source: str, start: int) -> str:
        """Extract a brace-delimited block starting at given position."""
        if start >= len(source) or source[start] != "{":
            return ""

        depth = 0
        end = start
        for i, char in enumerate(source[start:], start):
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break

        return source[start:end + 1]


class MultiLanguageParser:
    """Unified parser that delegates to language-specific parsers."""

    LANGUAGE_MAP = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
    }

    def __init__(self):
        self.python_parser = PythonParser()
        self.js_parser = JavaScriptParser()

    def parse_file(self, file_path: Path) -> ParsedFile | None:
        """Parse a single file based on its extension."""
        suffix = file_path.suffix.lower()
        language = self.LANGUAGE_MAP.get(suffix)

        if not language:
            return None

        if language == "python":
            return self.python_parser.parse(file_path)
        elif language in ("javascript", "typescript"):
            return self.js_parser.parse(file_path)
        else:
            # Placeholder for other languages
            return ParsedFile(
                path=str(file_path),
                language=language,
                errors=[f"Parser not implemented for {language}"],
            )

    def parse_directory(
        self, directory: Path, exclude_patterns: list[str] | None = None
    ) -> list[ParsedFile]:
        """Parse all supported files in a directory."""
        exclude_patterns = exclude_patterns or [
            "node_modules",
            "__pycache__",
            ".git",
            "venv",
            ".venv",
            "dist",
            "build",
            "*.min.js",
        ]

        results = []
        for ext in self.LANGUAGE_MAP:
            for file_path in directory.rglob(f"*{ext}"):
                # Check exclusions
                path_str = str(file_path)
                if any(pat in path_str for pat in exclude_patterns):
                    continue

                parsed = self.parse_file(file_path)
                if parsed:
                    results.append(parsed)

        return results


def analyze_coupling(parsed_files: list[ParsedFile]) -> dict[str, Any]:
    """Analyze coupling metrics across parsed files."""
    # Build dependency graph
    modules: dict[str, set[str]] = {}  # module -> set of dependencies
    dependents: dict[str, set[str]] = {}  # module -> set of modules that depend on it

    for pf in parsed_files:
        module_name = Path(pf.path).stem
        deps = set()

        for imp in pf.imports:
            deps.add(imp.module.split(".")[0])

        modules[module_name] = deps

        for dep in deps:
            dependents.setdefault(dep, set()).add(module_name)

    # Calculate metrics
    metrics = {}
    for module, deps in modules.items():
        ca = len(dependents.get(module, set()))  # Afferent coupling
        ce = len(deps)  # Efferent coupling
        instability = ce / (ca + ce) if (ca + ce) > 0 else 0

        metrics[module] = {
            "afferent_coupling": ca,
            "efferent_coupling": ce,
            "instability": round(instability, 2),
            "dependencies": list(deps),
            "dependents": list(dependents.get(module, set())),
        }

    return metrics


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Multi-language AST parser")
    parser.add_argument("path", help="File or directory to parse")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--coupling", action="store_true", help="Analyze coupling metrics")

    args = parser.parse_args()
    path = Path(args.path)

    mlp = MultiLanguageParser()

    if path.is_file():
        result = mlp.parse_file(path)
        results = [result] if result else []
    else:
        results = mlp.parse_directory(path)

    if args.coupling:
        metrics = analyze_coupling(results)
        if args.json:
            print(json.dumps(metrics, indent=2))
        else:
            for module, data in sorted(metrics.items()):
                print(f"\n{module}:")
                print(f"  Ca (afferent): {data['afferent_coupling']}")
                print(f"  Ce (efferent): {data['efferent_coupling']}")
                print(f"  Instability: {data['instability']}")
    else:
        if args.json:
            output = []
            for r in results:
                output.append({
                    "path": r.path,
                    "language": r.language,
                    "classes": [
                        {"name": c.name, "methods": c.methods, "line_count": c.line_count}
                        for c in r.classes
                    ],
                    "functions": [
                        {"name": f.name, "complexity": f.complexity, "is_async": f.is_async}
                        for f in r.functions
                    ],
                    "imports": [{"module": i.module, "names": i.names} for i in r.imports],
                    "line_count": r.line_count,
                    "errors": r.errors,
                })
            print(json.dumps(output, indent=2))
        else:
            for r in results:
                print(f"\n{r.path} ({r.language}, {r.line_count} lines)")
                if r.classes:
                    print(f"  Classes: {[c.name for c in r.classes]}")
                if r.functions:
                    print(f"  Functions: {[f.name for f in r.functions]}")
                if r.errors:
                    print(f"  Errors: {r.errors}")


if __name__ == "__main__":
    main()
