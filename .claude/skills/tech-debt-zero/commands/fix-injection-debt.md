# /fix-injection-debt

Fix SQL, XSS, command, SSRF, path traversal, NoSQL, and XXE injection vulnerabilities.

## Usage

```
/fix-injection-debt [path] [options]
```

### Options

- `--type <type>` - Focus on specific injection type (sql, xss, command, ssrf, path, nosql, xxe)
- `--dry-run` - Show what would be fixed without making changes
- `--interactive` - Prompt before each fix

## Instructions

When the user runs `/fix-injection-debt`:

1. **Run the injection analyzer** to identify vulnerabilities:
   ```bash
   python ~/.claude/skills/tech-debt-zero/scripts/analyzers/analyze_injection.py [path]
   ```

2. **For each finding, apply the appropriate fix**:

### SQL Injection Fixes

**Before (vulnerable):**
```javascript
// Template literal
db.query(`SELECT * FROM users WHERE id = ${userId}`)

// String concatenation
db.query('SELECT * FROM users WHERE name = ' + name)

// Python f-string
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
```

**After (safe):**
```javascript
// Parameterized query (Node.js)
db.query('SELECT * FROM users WHERE id = $1', [userId])

// Prepared statement (Python)
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

### XSS Fixes

**Before (vulnerable):**
```javascript
element.innerHTML = userInput
document.write(data)
<div dangerouslySetInnerHTML={{__html: userContent}} />
```

**After (safe):**
```javascript
// Use textContent for plain text
element.textContent = userInput

// Use DOMPurify for HTML
import DOMPurify from 'dompurify'
element.innerHTML = DOMPurify.sanitize(userInput)

// React: Sanitize before use
<div dangerouslySetInnerHTML={{__html: DOMPurify.sanitize(userContent)}} />
```

### Command Injection Fixes

**Before (vulnerable):**
```javascript
exec(`ls ${userDir}`)
spawn('bash', ['-c', userCommand], {shell: true})
```

**After (safe):**
```javascript
// Use execFile with array arguments
const { execFile } = require('child_process')
execFile('ls', [sanitizedDir])

// spawn without shell
spawn('ls', [sanitizedDir], {shell: false})
```

### SSRF Fixes

**Before (vulnerable):**
```javascript
const response = await fetch(req.body.url)
```

**After (safe):**
```javascript
const { URL } = require('url')

function isAllowedUrl(urlString) {
  const parsed = new URL(urlString)
  const allowedHosts = ['api.trusted.com', 'cdn.trusted.com']

  // Check scheme
  if (!['http:', 'https:'].includes(parsed.protocol)) {
    return false
  }

  // Check host whitelist
  if (!allowedHosts.includes(parsed.hostname)) {
    return false
  }

  // Block private IPs
  if (isPrivateIP(parsed.hostname)) {
    return false
  }

  return true
}

if (!isAllowedUrl(req.body.url)) {
  return res.status(400).json({ error: 'URL not allowed' })
}
const response = await fetch(req.body.url)
```

### Path Traversal Fixes

**Before (vulnerable):**
```javascript
const filePath = path.join('/uploads', userInput)
fs.readFile(filePath)
```

**After (safe):**
```javascript
const baseDir = path.resolve('/uploads')
const filePath = path.resolve(baseDir, userInput)

// Verify path is within allowed directory
if (!filePath.startsWith(baseDir + path.sep)) {
  throw new Error('Invalid path')
}

fs.readFile(filePath)
```

3. **Verify the fix**:
   - Re-run the analyzer to confirm vulnerability is fixed
   - Run existing tests to check for regressions
   - If no tests, suggest adding security test cases

4. **Generate test cases** for the fixed vulnerability:
   ```javascript
   describe('SQL Injection Prevention', () => {
     it('should handle malicious input safely', async () => {
       const maliciousInput = "'; DROP TABLE users; --"
       const result = await getUser(maliciousInput)
       expect(result).toBeNull() // Not executed as SQL
     })
   })
   ```

## Remediation Checklist

### SQL Injection
- [ ] All queries use parameterized statements
- [ ] ORM queries don't use raw() with user input
- [ ] No string concatenation in queries
- [ ] Input validation as defense in depth
- [ ] Test with malicious SQL strings

### XSS
- [ ] All user input escaped/encoded on output
- [ ] innerHTML replaced with textContent where possible
- [ ] DOMPurify used for necessary HTML rendering
- [ ] CSP headers configured
- [ ] Test with XSS payloads

### Command Injection
- [ ] execFile used instead of exec
- [ ] spawn uses shell: false
- [ ] User input never in command strings
- [ ] Input validated against whitelist
- [ ] Test with shell metacharacters

### SSRF
- [ ] URL whitelist enforced
- [ ] Private IP ranges blocked
- [ ] Redirects limited or disabled
- [ ] DNS rebinding protection
- [ ] Test with internal URLs

## References

- CWE-89: SQL Injection
- CWE-79: Cross-site Scripting
- CWE-78: OS Command Injection
- CWE-918: Server-Side Request Forgery
- CWE-22: Path Traversal
- OWASP A03:2021 - Injection
