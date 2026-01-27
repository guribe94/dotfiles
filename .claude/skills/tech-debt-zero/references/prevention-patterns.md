# Prevention Patterns

Quality gates and CI/CD integration to prevent new tech debt from entering the codebase.

---

## Pre-Commit Hooks

### Setup with Husky (Node.js)

```bash
npx husky-init && npm install
npx husky add .husky/pre-commit "npm run pre-commit"
```

### Pre-Commit Configuration

```yaml
# .pre-commit-config.yaml
repos:
  # Secrets Detection
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']

  # Security Linting
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ['-c', 'pyproject.toml']

  # Dependency Check
  - repo: local
    hooks:
      - id: npm-audit
        name: npm audit
        entry: npm audit --audit-level moderate
        language: system
        pass_filenames: false
        files: package-lock.json

  # Type Checking
  - repo: local
    hooks:
      - id: typecheck
        name: TypeScript type check
        entry: npx tsc --noEmit
        language: system
        pass_filenames: false
        types: [typescript]
```

### Custom Pre-Commit Checks

```python
#!/usr/bin/env python3
# .git/hooks/pre-commit-custom

"""Custom pre-commit checks for tech debt prevention."""

import subprocess
import sys

def check_no_console_log():
    """Prevent console.log in production code."""
    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only', '-z'],
        capture_output=True, text=True
    )

    files = [f for f in result.stdout.split('\0')
             if f.endswith(('.ts', '.js')) and 'test' not in f]

    for file in files:
        diff = subprocess.run(
            ['git', 'diff', '--cached', file],
            capture_output=True, text=True
        )
        if 'console.log' in diff.stdout and '+' in diff.stdout:
            print(f"ERROR: console.log found in {file}")
            return False
    return True

def check_no_hardcoded_urls():
    """Prevent hardcoded URLs in production code."""
    patterns = [
        r'https?://localhost',
        r'https?://127\.0\.0\.1',
        r'https?://.*\.dev\.',
        r'https?://.*\.staging\.',
    ]
    # Implementation similar to above
    return True

def check_timeout_on_fetch():
    """Ensure fetch/axios calls have timeout."""
    # Scan for fetch() or axios without timeout config
    return True

if __name__ == '__main__':
    checks = [
        ('No console.log', check_no_console_log),
        ('No hardcoded URLs', check_no_hardcoded_urls),
        ('Timeouts on fetch', check_timeout_on_fetch),
    ]

    failed = []
    for name, check in checks:
        if not check():
            failed.append(name)

    if failed:
        print(f"\nPre-commit checks failed: {', '.join(failed)}")
        sys.exit(1)
```

---

## CI Pipeline Gates

### GitHub Actions Example

```yaml
# .github/workflows/quality-gates.yml
name: Quality Gates

on:
  pull_request:
    branches: [main, develop]

jobs:
  security-gate:
    name: Security Gate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Secret Detection
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.pull_request.base.sha }}
          head: ${{ github.event.pull_request.head.sha }}

      - name: Dependency Audit
        run: npm audit --audit-level moderate

      - name: SAST Scan
        uses: returntocorp/semgrep-action@v1
        with:
          config: >-
            p/security-audit
            p/secrets
            p/owasp-top-ten

      - name: Security Debt Scan
        run: |
          python scripts/analyzers/analyze_injection.py --fail-on critical
          python scripts/analyzers/analyze_secrets.py --fail-on critical
          python scripts/analyzers/analyze_auth.py --fail-on critical

  resilience-gate:
    name: Resilience Gate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Timeout Check
        run: python scripts/analyzers/analyze_resilience.py --check timeouts

      - name: Circuit Breaker Check
        run: python scripts/analyzers/analyze_resilience.py --check circuit-breakers

  quality-gate:
    name: Quality Gate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Dependencies
        run: npm ci

      - name: Type Check
        run: npx tsc --noEmit --strict

      - name: Lint
        run: npm run lint -- --max-warnings 0

      - name: Test with Coverage
        run: npm run test:coverage

      - name: Coverage Threshold
        run: |
          COVERAGE=$(cat coverage/coverage-summary.json | jq '.total.lines.pct')
          if (( $(echo "$COVERAGE < 80" | bc -l) )); then
            echo "Coverage $COVERAGE% is below 80% threshold"
            exit 1
          fi

  architecture-gate:
    name: Architecture Gate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for comparison

      - name: Coupling Metrics
        run: |
          python scripts/analyzers/analyze_coupling.py --baseline main
          # Fail if coupling increased significantly

      - name: Circular Dependency Check
        run: npx madge --circular src/

      - name: Bundle Size Check
        run: |
          npm run build
          BUNDLE_SIZE=$(stat -f%z dist/bundle.js 2>/dev/null || stat -c%s dist/bundle.js)
          MAX_SIZE=500000  # 500KB
          if [ "$BUNDLE_SIZE" -gt "$MAX_SIZE" ]; then
            echo "Bundle size $BUNDLE_SIZE exceeds $MAX_SIZE"
            exit 1
          fi
```

### GitLab CI Example

```yaml
# .gitlab-ci.yml
stages:
  - security
  - quality
  - test
  - build

security-scan:
  stage: security
  script:
    - npm audit --audit-level moderate
    - semgrep --config=auto --error .
    - detect-secrets scan --all-files
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"

dependency-check:
  stage: security
  script:
    - npm ci
    - npx snyk test --severity-threshold=high
  allow_failure: false

quality-check:
  stage: quality
  script:
    - npm ci
    - npm run lint -- --max-warnings 0
    - npx tsc --noEmit --strict
    - python scripts/analyzers/analyze_coupling.py

test-coverage:
  stage: test
  script:
    - npm ci
    - npm run test:coverage
    - |
      COVERAGE=$(cat coverage/coverage-summary.json | jq '.total.lines.pct')
      if (( $(echo "$COVERAGE < 80" | bc -l) )); then
        exit 1
      fi
  coverage: '/All files[^|]*\|[^|]*\s+([\d\.]+)/'
```

---

## PR Review Automation

### CODEOWNERS for Security

```
# .github/CODEOWNERS

# Security-sensitive files require security team review
**/auth/**          @security-team
**/crypto/**        @security-team
**/secrets/**       @security-team
*.env*              @security-team
**/middleware/auth* @security-team

# Infrastructure requires DevOps review
terraform/**        @devops-team
kubernetes/**       @devops-team
docker-compose*     @devops-team
Dockerfile*         @devops-team

# API changes require API team review
**/api/**           @api-team
openapi.yaml        @api-team
```

### PR Template

```markdown
<!-- .github/pull_request_template.md -->

## Summary
<!-- What does this PR do? -->

## Type of Change
- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change
- [ ] Security fix
- [ ] Performance improvement
- [ ] Refactoring (no functional change)

## Checklist

### Security
- [ ] No secrets committed
- [ ] Input validated
- [ ] Auth/authz enforced where needed
- [ ] No injection vulnerabilities

### Quality
- [ ] Tests added/updated
- [ ] Coverage maintained/improved
- [ ] Types correct (no `any`)
- [ ] No lint warnings

### Resilience
- [ ] External calls have timeouts
- [ ] Errors handled gracefully
- [ ] Logging added where needed

### Documentation
- [ ] README updated (if needed)
- [ ] API docs updated (if needed)
- [ ] Comments added for complex logic

## Testing Done
<!-- How did you test this? -->

## Rollback Plan
<!-- How would we rollback if this causes issues? -->
```

### Danger.js Rules

```javascript
// dangerfile.js
import { danger, warn, fail, message } from 'danger';

// Large PRs
const bigPRThreshold = 500;
if (danger.github.pr.additions + danger.github.pr.deletions > bigPRThreshold) {
  warn('This PR is quite large. Consider splitting it.');
}

// No tests
const hasTests = danger.git.modified_files.some(f => f.includes('test'));
const hasSrcChanges = danger.git.modified_files.some(f =>
  f.includes('src/') && !f.includes('test')
);
if (hasSrcChanges && !hasTests) {
  warn('No tests were modified. Are tests needed for this change?');
}

// Security-sensitive files
const securityFiles = ['auth', 'crypto', 'password', 'secret', 'token'];
const touchesSecurity = danger.git.modified_files.some(f =>
  securityFiles.some(s => f.toLowerCase().includes(s))
);
if (touchesSecurity) {
  message('This PR touches security-sensitive files. Ensure security review.');
}

// TODO/FIXME
const newTodos = danger.git.created_files
  .filter(f => f.endsWith('.ts') || f.endsWith('.js'))
  .some(f => {
    const content = danger.git.diffForFile(f);
    return content && content.includes('TODO') || content.includes('FIXME');
  });
if (newTodos) {
  warn('New TODO/FIXME comments added. Consider creating issues instead.');
}

// Console.log in production code
const hasConsoleLogs = danger.git.modified_files
  .filter(f => f.includes('src/') && !f.includes('test'))
  .some(async f => {
    const diff = await danger.git.diffForFile(f);
    return diff && diff.added.includes('console.log');
  });
if (hasConsoleLogs) {
  fail('console.log found in production code. Please remove.');
}
```

---

## IDE Integration

### ESLint Rules for Prevention

```javascript
// .eslintrc.js
module.exports = {
  rules: {
    // Security
    'no-eval': 'error',
    'no-implied-eval': 'error',
    'no-new-func': 'error',

    // Resilience
    'no-await-in-loop': 'warn',
    'require-await': 'error',

    // Quality
    'no-console': ['error', { allow: ['warn', 'error'] }],
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/explicit-function-return-type': 'warn',

    // Custom rule for timeouts (via plugin)
    'tech-debt/require-timeout': 'error',
  },
};
```

### VSCode Settings

```json
{
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "typescript.tsdk": "node_modules/typescript/lib",
  "typescript.enablePromptUseWorkspaceTsdk": true,
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "editor.formatOnSave": true
}
```

---

## Branch Protection Rules

### GitHub Branch Protection

```yaml
# Required for main branch
protection_rules:
  required_status_checks:
    strict: true
    contexts:
      - security-gate
      - resilience-gate
      - quality-gate
      - test-coverage

  required_pull_request_reviews:
    dismiss_stale_reviews: true
    require_code_owner_reviews: true
    required_approving_review_count: 1

  restrictions:
    users: []
    teams: []

  required_linear_history: true
  allow_force_pushes: false
  allow_deletions: false
```

---

## Debt Prevention Metrics

### Track Prevention Effectiveness

```yaml
metrics:
  - name: blocked_prs
    description: PRs blocked by quality gates
    labels: [gate_type, reason]

  - name: pre_commit_failures
    description: Pre-commit hook failures
    labels: [check_name]

  - name: new_debt_introduced
    description: New debt items per sprint
    labels: [category, severity]

  - name: debt_prevented
    description: Debt items caught before merge
    labels: [category, stage]
```

### Weekly Report

```markdown
## Tech Debt Prevention Report

### Gates Effectiveness
- PRs blocked by security gate: 12
- PRs blocked by quality gate: 8
- Pre-commit failures caught: 45

### Debt Prevented
| Category | Caught Pre-commit | Caught CI | Escaped |
|----------|-------------------|-----------|---------|
| Security | 15 | 8 | 0 |
| Quality | 30 | 12 | 2 |
| Resilience | 5 | 3 | 1 |

### Trends
- Gate failure rate: ↓ 15% (developers learning)
- New debt introduced: ↓ 22%
- Escaped debt: ↓ 50%
```

---

## Continuous Improvement

### Quarterly Gate Review

1. **Effectiveness Analysis**
   - What debt escaped the gates?
   - What valid PRs were blocked incorrectly?
   - What's the developer experience?

2. **Gate Tuning**
   - Add new checks for escaped debt patterns
   - Remove/adjust overly strict checks
   - Update thresholds based on data

3. **Documentation Update**
   - Update prevention patterns
   - Add examples of caught issues
   - Improve error messages
