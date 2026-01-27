#!/usr/bin/env python3
"""
Injection Vulnerability Analyzer.
Detects SQL, XSS, command, SSRF, path traversal, and other injection vulnerabilities.
"""

import re
from pathlib import Path
from typing import Any

# Import from parent
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from audit_orchestrator import BaseAnalyzer, Category, Finding, Severity


class InjectionAnalyzer(BaseAnalyzer):
    """Analyze code for injection vulnerabilities."""

    category = Category.INJECTION

    # SQL Injection patterns
    SQL_PATTERNS = [
        # Template literals with variables
        (r'(query|execute|raw)\s*\(\s*`[^`]*\$\{[^}]+\}[^`]*`', "SQL injection via template literal"),
        # String concatenation in queries
        (r'(query|execute)\s*\([^)]*\+\s*\w+', "SQL injection via string concatenation"),
        (r"(query|execute)\s*\([^)]*'\s*\+\s*\w+", "SQL injection via string concatenation"),
        # f-strings in Python queries
        (r'(execute|cursor\.execute)\s*\(\s*f["\'][^"\']*\{', "SQL injection via f-string"),
        # .format() in queries
        (r'(execute|query)\s*\([^)]*\.format\s*\(', "SQL injection via .format()"),
        # Raw queries with user input
        (r'\.raw\s*\(\s*[^)]*\+', "SQL injection in raw query"),
    ]

    # XSS patterns
    XSS_PATTERNS = [
        # innerHTML
        (r'\.innerHTML\s*=\s*(?![\'"]\s*[\'"]\s*;)', "XSS via innerHTML"),
        # outerHTML
        (r'\.outerHTML\s*=', "XSS via outerHTML"),
        # document.write
        (r'document\.write\s*\(', "XSS via document.write"),
        # insertAdjacentHTML
        (r'\.insertAdjacentHTML\s*\(', "XSS via insertAdjacentHTML"),
        # React dangerouslySetInnerHTML
        (r'dangerouslySetInnerHTML\s*=\s*\{\s*\{', "XSS via dangerouslySetInnerHTML"),
        # Vue v-html
        (r'v-html\s*=', "XSS via Vue v-html directive"),
        # Angular [innerHTML]
        (r'\[innerHTML\]\s*=', "XSS via Angular innerHTML binding"),
    ]

    # Command injection patterns
    COMMAND_PATTERNS = [
        # exec with variable
        (r'exec\s*\(\s*[^)]*\+', "Command injection via exec"),
        (r'exec\s*\(\s*`[^`]*\$\{', "Command injection via exec with template"),
        (r'exec\s*\(\s*f["\']', "Command injection via exec with f-string"),
        # execSync
        (r'execSync\s*\(\s*[^)]*\+', "Command injection via execSync"),
        # spawn with shell: true
        (r'spawn\s*\([^)]*shell\s*:\s*true', "Command injection via spawn with shell"),
        # Python os.system
        (r'os\.system\s*\(\s*[^)]*\+', "Command injection via os.system"),
        (r'os\.system\s*\(\s*f["\']', "Command injection via os.system with f-string"),
        # Python subprocess with shell=True
        (r'subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True', "Command injection via subprocess with shell"),
    ]

    # SSRF patterns
    SSRF_PATTERNS = [
        # fetch with user input
        (r'fetch\s*\(\s*(?:req\.|request\.|params\.|body\.)', "SSRF via fetch with user input"),
        # axios with user input
        (r'axios\.(get|post|put|delete)\s*\(\s*(?:req\.|request\.|params\.|body\.)', "SSRF via axios with user input"),
        # request library
        (r'request\s*\(\s*(?:req\.|params\.|body\.)', "SSRF via request with user input"),
        # Python requests
        (r'requests\.(get|post|put|delete)\s*\(\s*(?:request\.|params\.)', "SSRF via requests with user input"),
        # urllib
        (r'urllib\.request\.urlopen\s*\(\s*(?:request\.|params\.)', "SSRF via urllib with user input"),
    ]

    # Path traversal patterns
    PATH_PATTERNS = [
        # fs operations with user input
        (r'fs\.(readFile|writeFile|unlink|rmdir)\s*\(\s*(?:req\.|params\.|body\.)', "Path traversal via fs operation"),
        (r'fs\.(readFile|writeFile|unlink|rmdir)Sync\s*\(\s*(?:req\.|params\.|body\.)', "Path traversal via fs operation"),
        # path.join without validation
        (r'path\.join\s*\([^)]*\.\.', "Path traversal via path.join with .."),
        # Python file operations
        (r'open\s*\(\s*(?:request\.|params\.)', "Path traversal via open with user input"),
        # require with variable (code injection)
        (r'require\s*\(\s*(?:req\.|params\.|body\.)', "Code injection via dynamic require"),
    ]

    # NoSQL injection patterns
    NOSQL_PATTERNS = [
        # MongoDB $where
        (r'\$where\s*:', "NoSQL injection via $where operator"),
        # Unvalidated query objects
        (r'\.find\s*\(\s*req\.body', "NoSQL injection via unvalidated query object"),
        (r'\.findOne\s*\(\s*req\.body', "NoSQL injection via unvalidated query object"),
    ]

    # XXE patterns
    XXE_PATTERNS = [
        # XML parsing without entity restriction
        (r'new\s+DOMParser\s*\(\s*\)', "Potential XXE - DOMParser without configuration"),
        (r'parseString\s*\(', "Potential XXE - XML parsing"),
        (r'etree\.parse\s*\(', "Potential XXE - lxml parsing"),
        (r'xml\.etree\.ElementTree', "Potential XXE - ElementTree (verify entity handling)"),
    ]

    SUPPORTED_EXTENSIONS = {'.js', '.jsx', '.ts', '.tsx', '.py', '.rb', '.php', '.java', '.go'}

    async def analyze(self) -> list[Finding]:
        """Analyze codebase for injection vulnerabilities."""
        findings = []

        for file_path in self._get_source_files():
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')

                # Check SQL injection
                findings.extend(self._check_patterns(
                    file_path, lines, self.SQL_PATTERNS,
                    Severity.CRITICAL, "CWE-89", "A03:2021"
                ))

                # Check XSS
                findings.extend(self._check_patterns(
                    file_path, lines, self.XSS_PATTERNS,
                    Severity.HIGH, "CWE-79", "A03:2021"
                ))

                # Check command injection
                findings.extend(self._check_patterns(
                    file_path, lines, self.COMMAND_PATTERNS,
                    Severity.CRITICAL, "CWE-78", "A03:2021"
                ))

                # Check SSRF
                findings.extend(self._check_patterns(
                    file_path, lines, self.SSRF_PATTERNS,
                    Severity.HIGH, "CWE-918", "A10:2021"
                ))

                # Check path traversal
                findings.extend(self._check_patterns(
                    file_path, lines, self.PATH_PATTERNS,
                    Severity.HIGH, "CWE-22", "A01:2021"
                ))

                # Check NoSQL injection
                findings.extend(self._check_patterns(
                    file_path, lines, self.NOSQL_PATTERNS,
                    Severity.HIGH, "CWE-943", "A03:2021"
                ))

                # Check XXE
                findings.extend(self._check_patterns(
                    file_path, lines, self.XXE_PATTERNS,
                    Severity.MEDIUM, "CWE-611", "A05:2021"
                ))

            except Exception as e:
                # Skip files that can't be read
                continue

        self.findings = findings
        return findings

    def _get_source_files(self):
        """Get all source files to analyze."""
        exclude_dirs = {'node_modules', '__pycache__', '.git', 'venv', '.venv', 'dist', 'build', 'vendor'}

        for ext in self.SUPPORTED_EXTENSIONS:
            for file_path in self.project_path.rglob(f'*{ext}'):
                # Skip excluded directories
                if any(excl in file_path.parts for excl in exclude_dirs):
                    continue
                yield file_path

    def _check_patterns(
        self,
        file_path: Path,
        lines: list[str],
        patterns: list[tuple[str, str]],
        severity: Severity,
        cwe_id: str,
        owasp_id: str,
    ) -> list[Finding]:
        """Check file content against patterns."""
        findings = []

        for line_num, line in enumerate(lines, 1):
            for pattern, description in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Get context (line before and after)
                    start = max(0, line_num - 2)
                    end = min(len(lines), line_num + 1)
                    snippet = '\n'.join(lines[start:end])

                    findings.append(self.create_finding(
                        severity=severity,
                        title=description,
                        description=f"Potential injection vulnerability detected: {description}",
                        file_path=str(file_path.relative_to(self.project_path)),
                        line_number=line_num,
                        code_snippet=snippet,
                        remediation=self._get_remediation(description),
                        cwe_id=cwe_id,
                        owasp_id=owasp_id,
                        tags=["injection", "security"],
                    ))

        return findings

    def _get_remediation(self, description: str) -> str:
        """Get remediation advice based on vulnerability type."""
        if "SQL" in description:
            return "Use parameterized queries or prepared statements. Never concatenate user input into SQL queries."
        elif "XSS" in description:
            return "Use proper output encoding/escaping. Avoid innerHTML; use textContent instead. Use framework-provided sanitization."
        elif "Command" in description:
            return "Avoid shell execution with user input. Use execFile instead of exec. Validate and sanitize all inputs."
        elif "SSRF" in description:
            return "Validate and whitelist allowed URLs. Block internal IP ranges. Use URL parsing to verify host."
        elif "Path" in description:
            return "Validate file paths against a whitelist. Use path.resolve and check the result starts with allowed directory."
        elif "NoSQL" in description:
            return "Validate query objects. Don't pass raw request body to database queries. Use explicit field selection."
        elif "XXE" in description:
            return "Disable external entity processing in XML parsers. Use defusedxml in Python."
        else:
            return "Validate and sanitize all user input. Apply defense in depth."


async def main():
    """CLI entry point."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Injection Vulnerability Analyzer")
    parser.add_argument("path", nargs="?", default=".", help="Project path to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--fail-on", choices=["critical", "high", "medium", "low"],
                        help="Exit with error if findings at this severity or above")

    args = parser.parse_args()
    project_path = Path(args.path).resolve()

    analyzer = InjectionAnalyzer(project_path)
    findings = await analyzer.analyze()

    if args.json:
        print(json.dumps([f.to_dict() for f in findings], indent=2))
    else:
        if not findings:
            print("No injection vulnerabilities found.")
        else:
            print(f"Found {len(findings)} potential injection vulnerabilities:\n")
            for f in findings:
                loc = f.file_path
                if f.line_number:
                    loc += f":{f.line_number}"
                print(f"[{f.severity.value.upper()}] {f.title}")
                print(f"  Location: {loc}")
                print(f"  {f.description}")
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
