#!/usr/bin/env python3
"""
Config Detector - Detect existing configuration patterns in a codebase.

Usage:
    python detect_config.py <path> [--format json|text]

This script analyzes a codebase to find:
1. Existing config files (.env, config.py, settings.json, etc.)
2. Config loading patterns in code
3. Environment variable usage
4. Existing constants/config modules

Run this BEFORE extracting hardcodes to understand the existing config system.
"""

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Generator

@dataclass
class ConfigFile:
    path: str
    type: str  # env, python, javascript, json, yaml, toml, properties, xml
    framework: str | None  # django, flask, express, spring, dotnet, etc.
    variables: list[str]  # List of config keys found
    description: str

@dataclass 
class ConfigPattern:
    file: str
    line: int
    pattern_type: str  # env_access, config_import, settings_access
    code: str
    config_source: str | None  # What config file/module it references

@dataclass
class ConfigAnalysis:
    config_files: list[ConfigFile]
    config_patterns: list[ConfigPattern]
    detected_framework: str | None
    detected_language: str
    recommendations: list[str]


# Known config file patterns
CONFIG_FILE_PATTERNS = {
    # Environment files
    '.env': {'type': 'env', 'framework': None},
    '.env.local': {'type': 'env', 'framework': None},
    '.env.development': {'type': 'env', 'framework': None},
    '.env.production': {'type': 'env', 'framework': None},
    '.env.example': {'type': 'env', 'framework': None},
    '.env.sample': {'type': 'env', 'framework': None},
    'config.py': {'type': 'python', 'framework': None},
    'settings.py': {'type': 'python', 'framework': None},  # Could be Django, but need more evidence
    'config/settings.py': {'type': 'python', 'framework': None},
    'conf.py': {'type': 'python', 'framework': 'sphinx'},
    'constants.py': {'type': 'python', 'framework': None},
    'config/__init__.py': {'type': 'python', 'framework': None},
    'app/config.py': {'type': 'python', 'framework': 'flask'},
    'src/config.py': {'type': 'python', 'framework': None},
    
    # JavaScript/TypeScript
    'config.js': {'type': 'javascript', 'framework': None},
    'config.ts': {'type': 'typescript', 'framework': None},
    'config/index.js': {'type': 'javascript', 'framework': None},
    'config/index.ts': {'type': 'typescript', 'framework': None},
    'src/config.js': {'type': 'javascript', 'framework': None},
    'src/config.ts': {'type': 'typescript', 'framework': None},
    'src/config/index.ts': {'type': 'typescript', 'framework': None},
    'constants.js': {'type': 'javascript', 'framework': None},
    'constants.ts': {'type': 'typescript', 'framework': None},
    '.env.local': {'type': 'env', 'framework': 'nextjs'},
    'next.config.js': {'type': 'javascript', 'framework': 'nextjs'},
    'next.config.ts': {'type': 'typescript', 'framework': 'nextjs'},
    'nuxt.config.js': {'type': 'javascript', 'framework': 'nuxt'},
    'nuxt.config.ts': {'type': 'typescript', 'framework': 'nuxt'},
    'vite.config.js': {'type': 'javascript', 'framework': 'vite'},
    'vite.config.ts': {'type': 'typescript', 'framework': 'vite'},
    
    # Go
    'config.yaml': {'type': 'yaml', 'framework': None},
    'config.yml': {'type': 'yaml', 'framework': None},
    'config.go': {'type': 'go', 'framework': None},
    'config/config.go': {'type': 'go', 'framework': None},
    'internal/config/config.go': {'type': 'go', 'framework': None},
    'cmd/config.go': {'type': 'go', 'framework': None},
    
    # Rust
    'config.toml': {'type': 'toml', 'framework': None},
    'Config.toml': {'type': 'toml', 'framework': None},
    'src/config.rs': {'type': 'rust', 'framework': None},
    'src/settings.rs': {'type': 'rust', 'framework': None},
    
    # Java/Kotlin
    'application.properties': {'type': 'properties', 'framework': 'spring'},
    'application.yml': {'type': 'yaml', 'framework': 'spring'},
    'application.yaml': {'type': 'yaml', 'framework': 'spring'},
    'application-dev.properties': {'type': 'properties', 'framework': 'spring'},
    'application-prod.properties': {'type': 'properties', 'framework': 'spring'},
    'src/main/resources/application.properties': {'type': 'properties', 'framework': 'spring'},
    'src/main/resources/application.yml': {'type': 'yaml', 'framework': 'spring'},
    
    # .NET
    'appsettings.json': {'type': 'json', 'framework': 'dotnet'},
    'appsettings.Development.json': {'type': 'json', 'framework': 'dotnet'},
    'appsettings.Production.json': {'type': 'json', 'framework': 'dotnet'},
    'web.config': {'type': 'xml', 'framework': 'dotnet'},
    'app.config': {'type': 'xml', 'framework': 'dotnet'},
    
    # Ruby
    'config/application.rb': {'type': 'ruby', 'framework': 'rails'},
    'config/environments/development.rb': {'type': 'ruby', 'framework': 'rails'},
    'config/environments/production.rb': {'type': 'ruby', 'framework': 'rails'},
    'config/secrets.yml': {'type': 'yaml', 'framework': 'rails'},
    'config/credentials.yml.enc': {'type': 'yaml', 'framework': 'rails'},
    
    # PHP
    'config/app.php': {'type': 'php', 'framework': 'laravel'},
    'config/database.php': {'type': 'php', 'framework': 'laravel'},
    'config.php': {'type': 'php', 'framework': None},
    
    # General
    'config.json': {'type': 'json', 'framework': None},
    'settings.json': {'type': 'json', 'framework': None},
    'config.xml': {'type': 'xml', 'framework': None},
}

# Patterns to detect config usage in code
CODE_CONFIG_PATTERNS = {
    'python': {
        'env_access': [
            (r'os\.environ\[[\'"]([\w_]+)[\'"]\]', 'os.environ'),
            (r'os\.getenv\([\'"]([\w_]+)[\'"]', 'os.getenv'),
            (r'os\.environ\.get\([\'"]([\w_]+)[\'"]', 'os.environ.get'),
        ],
        'config_import': [
            (r'from\s+(config|settings|conf)\s+import', 'config module'),
            (r'import\s+(config|settings|conf)', 'config module'),
            (r'from\s+django\.conf\s+import\s+settings', 'django.conf.settings'),
            (r'from\s+flask\s+import.*current_app', 'flask.current_app.config'),
            (r'current_app\.config\[', 'flask.current_app.config'),
        ],
        'settings_access': [
            (r'settings\.([\w_]+)', 'settings'),
            (r'config\.([\w_]+)', 'config'),
            (r'Config\.([\w_]+)', 'Config'),
            (r'CONFIG\[[\'"]([\w_]+)[\'"]\]', 'CONFIG'),
        ],
    },
    'javascript': {
        'env_access': [
            (r'process\.env\.([\w_]+)', 'process.env'),
            (r'process\.env\[[\'"]([\w_]+)[\'"]\]', 'process.env'),
            (r'import\.meta\.env\.([\w_]+)', 'import.meta.env'),
        ],
        'config_import': [
            (r'require\([\'"]\.?\.?/?config', 'config module'),
            (r'from\s+[\'"]\.?\.?/?config', 'config module'),
            (r'import.*from\s+[\'"]\.?\.?/?config', 'config module'),
            (r'import\s+config\s+from', 'config module'),
        ],
        'settings_access': [
            (r'config\.([\w_]+)', 'config'),
            (r'Config\.([\w_]+)', 'Config'),
            (r'settings\.([\w_]+)', 'settings'),
        ],
    },
    'go': {
        'env_access': [
            (r'os\.Getenv\([\'"]([\w_]+)[\'"]', 'os.Getenv'),
            (r'os\.LookupEnv\([\'"]([\w_]+)[\'"]', 'os.LookupEnv'),
        ],
        'config_import': [
            (r'viper\.', 'viper'),
            (r'envconfig\.Process', 'envconfig'),
        ],
        'settings_access': [
            (r'cfg\.([\w_]+)', 'cfg'),
            (r'config\.([\w_]+)', 'config'),
            (r'Config\.([\w_]+)', 'Config'),
        ],
    },
    'rust': {
        'env_access': [
            (r'std::env::var\([\'"]([\w_]+)[\'"]', 'std::env::var'),
            (r'env::var\([\'"]([\w_]+)[\'"]', 'env::var'),
            (r'dotenvy::var\([\'"]([\w_]+)[\'"]', 'dotenvy'),
        ],
        'config_import': [
            (r'use\s+config::', 'config crate'),
            (r'use\s+figment::', 'figment'),
        ],
        'settings_access': [
            (r'config\.([\w_]+)', 'config'),
            (r'settings\.([\w_]+)', 'settings'),
        ],
    },
    'java': {
        'env_access': [
            (r'System\.getenv\([\'"]([\w_]+)[\'"]', 'System.getenv'),
            (r'System\.getProperty\([\'"]([\w_.]+)[\'"]', 'System.getProperty'),
        ],
        'config_import': [
            (r'@Value\s*\(\s*[\'"]?\$\{([\w_.]+)', 'Spring @Value'),
            (r'@ConfigurationProperties', 'Spring @ConfigurationProperties'),
        ],
        'settings_access': [
            (r'environment\.getProperty\([\'"]([\w_.]+)[\'"]', 'Environment'),
        ],
    },
    'csharp': {
        'env_access': [
            (r'Environment\.GetEnvironmentVariable\([\'"]([\w_]+)[\'"]', 'Environment'),
        ],
        'config_import': [
            (r'IConfiguration', 'IConfiguration'),
            (r'Configuration\[[\'"]([\w_:]+)[\'"]\]', 'Configuration'),
        ],
        'settings_access': [
            (r'_config\[[\'"]([\w_:]+)[\'"]\]', '_config'),
            (r'configuration\[[\'"]([\w_:]+)[\'"]\]', 'configuration'),
        ],
    },
}

# File extensions to language mapping
LANG_EXTENSIONS = {
    '.py': 'python',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'javascript',  # Use same patterns
    '.tsx': 'javascript',
    '.go': 'go',
    '.rs': 'rust',
    '.java': 'java',
    '.kt': 'java',  # Kotlin uses similar patterns
    '.cs': 'csharp',
}

SKIP_DIRS = {
    'node_modules', '.git', '__pycache__', 'venv', '.venv', 'env',
    'dist', 'build', 'target', '.idea', '.vscode', 'vendor',
}


def parse_env_file(filepath: Path) -> list[str]:
    """Extract variable names from .env file."""
    variables = []
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                var_name = line.split('=')[0].strip()
                if var_name:
                    variables.append(var_name)
    except (IOError, OSError):
        pass
    return variables


def parse_json_config(filepath: Path) -> list[str]:
    """Extract top-level keys from JSON config."""
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
        data = json.loads(content)
        if isinstance(data, dict):
            return list(data.keys())
    except (IOError, OSError, json.JSONDecodeError):
        pass
    return []


def parse_properties_file(filepath: Path) -> list[str]:
    """Extract property names from .properties file."""
    variables = []
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                var_name = line.split('=')[0].strip()
                if var_name:
                    variables.append(var_name)
    except (IOError, OSError):
        pass
    return variables


def find_config_files(root: Path) -> Generator[ConfigFile, None, None]:
    """Find all config files in the directory."""
    for path in root.rglob('*'):
        if path.is_file():
            # Check if any part of path is in skip dirs
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            
            # Get relative path for matching
            try:
                rel_path = path.relative_to(root)
            except ValueError:
                rel_path = path
            
            rel_str = str(rel_path).replace('\\', '/')
            
            # Check against known patterns
            for pattern, info in CONFIG_FILE_PATTERNS.items():
                if rel_str == pattern or rel_str.endswith('/' + pattern) or path.name == pattern:
                    # Parse the file to get variables
                    variables = []
                    if info['type'] == 'env':
                        variables = parse_env_file(path)
                    elif info['type'] == 'json':
                        variables = parse_json_config(path)
                    elif info['type'] == 'properties':
                        variables = parse_properties_file(path)
                    
                    yield ConfigFile(
                        path=str(rel_path),
                        type=info['type'],
                        framework=info['framework'],
                        variables=variables,
                        description=f"{info['type'].upper()} config" + 
                                   (f" ({info['framework']})" if info['framework'] else "")
                    )
                    break


def find_config_patterns(root: Path) -> Generator[ConfigPattern, None, None]:
    """Find config usage patterns in source code."""
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        
        # Check if any part of path is in skip dirs
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        
        # Get language from extension
        lang = LANG_EXTENSIONS.get(path.suffix.lower())
        if not lang:
            continue
        
        patterns = CODE_CONFIG_PATTERNS.get(lang, {})
        if not patterns:
            continue
        
        try:
            content = path.read_text(encoding='utf-8', errors='ignore')
        except (IOError, OSError):
            continue
        
        try:
            rel_path = str(path.relative_to(root))
        except ValueError:
            rel_path = str(path)
        
        for line_num, line in enumerate(content.split('\n'), 1):
            for pattern_type, pattern_list in patterns.items():
                for regex, source in pattern_list:
                    if re.search(regex, line, re.IGNORECASE):
                        yield ConfigPattern(
                            file=rel_path,
                            line=line_num,
                            pattern_type=pattern_type,
                            code=line.strip()[:100],
                            config_source=source
                        )
                        break  # Only report once per line per pattern type


def detect_primary_language(root: Path) -> str:
    """Detect the primary language of the project."""
    counts = {}
    for path in root.rglob('*'):
        if path.is_file() and not any(part in SKIP_DIRS for part in path.parts):
            lang = LANG_EXTENSIONS.get(path.suffix.lower())
            if lang:
                counts[lang] = counts.get(lang, 0) + 1
    
    if not counts:
        return 'unknown'
    return max(counts, key=counts.get)


def detect_framework(config_files: list[ConfigFile], config_patterns: list[ConfigPattern], root: Path) -> str | None:
    """Detect the framework based on config files, code patterns, and other indicators."""
    # First check code patterns - most reliable
    for cp in config_patterns:
        if 'django.conf.settings' in cp.config_source:
            return 'django'
        if 'flask.current_app.config' in cp.config_source:
            return 'flask'
        if 'Spring @Value' in cp.config_source or 'Spring @ConfigurationProperties' in cp.config_source:
            return 'spring'
        if 'viper' in cp.config_source:
            return 'go-viper'
    
    # Check config files for framework hints
    for cf in config_files:
        if cf.framework:
            return cf.framework
    
    # Check for framework-specific files
    indicators = {
        'django': ['manage.py', 'wsgi.py', 'asgi.py'],
        'flask': [],  # Flask is harder to detect by files alone
        'fastapi': [],
        'express': ['app.js', 'server.js'],
        'nextjs': ['next.config.js', 'next.config.ts', 'next.config.mjs'],
        'nuxt': ['nuxt.config.js', 'nuxt.config.ts'],
        'rails': ['Gemfile', 'config/routes.rb', 'Rakefile'],
        'laravel': ['artisan', 'config/app.php'],
        'spring': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
        'dotnet': [],
    }
    
    for framework, files in indicators.items():
        for f in files:
            if (root / f).exists():
                return framework
    
    # Check for .csproj or .sln files (dotnet)
    if list(root.glob('*.csproj')) or list(root.glob('*.sln')):
        return 'dotnet'
    
    return None


def generate_recommendations(
    config_files: list[ConfigFile],
    config_patterns: list[ConfigPattern],
    language: str,
    framework: str | None
) -> list[str]:
    """Generate recommendations based on analysis."""
    recommendations = []
    
    # Check for .env file
    has_env = any(cf.type == 'env' and not cf.path.endswith('.example') for cf in config_files)
    has_env_example = any('.example' in cf.path or '.sample' in cf.path for cf in config_files)
    
    if not has_env:
        recommendations.append(
            "No .env file found. Create one for secrets and environment-specific values."
        )
    
    if has_env and not has_env_example:
        recommendations.append(
            "Found .env but no .env.example. Create .env.example as a template for other developers."
        )
    
    # Check for config module
    has_config_module = any(
        cf.type in ('python', 'javascript', 'typescript', 'go', 'rust') 
        for cf in config_files
    )
    
    if not has_config_module:
        if language == 'python':
            recommendations.append(
                "No config.py or settings.py found. Consider creating one to centralize configuration."
            )
        elif language == 'javascript':
            recommendations.append(
                "No config.js/ts found. Consider creating src/config/index.ts to centralize configuration."
            )
    
    # Check for inconsistent patterns
    env_sources = set()
    for cp in config_patterns:
        if cp.pattern_type == 'env_access':
            env_sources.add(cp.config_source)
    
    if len(env_sources) > 2:
        recommendations.append(
            f"Multiple env access patterns found ({', '.join(env_sources)}). "
            "Consider standardizing on one approach."
        )
    
    # Framework-specific recommendations
    if framework == 'django':
        recommendations.append(
            "Django project detected. Use django-environ or python-dotenv with settings.py."
        )
    elif framework == 'spring':
        recommendations.append(
            "Spring Boot project detected. Use application.properties/yml with @ConfigurationProperties."
        )
    elif framework == 'dotnet':
        recommendations.append(
            ".NET project detected. Use appsettings.json with IConfiguration and User Secrets for development."
        )
    
    return recommendations


def analyze_config(root: Path) -> ConfigAnalysis:
    """Perform complete config analysis on a directory."""
    config_files = list(find_config_files(root))
    config_patterns = list(find_config_patterns(root))
    language = detect_primary_language(root)
    framework = detect_framework(config_files, config_patterns, root)
    recommendations = generate_recommendations(config_files, config_patterns, language, framework)
    
    return ConfigAnalysis(
        config_files=config_files,
        config_patterns=config_patterns,
        detected_framework=framework,
        detected_language=language,
        recommendations=recommendations
    )


def format_text_report(analysis: ConfigAnalysis) -> str:
    """Format analysis as readable text."""
    lines = [
        "🔧 Config Analysis Report",
        "=" * 60,
        f"Primary Language: {analysis.detected_language}",
        f"Framework: {analysis.detected_framework or 'None detected'}",
        "",
    ]
    
    # Config files
    lines.append(f"📁 Config Files Found ({len(analysis.config_files)})")
    lines.append("-" * 40)
    
    if analysis.config_files:
        for cf in analysis.config_files:
            lines.append(f"  • {cf.path}")
            lines.append(f"    Type: {cf.type}" + (f" ({cf.framework})" if cf.framework else ""))
            if cf.variables:
                var_preview = ', '.join(cf.variables[:5])
                if len(cf.variables) > 5:
                    var_preview += f", ... (+{len(cf.variables) - 5} more)"
                lines.append(f"    Variables: {var_preview}")
    else:
        lines.append("  ⚠️  No config files found!")
    
    lines.append("")
    
    # Config patterns in code
    pattern_counts = {}
    for cp in analysis.config_patterns:
        key = (cp.pattern_type, cp.config_source)
        pattern_counts[key] = pattern_counts.get(key, 0) + 1
    
    lines.append(f"📊 Config Usage Patterns ({len(analysis.config_patterns)} occurrences)")
    lines.append("-" * 40)
    
    if pattern_counts:
        for (ptype, source), count in sorted(pattern_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  • {source}: {count} uses ({ptype})")
    else:
        lines.append("  No config patterns detected in code")
    
    lines.append("")
    
    # Recommendations
    lines.append("💡 Recommendations")
    lines.append("-" * 40)
    
    if analysis.recommendations:
        for rec in analysis.recommendations:
            lines.append(f"  • {rec}")
    else:
        lines.append("  ✅ Config setup looks good!")
    
    lines.append("")
    
    # Summary for hardcode extraction
    lines.append("📋 For Hardcode Extraction")
    lines.append("-" * 40)
    
    if analysis.config_files:
        env_files = [cf for cf in analysis.config_files if cf.type == 'env']
        config_modules = [cf for cf in analysis.config_files if cf.type in ('python', 'javascript', 'typescript', 'go', 'rust')]
        
        if env_files:
            lines.append(f"  → Add secrets to: {env_files[0].path}")
        else:
            lines.append("  → Create .env for secrets")
        
        if config_modules:
            lines.append(f"  → Add config values to: {config_modules[0].path}")
        else:
            lines.append(f"  → Create config module for {analysis.detected_language}")
    else:
        lines.append("  → Create .env for secrets")
        lines.append(f"  → Create config module for {analysis.detected_language}")
    
    return '\n'.join(lines)


def format_json_report(analysis: ConfigAnalysis) -> str:
    """Format analysis as JSON."""
    return json.dumps({
        'detected_language': analysis.detected_language,
        'detected_framework': analysis.detected_framework,
        'config_files': [asdict(cf) for cf in analysis.config_files],
        'config_patterns': [asdict(cp) for cp in analysis.config_patterns],
        'recommendations': analysis.recommendations,
    }, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description='Detect existing configuration patterns in a codebase',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s ./my-project              # Analyze project
  %(prog)s . --format json           # JSON output
        '''
    )
    parser.add_argument('path', help='Project directory to analyze')
    parser.add_argument('--format', '-f', choices=['text', 'json'], default='text',
                        help='Output format (default: text)')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    
    args = parser.parse_args()
    
    root = Path(args.path)
    if not root.is_dir():
        print(f"Error: {root} is not a directory")
        return 1
    
    analysis = analyze_config(root)
    
    if args.format == 'json':
        output = format_json_report(analysis)
    else:
        output = format_text_report(analysis)
    
    if args.output:
        Path(args.output).write_text(output)
        print(f"Report saved to {args.output}")
    else:
        print(output)
    
    return 0


if __name__ == '__main__':
    exit(main())
