#!/usr/bin/env python3
"""
Resilience Analyzer.
Detects missing timeouts, retries without backoff, absent circuit breakers.
"""

import re
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from audit_orchestrator import BaseAnalyzer, Category, Finding, Severity


class ResilienceAnalyzer(BaseAnalyzer):
    """Analyze code for resilience issues."""

    category = Category.RESILIENCE

    # Missing timeout patterns
    MISSING_TIMEOUT_PATTERNS = [
        # HTTP clients without timeout
        (r'axios\.(get|post|put|delete|patch|request)\s*\([^)]+\)(?!.*timeout)', "HTTP request without timeout (axios)", Severity.HIGH),
        (r'fetch\s*\([^)]+\)(?!.*timeout|.*signal)', "HTTP request without timeout (fetch)", Severity.HIGH),
        (r'requests\.(get|post|put|delete|patch)\s*\([^)]+\)(?!.*timeout)', "HTTP request without timeout (requests)", Severity.HIGH),
        (r'http\.request\s*\([^)]+\)(?!.*timeout)', "HTTP request without timeout (http)", Severity.HIGH),
        (r'urllib\.request\.urlopen\s*\([^)]+\)(?!.*timeout)', "HTTP request without timeout (urllib)", Severity.HIGH),

        # Database operations
        (r'new Pool\s*\(\s*\{(?!.*connectionTimeoutMillis)', "Database pool without connection timeout", Severity.MEDIUM),
        (r'createConnection\s*\(\s*\{(?!.*connectTimeout)', "Database connection without timeout", Severity.MEDIUM),
        (r'mongoose\.connect\s*\([^)]+\)(?!.*serverSelectionTimeoutMS)', "MongoDB connection without timeout", Severity.MEDIUM),

        # gRPC
        (r'\.call\s*\([^)]+\)(?!.*deadline)', "gRPC call without deadline", Severity.MEDIUM),
    ]

    # Bad retry patterns (without backoff)
    BAD_RETRY_PATTERNS = [
        # Fixed delay retries
        (r'for\s*\([^)]*;\s*\w+\s*<\s*\d+\s*;[^)]*\)\s*\{[^}]*await\s+\w+[^}]*sleep\s*\(\s*\d+\s*\)', "Retry with fixed delay (no exponential backoff)", Severity.MEDIUM),
        (r'while\s*\([^)]+\)\s*\{[^}]*catch[^}]*sleep\s*\(\s*\d+\s*\)[^}]*\}', "Retry loop with fixed delay", Severity.MEDIUM),
        # Retry without jitter
        (r'Math\.pow\s*\(\s*2\s*,\s*\w+\s*\)\s*\*\s*\d+(?!.*random|.*jitter)', "Exponential backoff without jitter", Severity.LOW),
    ]

    # Missing circuit breaker patterns (external service calls)
    MISSING_CIRCUIT_BREAKER_PATTERNS = [
        # Direct external service calls in critical paths
        (r'async\s+function\s+\w*(?:payment|checkout|order|transaction)\w*\s*\([^)]*\)\s*\{[^}]*(?:axios|fetch|request)\s*\(', "Critical operation without circuit breaker protection", Severity.HIGH),
    ]

    # No fallback patterns
    NO_FALLBACK_PATTERNS = [
        # Single point of failure
        (r'const\s+\w+\s*=\s*await\s+(?:axios|fetch)\s*\([^)]+\)\s*;?\s*return\s+\w+', "External call without fallback handling", Severity.MEDIUM),
    ]

    # Unbounded operations
    UNBOUNDED_PATTERNS = [
        # No limit on items
        (r'\.findAll\s*\(\s*\)(?!.*limit)', "Database query without limit", Severity.MEDIUM),
        (r'\.find\s*\(\s*\{[^}]*\}\s*\)(?!.*limit)', "Database query without limit", Severity.MEDIUM),
        # Unbounded loops
        (r'while\s*\(\s*true\s*\)', "Unbounded while loop", Severity.LOW),
    ]

    # Resource exhaustion patterns
    RESOURCE_EXHAUSTION_PATTERNS = [
        # Reading entire file into memory
        (r'readFileSync\s*\([^)]+\)', "Synchronous file read (may block event loop)", Severity.LOW),
        (r'\.readFile\s*\([^)]+\)\s*\.then\s*\(\s*\w+\s*=>\s*\w+\.toString\s*\(\s*\)', "Reading entire file into memory", Severity.LOW),
        # Loading all records
        (r'await\s+\w+\.findAll\s*\(\s*\)', "Loading all database records into memory", Severity.MEDIUM),
    ]

    SUPPORTED_EXTENSIONS = {'.js', '.jsx', '.ts', '.tsx', '.py', '.go', '.java'}

    async def analyze(self) -> list[Finding]:
        """Analyze codebase for resilience issues."""
        findings = []

        for file_path in self._get_source_files():
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')

                # Check timeout issues
                findings.extend(self._check_multiline_patterns(
                    file_path, content, self.MISSING_TIMEOUT_PATTERNS,
                    "timeout"
                ))

                # Check retry issues
                findings.extend(self._check_multiline_patterns(
                    file_path, content, self.BAD_RETRY_PATTERNS,
                    "retry"
                ))

                # Check circuit breaker issues
                findings.extend(self._check_multiline_patterns(
                    file_path, content, self.MISSING_CIRCUIT_BREAKER_PATTERNS,
                    "circuit-breaker"
                ))

                # Check unbounded operations
                findings.extend(self._check_multiline_patterns(
                    file_path, content, self.UNBOUNDED_PATTERNS,
                    "unbounded"
                ))

                # Check resource exhaustion
                findings.extend(self._check_multiline_patterns(
                    file_path, content, self.RESOURCE_EXHAUSTION_PATTERNS,
                    "resource"
                ))

            except Exception:
                continue

        # Check for resilience library usage
        findings.extend(self._check_resilience_libraries())

        self.findings = findings
        return findings

    def _get_source_files(self):
        """Get all source files to analyze."""
        exclude_dirs = {'node_modules', '__pycache__', '.git', 'venv', '.venv', 'dist', 'build', 'vendor', 'test', 'tests', '__tests__'}

        for ext in self.SUPPORTED_EXTENSIONS:
            for file_path in self.project_path.rglob(f'*{ext}'):
                if any(excl in file_path.parts for excl in exclude_dirs):
                    continue
                # Skip test files
                if '.test.' in file_path.name or '.spec.' in file_path.name or '_test.' in file_path.name:
                    continue
                yield file_path

    def _check_multiline_patterns(
        self,
        file_path: Path,
        content: str,
        patterns: list[tuple[str, str, Severity]],
        tag: str,
    ) -> list[Finding]:
        """Check content against multiline patterns."""
        findings = []
        lines = content.split('\n')

        for pattern, description, severity in patterns:
            # Use DOTALL to match across lines
            for match in re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE):
                # Calculate line number
                line_num = content[:match.start()].count('\n') + 1

                # Get context
                start_line = max(0, line_num - 2)
                end_line = min(len(lines), line_num + 3)
                snippet = '\n'.join(lines[start_line:end_line])

                findings.append(self.create_finding(
                    severity=severity,
                    title=description,
                    description=f"Resilience issue detected: {description}",
                    file_path=str(file_path.relative_to(self.project_path)),
                    line_number=line_num,
                    code_snippet=snippet[:300],
                    remediation=self._get_remediation(tag),
                    tags=["resilience", tag],
                ))

        return findings

    def _check_resilience_libraries(self) -> list[Finding]:
        """Check if resilience libraries are being used."""
        findings = []

        # Check package.json for Node.js projects
        package_json = self.project_path / 'package.json'
        if package_json.exists():
            try:
                import json
                data = json.loads(package_json.read_text())
                deps = list(data.get('dependencies', {}).keys()) + list(data.get('devDependencies', {}).keys())

                resilience_libs = ['opossum', 'cockatiel', 'resilience4j', 'polly-js', 'retry']
                has_resilience = any(lib in deps for lib in resilience_libs)

                if not has_resilience:
                    # Check if there are external HTTP calls
                    http_libs = ['axios', 'node-fetch', 'got', 'request', 'superagent']
                    has_http = any(lib in deps for lib in http_libs)

                    if has_http:
                        findings.append(self.create_finding(
                            severity=Severity.MEDIUM,
                            title="No resilience library detected",
                            description="Project makes HTTP requests but has no circuit breaker library. Consider adding opossum or cockatiel.",
                            file_path="package.json",
                            remediation="Add a circuit breaker library like opossum: npm install opossum",
                            tags=["resilience", "circuit-breaker", "dependency"],
                        ))
            except Exception:
                pass

        # Check requirements.txt or pyproject.toml for Python projects
        requirements = self.project_path / 'requirements.txt'
        if requirements.exists():
            try:
                content = requirements.read_text().lower()
                resilience_libs = ['circuitbreaker', 'pybreaker', 'tenacity', 'backoff']
                has_resilience = any(lib in content for lib in resilience_libs)

                http_libs = ['requests', 'httpx', 'aiohttp', 'urllib3']
                has_http = any(lib in content for lib in http_libs)

                if has_http and not has_resilience:
                    findings.append(self.create_finding(
                        severity=Severity.MEDIUM,
                        title="No resilience library detected",
                        description="Project makes HTTP requests but has no circuit breaker library. Consider adding pybreaker or tenacity.",
                        file_path="requirements.txt",
                        remediation="Add a resilience library: pip install tenacity pybreaker",
                        tags=["resilience", "circuit-breaker", "dependency"],
                    ))
            except Exception:
                pass

        return findings

    def _get_remediation(self, tag: str) -> str:
        """Get remediation advice based on issue type."""
        remediations = {
            "timeout": "Add timeout configuration to all external calls. Example: axios.get(url, { timeout: 5000 })",
            "retry": "Implement exponential backoff with jitter. Use libraries like p-retry (Node.js) or tenacity (Python).",
            "circuit-breaker": "Wrap external service calls in a circuit breaker. Use opossum (Node.js) or pybreaker (Python).",
            "unbounded": "Add limits to queries and pagination to prevent resource exhaustion.",
            "resource": "Use streaming for large files. Add pagination for database queries. Implement backpressure.",
            "fallback": "Implement fallback behavior for when external services fail. Return cached data or gracefully degrade.",
        }
        return remediations.get(tag, "Review and improve resilience handling.")


async def main():
    """CLI entry point."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Resilience Analyzer")
    parser.add_argument("path", nargs="?", default=".", help="Project path to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--check", choices=["timeouts", "circuit-breakers", "retries", "all"],
                        default="all", help="Specific check to run")
    parser.add_argument("--fail-on", choices=["critical", "high", "medium", "low"],
                        help="Exit with error if findings at this severity or above")

    args = parser.parse_args()
    project_path = Path(args.path).resolve()

    analyzer = ResilienceAnalyzer(project_path)
    findings = await analyzer.analyze()

    # Filter by check type if specified
    if args.check != "all":
        tag_map = {"timeouts": "timeout", "circuit-breakers": "circuit-breaker", "retries": "retry"}
        tag = tag_map.get(args.check, args.check)
        findings = [f for f in findings if tag in f.tags]

    if args.json:
        print(json.dumps([f.to_dict() for f in findings], indent=2))
    else:
        if not findings:
            print("No resilience issues found.")
        else:
            print(f"Found {len(findings)} resilience issues:\n")
            for f in findings:
                loc = f.file_path
                if f.line_number:
                    loc += f":{f.line_number}"
                print(f"[{f.severity.value.upper()}] {f.title}")
                print(f"  Location: {loc}")
                print(f"  Fix: {f.remediation}")
                print()

    if args.fail_on:
        severity_order = ["critical", "high", "medium", "low"]
        fail_index = severity_order.index(args.fail_on)
        for finding in findings:
            if finding.severity.value in severity_order[:fail_index + 1]:
                sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
