# Generate Refactoring Plan

Create a prioritized, safe refactoring roadmap.

## Arguments

$ARGUMENTS: Path to plan refactoring for. Defaults to current directory.

## What I Generate

A phased plan that:
1. **Prioritizes by risk/impact** - Critical security first, cosmetic last
2. **Sequences for safety** - Tests before refactoring
3. **Estimates effort** - S/M/L for each task
4. **Groups related changes** - Batch changes that should go together

## Plan Structure

```markdown
## Phase 1: Critical (Do Immediately)
Security vulnerabilities, data corruption risks

## Phase 2: Add Test Coverage  
Write tests for code we'll refactor

## Phase 3: High-Impact Refactoring
Break up large functions, fix error handling

## Phase 4: Code Quality
Reduce complexity, remove duplication

## Phase 5: Polish (Optional)
Style, documentation
```

## Each Item Includes

- [ ] Checkbox for tracking
- File and line location
- What to change and why
- Effort estimate (S/M/L)
- Dependencies

## Example Output

```markdown
## Phase 1: Critical

- [ ] **Fix SQL injection** [CRITICAL]
  - File: `src/api/users.ts:45`
  - Change: Use parameterized query
  - Effort: S

## Phase 2: Add Tests

- [ ] **Test UserService.authenticate**
  - File: `src/services/user.ts:78-120`
  - Reason: Will refactor in Phase 3
  - Effort: M
```

## Examples

```
/refactor-plan
/refactor-plan src/
/refactor-plan src/api/
```
