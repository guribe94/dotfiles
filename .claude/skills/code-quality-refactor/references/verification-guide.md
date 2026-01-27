# Issue Verification Guide

**Golden Rule:** Never report an issue without reading the actual code.

## Security Verification

### SQL Injection
**Verify:** Is input user-controlled? Parameterized elsewhere? Just a template?
```python
# REAL: user_id = request.args.get('id'); cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
# FALSE POSITIVE: QUERY = "SELECT * FROM users WHERE id = %s"; cursor.execute(QUERY, (id,))
```

### Command Injection  
**Verify:** Is input user-controlled? Is shell=True needed? Is input validated?
```python
# REAL: os.system(f"convert {user_filename} output.pdf")
# FALSE POSITIVE: os.system("systemctl restart nginx")  # constant
```

### Hardcoded Secrets
**Verify:** Real secret or placeholder? In test file? Obviously fake?
```python
# REAL: API_KEY = "sk-live-abc123realkey456"
# FALSE POSITIVE: API_KEY = os.environ.get("API_KEY", "dev-fallback")
# FALSE POSITIVE: api_key = "your-api-key-here"  # placeholder
```

### XSS
**Verify:** Is content user-controlled? Is it sanitized? Static content?
```javascript
// REAL: element.innerHTML = userComment;
// FALSE POSITIVE: element.innerHTML = '<span class="icon">✓</span>';
// FALSE POSITIVE: element.innerHTML = DOMPurify.sanitize(userComment);
```

## Error Handling Verification

### Bare/Silent Except
**Verify:** Is silence intentional? Would logging help? Is it cleanup code?
```python
# PROBLEMATIC: except: pass  # Hides all errors
# ACCEPTABLE (with reason): except OSError: pass  # File might be deleted
```

## Performance Verification

### N+1 Queries
**Verify:** Is eager loading used? Is N actually large? Intentional batching?
```python
# REAL N+1: for user in users: orders = Order.objects.filter(user=user)
# FALSE POSITIVE: users = User.objects.prefetch_related('orders')  # Eager loaded
```

### Unbounded Data
**Verify:** Pagination elsewhere? Known small dataset? Has WHERE clause?
```python
# REAL: return User.objects.all()  # Could be millions
# FALSE POSITIVE: return Settings.objects.all()  # Config table, ~10 rows
```

## Before Reporting Checklist

- [ ] I read the actual code
- [ ] I understand the context
- [ ] I checked for mitigating factors
- [ ] I traced data flow where relevant
- [ ] I can explain WHY this is a problem
- [ ] I have a specific fix
