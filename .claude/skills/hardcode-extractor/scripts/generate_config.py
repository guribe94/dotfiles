#!/usr/bin/env python3
"""
Config Generator - Generate starter config files from hardcode scan results.

Usage:
    python generate_config.py <scan_report.json> --language python [--output ./config]
    python generate_config.py <scan_report.json> --language typescript
    
This script takes a JSON report from scan_hardcodes.py and generates
appropriate config files with placeholder values.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any

# Templates for different languages
TEMPLATES = {
    'python': {
        'env': '''# Environment Variables
# Copy this to .env and fill in actual values
# DO NOT commit .env to version control!

{env_vars}
''',
        'config': '''"""Application configuration."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# Required Settings (will raise if missing)
# =============================================================================
{required_settings}

# =============================================================================
# Optional Settings (with defaults)
# =============================================================================
{optional_settings}

# =============================================================================
# Derived Settings
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
''',
        'constants': '''"""Application constants - values that don't change per environment."""

{constants}
''',
    },
    'typescript': {
        'env': '''# Environment Variables
# Copy this to .env and fill in actual values
# DO NOT commit .env to version control!

{env_vars}
''',
        'config': '''/**
 * Application configuration
 * Loads from environment variables with type safety
 */
import dotenv from 'dotenv';
dotenv.config();

function required(key: string): string {{
  const value = process.env[key];
  if (!value) {{
    throw new Error(`Missing required environment variable: ${{key}}`);
  }}
  return value;
}}

function optional(key: string, defaultValue: string): string {{
  return process.env[key] ?? defaultValue;
}}

function optionalInt(key: string, defaultValue: number): number {{
  const value = process.env[key];
  return value ? parseInt(value, 10) : defaultValue;
}}

function optionalBool(key: string, defaultValue: boolean): boolean {{
  const value = process.env[key];
  return value ? value.toLowerCase() === 'true' : defaultValue;
}}

// =============================================================================
// Required Settings
// =============================================================================
{required_settings}

// =============================================================================
// Optional Settings (with defaults)
// =============================================================================
{optional_settings}

export const config = {{
{exports}
}};
''',
        'constants': '''/**
 * Application constants - values that don't change per environment
 */

{constants}

export const constants = {{
{const_exports}
}} as const;
''',
    },
    'go': {
        'env': '''# Environment Variables
# Copy this to .env and fill in actual values
# DO NOT commit .env to version control!

{env_vars}
''',
        'config': '''package config

import (
	"os"
	"strconv"
)

// Config holds all configuration values
type Config struct {{
{struct_fields}
}}

// Load reads configuration from environment variables
func Load() (*Config, error) {{
	cfg := &Config{{}}
	
{field_loaders}
	
	return cfg, nil
}}

func getEnv(key, fallback string) string {{
	if value := os.Getenv(key); value != "" {{
		return value
	}}
	return fallback
}}

func getEnvInt(key string, fallback int) int {{
	if value := os.Getenv(key); value != "" {{
		if i, err := strconv.Atoi(value); err == nil {{
			return i
		}}
	}}
	return fallback
}}

func requireEnv(key string) string {{
	value := os.Getenv(key)
	if value == "" {{
		panic("Missing required environment variable: " + key)
	}}
	return value
}}
''',
        'constants': '''package constants

{constants}
''',
    },
}


def to_env_var_name(value: str, category: str) -> str:
    """Convert a value to an appropriate env var name."""
    # Extract meaningful parts from the value
    if category == 'secret':
        if 'api' in value.lower() and 'key' in value.lower():
            return 'API_KEY'
        if 'password' in value.lower():
            return 'DB_PASSWORD'
        if 'token' in value.lower():
            return 'AUTH_TOKEN'
        if value.startswith('AKIA'):
            return 'AWS_ACCESS_KEY_ID'
        if 'ghp_' in value or 'gho_' in value:
            return 'GITHUB_TOKEN'
        if 'sk_live' in value or 'sk_test' in value:
            return 'STRIPE_SECRET_KEY'
        if 'xoxb-' in value or 'xoxp-' in value:
            return 'SLACK_TOKEN'
        if 'SG.' in value:
            return 'SENDGRID_API_KEY'
        if 'postgres://' in value or 'mysql://' in value or 'mongodb://' in value:
            return 'DATABASE_URL'
        return 'SECRET_KEY'
    
    if category == 'url':
        if 'api' in value.lower():
            return 'API_URL'
        if 'webhook' in value.lower():
            return 'WEBHOOK_URL'
        if 'ws://' in value or 'wss://' in value:
            return 'WS_URL'
        return 'BASE_URL'
    
    if category == 'path':
        if 's3://' in value:
            return 'S3_BUCKET'
        if 'gs://' in value:
            return 'GCS_BUCKET'
        if 'log' in value.lower():
            return 'LOG_PATH'
        if 'upload' in value.lower():
            return 'UPLOAD_PATH'
        return 'DATA_PATH'
    
    if category == 'number':
        return 'CONFIG_VALUE'
    
    return 'CONFIG_VALUE'


def to_const_name(value: str, category: str, suggestion: str) -> str:
    """Generate a constant name from value and suggestion."""
    # Try to extract from suggestion
    suggestion_lower = suggestion.lower()
    
    if 'timeout' in suggestion_lower:
        return 'TIMEOUT_MS'
    if 'retries' in suggestion_lower:
        return 'MAX_RETRIES'
    if 'batch' in suggestion_lower:
        return 'BATCH_SIZE'
    if 'page' in suggestion_lower:
        return 'PAGE_SIZE'
    if 'cache' in suggestion_lower or 'ttl' in suggestion_lower:
        return 'CACHE_TTL'
    if 'pool' in suggestion_lower:
        return 'POOL_SIZE'
    if 'port' in suggestion_lower:
        return 'PORT'
    
    # Default
    return f'CONFIG_{category.upper()}'


def generate_python_config(findings: list[dict]) -> dict[str, str]:
    """Generate Python config files from findings."""
    env_vars = []
    required_settings = []
    optional_settings = []
    constants = []
    
    seen_vars = set()
    
    for f in findings:
        var_name = to_env_var_name(f['value'], f['category'])
        
        # Make unique
        base_name = var_name
        counter = 1
        while var_name in seen_vars:
            var_name = f"{base_name}_{counter}"
            counter += 1
        seen_vars.add(var_name)
        
        if f['severity'] == 'high':
            # Secrets go to .env and required settings
            env_vars.append(f'{var_name}=  # {f["suggestion"]}')
            required_settings.append(f'{var_name} = os.environ["{var_name}"]')
        elif f['severity'] == 'medium':
            # Medium severity: env with defaults
            default = f['value'][:30] if len(f['value']) > 30 else f['value']
            if f['category'] == 'number':
                optional_settings.append(f'{var_name} = int(os.getenv("{var_name}", "{default}"))')
            else:
                optional_settings.append(f'{var_name} = os.getenv("{var_name}", "{default}")')
        else:
            # Low severity: constants
            const_name = to_const_name(f['value'], f['category'], f['suggestion'])
            if const_name in seen_vars:
                const_name = f"{const_name}_{counter}"
            seen_vars.add(const_name)
            
            if f['category'] == 'number':
                constants.append(f'{const_name} = {f["value"]}')
            else:
                constants.append(f'{const_name} = "{f["value"]}"')
    
    return {
        '.env.example': TEMPLATES['python']['env'].format(
            env_vars='\n'.join(env_vars) if env_vars else '# No secrets detected'
        ),
        'config/settings.py': TEMPLATES['python']['config'].format(
            required_settings='\n'.join(required_settings) if required_settings else '# No required settings',
            optional_settings='\n'.join(optional_settings) if optional_settings else '# No optional settings',
        ),
        'config/constants.py': TEMPLATES['python']['constants'].format(
            constants='\n'.join(constants) if constants else '# No constants detected'
        ),
    }


def generate_typescript_config(findings: list[dict]) -> dict[str, str]:
    """Generate TypeScript config files from findings."""
    env_vars = []
    required_settings = []
    optional_settings = []
    exports = []
    constants = []
    const_exports = []
    
    seen_vars = set()
    
    for f in findings:
        var_name = to_env_var_name(f['value'], f['category'])
        
        # Make unique
        base_name = var_name
        counter = 1
        while var_name in seen_vars:
            var_name = f"{base_name}_{counter}"
            counter += 1
        seen_vars.add(var_name)
        
        camel_name = ''.join(
            word.capitalize() if i > 0 else word.lower()
            for i, word in enumerate(var_name.split('_'))
        )
        
        if f['severity'] == 'high':
            env_vars.append(f'{var_name}=  # {f["suggestion"]}')
            required_settings.append(f'const {camel_name} = required("{var_name}");')
            exports.append(f'  {camel_name},')
        elif f['severity'] == 'medium':
            default = f['value'][:30] if len(f['value']) > 30 else f['value']
            if f['category'] == 'number':
                optional_settings.append(f'const {camel_name} = optionalInt("{var_name}", {default});')
            else:
                optional_settings.append(f'const {camel_name} = optional("{var_name}", "{default}");')
            exports.append(f'  {camel_name},')
        else:
            const_name = to_const_name(f['value'], f['category'], f['suggestion'])
            if const_name in seen_vars:
                const_name = f"{const_name}_{counter}"
            seen_vars.add(const_name)
            
            if f['category'] == 'number':
                constants.append(f'const {const_name} = {f["value"]};')
            else:
                constants.append(f'const {const_name} = "{f["value"]}";')
            const_exports.append(f'  {const_name},')
    
    return {
        '.env.example': TEMPLATES['typescript']['env'].format(
            env_vars='\n'.join(env_vars) if env_vars else '# No secrets detected'
        ),
        'src/config/index.ts': TEMPLATES['typescript']['config'].format(
            required_settings='\n'.join(required_settings) if required_settings else '// No required settings',
            optional_settings='\n'.join(optional_settings) if optional_settings else '// No optional settings',
            exports='\n'.join(exports) if exports else '  // No exports',
        ),
        'src/config/constants.ts': TEMPLATES['typescript']['constants'].format(
            constants='\n'.join(constants) if constants else '// No constants detected',
            const_exports='\n'.join(const_exports) if const_exports else '  // No exports',
        ),
    }


def generate_go_config(findings: list[dict]) -> dict[str, str]:
    """Generate Go config files from findings."""
    env_vars = []
    struct_fields = []
    field_loaders = []
    constants = []
    
    seen_vars = set()
    
    for f in findings:
        var_name = to_env_var_name(f['value'], f['category'])
        
        # Make unique
        base_name = var_name
        counter = 1
        while var_name in seen_vars:
            var_name = f"{base_name}_{counter}"
            counter += 1
        seen_vars.add(var_name)
        
        # Go field name (PascalCase)
        go_name = ''.join(word.capitalize() for word in var_name.split('_'))
        
        if f['severity'] == 'high':
            env_vars.append(f'{var_name}=  # {f["suggestion"]}')
            struct_fields.append(f'\t{go_name} string')
            field_loaders.append(f'\tcfg.{go_name} = requireEnv("{var_name}")')
        elif f['severity'] == 'medium':
            default = f['value'][:30] if len(f['value']) > 30 else f['value']
            if f['category'] == 'number':
                struct_fields.append(f'\t{go_name} int')
                field_loaders.append(f'\tcfg.{go_name} = getEnvInt("{var_name}", {default})')
            else:
                struct_fields.append(f'\t{go_name} string')
                field_loaders.append(f'\tcfg.{go_name} = getEnv("{var_name}", "{default}")')
        else:
            const_name = to_const_name(f['value'], f['category'], f['suggestion'])
            if const_name in seen_vars:
                const_name = f"{const_name}_{counter}"
            seen_vars.add(const_name)
            
            if f['category'] == 'number':
                constants.append(f'const {const_name} = {f["value"]}')
            else:
                constants.append(f'const {const_name} = "{f["value"]}"')
    
    return {
        '.env.example': TEMPLATES['go']['env'].format(
            env_vars='\n'.join(env_vars) if env_vars else '# No secrets detected'
        ),
        'internal/config/config.go': TEMPLATES['go']['config'].format(
            struct_fields='\n'.join(struct_fields) if struct_fields else '\t// No fields',
            field_loaders='\n'.join(field_loaders) if field_loaders else '\t// No loaders',
        ),
        'internal/constants/constants.go': TEMPLATES['go']['constants'].format(
            constants='\n'.join(constants) if constants else '// No constants detected'
        ),
    }


GENERATORS = {
    'python': generate_python_config,
    'typescript': generate_typescript_config,
    'javascript': generate_typescript_config,  # Same as TS
    'go': generate_go_config,
}


def main():
    parser = argparse.ArgumentParser(
        description='Generate config files from hardcode scan results',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s report.json --language python
  %(prog)s report.json --language typescript --output ./src/config
  %(prog)s report.json --language go --output ./internal
        '''
    )
    parser.add_argument('report', help='JSON report from scan_hardcodes.py')
    parser.add_argument('--language', '-l', required=True, 
                        choices=list(GENERATORS.keys()),
                        help='Target language for config files')
    parser.add_argument('--output', '-o', default='.',
                        help='Output directory (default: current directory)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print files that would be created without writing')
    
    args = parser.parse_args()
    
    # Load report
    report_path = Path(args.report)
    if not report_path.exists():
        print(f"Error: Report file not found: {report_path}")
        return 1
    
    with open(report_path) as f:
        report = json.load(f)
    
    findings = report.get('findings', [])
    if not findings:
        print("No findings in report. Nothing to generate.")
        return 0
    
    # Generate configs
    generator = GENERATORS[args.language]
    files = generator(findings)
    
    # Output
    output_dir = Path(args.output)
    
    print(f"📁 Generating {args.language} config files...")
    print(f"   Source: {report_path}")
    print(f"   Findings: {len(findings)}")
    print()
    
    for filepath, content in files.items():
        full_path = output_dir / filepath
        
        if args.dry_run:
            print(f"Would create: {full_path}")
            print("-" * 40)
            print(content[:500] + "..." if len(content) > 500 else content)
            print()
        else:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            print(f"✅ Created: {full_path}")
    
    if not args.dry_run:
        print()
        print("📋 Next steps:")
        print("   1. Review generated files and adjust variable names")
        print("   2. Copy .env.example to .env and fill in actual values")
        print("   3. Add .env to .gitignore")
        print("   4. Update imports in your code to use the new config")
    
    return 0


if __name__ == '__main__':
    exit(main())
