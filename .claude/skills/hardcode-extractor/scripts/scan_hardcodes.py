#!/usr/bin/env python3
"""
Hardcode Scanner - Detect hardcoded values in source code.

Usage:
    python scan_hardcodes.py <path> [--output report.json] [--format json|text] [--severity all|high|medium]
    
Examples:
    python scan_hardcodes.py ./src                    # Scan directory, text output
    python scan_hardcodes.py ./app.py --format json   # Scan file, JSON output
    python scan_hardcodes.py . --output report.json   # Scan cwd, save to file
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Generator

class Severity(Enum):
    HIGH = "high"      # Secrets, credentials - must extract
    MEDIUM = "medium"  # URLs, paths, thresholds - should extract
    LOW = "low"        # Magic numbers, strings - consider extracting

class Category(Enum):
    SECRET = "secret"
    URL = "url"
    NUMBER = "number"
    STRING = "string"
    PATH = "path"

@dataclass
class Hardcode:
    file: str
    line: int
    column: int
    value: str
    category: str
    severity: str
    context: str
    suggestion: str

# File extensions to scan by language
EXTENSIONS = {
    '.py': 'python',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.go': 'go',
    '.rs': 'rust',
    '.java': 'java',
    '.cs': 'csharp',
    '.rb': 'ruby',
    '.php': 'php',
    '.swift': 'swift',
    '.kt': 'kotlin',
    '.scala': 'scala',
    '.c': 'c',
    '.cpp': 'cpp',
    '.h': 'c',
    '.hpp': 'cpp',
}

# Directories to skip
SKIP_DIRS = {
    'node_modules', '.git', '__pycache__', 'venv', '.venv', 'env',
    '.env', 'dist', 'build', 'target', '.idea', '.vscode', 'vendor',
    'coverage', '.pytest_cache', '.mypy_cache', 'eggs', '*.egg-info',
}

# Files to skip
SKIP_FILES = {
    'package-lock.json', 'yarn.lock', 'poetry.lock', 'Cargo.lock',
    'go.sum', 'pnpm-lock.yaml', '*.min.js', '*.min.css',
}

# Patterns for detecting hardcoded values
PATTERNS = {
    # ===========================================
    # HIGH SEVERITY - Secrets (must extract)
    # ===========================================
    
    # Generic secrets
    'api_key': {
        'pattern': r'''(?:api[_-]?key|apikey|api[_-]?secret)\s*[=:]\s*["\']([^"\']{16,})["\']''',
        'category': Category.SECRET,
        'severity': Severity.HIGH,
        'suggestion': 'Move to .env as API_KEY or use secrets manager',
    },
    'password': {
        'pattern': r'''(?:password|passwd|pwd|secret|credential)\s*[=:]\s*["\']([^"\']+)["\']''',
        'category': Category.SECRET,
        'severity': Severity.HIGH,
        'suggestion': 'Move to .env or use secrets manager - NEVER commit passwords',
    },
    'token': {
        'pattern': r'''(?:token|auth[_-]?token|access[_-]?token|bearer|jwt[_-]?secret)\s*[=:]\s*["\']([^"\']{20,})["\']''',
        'category': Category.SECRET,
        'severity': Severity.HIGH,
        'suggestion': 'Move to .env as AUTH_TOKEN or use secrets manager',
    },
    'private_key': {
        'pattern': r'''-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----''',
        'category': Category.SECRET,
        'severity': Severity.HIGH,
        'suggestion': 'Private key in code - move to secure file or secrets manager',
    },
    'connection_string': {
        'pattern': r'''(?:mongodb(?:\+srv)?|postgres(?:ql)?|mysql|redis|amqp|mssql)://[^"\'\s]+:[^"\'\s]+@[^"\'\s]+''',
        'category': Category.SECRET,
        'severity': Severity.HIGH,
        'suggestion': 'Database connection string with credentials - use env vars',
    },
    
    # AWS
    'aws_access_key': {
        'pattern': r'''["\'"]?(AKIA[0-9A-Z]{16})["\']?''',
        'category': Category.SECRET,
        'severity': Severity.HIGH,
        'suggestion': 'AWS access key - use IAM roles, instance profiles, or env vars',
    },
    'aws_secret_key': {
        'pattern': r'''(?:aws[_-]?secret|secret[_-]?access[_-]?key)\s*[=:]\s*["\']([A-Za-z0-9/+=]{40})["\']''',
        'category': Category.SECRET,
        'severity': Severity.HIGH,
        'suggestion': 'AWS secret key - use IAM roles or secrets manager',
    },
    
    # GitHub
    'github_token': {
        'pattern': r'''["\'"]?(ghp_[A-Za-z0-9]{36}|gho_[A-Za-z0-9]{36}|ghu_[A-Za-z0-9]{36}|ghs_[A-Za-z0-9]{36}|ghr_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9]{22}_[A-Za-z0-9]{59})["\']?''',
        'category': Category.SECRET,
        'severity': Severity.HIGH,
        'suggestion': 'GitHub token - use GITHUB_TOKEN env var or secrets',
    },
    
    # Stripe
    'stripe_key': {
        'pattern': r'''["\'"]?(sk_live_[A-Za-z0-9]{24,}|pk_live_[A-Za-z0-9]{24,}|sk_test_[A-Za-z0-9]{24,}|pk_test_[A-Za-z0-9]{24,}|rk_live_[A-Za-z0-9]{24,}|rk_test_[A-Za-z0-9]{24,})["\']?''',
        'category': Category.SECRET,
        'severity': Severity.HIGH,
        'suggestion': 'Stripe API key - use STRIPE_SECRET_KEY env var',
    },
    
    # Slack
    'slack_token': {
        'pattern': r'''["\'"]?(xox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*)["\']?''',
        'category': Category.SECRET,
        'severity': Severity.HIGH,
        'suggestion': 'Slack token - use SLACK_TOKEN env var or Slack secrets',
    },
    'slack_webhook': {
        'pattern': r'''["\'"]?(https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+)["\']?''',
        'category': Category.SECRET,
        'severity': Severity.HIGH,
        'suggestion': 'Slack webhook URL - use SLACK_WEBHOOK_URL env var',
    },
    
    # Google
    'google_api_key': {
        'pattern': r'''["\'"]?(AIza[0-9A-Za-z_-]{35})["\']?''',
        'category': Category.SECRET,
        'severity': Severity.HIGH,
        'suggestion': 'Google API key - use GOOGLE_API_KEY env var or service account',
    },
    'google_oauth': {
        'pattern': r'''["\'"]?([0-9]+-[a-z0-9]+\.apps\.googleusercontent\.com)["\']?''',
        'category': Category.SECRET,
        'severity': Severity.HIGH,
        'suggestion': 'Google OAuth client ID - use env var',
    },
    'gcp_service_account': {
        'pattern': r'''"type"\s*:\s*"service_account"''',
        'category': Category.SECRET,
        'severity': Severity.HIGH,
        'suggestion': 'GCP service account JSON - use GOOGLE_APPLICATION_CREDENTIALS path',
    },
    
    # SendGrid / Twilio / Other SaaS
    'sendgrid_key': {
        'pattern': r'''["\'"]?(SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43})["\']?''',
        'category': Category.SECRET,
        'severity': Severity.HIGH,
        'suggestion': 'SendGrid API key - use SENDGRID_API_KEY env var',
    },
    'twilio_key': {
        'pattern': r'''["\'"]?(SK[a-f0-9]{32})["\']?''',
        'category': Category.SECRET,
        'severity': Severity.HIGH,
        'suggestion': 'Twilio API key - use TWILIO_API_KEY env var',
    },
    'mailchimp_key': {
        'pattern': r'''["\'"]?([a-f0-9]{32}-us[0-9]{1,2})["\']?''',
        'category': Category.SECRET,
        'severity': Severity.HIGH,
        'suggestion': 'Mailchimp API key - use MAILCHIMP_API_KEY env var',
    },
    
    # NPM / PyPI
    'npm_token': {
        'pattern': r'''["\'"]?(npm_[A-Za-z0-9]{36})["\']?''',
        'category': Category.SECRET,
        'severity': Severity.HIGH,
        'suggestion': 'NPM token - use NPM_TOKEN env var',
    },
    
    # Heroku
    'heroku_api_key': {
        'pattern': r'''["\'"]?([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})["\']?''',
        'category': Category.SECRET,
        'severity': Severity.MEDIUM,  # UUID format has false positives
        'suggestion': 'Possible Heroku API key or UUID - verify and extract if secret',
    },
    
    # Generic high-entropy strings (likely secrets)
    'high_entropy_secret': {
        'pattern': r'''(?:secret|key|token|password|credential|auth)\s*[=:]\s*["\']([A-Za-z0-9+/=_-]{32,})["\']''',
        'category': Category.SECRET,
        'severity': Severity.HIGH,
        'suggestion': 'High-entropy secret value - move to env var or secrets manager',
    },
    
    # ===========================================
    # MEDIUM SEVERITY - URLs and paths (should extract)
    # ===========================================
    'http_url': {
        'pattern': r'''["']+(https?://(?!example\.com|localhost|127\.0\.0\.1|0\.0\.0\.0|schemas\.)[a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,}[^"']*)["\']''',
        'category': Category.URL,
        'severity': Severity.MEDIUM,
        'suggestion': 'Extract to config as API_URL or BASE_URL',
    },
    'websocket_url': {
        'pattern': r'''["']+(wss?://[a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,}[^"']*)["\']''',
        'category': Category.URL,
        'severity': Severity.MEDIUM,
        'suggestion': 'Extract WebSocket URL to config as WS_URL',
    },
    'ip_address': {
        'pattern': r'''["']((?!127\.0\.0\.1|0\.0\.0\.0|255\.255\.255\.\d+)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})["\':,\]]''',
        'category': Category.URL,
        'severity': Severity.MEDIUM,
        'suggestion': 'Extract IP to config - may vary by environment',
    },
    'port_number': {
        'pattern': r'''(?:port|PORT)\s*[=:]\s*(\d{4,5})(?!\d)''',
        'category': Category.NUMBER,
        'severity': Severity.MEDIUM,
        'suggestion': 'Extract port to config for environment flexibility',
    },
    'file_path_absolute': {
        'pattern': r'''["'](/(?:home|usr|var|etc|opt|tmp|data|app|srv)[^"']+)["\']''',
        'category': Category.PATH,
        'severity': Severity.MEDIUM,
        'suggestion': 'Absolute path - extract to config or use relative paths',
    },
    'windows_path': {
        'pattern': r'''["']+([A-Z]:\\[^"']+)["\']''',
        'category': Category.PATH,
        'severity': Severity.MEDIUM,
        'suggestion': 'Windows absolute path - extract to config',
    },
    's3_bucket': {
        'pattern': r'''["']+(s3://[a-z0-9][-a-z0-9.]*[^"']*|arn:aws:s3:::[a-z0-9][-a-z0-9.]*)["\']''',
        'category': Category.PATH,
        'severity': Severity.MEDIUM,
        'suggestion': 'S3 bucket/ARN - extract to config as S3_BUCKET',
    },
    'gcs_bucket': {
        'pattern': r'''["']+(gs://[a-z0-9][-a-z0-9.]*[^"']*)["\']''',
        'category': Category.PATH,
        'severity': Severity.MEDIUM,
        'suggestion': 'GCS bucket - extract to config as GCS_BUCKET',
    },
    
    # ===========================================
    # MEDIUM SEVERITY - Thresholds and limits
    # ===========================================
    'timeout': {
        'pattern': r'''(?:timeout|TIMEOUT|time_out|TIME_OUT)\s*[=:]\s*(\d+)(?:\s*\*?\s*(?:1000|60|3600))?''',
        'category': Category.NUMBER,
        'severity': Severity.MEDIUM,
        'suggestion': 'Extract timeout to config as TIMEOUT_MS or TIMEOUT_SECONDS',
    },
    'retry_count': {
        'pattern': r'''(?:max[_-]?retries?|retry[_-]?count|attempts?|MAX_RETRIES)\s*[=:]\s*(\d+)''',
        'category': Category.NUMBER,
        'severity': Severity.MEDIUM,
        'suggestion': 'Extract to config as MAX_RETRIES',
    },
    'batch_size': {
        'pattern': r'''(?:batch[_-]?size|page[_-]?size|limit|BATCH_SIZE|PAGE_SIZE)\s*[=:]\s*(\d+)''',
        'category': Category.NUMBER,
        'severity': Severity.MEDIUM,
        'suggestion': 'Extract to config as BATCH_SIZE or PAGE_SIZE',
    },
    'cache_ttl': {
        'pattern': r'''(?:cache[_-]?ttl|ttl|expir(?:y|ation)|max[_-]?age)\s*[=:]\s*(\d+)''',
        'category': Category.NUMBER,
        'severity': Severity.MEDIUM,
        'suggestion': 'Extract to config as CACHE_TTL_SECONDS',
    },
    'pool_size': {
        'pattern': r'''(?:pool[_-]?size|max[_-]?connections?|min[_-]?connections?|workers?)\s*[=:]\s*(\d+)''',
        'category': Category.NUMBER,
        'severity': Severity.MEDIUM,
        'suggestion': 'Extract to config for environment-specific tuning',
    },
    
    # ===========================================
    # LOW SEVERITY - Magic numbers (consider extracting)
    # ===========================================
    'magic_number_large': {
        'pattern': r'''(?<![0-9a-zA-Z_])([1-9]\d{4,})(?![0-9a-zA-Z_])''',
        'category': Category.NUMBER,
        'severity': Severity.LOW,
        'suggestion': 'Large number - consider naming as constant if it has business meaning',
    },
    'magic_number_float': {
        'pattern': r'''(?<![0-9a-zA-Z_])(\d+\.\d{2,})(?![0-9a-zA-Z_])''',
        'category': Category.NUMBER,
        'severity': Severity.LOW,
        'suggestion': 'Float literal - consider naming if it represents a rate/threshold',
    },
    'email_address': {
        'pattern': r'''["']([a-zA-Z0-9._%+-]+@(?!example\.com)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})["']''',
        'category': Category.STRING,
        'severity': Severity.LOW,
        'suggestion': 'Email address - extract to config if environment-specific',
    },
    'hardcoded_env': {
        'pattern': r'''["'](production|staging|development|prod|dev|stage|qa)["']''',
        'category': Category.STRING,
        'severity': Severity.LOW,
        'suggestion': 'Environment name should come from NODE_ENV or APP_ENV',
    },
}

# Values to ignore (false positives)
IGNORE_VALUES = {
    # Common test/example values
    'example.com', 'test.com', 'localhost', '127.0.0.1', '0.0.0.0',
    'your-api-key', 'your-secret', 'xxx', 'placeholder', 'changeme',
    'password', 'secret', 'token', 'key',  # Generic placeholders
    'TODO', 'FIXME', 'XXX', 'HACK',
    # Common acceptable numbers
    '0', '1', '2', '3', '4', '5', '10', '-1', '100',
    '200', '201', '204', '301', '302', '304',  # HTTP status codes
    '400', '401', '403', '404', '405', '409', '422', '429',
    '500', '502', '503', '504',
    '1000', '60', '3600', '86400', '604800',  # Common time units
    '1024', '2048', '4096', '8192', '16384', '32768', '65536',  # Powers of 2
    '1048576', '1073741824',  # 1MB, 1GB in bytes
    # Common version/year patterns
    '2020', '2021', '2022', '2023', '2024', '2025',
}

# Patterns that indicate value is already configurable
ALREADY_CONFIG_PATTERNS = [
    r'(?:os\.)?(?:environ|getenv|env)\s*[.\[(]',  # Python env
    r'process\.env\.',  # Node.js env
    r'System\.getenv\s*\(',  # Java env
    r'Environment\.GetEnvironmentVariable',  # C# env
    r'std::env::var',  # Rust env
    r'os\.Getenv\s*\(',  # Go env
    r'ENV\[',  # Ruby env
    r'\$_ENV\[',  # PHP env
    r'config\s*[.\[(]',  # Generic config access
    r'settings\s*[.\[]',  # Settings access
    r'Config\.',  # Config class
    r'@Value\s*\(',  # Spring annotation
    r'@ConfigurationProperties',  # Spring Boot
    r'configuration\[',  # Configuration access
    r'AppConfig\.',  # App config
    r'viper\.',  # Go viper
    r'figment::',  # Rust figment
    r'\.env\.',  # Dotenv access
    r'IConfiguration',  # .NET configuration
    r'ConfigParser',  # Python configparser
]


def should_skip_path(path: Path) -> bool:
    """Check if path should be skipped."""
    for part in path.parts:
        if part in SKIP_DIRS or part.startswith('.'):
            return True
    for pattern in SKIP_FILES:
        if path.match(pattern):
            return True
    return False


def get_language(path: Path) -> str | None:
    """Get language from file extension."""
    return EXTENSIONS.get(path.suffix.lower())


def is_in_comment(line: str, match_start: int, language: str) -> bool:
    """Check if match position is inside a comment."""
    # Single-line comment markers by language
    comment_markers = {
        'python': ['#'],
        'javascript': ['//', '/*'],
        'typescript': ['//', '/*'],
        'go': ['//', '/*'],
        'rust': ['//', '/*'],
        'java': ['//', '/*'],
        'csharp': ['//', '/*'],
        'ruby': ['#'],
        'php': ['//', '#', '/*'],
        'swift': ['//', '/*'],
        'kotlin': ['//', '/*'],
        'scala': ['//', '/*'],
        'c': ['//', '/*'],
        'cpp': ['//', '/*'],
    }
    
    markers = comment_markers.get(language, ['//', '#'])
    for marker in markers:
        pos = line.find(marker)
        if pos != -1 and pos < match_start:
            return True
    return False


def is_already_configurable(line: str) -> bool:
    """Check if the line already uses configuration."""
    for pattern in ALREADY_CONFIG_PATTERNS:
        if re.search(pattern, line, re.IGNORECASE):
            return True
    return False


def scan_file(filepath: Path, min_severity: Severity = Severity.LOW) -> Generator[Hardcode, None, None]:
    """Scan a single file for hardcoded values."""
    language = get_language(filepath)
    if not language:
        return
    
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
    except (IOError, OSError):
        return
    
    lines = content.split('\n')
    severity_order = [Severity.HIGH, Severity.MEDIUM, Severity.LOW]
    min_severity_idx = severity_order.index(min_severity)
    
    for line_num, line in enumerate(lines, 1):
        # Skip empty lines and lines that are already using config
        if not line.strip() or is_already_configurable(line):
            continue
        
        for name, config in PATTERNS.items():
            # Skip if below minimum severity
            if severity_order.index(config['severity']) > min_severity_idx:
                continue
                
            for match in re.finditer(config['pattern'], line, re.IGNORECASE):
                # Get the captured value (first group or full match)
                value = match.group(1) if match.lastindex else match.group(0)
                
                # Skip ignored values
                if value.lower() in IGNORE_VALUES or len(value) < 3:
                    continue
                
                # Skip if in comment
                if is_in_comment(line, match.start(), language):
                    continue
                
                # Get context (surrounding code)
                start = max(0, line_num - 2)
                end = min(len(lines), line_num + 1)
                context_lines = lines[start:end]
                context = '\n'.join(f"{start + i + 1}: {l}" for i, l in enumerate(context_lines))
                
                yield Hardcode(
                    file=str(filepath),
                    line=line_num,
                    column=match.start() + 1,
                    value=value[:100] + ('...' if len(value) > 100 else ''),
                    category=config['category'].value,
                    severity=config['severity'].value,
                    context=context,
                    suggestion=config['suggestion'],
                )


def scan_directory(dirpath: Path, min_severity: Severity = Severity.LOW) -> Generator[Hardcode, None, None]:
    """Recursively scan directory for hardcoded values."""
    for path in dirpath.rglob('*'):
        if path.is_file() and not should_skip_path(path):
            yield from scan_file(path, min_severity)


def scan_path(path: Path, min_severity: Severity = Severity.LOW) -> list[Hardcode]:
    """Scan path (file or directory) for hardcoded values."""
    if path.is_file():
        return list(scan_file(path, min_severity))
    elif path.is_dir():
        return list(scan_directory(path, min_severity))
    else:
        print(f"Error: Path not found: {path}", file=sys.stderr)
        return []


def format_text_report(hardcodes: list[Hardcode], show_duplicates: bool = False) -> str:
    """Format hardcodes as readable text report."""
    if not hardcodes:
        return "✅ No hardcoded values detected!"
    
    # Deduplicate by value (keep first occurrence)
    seen_values = {}
    unique_hardcodes = []
    duplicate_count = 0
    
    for h in hardcodes:
        if h.value in seen_values:
            duplicate_count += 1
            seen_values[h.value].append(f"{h.file}:{h.line}")
        else:
            seen_values[h.value] = [f"{h.file}:{h.line}"]
            unique_hardcodes.append(h)
    
    display_list = hardcodes if show_duplicates else unique_hardcodes
    
    # Group by severity
    by_severity = {'high': [], 'medium': [], 'low': []}
    for h in display_list:
        by_severity[h.severity].append(h)
    
    lines = [
        f"🔍 Hardcode Scan Results",
        f"{'=' * 60}",
        f"Total findings: {len(hardcodes)} ({len(unique_hardcodes)} unique values)",
    ]
    
    if duplicate_count > 0:
        lines.append(f"  ⚠️  {duplicate_count} duplicates across files (same value, multiple locations)")
    
    lines.extend([
        f"  🔴 High:   {len(by_severity['high'])} (must extract)",
        f"  🟡 Medium: {len(by_severity['medium'])} (should extract)",
        f"  🟢 Low:    {len(by_severity['low'])} (consider extracting)",
        "",
    ])
    
    # Show values that appear in multiple files
    multi_file_values = {v: locs for v, locs in seen_values.items() if len(locs) > 1}
    if multi_file_values and not show_duplicates:
        lines.append("📋 Values found in multiple locations (good extraction candidates):")
        lines.append("-" * 60)
        for value, locations in sorted(multi_file_values.items(), key=lambda x: -len(x[1]))[:10]:
            display_val = value[:50] + "..." if len(value) > 50 else value
            lines.append(f"  • \"{display_val}\" → {len(locations)} locations")
        lines.append("")
    
    for severity in ['high', 'medium', 'low']:
        items = by_severity[severity]
        if not items:
            continue
        
        icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}[severity]
        lines.append(f"\n{icon} {severity.upper()} SEVERITY ({len(items)} findings)")
        lines.append('-' * 60)
        
        for h in items:
            lines.extend([
                f"\n📍 {h.file}:{h.line}:{h.column}",
                f"   Category: {h.category}",
                f"   Value: {h.value}",
                f"   💡 {h.suggestion}",
            ])
            
            # Show other locations if this value appears multiple times
            if h.value in multi_file_values and len(multi_file_values[h.value]) > 1:
                other_locs = [loc for loc in multi_file_values[h.value] if not loc.startswith(f"{h.file}:{h.line}")]
                if other_locs:
                    lines.append(f"   📎 Also at: {', '.join(other_locs[:3])}" + 
                                (" ..." if len(other_locs) > 3 else ""))
            
            lines.append(f"   Context:")
            lines.extend([f"      {l}" for l in h.context.split('\n')])
    
    return '\n'.join(lines)


def format_json_report(hardcodes: list[Hardcode]) -> str:
    """Format hardcodes as JSON report."""
    report = {
        'summary': {
            'total': len(hardcodes),
            'by_severity': {
                'high': len([h for h in hardcodes if h.severity == 'high']),
                'medium': len([h for h in hardcodes if h.severity == 'medium']),
                'low': len([h for h in hardcodes if h.severity == 'low']),
            },
            'by_category': {},
        },
        'findings': [asdict(h) for h in hardcodes],
    }
    
    # Count by category
    for h in hardcodes:
        report['summary']['by_category'][h.category] = \
            report['summary']['by_category'].get(h.category, 0) + 1
    
    return json.dumps(report, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='Scan code for hardcoded values',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s ./src                           # Scan directory
  %(prog)s ./app.py --format json          # Scan file, JSON output  
  %(prog)s . --severity high               # Only high severity issues
  %(prog)s . --output report.json          # Save to file
  %(prog)s . --exclude "*.test.py,*_test.go"  # Exclude test files
  %(prog)s . --include-tests               # Include test directories
  %(prog)s . --show-duplicates             # Show all occurrences
        '''
    )
    parser.add_argument('path', help='File or directory to scan')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--format', '-f', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    parser.add_argument('--severity', '-s', choices=['all', 'high', 'medium'], default='all',
                        help='Minimum severity to report (default: all)')
    parser.add_argument('--exclude', '-e', 
                        help='Comma-separated glob patterns to exclude (e.g., "*.test.py,*_test.go")')
    parser.add_argument('--include-tests', action='store_true',
                        help='Include test directories (tests/, __tests__, spec/)')
    parser.add_argument('--show-duplicates', action='store_true',
                        help='Show all occurrences of duplicate values')
    
    args = parser.parse_args()
    
    # Add test directories to skip list if not including tests
    if not args.include_tests:
        SKIP_DIRS.update({'tests', 'test', '__tests__', 'spec', 'specs', 'testing'})
    
    # Add custom exclusion patterns
    if args.exclude:
        for pattern in args.exclude.split(','):
            pattern = pattern.strip()
            if '/' in pattern or '\\' in pattern:
                SKIP_DIRS.add(pattern)
            else:
                SKIP_FILES.add(pattern)
    
    # Map severity argument
    min_severity = {
        'all': Severity.LOW,
        'medium': Severity.MEDIUM,
        'high': Severity.HIGH,
    }[args.severity]
    
    # Scan
    path = Path(args.path)
    hardcodes = scan_path(path, min_severity)
    
    # Sort by severity (high first), then by file and line
    severity_order = {'high': 0, 'medium': 1, 'low': 2}
    hardcodes.sort(key=lambda h: (severity_order[h.severity], h.file, h.line))
    
    # Format output
    if args.format == 'json':
        output = format_json_report(hardcodes)
    else:
        output = format_text_report(hardcodes, show_duplicates=args.show_duplicates)
    
    # Write output
    if args.output:
        Path(args.output).write_text(output)
        print(f"Report saved to {args.output}")
    else:
        print(output)
    
    # Exit with error code if high severity issues found
    high_count = len([h for h in hardcodes if h.severity == 'high'])
    sys.exit(1 if high_count > 0 else 0)


if __name__ == '__main__':
    main()
