# Cryptographic Standards

Modern cryptographic standards for secure implementations.

---

## Password Storage

### Recommended Algorithms

| Algorithm | Work Factor | Notes |
|-----------|-------------|-------|
| **Argon2id** | Memory: 64MB, Iterations: 3, Parallelism: 4 | Preferred, memory-hard |
| **bcrypt** | Cost: 12 | Well-tested, widely available |
| **scrypt** | N: 2^17, r: 8, p: 1 | Memory-hard alternative |

### Implementation

```javascript
// Node.js - bcrypt
const bcrypt = require('bcrypt');
const SALT_ROUNDS = 12;

async function hashPassword(password) {
  return await bcrypt.hash(password, SALT_ROUNDS);
}

async function verifyPassword(password, hash) {
  return await bcrypt.compare(password, hash);
}

// Node.js - argon2
const argon2 = require('argon2');

async function hashPassword(password) {
  return await argon2.hash(password, {
    type: argon2.argon2id,
    memoryCost: 65536,  // 64MB
    timeCost: 3,
    parallelism: 4
  });
}

async function verifyPassword(password, hash) {
  return await argon2.verify(hash, password);
}
```

```python
# Python - bcrypt
import bcrypt

def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))

def verify_password(password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(password.encode(), hashed)

# Python - argon2
from argon2 import PasswordHasher

ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4
)

def hash_password(password: str) -> str:
    return ph.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    try:
        return ph.verify(hashed, password)
    except:
        return False
```

### Never Use

- MD5 (broken)
- SHA1 (broken)
- SHA256 without salt (rainbow tables)
- Single-round hashing
- Custom hashing schemes

---

## Encryption

### Symmetric Encryption

| Algorithm | Key Size | Notes |
|-----------|----------|-------|
| **AES-256-GCM** | 256 bits | Preferred, authenticated |
| **ChaCha20-Poly1305** | 256 bits | Good for mobile/low-power |

### Implementation

```javascript
// Node.js - AES-256-GCM
const crypto = require('crypto');

function encrypt(plaintext, key) {
  const iv = crypto.randomBytes(12);  // 96 bits for GCM
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);

  let encrypted = cipher.update(plaintext, 'utf8', 'hex');
  encrypted += cipher.final('hex');

  const authTag = cipher.getAuthTag();

  return {
    iv: iv.toString('hex'),
    encrypted: encrypted,
    authTag: authTag.toString('hex')
  };
}

function decrypt(encrypted, key, iv, authTag) {
  const decipher = crypto.createDecipheriv(
    'aes-256-gcm',
    key,
    Buffer.from(iv, 'hex')
  );
  decipher.setAuthTag(Buffer.from(authTag, 'hex'));

  let decrypted = decipher.update(encrypted, 'hex', 'utf8');
  decrypted += decipher.final('utf8');

  return decrypted;
}
```

```python
# Python - AES-256-GCM
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

def encrypt(plaintext: bytes, key: bytes) -> tuple[bytes, bytes]:
    """Returns (nonce, ciphertext)"""
    nonce = os.urandom(12)  # 96 bits for GCM
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce, ciphertext

def decrypt(nonce: bytes, ciphertext: bytes, key: bytes) -> bytes:
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)
```

### Key Generation

```javascript
// Generate 256-bit key
const key = crypto.randomBytes(32);

// Derive key from password
const crypto = require('crypto');

function deriveKey(password, salt) {
  return crypto.scryptSync(password, salt, 32, {
    N: 2 ** 17,
    r: 8,
    p: 1
  });
}
```

### Never Use

- ECB mode (pattern leakage)
- CBC without authentication
- DES / 3DES (deprecated)
- RC4 (broken)
- Custom encryption schemes

---

## Random Number Generation

### Cryptographically Secure

```javascript
// Node.js
const crypto = require('crypto');

// Generate random bytes
const randomBytes = crypto.randomBytes(32);

// Generate random number in range
function secureRandomInt(min, max) {
  const range = max - min;
  const bytesNeeded = Math.ceil(Math.log2(range) / 8);
  let randomValue;

  do {
    randomValue = crypto.randomBytes(bytesNeeded).readUIntBE(0, bytesNeeded);
  } while (randomValue >= range);

  return min + randomValue;
}

// Generate token
function generateToken(length = 32) {
  return crypto.randomBytes(length).toString('hex');
}

// Generate UUID
const { randomUUID } = require('crypto');
const uuid = randomUUID();
```

```python
# Python
import secrets
import os

# Generate random bytes
random_bytes = os.urandom(32)
# or
random_bytes = secrets.token_bytes(32)

# Generate random token
token = secrets.token_hex(32)  # 64 hex characters
url_safe_token = secrets.token_urlsafe(32)

# Generate random number in range
random_int = secrets.randbelow(100)  # 0 to 99

# Compare strings safely (timing attack resistant)
secrets.compare_digest(a, b)
```

### Never Use for Security

- `Math.random()` (JavaScript)
- `random.random()` (Python)
- `rand()` (C)
- `java.util.Random`
- Any unseeded or time-seeded generator

---

## Digital Signatures

### Recommended Algorithms

| Algorithm | Key Size | Notes |
|-----------|----------|-------|
| **Ed25519** | 256 bits | Fast, secure, small signatures |
| **ECDSA P-256** | 256 bits | Widely supported |
| **RSA-PSS** | 2048+ bits | Legacy compatibility |

### Implementation

```javascript
// Node.js - Ed25519
const crypto = require('crypto');

// Generate key pair
const { publicKey, privateKey } = crypto.generateKeyPairSync('ed25519');

// Sign
function sign(data, privateKey) {
  return crypto.sign(null, Buffer.from(data), privateKey);
}

// Verify
function verify(data, signature, publicKey) {
  return crypto.verify(null, Buffer.from(data), publicKey, signature);
}
```

---

## JWT Best Practices

### Recommended Algorithms

| Algorithm | Notes |
|-----------|-------|
| **RS256** | RSA signature, asymmetric |
| **ES256** | ECDSA P-256, asymmetric |
| **EdDSA** | Ed25519, asymmetric (preferred) |

### Implementation

```javascript
const jwt = require('jsonwebtoken');

// Always specify algorithm explicitly
const token = jwt.sign(payload, privateKey, {
  algorithm: 'RS256',
  expiresIn: '1h',
  issuer: 'your-app',
  audience: 'your-api'
});

// Verify with explicit algorithm
const decoded = jwt.verify(token, publicKey, {
  algorithms: ['RS256'],  // Whitelist only!
  issuer: 'your-app',
  audience: 'your-api'
});
```

### JWT Security Rules

1. **Never accept 'none' algorithm**
2. **Whitelist allowed algorithms**
3. **Use asymmetric algorithms for distributed systems**
4. **Set reasonable expiration**
5. **Include audience and issuer claims**
6. **Don't store sensitive data in payload (it's not encrypted)**

### Vulnerable Patterns

```javascript
// NEVER do this - accepts 'none' algorithm
jwt.verify(token, secret);  // No algorithm specified!

// NEVER do this - algorithm confusion attack
jwt.verify(token, publicKey, { algorithms: ['RS256', 'HS256'] });
// Attacker can sign with public key using HS256!
```

---

## TLS Configuration

### Minimum Requirements

- TLS 1.2 or higher
- Strong cipher suites only
- Perfect Forward Secrecy (PFS)
- HSTS enabled

### Nginx Example

```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers on;
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;
ssl_stapling on;
ssl_stapling_verify on;

add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

---

## Key Management

### Principles

1. **Never hardcode keys**
2. **Rotate keys regularly**
3. **Use separate keys for separate purposes**
4. **Store keys in secure vaults (AWS KMS, HashiCorp Vault)**
5. **Audit key access**

### Key Hierarchy

```
Master Key (in HSM/KMS)
└── Data Encryption Keys (DEKs)
    └── Encrypt actual data
```

### Rotation Schedule

| Key Type | Rotation Period |
|----------|-----------------|
| Master keys | Annually |
| Data encryption keys | Quarterly |
| API keys | Quarterly or on compromise |
| Session keys | Per session |
| JWT signing keys | Quarterly |

---

## Common Vulnerabilities

### Timing Attacks

```javascript
// VULNERABLE - variable-time comparison
function checkToken(provided, expected) {
  return provided === expected;  // Short-circuits!
}

// SAFE - constant-time comparison
const crypto = require('crypto');
function checkToken(provided, expected) {
  return crypto.timingSafeEqual(
    Buffer.from(provided),
    Buffer.from(expected)
  );
}
```

### IV/Nonce Reuse

```javascript
// VULNERABLE - reusing IV
const iv = Buffer.from('fixed-iv-value!');  // Never reuse!

// SAFE - random IV per encryption
const iv = crypto.randomBytes(12);
```

### Padding Oracle

```javascript
// Use authenticated encryption (GCM) to prevent
// Never use CBC without HMAC
// Never reveal padding errors in responses
```
