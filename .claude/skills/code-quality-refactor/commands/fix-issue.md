# Fix Issue

Safely fix a specific code quality issue.

## Arguments

$ARGUMENTS: Location and optional description in format: `<file:line> [description]`

Examples:
- `src/api/users.ts:45`
- `src/api/users.ts:45 SQL injection`
- `src/services/auth.py:authenticate function too long`

## What I Do

1. **Read the code** - Understand current behavior
2. **Check for tests** - If none exist, offer to write them first
3. **Plan the fix** - Smallest change that solves the problem
4. **Make the change** - One refactoring only
5. **Verify** - Run tests, ensure behavior preserved

## Safety Checks

Before any change:
- [ ] I understand current behavior
- [ ] Tests exist (or I'll write them first)
- [ ] Fix is minimal and focused
- [ ] Change preserves behavior

## Fix Types I Handle

| Issue | How I Fix |
|-------|-----------|
| Long function | Extract helper functions |
| Deep nesting | Early returns, extract logic |
| SQL injection | Parameterized queries |
| Bare except | Catch specific exceptions |
| Hardcoded secret | Move to environment variable |
| Silent exception | Add logging |
| N+1 query | Add eager loading |
| Missing validation | Add input validation |

## What I Won't Do

- ❌ Multiple changes at once
- ❌ Refactor without tests
- ❌ Change public API without approval
- ❌ "Improve" beyond the specific issue

## Examples

```
/fix-issue src/api/users.ts:45
/fix-issue src/services/auth.py:78 function too long
/fix-issue src/utils/db.ts:23 SQL injection
```

## After Fixing

I'll show:
1. The exact change (diff)
2. Test results
3. Any follow-up recommendations
