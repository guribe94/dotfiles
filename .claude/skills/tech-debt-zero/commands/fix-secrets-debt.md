# /fix-secrets-debt

Fix hardcoded secrets, rotation gaps, and secret exposure in logs/artifacts.

## Usage

```
/fix-secrets-debt [path] [options]
```

### Options

- `--rotate` - Also rotate discovered secrets (requires manual confirmation)
- `--clean-history` - Generate commands to clean Git history
- `--dry-run` - Show what would be fixed without making changes

## Instructions

When the user runs `/fix-secrets-debt`:

1. **Run the secrets analyzer**:
   ```bash
   python ~/.claude/skills/tech-debt-zero/scripts/analyzers/analyze_secrets.py [path]
   ```

2. **For each finding, follow this remediation sequence**:

### Step 1: Remove Secret from Code

**Before (vulnerable):**
```javascript
const API_KEY = 'sk-live-abc123xyz789'
const JWT_SECRET = 'super-secret-key'
const DB_PASSWORD = 'production_password'
```

**After (safe):**
```javascript
// Use environment variables
const API_KEY = process.env.API_KEY
const JWT_SECRET = process.env.JWT_SECRET
const DB_PASSWORD = process.env.DB_PASSWORD

// Validate at startup
if (!API_KEY || !JWT_SECRET) {
  throw new Error('Missing required environment variables')
}
```

### Step 2: Add to .gitignore

```gitignore
# Environment files
.env
.env.local
.env.*.local

# Never commit these
*.pem
*.key
secrets.json
credentials.json
```

### Step 3: Create .env.example

```bash
# .env.example (commit this, not .env)
API_KEY=your_api_key_here
JWT_SECRET=generate_a_secure_random_string
DB_PASSWORD=your_database_password
```

### Step 4: Rotate the Secret

**CRITICAL**: If a secret was committed, it's compromised. Rotate it:

1. **AWS Keys**:
   ```bash
   # Create new key
   aws iam create-access-key --user-name my-user
   # Delete old key after updating
   aws iam delete-access-key --access-key-id AKIA...
   ```

2. **API Keys**:
   - Go to provider dashboard
   - Generate new key
   - Update environment variables
   - Revoke old key

3. **Database Passwords**:
   ```sql
   ALTER USER 'app_user'@'%' IDENTIFIED BY 'new_secure_password';
   ```

4. **JWT Secrets**:
   ```bash
   # Generate new secret
   node -e "console.log(require('crypto').randomBytes(64).toString('hex'))"
   ```

### Step 5: Clean Git History (if needed)

**Option A: BFG Repo-Cleaner (faster)**
```bash
# Install BFG
brew install bfg

# Remove secrets from history
bfg --replace-text secrets.txt repo.git
cd repo.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push (coordinate with team!)
git push --force
```

**Option B: git filter-branch**
```bash
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/secret/file" \
  --prune-empty --tag-name-filter cat -- --all
```

### Step 6: Use Secrets Manager (Production)

**AWS Secrets Manager:**
```javascript
const { SecretsManagerClient, GetSecretValueCommand } = require('@aws-sdk/client-secrets-manager')

async function getSecret(secretName) {
  const client = new SecretsManagerClient({ region: 'us-east-1' })
  const command = new GetSecretValueCommand({ SecretId: secretName })
  const response = await client.send(command)
  return JSON.parse(response.SecretString)
}

// Usage
const secrets = await getSecret('my-app/production')
const dbPassword = secrets.DB_PASSWORD
```

**HashiCorp Vault:**
```javascript
const vault = require('node-vault')({ endpoint: process.env.VAULT_ADDR })

async function getSecret(path) {
  await vault.approleLogin({
    role_id: process.env.VAULT_ROLE_ID,
    secret_id: process.env.VAULT_SECRET_ID
  })
  const result = await vault.read(path)
  return result.data.data
}
```

### Step 7: Fix Secrets in Logs

**Before (vulnerable):**
```javascript
logger.info('User login', { email, password: req.body.password })
logger.error('API call failed', { apiKey: config.apiKey, error })
```

**After (safe):**
```javascript
// Redaction utility
function redactSecrets(obj) {
  const sensitiveFields = ['password', 'secret', 'token', 'apiKey', 'key', 'credential']
  const redacted = { ...obj }

  for (const field of sensitiveFields) {
    if (redacted[field]) {
      redacted[field] = '[REDACTED]'
    }
  }
  return redacted
}

logger.info('User login', { email })  // Don't log password at all
logger.error('API call failed', redactSecrets({ apiKey: config.apiKey, error }))
```

3. **Verify remediation**:
   - Re-run secrets analyzer
   - Verify .gitignore is correct
   - Verify environment variables work
   - Test secret loading

## Remediation Checklist

- [ ] Secret removed from source code
- [ ] Environment variable created
- [ ] .gitignore updated
- [ ] .env.example created
- [ ] Secret rotated (if was committed)
- [ ] Git history cleaned (if necessary)
- [ ] Secrets manager configured (production)
- [ ] Logging sanitized
- [ ] Tests updated to use test secrets
- [ ] CI/CD updated with new secrets

## Prevention

Add to pre-commit:
```yaml
- repo: https://github.com/Yelp/detect-secrets
  rev: v1.4.0
  hooks:
    - id: detect-secrets
      args: ['--baseline', '.secrets.baseline']
```

## References

- CWE-798: Use of Hardcoded Credentials
- CWE-312: Cleartext Storage of Sensitive Information
- CWE-532: Insertion of Sensitive Information into Log File
- OWASP A07:2021 - Identification and Authentication Failures
