---
name: code-quality-refactor
description: Production-grade code quality improvement through LLM-verified analysis. Use for improving code quality, refactoring, fixing AI-generated code issues, reducing technical debt, improving maintainability, breaking up large components, adding tests, or making code production-ready. Features deep AST analysis for TypeScript/JavaScript and Python, dead code detection, circular dependency detection, duplicate detection, and auto-fix generation. Works on entire codebase or specific paths.
---

# Code Quality Refactor

Production-grade code quality improvement through systematic, verified analysis.

## Core Principle

**YOU are the expert. Scripts provide data. YOU analyze, verify, and judge.**

Scripts extract metrics and flag potential issues. You must:
1. Read the actual code before reporting any issue
2. Verify issues are real (not false positives)
3. Understand context before making changes
4. Never trust pattern matches blindly

## Available Commands

| Command | Purpose |
|---------|---------|
| `/analyze-quality` | Full analysis with verification |
| `/refactor-plan` | Generate prioritized refactoring roadmap |
| `/fix-issue` | Safely fix a specific issue |
| `/add-tests` | Generate tests before refactoring |
| `/check-security` | Security-focused analysis |

## Language Support

| Language | Analysis Method | Features |
|----------|-----------------|----------|
| **TypeScript/JavaScript** | TypeScript Compiler API | Full AST, type errors, dead code, duplicates |
| **Python** | Python AST module | Full AST, dead code, circular imports, type hints |
| **Go** | go vet + staticcheck | Linter integration, vet analysis |
| **Other** | Regex patterns | Basic pattern detection |

## Workflow

### Phase 1: Analyze

Run the main analyzer:

```bash
python3 scripts/analyze.py <path> --summary
```

This runs language-specific analyzers and aggregates results:
- TypeScript/JavaScript: `analyze_typescript.js`
- Python: `analyze_python.py`
- Go: `go vet` + `staticcheck`

Output includes:
- File/function metrics (length, complexity, nesting)
- Dead code (unused imports, exports, unreachable code)
- Circular dependencies
- Duplicate code blocks
- Security patterns (for verification)
- Type errors (TypeScript)

### Phase 2: Verify

**CRITICAL: You must verify every issue before reporting.**

For each flagged item:
1. Read the actual code at the specified location
2. Check the `references/verification-guide.md` for verification steps
3. Determine if it's a real issue or false positive
4. Only report confirmed issues with specific fixes

### Phase 3: Plan

Before making changes:
1. Prioritize: CRITICAL (security) → HIGH (errors, circular deps) → MEDIUM (complexity) → LOW (style)
2. Check test coverage - if missing, write tests FIRST
3. Sequence changes to minimize risk
4. Use `/refactor-plan` for complex refactoring

### Phase 4: Fix

For each issue:
1. Verify tests exist (or write them first)
2. Make ONE minimal change
3. Run tests immediately
4. Commit with clear message

## Analysis Categories

### Security (CRITICAL) - Always Verify

| Issue | What to Check |
|-------|---------------|
| SQL Injection | Is input user-controlled? Is it parameterized elsewhere? |
| Command Injection | Is shell=True needed? Is input validated? |
| XSS | Is content sanitized? Is it user-controlled? |
| Hardcoded Secrets | Is it a real secret or placeholder/test value? |

### Error Handling (HIGH)

| Issue | What to Check |
|-------|---------------|
| Bare except | Is broad catch intentional and documented? |
| Silent swallowing | Would logging here help? Should it re-raise? |
| Missing handling | Is handling done at a higher level? |

### Structural (MEDIUM)

| Issue | Threshold | What to Check |
|-------|-----------|---------------|
| Function too long | > 40 lines | Can logical sections be extracted? |
| High complexity | > 12 | Can conditions be simplified? |
| Deep nesting | > 4 levels | Can early returns help? |
| Too many params | > 5 | Should use config object? |
| Large file | > 400 lines | Are there natural split points? |

### Dead Code (LOW)

| Issue | What to Check |
|-------|---------------|
| Unused import | Is it used dynamically? Used in type hints only? |
| Unused export | Is it part of public API? Used by external code? |
| Unreachable code | Is it intentional (debug code)? |

### Duplicates (LOW)

Duplicates flagged by AST similarity. Before consolidating:
- Are they truly the same logic or coincidentally similar?
- Do they need different error handling?
- Would extraction actually improve maintainability?

## Auto-Fix Support

The analyzer can generate fix suggestions:

```bash
python3 scripts/analyze.py <path> --fix --summary
```

Fix types:
- **Safe**: Can be applied automatically (unused imports, bare except)
- **Needs review**: Require verification (long functions, duplicates)

## Output Format

Analysis output is JSON with these sections:

```json
{
  "summary": { ... },
  "security_issues": [ ... ],
  "error_handling_issues": [ ... ],
  "dead_code": [ ... ],
  "duplicates": [ ... ],
  "circular_deps": [ ... ],
  "complex_functions": [ ... ],
  "long_functions": [ ... ],
  "type_errors": [ ... ],
  "fixes": [ ... ]
}
```

## Verification Reminders

Before reporting ANY issue:

1. [ ] I have read the actual code
2. [ ] I understand what the code is trying to do
3. [ ] I have checked for mitigating factors
4. [ ] I can explain WHY this is a problem
5. [ ] I have a specific, minimal fix

See `references/verification-guide.md` for detailed verification procedures.

## What NOT to Do

- ❌ Report issues from pattern matching without reading code
- ❌ Suggest architectural rewrites for small changes
- ❌ Add abstraction "for flexibility"
- ❌ Change working code based on style preference
- ❌ Refactor without tests in place
- ❌ Make multiple changes at once

## Quality Checklist

Before approving code as production-ready:

**Security**
- [ ] No secrets in code
- [ ] User input sanitized
- [ ] No injection vulnerabilities

**Reliability**
- [ ] Error paths handled
- [ ] Edge cases covered
- [ ] Resources cleaned up

**Maintainability**
- [ ] Functions do one thing
- [ ] No deep nesting
- [ ] Clear naming

**Testing**
- [ ] Critical paths tested
- [ ] Error cases tested
- [ ] Tests are reliable
