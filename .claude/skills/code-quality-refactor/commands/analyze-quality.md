# Analyze Code Quality

Perform comprehensive, verified code quality analysis.

## Arguments

$ARGUMENTS: Path to analyze (file or directory). Defaults to current directory.

## What I Do

1. **Run language-specific analyzers** (TypeScript, Python, Go)
2. **Gather metrics**: complexity, length, nesting, dead code, duplicates
3. **Verify each potential issue** by reading actual code
4. **Report only confirmed issues** with specific fixes

## Analysis Includes

| Category | What's Checked |
|----------|----------------|
| **Security** | SQL injection, XSS, hardcoded secrets, command injection |
| **Error Handling** | Bare except, silent swallowing, missing handling |
| **Complexity** | Cyclomatic complexity > 12, deep nesting > 4 |
| **Structure** | Functions > 40 lines, files > 400 lines |
| **Dead Code** | Unused imports/exports, unreachable code |
| **Duplicates** | AST-similar code blocks |
| **Types** | TypeScript type errors |
| **Dependencies** | Circular imports |

## Output

For each verified issue:
- Severity (CRITICAL/HIGH/MEDIUM/LOW)
- Exact location (file:line)
- What's wrong and why it matters
- Specific fix with code

## Examples

```
/analyze-quality
/analyze-quality src/
/analyze-quality src/services/auth.ts
```

## After Analysis

Based on results, you can:
- `/fix-issue <file:line>` to fix specific issues
- `/refactor-plan` for a full roadmap
- `/add-tests <file>` to improve coverage first
