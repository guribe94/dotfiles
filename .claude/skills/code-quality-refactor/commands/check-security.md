# Security Check

Focused security analysis with verification.

## Arguments

$ARGUMENTS: Path to check (file or directory). Defaults to current directory.

## What I Check

### Critical (Must Fix)
- **SQL Injection** - String formatting in queries
- **Command Injection** - User input in shell commands  
- **Hardcoded Secrets** - API keys, passwords in code
- **Code Injection** - eval/exec with user input

### High (Should Fix)
- **XSS** - Unsanitized HTML rendering (innerHTML, dangerouslySetInnerHTML)
- **Path Traversal** - User input in file paths
- **Insecure Deserialization** - pickle/yaml with untrusted data
- **Missing Auth** - Unprotected endpoints

### Medium (Review)
- **Missing Validation** - Unvalidated request data
- **Permissive CORS** - Overly broad cross-origin access
- **Sensitive Data Logging** - Passwords/tokens in logs

## Verification Process

For EVERY finding, I will:
1. **Read the code** - Not just pattern match
2. **Trace data flow** - Is input actually user-controlled?
3. **Check mitigations** - Validation/sanitization elsewhere?
4. **Assess exploitability** - Is this actually exploitable?

## Output Format

```markdown
## 🔴 CRITICAL: SQL Injection

**File:** src/api/users.ts:45
**Verified:** Yes - user input flows directly to query

**Vulnerable Code:**
```typescript
const id = req.params.id;
db.query(`SELECT * FROM users WHERE id = ${id}`);
```

**Fix:**
```typescript
db.query('SELECT * FROM users WHERE id = ?', [id]);
```
```

## Examples

```
/check-security
/check-security src/api/
/check-security src/services/auth.ts
```

## After Check

I provide:
1. Prioritized list of verified vulnerabilities
2. Specific fixes for each
3. Security improvement recommendations
