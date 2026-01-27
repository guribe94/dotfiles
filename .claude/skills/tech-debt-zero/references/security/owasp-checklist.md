# OWASP Security Checklist

Based on OWASP Top 10 (2021) and ASVS 4.0.

---

## A01: Broken Access Control

### Checklist

- [ ] Deny by default (except public resources)
- [ ] Access control enforced once, reused throughout
- [ ] Model access control enforces record ownership
- [ ] Unique business limit requirements enforced by domain models
- [ ] Directory listing disabled
- [ ] File metadata and backups not in web roots
- [ ] Rate limiting on API and controller access
- [ ] Stateless sessions invalidated on logout
- [ ] JWT invalidation for stateless tokens

### Detection Patterns

```javascript
// IDOR - Direct object reference without ownership check
app.get('/api/documents/:id', async (req, res) => {
  const doc = await Document.findById(req.params.id); // No user check!
  res.json(doc);
});

// Missing auth middleware
app.delete('/api/users/:id', deleteUser); // No auth!

// Privilege escalation
if (req.body.role) {
  user.role = req.body.role; // User can set own role!
}
```

### Remediation

```javascript
// Fixed IDOR
app.get('/api/documents/:id', requireAuth, async (req, res) => {
  const doc = await Document.findOne({
    _id: req.params.id,
    userId: req.user.id  // Ownership check
  });
  if (!doc) return res.status(404).json({ error: 'Not found' });
  res.json(doc);
});
```

---

## A02: Cryptographic Failures

### Checklist

- [ ] No sensitive data transmitted in clear text (HTTP)
- [ ] No deprecated cryptographic algorithms (MD5, SHA1, DES, RC4)
- [ ] Strong key generation, management, rotation
- [ ] Passwords stored with strong adaptive hashing (bcrypt, argon2)
- [ ] Initialization vectors unique and random
- [ ] Authenticated encryption (not just encryption)
- [ ] Keys generated cryptographically randomly

### Detection Patterns

```javascript
// Weak hashing
const hash = crypto.createHash('md5').update(password).digest('hex');
const hash = crypto.createHash('sha1').update(password).digest('hex');

// Insecure random
const token = Math.random().toString(36);
const sessionId = Date.now().toString();

// Hardcoded keys
const SECRET = 'my-secret-key-123';
const JWT_SECRET = 'super-secret';
```

### Remediation

```javascript
// Strong password hashing
const bcrypt = require('bcrypt');
const hash = await bcrypt.hash(password, 12);

// Secure random
const crypto = require('crypto');
const token = crypto.randomBytes(32).toString('hex');

// Key from environment
const JWT_SECRET = process.env.JWT_SECRET;
if (!JWT_SECRET || JWT_SECRET.length < 32) {
  throw new Error('Invalid JWT_SECRET');
}
```

---

## A03: Injection

### Checklist

- [ ] Parameterized queries for SQL
- [ ] Context-aware output encoding for XSS
- [ ] No OS command interpreter calls with user data
- [ ] ORM used safely (no raw queries with user input)
- [ ] XML parsers configured to prevent XXE
- [ ] LDAP queries properly escaped

### Detection Patterns

```javascript
// SQL injection
db.query(`SELECT * FROM users WHERE id = ${userId}`);
db.query('SELECT * FROM users WHERE name = ' + name);

// XSS
element.innerHTML = userInput;
res.send(`<div>${req.query.name}</div>`);

// Command injection
exec(`ls ${userDir}`);
spawn('bash', ['-c', userCommand]);

// XXE
const parser = new DOMParser();
parser.parseFromString(userXML, 'text/xml'); // No entity restriction
```

### Remediation

```javascript
// Parameterized SQL
db.query('SELECT * FROM users WHERE id = $1', [userId]);

// Output encoding
const escaped = escapeHtml(userInput);
res.send(`<div>${escaped}</div>`);

// Safe command execution
const { execFile } = require('child_process');
execFile('ls', [sanitizedDir]); // No shell

// XXE prevention
const parser = new DOMParser();
parser.setFeature('http://apache.org/xml/features/disallow-doctype-decl', true);
```

---

## A04: Insecure Design

### Checklist

- [ ] Threat modeling for critical flows
- [ ] Business logic tested for abuse cases
- [ ] Rate limiting on resource-intensive operations
- [ ] Segregation of duties for sensitive operations
- [ ] Proper failure handling (fail securely)

### Detection Patterns

```javascript
// Missing rate limit on sensitive operation
app.post('/api/password-reset', async (req, res) => {
  // No rate limiting - can enumerate emails
  await sendPasswordReset(req.body.email);
});

// Missing transaction/locking
async function transfer(from, to, amount) {
  const fromBalance = await getBalance(from);
  if (fromBalance >= amount) {
    // Race condition between check and update!
    await deduct(from, amount);
    await credit(to, amount);
  }
}
```

---

## A05: Security Misconfiguration

### Checklist

- [ ] Security hardening across all environments
- [ ] No default credentials
- [ ] Error handling doesn't reveal stack traces
- [ ] Security headers enabled
- [ ] Components up to date
- [ ] No unnecessary features enabled

### Detection Patterns

```javascript
// Stack trace exposure
app.use((err, req, res, next) => {
  res.status(500).json({ error: err.stack }); // Exposes internals!
});

// Missing security headers
app.use(express.static('public')); // No helmet

// Default credentials
const admin = { user: 'admin', pass: 'admin' };
```

### Remediation

```javascript
// Safe error handling
app.use((err, req, res, next) => {
  console.error(err); // Log full error
  res.status(500).json({ error: 'Internal server error' }); // Generic message
});

// Security headers
const helmet = require('helmet');
app.use(helmet());
app.use(helmet.contentSecurityPolicy({
  directives: {
    defaultSrc: ["'self'"],
    scriptSrc: ["'self'"],
    styleSrc: ["'self'", "'unsafe-inline'"],
  }
}));
```

---

## A06: Vulnerable and Outdated Components

### Checklist

- [ ] Inventory of components and versions
- [ ] Regular vulnerability scanning
- [ ] Components from official sources
- [ ] No unmaintained libraries
- [ ] Security patches applied promptly

### Detection Commands

```bash
# Node.js
npm audit
npx snyk test

# Python
pip-audit
safety check

# Go
go list -m all | nancy
govulncheck ./...

# Rust
cargo audit
```

---

## A07: Identification and Authentication Failures

### Checklist

- [ ] Brute force protection
- [ ] No default/weak passwords
- [ ] Secure password recovery
- [ ] Multi-factor where appropriate
- [ ] Proper session management
- [ ] Session invalidation on logout

### Detection Patterns

```javascript
// Weak password policy
if (password.length >= 4) { // Too weak!
  createUser(email, password);
}

// No brute force protection
app.post('/login', async (req, res) => {
  const user = await User.findOne({ email: req.body.email });
  // No rate limiting, no lockout
});

// Session fixation
app.post('/login', (req, res) => {
  req.session.userId = user.id;
  // Should regenerate session ID!
});
```

### Remediation

```javascript
// Strong password policy
const passwordPolicy = {
  minLength: 12,
  requireNumbers: true,
  requireSymbols: true,
  rejectCommon: true,
};

// Rate limiting
const rateLimit = require('express-rate-limit');
const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 5,
  message: 'Too many login attempts'
});
app.post('/login', loginLimiter, loginHandler);

// Session regeneration
app.post('/login', (req, res) => {
  req.session.regenerate((err) => {
    req.session.userId = user.id;
    res.json({ success: true });
  });
});
```

---

## A08: Software and Data Integrity Failures

### Checklist

- [ ] Digital signatures verify software/data integrity
- [ ] npm/pip packages from trusted repositories
- [ ] CI/CD pipeline integrity protected
- [ ] No unsigned/unencrypted serialized data from untrusted sources
- [ ] Code review for CI/CD configuration changes

### Detection Patterns

```javascript
// Unsafe deserialization
const data = JSON.parse(untrustedInput);
eval(data.code); // Code execution!

// No integrity check on downloads
const script = await fetch(externalUrl);
eval(await script.text()); // No verification!
```

---

## A09: Security Logging and Monitoring Failures

### Checklist

- [ ] Login, access control, input validation failures logged
- [ ] Sufficient context for forensics
- [ ] Log format compatible with log management
- [ ] High-value transactions have audit trail
- [ ] Alerting thresholds and escalation
- [ ] No sensitive data in logs

### Detection Patterns

```javascript
// No security logging
app.post('/login', async (req, res) => {
  const user = await authenticate(req.body);
  if (!user) {
    return res.status(401).json({ error: 'Invalid' });
    // No logging of failed attempt!
  }
});

// Sensitive data in logs
logger.info('User login', { email, password: req.body.password });
```

### Remediation

```javascript
// Proper security logging
app.post('/login', async (req, res) => {
  const user = await authenticate(req.body);
  if (!user) {
    securityLogger.warn('Failed login attempt', {
      email: req.body.email,
      ip: req.ip,
      userAgent: req.get('user-agent'),
      timestamp: new Date().toISOString()
    });
    return res.status(401).json({ error: 'Invalid credentials' });
  }
  securityLogger.info('Successful login', {
    userId: user.id,
    ip: req.ip
  });
});
```

---

## A10: Server-Side Request Forgery (SSRF)

### Checklist

- [ ] URL schema, port, destination validated
- [ ] Raw responses not sent to clients
- [ ] HTTP redirects disabled or restricted
- [ ] Network segmentation limits SSRF impact
- [ ] Allowlist for permitted destinations

### Detection Patterns

```javascript
// SSRF vulnerability
app.get('/fetch', async (req, res) => {
  const data = await fetch(req.query.url); // User controls URL!
  res.json(await data.json());
});

// Unsafe redirect following
const response = await axios.get(userUrl, {
  maxRedirects: 10 // Could redirect to internal services
});
```

### Remediation

```javascript
// URL validation
const URL = require('url');
const ALLOWED_HOSTS = ['api.example.com', 'cdn.example.com'];

app.get('/fetch', async (req, res) => {
  const parsed = new URL(req.query.url);

  // Validate scheme
  if (!['http:', 'https:'].includes(parsed.protocol)) {
    return res.status(400).json({ error: 'Invalid protocol' });
  }

  // Validate host
  if (!ALLOWED_HOSTS.includes(parsed.hostname)) {
    return res.status(400).json({ error: 'Host not allowed' });
  }

  // Block internal IPs
  const ip = await dns.resolve(parsed.hostname);
  if (isPrivateIP(ip)) {
    return res.status(400).json({ error: 'Internal hosts not allowed' });
  }

  const data = await fetch(req.query.url);
  res.json(await data.json());
});
```
