---
name: hardcode-extractor
description: "Ruthlessly extract hardcoded values from code and centralize them in idiomatic config files. Use when: (1) Refactoring AI-generated code with embedded values, (2) Extracting magic numbers, strings, URLs, credentials, (3) Centralizing configuration across a project, (4) Preparing code for multi-environment deployment, (5) Security audit for leaked secrets. Supports Python, JavaScript/TypeScript, Go, Rust, Java, C#, Ruby, PHP. Can target whole projects or specific files."
---

# Hardcode Extractor

Extract hardcoded values from code and centralize them in sensible, idiomatic configuration files with minimal code changes.

## Core Principles

1. **Detect before create** - Always find existing config systems first
2. **Extend, don't replace** - Add to existing config files, never create parallel systems
3. **Follow existing conventions** - Match naming, structure, and patterns already in use
4. **Minimal changes only** - Touch only what's necessary to extract the hardcode
5. **Preserve behavior** - Defaults must match original values exactly
6. **One change at a time** - Extract, test, commit, repeat

## Workflow Overview

1. **Detect** → Find existing config files and patterns (ALWAYS DO THIS FIRST)
2. **Scan** → Find hardcoded values in target files
3. **Plan** → Map hardcodes to appropriate existing config locations
4. **Refactor** → Replace hardcodes with config references
5. **Validate** → Verify behavior is unchanged

## Step 1: Detect Existing Config (REQUIRED)

**Always run this first** to understand the existing config system:

```bash
python scripts/detect_config.py <project_path>
```

This identifies:
- Existing config files (.env, config.py, appsettings.json, etc.)
- Config loading patterns already in use (os.getenv, process.env, etc.)
- Framework conventions (Django settings, Spring properties, etc.)
- Where to add new config values

**Example output:**
```
🔧 Config Analysis Report
============================================================
Primary Language: python
Framework: django

📁 Config Files Found (3)
  • .env
    Type: env
    Variables: DEBUG, DATABASE_URL, SECRET_KEY
  • config/settings.py
    Type: python (django)
  • config/constants.py
    Type: python

📊 Config Usage Patterns (47 occurrences)
  • os.getenv: 12 uses (env_access)
  • django.conf.settings: 35 uses (settings_access)

📋 For Hardcode Extraction
  → Add secrets to: .env
  → Add config values to: config/settings.py
```

**Key decisions from detection:**

| If you find... | Then... |
|----------------|---------|
| Existing .env | Add secrets there, follow existing naming |
| config.py / settings.py | Add non-secret config there |
| constants.py | Add static constants there |
| Framework config (Django/Spring/etc.) | Follow that framework's conventions |
| Nothing | Create minimal config following language idioms |

## Step 2: Scan for Hardcodes

```bash
python scripts/scan_hardcodes.py <target_path> [options]
```

**Options:**
| Flag | Description |
|------|-------------|
| `--format json\|text` | Output format (default: text) |
| `--severity all\|high\|medium` | Minimum severity (default: all) |
| `--output FILE` | Save report to file |
| `--exclude "*.test.py"` | Comma-separated exclusion patterns |
| `--include-tests` | Include test directories |

**Severity levels:**
- 🔴 **HIGH** - Secrets, credentials → Must extract immediately
- 🟡 **MEDIUM** - URLs, paths, thresholds → Should extract for flexibility  
- 🟢 **LOW** - Magic numbers, env names → Consider extracting

## Step 3: Plan Config Mapping

Map each hardcode to the appropriate **existing** config location:

| Hardcode Type | Where to Put It | How to Access |
|---------------|-----------------|---------------|
| Secrets (API keys, passwords) | `.env` (existing or new) | Use existing env access pattern |
| Environment URLs | Existing config module | Use existing config access pattern |
| Thresholds, timeouts | Existing config module | Use existing config access pattern |
| Static constants | Existing constants file | Direct import |

**Critical rules:**
- If `.env` exists → add to it, follow its naming convention
- If `config.py` exists → add to it, follow its structure
- If framework config exists → use framework patterns
- Match existing SCREAMING_CASE vs camelCase vs snake_case
- Match existing grouping/organization

## Step 4: Refactor Code

Make **minimal, surgical changes**. Only modify what's necessary.

### What TO Do

```python
# ✅ Add to EXISTING .env
# .env (already has DATABASE_URL, SECRET_KEY)
DATABASE_URL=...
SECRET_KEY=...
API_KEY=your_new_key_here  # ← Add new value, match style

# ✅ Add to EXISTING config.py using EXISTING pattern
# config/settings.py (already uses os.getenv pattern)
DATABASE_URL = os.getenv("DATABASE_URL")  # existing
API_KEY = os.getenv("API_KEY")  # ← Add new, same pattern
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))  # ← With default

# ✅ Replace hardcode with config reference
# Before
response = requests.get("https://api.example.com", timeout=30)

# After (using existing config import that's already in file)
response = requests.get(settings.API_URL, timeout=settings.API_TIMEOUT)
```

### What NOT To Do

```python
# ❌ DON'T create new config file when one exists
# Bad: Creating config/new_settings.py when config/settings.py exists

# ❌ DON'T use different access pattern than existing code
# Bad: Using os.environ["KEY"] when codebase uses os.getenv("KEY")

# ❌ DON'T change config structure
# Bad: Reorganizing existing config into sections

# ❌ DON'T rename existing config variables
# Bad: Changing DATABASE_URL to DB_CONNECTION_STRING

# ❌ DON'T add unnecessary abstractions
# Bad: Creating a Config class when simple module variables are used
```

### Refactoring Checklist

Before each change, verify:
- [ ] I've identified the existing config file for this value
- [ ] I'm using the same access pattern as existing code
- [ ] I'm following the existing naming convention
- [ ] The default value matches the original hardcoded value
- [ ] I'm only changing what's necessary

## Step 5: Validate

After each refactoring:

1. **Run existing tests** - All tests must pass
2. **Manual smoke test** - App starts and basic functionality works
3. **Check config loading** - No errors on startup
4. **Verify defaults** - Behavior matches without .env changes
5. **Review diff** - Only expected files changed, minimal modifications

## Special Cases

### No Existing Config System

If detect_config.py finds nothing:

1. Start with `.env` + `.env.example` for secrets
2. Create minimal config module following language idioms
3. See `references/config-patterns.md` for starter patterns

### Multiple Config Files

If project has several config files:
- Determine which is "primary" (most imports, framework default)
- Add to the most appropriate existing file
- Don't consolidate - that's restructuring, not extracting

### Legacy/Inconsistent Patterns

If existing code has mixed patterns:
- Use the **most common** pattern for new additions
- Don't "fix" existing inconsistencies (that's a separate task)
- Document the inconsistency for future cleanup

### Framework-Specific Guidance

| Framework | Config Location | Pattern |
|-----------|-----------------|---------|
| Django | `settings.py` | `from django.conf import settings` |
| Flask | `app.config` | `current_app.config['KEY']` |
| Spring | `application.properties` | `@Value("${key}")` or `@ConfigurationProperties` |
| .NET | `appsettings.json` | `IConfiguration` / `IOptions<T>` |
| Next.js | `.env.local` | `process.env.NEXT_PUBLIC_*` |
| Rails | `config/` + credentials | `Rails.application.credentials` |

## Files in This Skill

- `scripts/detect_config.py` - **Run first** - Find existing config patterns
- `scripts/scan_hardcodes.py` - Find hardcoded values
- `scripts/generate_config.py` - Generate starter configs (only if none exist)
- `references/config-patterns.md` - Language-specific patterns and CI integration
