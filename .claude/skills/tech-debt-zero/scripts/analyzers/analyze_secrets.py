#!/usr/bin/env python3
"""
Secrets Analyzer.
Detects hardcoded secrets, API keys, passwords, and credentials.
"""

import re
from pathlib import Path
from typing import Any

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
from audit_orchestrator import BaseAnalyzer, Category, Finding, Severity


class SecretsAnalyzer(BaseAnalyzer):
    """Analyze code for hardcoded secrets."""

    category = Category.SECRETS

    # High-entropy string pattern (potential secrets)
    HIGH_ENTROPY_PATTERN = re.compile(r'["\'][A-Za-z0-9+/=_-]{32,}["\']')

    # Specific secret patterns with names
    SECRET_PATTERNS = [
        # AWS
        (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID", Severity.CRITICAL),
        (r'["\']?aws[_-]?secret[_-]?access[_-]?key["\']?\s*[:=]\s*["\'][^"\']{20,}["\']', "AWS Secret Access Key", Severity.CRITICAL),

        # API Keys (generic)
        (r'["\']?api[_-]?key["\']?\s*[:=]\s*["\'][^"\']{16,}["\']', "Hardcoded API key", Severity.HIGH),
        (r'["\']?apikey["\']?\s*[:=]\s*["\'][^"\']{16,}["\']', "Hardcoded API key", Severity.HIGH),

        # JWT secrets
        (r'["\']?jwt[_-]?secret["\']?\s*[:=]\s*["\'][^"\']+["\']', "Hardcoded JWT secret", Severity.CRITICAL),
        (r'["\']?token[_-]?secret["\']?\s*[:=]\s*["\'][^"\']+["\']', "Hardcoded token secret", Severity.CRITICAL),

        # Database passwords
        (r'["\']?(?:db|database)[_-]?password["\']?\s*[:=]\s*["\'][^"\']+["\']', "Hardcoded database password", Severity.CRITICAL),
        (r'["\']?(?:mysql|postgres|mongo)[_-]?password["\']?\s*[:=]\s*["\'][^"\']+["\']', "Hardcoded database password", Severity.CRITICAL),

        # Generic passwords
        (r'["\']?password["\']?\s*[:=]\s*["\'][^"\']{4,}["\']', "Hardcoded password", Severity.HIGH),
        (r'["\']?passwd["\']?\s*[:=]\s*["\'][^"\']{4,}["\']', "Hardcoded password", Severity.HIGH),

        # Private keys
        (r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----', "Private key in code", Severity.CRITICAL),
        (r'-----BEGIN PGP PRIVATE KEY BLOCK-----', "PGP private key in code", Severity.CRITICAL),

        # OAuth/Auth tokens
        (r'["\']?(?:oauth|auth)[_-]?token["\']?\s*[:=]\s*["\'][^"\']+["\']', "Hardcoded OAuth token", Severity.HIGH),
        (r'["\']?access[_-]?token["\']?\s*[:=]\s*["\'][^"\']+["\']', "Hardcoded access token", Severity.HIGH),
        (r'["\']?refresh[_-]?token["\']?\s*[:=]\s*["\'][^"\']+["\']', "Hardcoded refresh token", Severity.HIGH),

        # Stripe
        (r'sk_live_[0-9a-zA-Z]{24}', "Stripe live secret key", Severity.CRITICAL),
        (r'sk_test_[0-9a-zA-Z]{24}', "Stripe test secret key", Severity.MEDIUM),
        (r'rk_live_[0-9a-zA-Z]{24}', "Stripe restricted key", Severity.HIGH),

        # GitHub
        (r'ghp_[0-9a-zA-Z]{36}', "GitHub personal access token", Severity.CRITICAL),
        (r'gho_[0-9a-zA-Z]{36}', "GitHub OAuth token", Severity.CRITICAL),
        (r'github_pat_[0-9a-zA-Z_]{22,}', "GitHub personal access token", Severity.CRITICAL),

        # Slack
        (r'xox[baprs]-[0-9a-zA-Z-]+', "Slack token", Severity.HIGH),

        # Google
        (r'AIza[0-9A-Za-z_-]{35}', "Google API key", Severity.HIGH),

        # SendGrid
        (r'SG\.[0-9A-Za-z_-]{22}\.[0-9A-Za-z_-]{43}', "SendGrid API key", Severity.HIGH),

        # Twilio
        (r'SK[0-9a-fA-F]{32}', "Twilio API key", Severity.HIGH),

        # Mailchimp
        (r'[0-9a-f]{32}-us[0-9]{1,2}', "Mailchimp API key", Severity.HIGH),

        # Heroku
        (r'["\']?heroku[_-]?api[_-]?key["\']?\s*[:=]\s*["\'][0-9a-fA-F-]+["\']', "Heroku API key", Severity.HIGH),

        # Generic secrets
        (r'["\']?secret[_-]?key["\']?\s*[:=]\s*["\'][^"\']{8,}["\']', "Hardcoded secret key", Severity.HIGH),
        (r'["\']?encryption[_-]?key["\']?\s*[:=]\s*["\'][^"\']+["\']', "Hardcoded encryption key", Severity.CRITICAL),
        (r'["\']?signing[_-]?key["\']?\s*[:=]\s*["\'][^"\']+["\']', "Hardcoded signing key", Severity.CRITICAL),

        # Connection strings
        (r'(?:mongodb|postgres|mysql|redis)://[^"\'\s]+:[^"\'\s]+@', "Connection string with credentials", Severity.CRITICAL),
    ]

    # Patterns that indicate logging of secrets
    SECRET_LOGGING_PATTERNS = [
        (r'(?:console\.log|logger\.\w+|print)\s*\([^)]*(?:password|secret|token|key|credential)', "Secret potentially logged", Severity.HIGH),
        (r'(?:console\.log|logger\.\w+|print)\s*\([^)]*apiKey', "API key potentially logged", Severity.HIGH),
    ]

    # Files to skip
    SKIP_PATTERNS = [
        r'\.test\.',
        r'\.spec\.',
        r'_test\.',
        r'test_',
        r'mock',
        r'fixture',
        r'\.example',
        r'\.sample',
        r'\.md$',
        r'\.txt$',
        r'package-lock\.json',
        r'yarn\.lock',
        r'poetry\.lock',
    ]

    SUPPORTED_EXTENSIONS = {
        '.js', '.jsx', '.ts', '.tsx', '.py', '.rb', '.php', '.java',
        '.go', '.rs', '.cs', '.yaml', '.yml', '.json', '.env', '.config',
        '.properties', '.xml', '.toml', '.ini', '.conf'
    }

    async def analyze(self) -> list[Finding]:
        """Analyze codebase for hardcoded secrets."""
        findings = []

        for file_path in self._get_source_files():
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')

                # Check secret patterns
                for line_num, line in enumerate(lines, 1):
                    for pattern, description, severity in self.SECRET_PATTERNS:
                        if re.search(pattern, line, re.IGNORECASE):
                            # Check if it's a false positive
                            if self._is_false_positive(line, file_path):
                                continue

                            findings.append(self.create_finding(
                                severity=severity,
                                title=description,
                                description=f"Potential hardcoded secret detected: {description}",
                                file_path=str(file_path.relative_to(self.project_path)),
                                line_number=line_num,
                                code_snippet=self._redact_secret(line),
                                remediation="Remove hardcoded secret. Use environment variables or a secrets manager (AWS Secrets Manager, HashiCorp Vault).",
                                cwe_id="CWE-798",
                                owasp_id="A07:2021",
                                tags=["secrets", "security", "credentials"],
                            ))

                # Check secret logging
                for line_num, line in enumerate(lines, 1):
                    for pattern, description in self.SECRET_LOGGING_PATTERNS:
                        if re.search(pattern, line, re.IGNORECASE):
                            findings.append(self.create_finding(
                                severity=Severity.HIGH,
                                title=description,
                                description="Secrets should never be logged, even accidentally.",
                                file_path=str(file_path.relative_to(self.project_path)),
                                line_number=line_num,
                                code_snippet=line.strip(),
                                remediation="Remove secret from log output. Use a redaction utility for logging.",
                                cwe_id="CWE-532",
                                owasp_id="A09:2021",
                                tags=["secrets", "logging", "security"],
                            ))

            except Exception:
                continue

        # Check for .env files that might be committed
        findings.extend(self._check_env_files())

        self.findings = findings
        return findings

    def _get_source_files(self):
        """Get all source files to analyze."""
        exclude_dirs = {'node_modules', '__pycache__', '.git', 'venv', '.venv', 'dist', 'build', 'vendor'}

        for file_path in self.project_path.rglob('*'):
            if not file_path.is_file():
                continue

            # Check extension
            if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
                continue

            # Skip excluded directories
            if any(excl in file_path.parts for excl in exclude_dirs):
                continue

            # Skip test/mock files
            path_str = str(file_path)
            if any(re.search(skip, path_str, re.IGNORECASE) for skip in self.SKIP_PATTERNS):
                continue

            yield file_path

    def _is_false_positive(self, line: str, file_path: Path) -> bool:
        """Check if the match is likely a false positive."""
        line_lower = line.lower()

        # Skip comments
        stripped = line.strip()
        if stripped.startswith('//') or stripped.startswith('#') or stripped.startswith('*'):
            return True

        # Skip placeholder/example values
        placeholder_indicators = [
            'your_', 'your-', 'example', 'placeholder', 'xxx', 'changeme',
            'todo', 'fixme', 'replace', '<', '>'
        ]
        if any(ind in line_lower for ind in placeholder_indicators):
            return True

        # Skip env variable references
        if 'process.env' in line or 'os.environ' in line or 'getenv' in line:
            return True

        # Skip empty string assignments
        if re.search(r'[:=]\s*["\']["\']', line):
            return True

        return False

    def _redact_secret(self, line: str) -> str:
        """Redact the actual secret value from the line."""
        # Replace long strings that look like secrets
        redacted = re.sub(r'(["\'])[A-Za-z0-9+/=_-]{16,}\1', r'\1[REDACTED]\1', line)
        return redacted

    def _check_env_files(self) -> list[Finding]:
        """Check for .env files that might contain secrets."""
        findings = []
        env_files = list(self.project_path.glob('**/.env')) + list(self.project_path.glob('**/.env.*'))

        # Exclude .env.example, .env.sample
        env_files = [f for f in env_files if not any(
            ex in f.name for ex in ['.example', '.sample', '.template']
        )]

        for env_file in env_files:
            # Check if it's in .gitignore
            gitignore_path = self.project_path / '.gitignore'
            is_ignored = False

            if gitignore_path.exists():
                gitignore_content = gitignore_path.read_text()
                if '.env' in gitignore_content or env_file.name in gitignore_content:
                    is_ignored = True

            if not is_ignored:
                findings.append(self.create_finding(
                    severity=Severity.CRITICAL,
                    title=".env file may be committed to repository",
                    description=f"The file {env_file.name} exists and may not be in .gitignore. Environment files often contain secrets.",
                    file_path=str(env_file.relative_to(self.project_path)),
                    remediation="Add .env to .gitignore. If already committed, remove from history with git filter-branch or BFG.",
                    cwe_id="CWE-312",
                    owasp_id="A05:2021",
                    tags=["secrets", "security", "configuration"],
                ))

        return findings


async def main():
    """CLI entry point."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Secrets Analyzer")
    parser.add_argument("path", nargs="?", default=".", help="Project path to analyze")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--fail-on", choices=["critical", "high", "medium", "low"],
                        help="Exit with error if findings at this severity or above")

    args = parser.parse_args()
    project_path = Path(args.path).resolve()

    analyzer = SecretsAnalyzer(project_path)
    findings = await analyzer.analyze()

    if args.json:
        print(json.dumps([f.to_dict() for f in findings], indent=2))
    else:
        if not findings:
            print("No hardcoded secrets found.")
        else:
            print(f"Found {len(findings)} potential hardcoded secrets:\n")
            for f in findings:
                loc = f.file_path
                if f.line_number:
                    loc += f":{f.line_number}"
                print(f"[{f.severity.value.upper()}] {f.title}")
                print(f"  Location: {loc}")
                if f.code_snippet:
                    print(f"  Code: {f.code_snippet[:80]}...")
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
