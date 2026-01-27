# Add Tests

Generate tests for a file or function to enable safe refactoring.

## Arguments

$ARGUMENTS: Target to test. Can be:
- File path: `src/services/user.ts`
- File with function: `src/services/user.ts:authenticate`
- File with class: `src/models/order.py:Order`

## What I Do

1. **Analyze the code** - Understand inputs, outputs, side effects
2. **Identify test cases** - Happy path, edge cases, error cases
3. **Generate test file** - Using appropriate framework
4. **Run tests** - Verify they pass

## Test Coverage Goals

For each function:
- ✅ Happy path - Normal successful operation
- ✅ Edge cases - Empty inputs, nulls, boundaries  
- ✅ Error cases - Invalid inputs, failure conditions
- ✅ Side effects - External calls (mocked)

## Framework Detection

| Language | Framework |
|----------|-----------|
| TypeScript/JavaScript | Jest, Vitest |
| Python | pytest |
| Go | testing package |
| React | @testing-library/react |

## Test Location

```
src/services/user.ts      → src/services/user.test.ts
src/services/user.py      → tests/services/test_user.py  
src/services/user.go      → src/services/user_test.go
```

## Examples

```
/add-tests src/services/user.ts
/add-tests src/services/user.ts:authenticate
/add-tests src/models/order.py:Order
```

## Important

Tests capture CURRENT behavior (even if buggy). This enables safe refactoring. Fix bugs AFTER tests are in place.

See `references/test-generation-guide.md` for templates.
