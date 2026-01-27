# Test Generation Guide

Write tests BEFORE refactoring to ensure behavior is preserved.

## Coverage Goals

For each function:
- [ ] Happy path - Normal operation
- [ ] Edge cases - Empty, null, boundaries
- [ ] Error cases - Invalid input, failures
- [ ] Side effects - External calls (mocked)

## TypeScript/JavaScript (Jest)

```typescript
describe('functionName', () => {
  it('handles normal input', () => {
    const result = functionName(validInput);
    expect(result).toEqual(expected);
  });

  it('handles empty input', () => {
    expect(functionName([])).toEqual([]);
  });

  it('throws on invalid input', () => {
    expect(() => functionName(null)).toThrow('Invalid');
  });
});

// With mocks
jest.mock('./externalService');
it('calls external service correctly', async () => {
  externalService.call.mockResolvedValue({ ok: true });
  await processData(input);
  expect(externalService.call).toHaveBeenCalledWith(expected);
});
```

## Python (pytest)

```python
class TestFunctionName:
    def test_happy_path(self):
        result = function_name(valid_input)
        assert result == expected

    def test_empty_input(self):
        assert function_name([]) == []

    def test_invalid_input(self):
        with pytest.raises(ValueError):
            function_name(None)

# With mocks
from unittest.mock import Mock, patch

@patch('module.external_service')
def test_external_call(mock_service):
    mock_service.call.return_value = {'ok': True}
    result = process_data(input)
    mock_service.call.assert_called_once_with(expected)
```

## Go (testing)

```go
func TestFunctionName(t *testing.T) {
    tests := []struct {
        name    string
        input   InputType
        want    OutputType
        wantErr bool
    }{
        {"valid", validInput, expected, false},
        {"empty", emptyInput, emptyOutput, false},
        {"invalid", invalidInput, nil, true},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            got, err := FunctionName(tt.input)
            if (err != nil) != tt.wantErr {
                t.Errorf("error = %v, wantErr %v", err, tt.wantErr)
            }
            if !reflect.DeepEqual(got, tt.want) {
                t.Errorf("got %v, want %v", got, tt.want)
            }
        })
    }
}
```

## React Components

```typescript
import { render, screen, fireEvent } from '@testing-library/react';

describe('UserForm', () => {
  it('renders fields', () => {
    render(<UserForm />);
    expect(screen.getByLabelText('Email')).toBeInTheDocument();
  });

  it('submits with form data', () => {
    const onSubmit = jest.fn();
    render(<UserForm onSubmit={onSubmit} />);
    
    fireEvent.change(screen.getByLabelText('Email'), {
      target: { value: 'test@example.com' }
    });
    fireEvent.click(screen.getByRole('button', { name: 'Submit' }));
    
    expect(onSubmit).toHaveBeenCalledWith({ email: 'test@example.com' });
  });
});
```

## Test File Locations

```
src/services/user.ts   → src/services/user.test.ts
src/services/user.py   → tests/services/test_user.py
src/services/user.go   → src/services/user_test.go
```

## Anti-Patterns

❌ Testing implementation: `expect(cache.get).toBeCalled()`
✅ Testing behavior: `expect(result.id).toBe(1)`

❌ Flaky tests: `time.sleep(1); assert ...`
✅ Deterministic: Mock time/network

❌ Only happy path
✅ Include error cases
